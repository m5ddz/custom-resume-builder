import json, os, secrets, argparse, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
from .core import user_dir
from .service import dispatch, OPERATIONS

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass  # No URLs, tokens, personal data or document contents in logs.
    def valid_host(self): return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
    def authorized(self): return secrets.compare_digest(self.headers.get('Authorization',''), 'Bearer '+self.server.token)
    def reply(self,status,value,kind='application/json'):
        data=json.dumps(value).encode() if kind=='application/json' else value
        self.send_response(status); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if not self.valid_host(): return self.reply(403,{'error':'Host blocked'})
        path=urlsplit(self.path).path
        if path in ['/','/app.js','/style.css']:
            file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
            kind={'/':'text/html; charset=utf-8','/app.js':'text/javascript','/style.css':'text/css'}[path]
            return self.reply(200,Path(__file__).with_name(file).read_bytes(),kind)
        if not self.authorized(): return self.reply(401,{'error':'Authentication required'})
        if path=='/api/operations': return self.reply(200,OPERATIONS)
        if path=='/download':
            name=parse_qs(urlsplit(self.path).query).get('name',[''])[0]
            if Path(name).name!=name or Path(name).suffix not in ['.pdf','.docx','.json']: return self.reply(400,{'error':'Invalid file'})
            p=user_dir(self.server.user)/'exports'/name
            if not p.is_file(): return self.reply(404,{'error':'File not found'})
            return self.reply(200,p.read_bytes(),'application/octet-stream')
        self.reply(404,{'error':'Not found'})
    def do_POST(self):
        if not self.valid_host() or not self.authorized(): return self.reply(403,{'error':'Authentication required'})
        if self.headers.get('Origin') not in [None,f'http://127.0.0.1:{self.server.server_port}']: return self.reply(403,{'error':'Origin blocked'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=8*1024*1024: raise ValueError('Request exceeds limit')
            data=json.loads(self.rfile.read(n))
            if urlsplit(self.path).path!='/api/run': return self.reply(404,{'error':'Not found'})
            result=dispatch(self.server.user,data['operation'],data.get('args',{}))
            self.reply(200,result)
        except (ValueError,KeyError,TypeError) as e: self.reply(400,{'error':str(e)[:200]})
        except Exception: self.reply(502,{'error':'Operation failed. Check source availability, local dependency setup or authentication; private details are not logged.'})

def main():
    p=argparse.ArgumentParser(); p.add_argument('--port',type=int,default=8765); p.add_argument('--user',default='local'); a=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler); server.user=a.user; server.token=secrets.token_urlsafe(32)
    print(f'Open http://127.0.0.1:{a.port}/#{server.token}',flush=True)
    server.serve_forever()
if __name__=='__main__': main()
