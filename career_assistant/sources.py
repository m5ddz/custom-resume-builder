"""Bounded public HTTPS fetches with pinned DNS and no redirects or proxies."""
import http.client, socket, ssl, ipaddress, json, re, asyncio, os
from urllib.parse import urlsplit, quote
from datetime import datetime, timezone, timedelta

MAX_RESPONSE=2*1024*1024

def public_fetch(url):
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443): raise ValueError('Public HTTPS URLs on port 443 only')
    ips={r[4][0] for r in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)}
    if not ips or any(not ipaddress.ip_address(i).is_global for i in ips): raise ValueError('Private or reserved network blocked')
    conn=http.client.HTTPSConnection(u.hostname,443,timeout=12)
    sock=socket.create_connection((sorted(ips)[0],443),timeout=12)
    conn.sock=ssl.create_default_context().wrap_socket(sock,server_hostname=u.hostname)
    try:
        conn.request('GET',(u.path or '/')+('?' + u.query if u.query else ''),headers={'User-Agent':'CareerMemoryAssistant/0.1','Accept':'application/json,text/html','Accept-Encoding':'identity'})
        r=conn.getresponse()
        if r.status!=200: raise ValueError('Source unavailable; redirects are not followed')
        data=r.read(MAX_RESPONSE+1)
        if len(data)>MAX_RESPONSE: raise ValueError('Source response too large')
        return data.decode('utf-8')
    finally: conn.close()

def instant(value):
    if not isinstance(value,str): raise ValueError('Unknown timestamp')
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('Timestamp needs timezone')
    return d.astimezone(timezone.utc)

def strict(jobs, now=None):
    now=now or datetime.now(timezone.utc); seen=set(); good=[]; rejected=[]
    for j in jobs:
        key=j.get('url','').split('?')[0].rstrip('/')
        reason=None
        try:
            pub=instant(j['published_at']); checked=instant(j['checked_at'])
            if not now-timedelta(days=14)<=pub<=now: reason='outside 14-day publication window'
            elif not j.get('publication_evidence') or j.get('date_kind')!='published': reason='publication not evidenced'
            elif j.get('active') is not True or not now-timedelta(minutes=15)<=checked<=now: reason='active listing not freshly verified'
        except (KeyError,ValueError,TypeError): reason='unknown publication or verification date'
        if not key: reason='missing source URL'
        if key in seen: continue
        seen.add(key)
        (rejected if reason else good).append(dict(j,**({'exclusion_reason':reason} if reason else {})))
    return {'strict_results':good,'excluded':rejected,'window_days':14}

def jsonld_jobs(url):
    body=public_fetch(url); now=datetime.now(timezone.utc); result=[]
    def walk(v):
        if isinstance(v,list):
            for x in v: walk(x)
        elif isinstance(v,dict):
            if v.get('@type')=='JobPosting':
                expiry=v.get('validThrough'); active=False
                try: active=bool(expiry and instant(expiry)>now)
                except ValueError: pass
                result.append({'title':v.get('title',''),'company':v.get('hiringOrganization',{}).get('name',''),'url':url,'description':v.get('description',''),'published_at':v.get('datePosted'),'date_kind':'published','publication_evidence':{'url':url,'field':'JobPosting.datePosted','value':v.get('datePosted')},'active':active,'checked_at':now.isoformat(),'updated_at':v.get('dateModified'),'reposted_at':None,'first_discovered_at':now.isoformat()})
            if '@graph' in v: walk(v['@graph'])
    for block in re.findall(r'<script[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>',body,re.S|re.I):
        try: walk(json.loads(block))
        except json.JSONDecodeError: pass
    return result

