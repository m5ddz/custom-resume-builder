"""Build a source-only UV extension, never packaging private working data."""
import argparse, zipfile
from pathlib import Path

def build(output):
    root=Path(__file__).resolve().parents[1]
    paths=[root/name for name in ['manifest.json','pyproject.toml','README.md','SECURITY.md','LICENSE']]
    paths.extend((root/'career_assistant').glob('*.py'))
    paths.extend((root/'career_assistant').glob('*.html'))
    paths.extend((root/'career_assistant').glob('*.js'))
    paths.extend((root/'career_assistant').glob('*.css'))
    paths.append(root/'server/claude_entry.py')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for path in paths: z.write(path,path.relative_to(root))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);args=p.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True);build(args.output)
