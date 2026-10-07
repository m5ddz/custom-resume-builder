"""Generate private connection configuration without changing client settings."""
import argparse, json, os, secrets, sys
from pathlib import Path
from .core import root

def write_new(path,text,private=True):
    path=Path(path).expanduser()
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600 if private else 0o644)
    with os.fdopen(fd,'w') as f: f.write(text)
    return path

def claude_config(data_dir=None):
    return {'mcpServers':{'career-memory':{'command':str(Path(sys.executable).resolve()),
        'args':['-m','career_assistant.mcp_server'],
        'env':{'CAREER_USER':'local','CAREER_DATA_DIR':str(Path(data_dir or root()).expanduser().resolve())}}}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('claude',help='Write a local Claude MCP configuration to merge into client settings')
    c.add_argument('--output',type=Path,required=True);c.add_argument('--data-dir',type=Path)
    a=sub.add_parser('pairing',help='Create a private random HTTP connection secret')
    a.add_argument('--output',type=Path)
    args=p.parse_args()
    try:
        if args.action=='claude':
            path=write_new(args.output,json.dumps(claude_config(args.data_dir),indent=2)+'\n')
            print(f'Connection configuration written to {path}. Merge the career-memory entry into your client MCP settings and restart the client.')
        else:
            path=write_new(args.output or root()/'pairing-secret',secrets.token_urlsafe(32)+'\n')
            print(f'Private pairing secret created at {path}. Enter it only on your server connection approval page, never in chat.')
    except FileExistsError: p.error('File already exists; choose a different output path. Existing settings/secrets were not overwritten.')

if __name__=='__main__': main()