def employer_jobs(provider, board):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',board): raise ValueError('Invalid employer board')
    now=datetime.now(timezone.utc).isoformat()
    if provider=='greenhouse':
        data=json.loads(public_fetch(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs'))['jobs']
        return [dict(title=j['title'],company=board,url=j['absolute_url'],description=j.get('content',''),published_at=None,updated_at=j.get('updated_at'),date_kind='updated',publication_evidence=None,active=True,checked_at=now,first_discovered_at=now,reposted_at=None) for j in data[:100]]
    if provider=='lever':
        data=json.loads(public_fetch(f'https://api.lever.co/v0/postings/{board}?mode=json'))
        return [dict(title=j['text'],company=board,url=j['hostedUrl'],description=j.get('descriptionPlain',''),published_at=None,date_kind='unknown',publication_evidence=None,active=True,checked_at=now,first_discovered_at=now,reposted_at=None) for j in data[:100]]
    raise ValueError('Choose greenhouse or lever')

class LinkedIn:
    ALLOWED={'search_jobs','get_job_details','get_company_profile','get_company_employees','search_people'}

    async def call(self, tool, arguments):
        if tool not in self.ALLOWED: raise ValueError('Read-only tool not allowed')
        async with self.session() as session:
            return await self.invoke(session,tool,arguments)

    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def session(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        config=json.loads(os.environ.get('CAREER_LINKEDIN_COMMAND','null'))
        if not isinstance(config,list) or not config or not all(isinstance(x,str) for x in config): raise ValueError('Set CAREER_LINKEDIN_COMMAND to your own MCP command JSON array')
        # Config is operator controlled, never accepted from HTTP or MCP arguments.
        with open(os.devnull,'w') as errlog:
            async with stdio_client(StdioServerParameters(command=config[0],args=config[1:]),errlog=errlog) as (r,w):
                async with ClientSession(r,w) as session:
                    await session.initialize()
                    yield session

    async def invoke(self, session, tool, arguments):
        if tool not in self.ALLOWED: raise ValueError('Read-only tool not allowed')
        available=await session.list_tools()
        if tool not in {t.name for t in available.tools}: raise ValueError('Required LinkedIn tool unavailable')
        result=await session.call_tool(tool,arguments)
        if result.isError: raise ValueError('LinkedIn tool failed; authentication may need user action')
        return result.model_dump(mode='json')

async def linkedin_jobs(keywords, location=''):
    client=LinkedIn()
    async with client.session() as session:
        found=await client.invoke(session,'search_jobs',{'keywords':keywords,'location':location,'date_posted':'past_month','max_pages':1,'sort_by':'date'})
        data=found.get('structuredContent')
        if not data:
            data=json.loads(next(c['text'] for c in found['content'] if c.get('type')=='text'))
        candidates=[]
        for id in data.get('job_ids',[])[:10]:
            detail=await client.invoke(session,'get_job_details',{'job_id':str(id)})
            candidates.append({'url':f'https://www.linkedin.com/jobs/view/{id}/','published_at':None,'date_kind':'unknown','active':None,'checked_at':datetime.now(timezone.utc).isoformat(),'untrusted_evidence':detail})
    return strict(candidates)

def research(urls, role=''):
    if len(urls)>5: raise ValueError('At most five public evidence pages')
    evidence=[]; people=[]
    for url in urls:
        body=public_fetch(url)
        clean=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',body,flags=re.S|re.I)
        text=re.sub('<[^>]+>',' ',clean); text=re.sub(r'\s+',' ',text).strip()
        evidence.append({'url':url,'excerpt':text[:2000],'retrieved_at':datetime.now(timezone.utc).isoformat(),'trusted':False})
        for block in re.findall(r'<script[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>',body,re.S|re.I):
            try:
                parsed=json.loads(block); nodes=parsed if isinstance(parsed,list) else parsed.get('@graph',[parsed])
                for p in nodes:
                    if p.get('@type')=='Person' and p.get('name') and p.get('jobTitle') and p.get('worksFor'):
                        overlap=set(re.findall(r'\w+',role.lower())) & set(re.findall(r'\w+',str(p['jobTitle']).lower()))
                        if overlap: people.append({'name':p['name'],'title':p['jobTitle'],'employer_evidence':p['worksFor'],'source':url,'relationship':'inferred possible teammate from role overlap; employment and team membership need manual verification'})
            except (ValueError,TypeError,AttributeError): pass
    return {'company_evidence':evidence,'possible_teammates':people,'teammate_status':'inferred candidates' if people else 'not found'}


def observe(user, jobs):
    """Persist first discovery and earliest evidenced publication, never reset age on update."""
    import sqlite3
    from .core import user_dir
    path=user_dir(user)/'observations.sqlite'
    db=sqlite3.connect(path); path.chmod(0o600)
    db.execute('CREATE TABLE IF NOT EXISTS jobs (url TEXT PRIMARY KEY, first_seen TEXT, published TEXT)')
    for j in jobs:
        url=j.get('url','').split('?')[0].rstrip('/')
        row=db.execute('SELECT first_seen,published FROM jobs WHERE url=?',(url,)).fetchone()
        first=row[0] if row else datetime.now(timezone.utc).isoformat()
        published=j.get('published_at')
        if row and row[1]:
            try:
                if published and instant(published)>instant(row[1]): j['reposted_at']=published
            except ValueError: pass
            published=row[1]
        j['first_discovered_at']=first
        # A changed date does not become a new original publication.
        if published != j.get('published_at'):
            j['published_at']=published
            j['publication_evidence']=None
        db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?)',(url,first,published if j.get('date_kind')=='published' else (row[1] if row else None)))
    db.commit();db.close()
    return jobs
