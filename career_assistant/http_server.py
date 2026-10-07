"""OAuth-protected, single-owner HTTP MCP. Run behind owner-controlled HTTPS."""
import argparse, hmac, os, time
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from starlette.responses import HTMLResponse, RedirectResponse, Response, FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.routing import Route
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import TransportSecuritySettings
from . import delivery
from .oauth import OwnerOAuth
from .core import root
from .chat_workflow import INSTRUCTIONS

class OAuthBodyLimit:
    """Bound even chunked OAuth forms before the SDK parses them."""
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']=='http' and scope['method']=='POST' and scope['path']!='/mcp':
            chunks=[]; total=0
            while True:
                message=await receive()
                if message['type']=='http.disconnect': return
                total+=len(message.get('body',b''))
                if total>4096:
                    await Response('Request too large',413)(scope,receive,send); return
                chunks.append(message.get('body',b''))
                if not message.get('more_body',False): break
            pending=True
            async def bounded_receive():
                nonlocal pending
                if pending:
                    pending=False
                    return {'type':'http.request','body':b''.join(chunks),'more_body':False}
                return await receive()
            return await self.app(scope,bounded_receive,send)
        return await self.app(scope,receive,send)

def validate_base(value):
    u=urlsplit(value)
    if u.username or u.password or u.query or u.fragment or u.path not in ['', '/'] or not u.hostname:
        raise ValueError('Base URL must be an HTTPS origin without path, credentials or query')
    if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ['127.0.0.1','localhost','::1']):
        raise ValueError('HTTPS required, except loopback testing')
    return value.rstrip('/')

def create_app(base, secret):
    from . import mcp_server as local
    base=validate_base(base)
    if len(secret)<32: raise ValueError('Use a random pairing secret with at least 32 characters')
    provider=OwnerOAuth(base,local.USER)
    server=FastMCP('Career Memory Assistant',instructions=INSTRUCTIONS,
        auth_server_provider=provider,
        auth=AuthSettings(issuer_url=base,resource_server_url=base+'/mcp',validate_token_resource=True,
            required_scopes=['career'],client_registration_options=ClientRegistrationOptions(
                enabled=True,valid_scopes=['career'],default_scopes=['career']),
            revocation_options=RevocationOptions(enabled=True)),
        stateless_http=True,json_response=True,max_request_body_size=8*1024*1024,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=[urlsplit(base).netloc,'127.0.0.1:*','localhost:*'],allowed_origins=[base]))
    local.register_chat_tools(server)
    delivery.PUBLIC_BASE=base
    failures=[]
    headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer',
        'Content-Security-Policy':"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"}

    @server.custom_route('/pair',methods=['GET','POST'])
    async def pair(request):
        provider.prune()
        if request.method=='GET':
            handle=request.query_params.get('request','')
            pending=provider.pending.get(handle)
            if not pending: return Response('Pairing expired. Reconnect in your chat client.',400,headers=headers)
            client=pending[0]
            label=escape(client.client_name or client.client_id or 'chat client')
            callback=escape(str(pending[1].redirect_uri))
            return HTMLResponse('<!doctype html><title>Connect Career Memory</title><h1>Connect '+label+'</h1>'
                '<p>This grants access to your private career bank and generated resumes. Only approve a connection you started.</p>'
                '<p>Client callback: '+callback+'</p>'
                '<p>Enter the pairing secret from the private file created during setup. Never put it in chat.</p>'
                '<form method="post"><input type="hidden" name="request" value="'+escape(handle,quote=True)+'">'
                '<label>Pairing secret <input type="password" name="secret" required autocomplete="off"></label>'
                '<button>Approve connection</button></form>',headers=headers)
        if request.headers.get('origin')!=base: return Response('Origin blocked',403,headers=headers)
        if int(request.headers.get('content-length','0'))>4096: return Response('Request too large',413,headers=headers)
        body=await request.body()
        if len(body)>4096: return Response('Request too large',413,headers=headers)
        form=parse_qs(body.decode('utf-8',errors='replace'))
        handle=form.get('request',[''])[0]; supplied=form.get('secret',[''])[0]
        failures[:]=[t for t in failures if t>time.time()-60]
        if len(failures)>=10: return Response('Wait one minute and reconnect.',429,headers=headers)
        if handle not in provider.pending or not hmac.compare_digest(secret.encode(),supplied.encode()):
            failures.append(time.time()); return Response('Connection not approved. Check your pairing secret.',403,headers=headers)
        return RedirectResponse(provider.approve(handle),303,headers=headers)

    @server.custom_route('/files/{filename}',methods=['GET'])
    async def file(request):
        name=request.path_params['filename']
        if not delivery.valid_link(local.USER,name,request.query_params.get('expires'),request.query_params.get('token','')):
            return Response('Link expired or unavailable. Ask your assistant to generate the resume again.',403,headers=headers)
        p=delivery.export_path(local.USER,name)
        return FileResponse(p,media_type=delivery.MIME[p.suffix],filename=name,headers=headers)

    app=server.streamable_http_app()
    # SDK 1.30's public-client revoke form requires client_secret even when
    # the registered authentication method is 'none'. Accept the standard
    # optional field while retaining the SDK's client authentication.
    async def revoke(request):
        from mcp.server.auth.middleware.client_auth import ClientAuthenticator, AuthenticationError
        try:
            client=await ClientAuthenticator(provider).authenticate_request(request)
            form=await request.form()
            if not form.get('token'): return Response('Token required',400,headers={'Cache-Control':'no-store'})
            token=await provider.load_access_token(str(form.get('token','')))
            if not token: token=await provider.load_refresh_token(client,str(form.get('token','')))
            if token and token.client_id==client.client_id: await provider.revoke_token(token)
            return Response(status_code=200,headers={'Cache-Control':'no-store'})
        except AuthenticationError:
            return Response('Invalid client',401,headers={'Cache-Control':'no-store'})
    app.routes[:]=[Route('/revoke',revoke,methods=['POST']) if r.path=='/revoke' else r for r in app.routes]
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=[urlsplit(base).hostname,'127.0.0.1','localhost'])
    app.add_middleware(OAuthBodyLimit)
    app.state.oauth=provider
    return app

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',required=True,help='User-reachable HTTPS origin; /mcp is added automatically')
    p.add_argument('--port',type=int,default=8767)
    p.add_argument('--secret-file',type=Path)
    args=p.parse_args()
    args.secret_file=args.secret_file or root()/'pairing-secret'
    if not args.secret_file.is_file(): p.error('Run career-assistant-setup pairing first')
    if os.name!='nt' and args.secret_file.stat().st_mode & 0o077: p.error('Pairing secret file must be private (chmod 600)')
    app=create_app(args.base_url,args.secret_file.read_text().strip())
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False,log_level='warning',proxy_headers=False)

if __name__=='__main__': main()
