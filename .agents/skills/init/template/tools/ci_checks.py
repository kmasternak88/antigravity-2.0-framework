#!/usr/bin/env python3
"""Run configured global checks on the CI candidate; no fabricated local approvals."""
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('gov',ROOT/'.governance/bin/gov.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
def main():
    g.validate();cfg=g.config();source=g.snapshot();reports=[]
    dest=ROOT/'.governance/evidence/ci';dest.mkdir(parents=True,exist_ok=True)
    for name in cfg['required_release_checks']:
        ck=cfg['checks'][name];started=time.time()
        try:
            r=subprocess.run(ck['argv'],cwd=ROOT,shell=False,capture_output=True,text=True,timeout=ck['timeout']);code=r.returncode;log=r.stdout+'\n'+r.stderr
        except subprocess.TimeoutExpired as e:
            code=124;log='TIMEOUT: '+str(e)
        path=dest/(name.replace('/','_')+'.log');path.write_text(g.redact(log),encoding='utf-8')
        reports.append({'check':name,'argv':ck['argv'],'exitCode':code,'seconds':time.time()-started,'log':str(path.relative_to(ROOT)),'logSha256':g.digest(path.read_bytes())})
    unchanged=source==g.snapshot()
    report={'status':'PASS' if unchanged and reports and all(x['exitCode']==0 for x in reports) else 'FAIL','sourceDigest':source,'specDigest':g.spec_hash(),'sourceUnchanged':unchanged,'checks':reports,'humanApproval':'MUST_BE_ENFORCED_BY_PROTECTED_REPOSITORY','deploymentAuthorization':False}
    (dest/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
