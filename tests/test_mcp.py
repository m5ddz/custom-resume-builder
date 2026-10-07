import asyncio, tempfile, unittest, os, sys, json
from pathlib import Path
from unittest.mock import patch
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from career_assistant.sources import LinkedIn, linkedin_jobs

class MCPTests(unittest.TestCase):
 def test_server_real_protocol(self):
  async def check():
   with tempfile.TemporaryDirectory() as tmp:
    env=dict(os.environ,CAREER_DATA_DIR=tmp,CAREER_USER='protocol-test')
    async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','career_assistant.mcp_server'],env=env)) as (r,w):
     async with ClientSession(r,w) as s:
      await s.initialize(); tools=await s.list_tools()
      self.assertIn('export_resume',{t.name for t in tools.tools})
      r=await s.call_tool('career_memory',{'action':'save','arguments':{'fact':{'text':'Synthetic approved fact','approved':True},'consent':True}})
      self.assertFalse(r.isError)
      r=await s.call_tool('career_memory',{'action':'list','arguments':{}});self.assertIn('Synthetic approved fact',str(r))
  asyncio.run(check())
 def test_real_adapter_protocol_unknown_date_excluded(self):
  async def check():
   with patch.dict(os.environ,CAREER_LINKEDIN_COMMAND=json.dumps([sys.executable,str(Path('tests/mock_linkedin.py').resolve())])):
    r=await linkedin_jobs('synthetic')
    self.assertEqual(r['strict_results'],[]);self.assertEqual(len(r['excluded']),1)
    with self.assertRaises(ValueError):await LinkedIn().call('send_message',{})
  asyncio.run(check())
if __name__=='__main__':unittest.main()
