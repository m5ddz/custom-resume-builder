import asyncio, base64, json, subprocess, sys
from .core import Memory, QUESTIONS, tailored, user_dir
from .sources import strict, employer_jobs, jsonld_jobs, research, linkedin_jobs, LinkedIn
from .exports import export

OPERATIONS={
 'memory_list':'Inspect your private career facts',
 'memory_save':'Save or edit a fact with explicit consent and approval status',
 'memory_delete':'Delete one fact or all career memory',
 'memory_export':'Export all private career memory as JSON',
 'exports_delete':'Delete all generated private resume exports with confirmation',
 'questionnaire':'Get accomplishment interview questions',
 'resume_upload':'Extract an untrusted PDF DOCX or text upload without saving',
 'discover_jobs':'Find employer jobs and verify evidenced publication within 14 days',
 'research_company':'Read up to five cited public pages and identify possible teammates',
 'linkedin_read':'Call allowlisted read-only tools through your own LinkedIn MCP server',
 'tailor_resume':'Rank approved facts against a job without inventing claims',
 'export_resume':'Generate PDF DOCX and statement trace from approved facts'
}

def dispatch(user, operation, args):
    if not isinstance(args,dict): raise ValueError('Arguments must be an object')
    if operation in ['memory_list','memory_export']: return {'facts':Memory(user).list()}
    if operation=='memory_save': return Memory(user).put(args['fact'],args.get('consent',False))
    if operation=='memory_delete':
        if args.get('confirm') is not True: raise ValueError('Explicit delete confirmation required')
        return Memory(user).delete(args.get('id'))
    if operation=='exports_delete':
        if args.get('confirm') is not True: raise ValueError('Explicit delete confirmation required')
        import shutil
        p=user_dir(user)/'exports'
        if p.exists(): shutil.rmtree(p)
        return {'deleted':'all generated exports'}
    if operation=='questionnaire': return {'questions':QUESTIONS}
    if operation=='resume_upload':
        # Untrusted file parsers run in a separate process, with CPU/address-space bounds.
        payload=json.dumps(args)
        if len(payload)>8*1024*1024: raise ValueError('Upload too large')
        result=subprocess.run([sys.executable,'-m','career_assistant.upload_worker'],input=payload,capture_output=True,text=True,timeout=20)
        if result.returncode: raise ValueError('Upload could not be safely parsed')
        value=json.loads(result.stdout)
        if 'error' in value: raise ValueError(value['error'])
        return value
    if operation=='tailor_resume': return tailored(user,args['job'],args.get('limit',30))
    if operation=='export_resume': return export(user,args['profile'],args['title'],args['company'],args['job'],args.get('identity_approved',False))
    if operation=='research_company': return research(args['urls'],args.get('role',''))
    if operation=='linkedin_read': return asyncio.run(LinkedIn().call(args['tool'],args.get('arguments',{})))
    if operation=='discover_jobs':
        if args.get('provider')=='linkedin': return asyncio.run(linkedin_jobs(args['keywords'],args.get('location','')))
        jobs=employer_jobs(args['provider'],args['board']) if args.get('provider') in ['greenhouse','lever'] else []
        for url in args.get('urls',[])[:10]: jobs.extend(jsonld_jobs(url))
        from .sources import observe
        return strict(observe(user,jobs))
    raise ValueError('Unknown operation')
