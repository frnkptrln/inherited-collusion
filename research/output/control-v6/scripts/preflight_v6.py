"""Read-only account/job/pricing check; deliberately never retain auth secrets."""
from pathlib import Path
import subprocess,json,urllib.request,datetime,collections
ROOT=Path(__file__).resolve().parents[1]
HF='/home/user/projects/collusion-sprint/.venv/bin/hf'
def cli(args):
    p=subprocess.run([HF,*args],capture_output=True,text=True,timeout=90)
    if p.returncode: raise RuntimeError('Read-only CLI failed: '+args[0])
    return p.stdout
auth=cli(['auth','whoami'])
jobs=json.loads(cli(['jobs','ls','-a','--limit','0','--json']))
if isinstance(jobs,dict):
    jobs=jobs.get('jobs',jobs.get('data',[]))
counts=collections.Counter()
for j in jobs:
    value=j.get('status',{})
    if isinstance(value,dict):value=value.get('stage',value.get('status','unknown'))
    counts[str(value)]+=1
with urllib.request.urlopen('https://router.huggingface.co/v1/models',timeout=60) as r:
    data=json.load(r)
models=[]
for m in data['data']:
    if m['id'] in ('Qwen/Qwen3.6-35B-A3B','openai/gpt-oss-120b'):
        models.append({'id':m['id'],'providers':[p for p in m['providers'] if p['provider']=='deepinfra']})
assert len(models)==2 and all(m['providers'][0]['status']=='live' for m in models)
record={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'user_frnk_present':'frnk' in auth,'job_count':len(jobs),'status_counts':dict(counts),'no_jobs_started':True,'models':models,'source':'https://router.huggingface.co/v1/models'}
assert record['user_frnk_present']
p=ROOT/'evidence/preflight/hf-preflight.json'
assert not p.exists()
p.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
