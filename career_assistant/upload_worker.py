import resource, json, sys, base64
from .core import extract
resource.setrlimit(resource.RLIMIT_CPU,(15,15))
try: resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
except (ValueError,OSError): pass
try:
    args=json.loads(sys.stdin.read(8*1024*1024+1))
    print(json.dumps(extract(args['filename'],base64.b64decode(args['data'],validate=True))))
except Exception:
    print(json.dumps({'error':'Invalid, unsupported or over-limit upload'}))
