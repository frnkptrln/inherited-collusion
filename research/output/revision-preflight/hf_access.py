import subprocess,json,collections,datetime
from pathlib import Path
hf='/home/user/projects/collusion-sprint/.venv/bin/hf'
def cli(args):
 p=subprocess.run([hf,*args],capture_output=True,text=True,timeout=90)
 if p.returncode: raise RuntimeError('Read-only CLI failed: '+args[0])
 return p.stdout
auth=cli(['auth','whoami'])
jobs=json.loads(cli(['jobs','ls','-a','--limit','0','--json']))
if isinstance(jobs,dict): jobs=jobs.get('jobs',jobs.get('data',[]))
counts=collections.Counter()
for j in jobs:
 s=j.get('status','unknown')
 if isinstance(s,dict): s=s.get('stage',s.get('status','unknown'))
 counts[str(s)]+=1
record={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authenticated_user_frnk': 'frnk' in auth,'job_count':len(jobs),'job_status_counts':dict(counts),'jobs_started':0,'tokens_recorded':False}
assert record['authenticated_user_frnk']
out=Path(__file__).with_name('hf-access.json')
with out.open('x') as f: json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(record))
