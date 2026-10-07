"""Single-owner OAuth with PKCE delegated to the MCP SDK.

Each installation owns one private bank. Connections require the operator's random
pairing secret. Credentials are in memory, bounded and expire; restart revokes them.
"""
import secrets, time
from urllib.parse import urlsplit
from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken, TokenError, AuthorizeError, RegistrationError
from mcp.shared.auth import OAuthToken

class OwnerOAuth:
    def __init__(self,base,user):
        self.base=base; self.user=user
        self.clients={}; self.pending={}; self.codes={}; self.access={}; self.refresh={}
        self.families={}

    def prune(self):
        now=time.time()
        for values in [self.pending,self.codes,self.access,self.refresh]:
            for key,value in list(values.items()):
                expiry=value[2] if isinstance(value,tuple) else value.expires_at
                if expiry is not None and expiry<=now: values.pop(key,None)
        for key,(a,r) in list(self.families.items()):
            if a not in self.access and r not in self.refresh: self.families.pop(key,None)

    async def get_client(self,client_id): return self.clients.get(client_id)

    async def register_client(self,client_info):
        if len(self.clients)>=32: raise RegistrationError('invalid_client_metadata','Client registration capacity reached; restart the owner server')
        # Redirects may go to HTTPS clients or loopback desktop clients only.
        for uri in client_info.redirect_uris:
            u=urlsplit(str(uri))
            if u.fragment or u.username or u.password or not (u.scheme=='https' or (u.scheme=='http' and u.hostname in ['127.0.0.1','localhost','::1'])):
                raise RegistrationError('invalid_redirect_uri','HTTPS or loopback redirect required')
        self.clients[client_info.client_id]=client_info

    async def authorize(self,client,params):
        self.prune()
        if params.resource not in [None,self.base+'/mcp']:
            raise AuthorizeError('invalid_request','Resource must be this career server')
        if len(self.pending)>=32: raise AuthorizeError('temporarily_unavailable','Too many pending requests')
        handle=secrets.token_urlsafe(32)
        self.pending[handle]=(client,params,time.time()+300)
        return self.base+'/pair?request='+handle

    def approve(self,handle):
        self.prune()
        entry=self.pending.pop(handle,None)
        if not entry: raise ValueError('Pairing request expired')
        client,params,_=entry
        code=secrets.token_urlsafe(32)
        self.codes[code]=AuthorizationCode(code=code,scopes=['career'],expires_at=time.time()+60,
            client_id=client.client_id,code_challenge=params.code_challenge,redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=self.base+'/mcp',subject=self.user)
        from mcp.server.auth.provider import construct_redirect_uri
        return construct_redirect_uri(str(params.redirect_uri),code=code,state=params.state)

    async def load_authorization_code(self,client,authorization_code):
        self.prune(); code=self.codes.get(authorization_code)
        return code if code and code.client_id==client.client_id else None

    def issue(self,client_id,scopes):
        self.prune()
        if len(self.access)>=64 or len(self.refresh)>=64: raise TokenError('invalid_grant','Connection capacity reached')
        a=secrets.token_urlsafe(32); r=secrets.token_urlsafe(32); now=int(time.time())
        self.access[a]=AccessToken(token=a,client_id=client_id,scopes=scopes,expires_at=now+3600,resource=self.base+'/mcp',subject=self.user)
        self.refresh[r]=RefreshToken(token=r,client_id=client_id,scopes=scopes,expires_at=now+86400,resource=self.base+'/mcp',subject=self.user)
        self.families[r]=(a,r)
        return OAuthToken(access_token=a,token_type='Bearer',expires_in=3600,refresh_token=r,scope=' '.join(scopes))

    async def exchange_authorization_code(self,client,authorization_code):
        code=await self.load_authorization_code(client,authorization_code.code)
        if not code: raise TokenError('invalid_grant','Code expired or used')
        self.codes.pop(code.code)
        return self.issue(client.client_id,code.scopes)

    async def load_refresh_token(self,client,refresh_token):
        self.prune(); token=self.refresh.get(refresh_token)
        return token if token and token.client_id==client.client_id else None

    async def exchange_refresh_token(self,client,refresh_token,scopes):
        token=await self.load_refresh_token(client,refresh_token.token)
        if not token or not set(scopes)<=set(token.scopes): raise TokenError('invalid_grant','Invalid refresh')
        await self.revoke_token(token)
        return self.issue(client.client_id,scopes)

    async def load_access_token(self,token):
        self.prune(); return self.access.get(token)

    async def revoke_token(self,token):
        for key,(a,r) in list(self.families.items()):
            if token.token in [a,r]:
                self.access.pop(a,None); self.refresh.pop(r,None); self.families.pop(key,None)
