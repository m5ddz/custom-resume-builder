import os
from pathlib import Path
os.environ['CAREER_DATA_DIR']=str(Path('work/synthetic-private').resolve())
from career_assistant.core import Memory
from career_assistant.exports import export
m=Memory('synthetic');m.delete()
for f in [
 {'section':'Experience','employer':'Example Company','role':'Product Marketing Manager','dates':'2024 - 2026','location':'Remote','text':'Led product launch workshops with product and sales teams.'},
 {'section':'Experience','employer':'Example Company','role':'Product Marketing Manager','dates':'2024 - 2026','location':'Remote','text':'Created messaging guides and sales enablement materials for a software product.'},
 {'section':'Experience','employer':'Sample Studio','role':'Marketing Coordinator','dates':'2022 - 2024','location':'London','text':'Coordinated content calendars and customer interview notes.'},
 {'section':'Education','employer':'Fictional University','role':'BA Communications','dates':'2018 - 2022','text':'Completed a degree in communications.'},
 {'section':'Volunteering','employer':'Example Community Group','dates':'2023 - 2025','text':'Organized community writing workshops.'},
 {'section':'Skills','text':'Product messaging, launch planning, customer research, sales enablement.'},
 {'section':'Languages','text':'English: fluent. French: conversational.'}]:
 m.put(dict(f,approved=True,source='Synthetic demonstration; not a real person'),True)
print(export('synthetic',{'first_name':'Jane','last_name':'Smith','headline':'Product Marketing Manager','contact':'jane@example.com | London | example.com'},'Product Manager','Example Company','Product launch messaging sales enablement',True,output='outputs'))
