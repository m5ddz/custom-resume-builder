"""Isolated browser QA. Only reserved qa.example URLs use synthetic fixtures."""
import os,json
from datetime import datetime,timezone,timedelta
os.environ['CAREER_DATA_DIR']=os.path.abspath('work/qa-private')
from career_assistant import sources
original=sources.public_fetch
from pathlib import Path
clock=Path('work/qa-fixture-clock.txt')
clock.parent.mkdir(exist_ok=True)
if not clock.exists():clock.write_text(datetime.now(timezone.utc).isoformat())
now=datetime.fromisoformat(clock.read_text())
def fetch(url):
    if url=='https://qa.example/team':
        return '<h1>Fictional Example Company</h1><p>Product marketing team</p><script type="application/ld+json">'+json.dumps({'@type':'Person','name':'Alex Example','jobTitle':'Product Marketing Lead','worksFor':{'name':'Example Company'}})+'</script>'
    if url.startswith('https://qa.example/job-'):
        key=url.rsplit('-',1)[1]
        pub={'new':now-timedelta(days=2),'old':now-timedelta(days=20),'closed':now-timedelta(days=1)}.get(key)
        obj={'@type':'JobPosting','title':'Synthetic '+key+' Product Manager','hiringOrganization':{'name':'Example Company'},'validThrough':(now+timedelta(days=10) if key!='closed' else now-timedelta(days=1)).isoformat()}
        if pub:obj['datePosted']=pub.isoformat()
        else:obj['dateModified']=now.isoformat()
        return '<script type="application/ld+json">'+json.dumps(obj)+'</script>'
    return original(url)
sources.public_fetch=fetch
from career_assistant.web import main
if __name__=='__main__':main()
