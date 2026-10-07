"""Generated-file resources and bounded, short-lived download capabilities."""
import hashlib, hmac, secrets, time
from pathlib import Path
from urllib.parse import urlencode, quote
from .core import user_dir

MIME={'.pdf':'application/pdf','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.json':'application/json'}
PUBLIC_BASE=None
_KEY=secrets.token_bytes(32)

def export_path(user, filename):
    if Path(filename).name!=filename or Path(filename).suffix not in MIME:
        raise ValueError('Invalid generated filename')
    p=user_dir(user)/'exports'/filename
    if p.is_symlink() or not p.is_file() or p.stat().st_size>20*1024*1024:
        raise ValueError('Generated file unavailable; regenerate it')
    return p

def signature(user, filename, expires):
    p=export_path(user,filename)
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    return hmac.new(_KEY,f'{user}\n{filename}\n{expires}\n{digest}'.encode(),hashlib.sha256).hexdigest()

def valid_link(user, filename, expires, token):
    try:
        exp=int(expires)
        if not time.time()<=exp<=time.time()+901: return False
        return hmac.compare_digest(signature(user,filename,exp),token)
    except (ValueError,TypeError,OSError): return False

def deliver(user,result):
    files=[]
    for kind in ['pdf','docx','trace']:
        filename=result[kind]; p=export_path(user,filename)
        entry={'name':filename,'mime_type':MIME[p.suffix],'resource_uri':'career://exports/'+filename}
        if PUBLIC_BASE:
            expires=int(time.time())+900
            entry['download_url']=PUBLIC_BASE+'/files/'+quote(filename)+'?'+urlencode({'expires':expires,'token':signature(user,filename,expires)})
            entry['expires_in_seconds']=900
        else: entry['local_path']=str(p.resolve())
        files.append(entry)
    result=dict(result,files=files)
    if PUBLIC_BASE: result.pop('directory',None)
    return result
