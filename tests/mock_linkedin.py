import os
from mcp.server.fastmcp import FastMCP
m=FastMCP('Synthetic LinkedIn Protocol Fixture')
@m.tool()
def search_jobs(keywords: str, location: str='', date_posted: str='', max_pages: int=1, sort_by: str='date') -> dict:
    if os.environ.get('CAREER_TEST_BUSY')=='1': raise ValueError('Another LinkedIn MCP client is currently using the browser. Your saved session was not changed.')
    return {'job_ids':['synthetic-1']}
@m.tool()
def get_job_details(job_id: str) -> dict:
    return {'url':'https://example.org/jobs/synthetic-1','sections':{'job_posting':'Synthetic job · Reposted 1 day ago'}}
if __name__=='__main__':m.run()
