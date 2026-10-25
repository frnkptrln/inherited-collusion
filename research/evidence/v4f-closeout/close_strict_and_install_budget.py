"""Called only after the original V4 dispatcher has exited; never dispatches a model."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,os,subprocess
from contextlib import ExitStack

ROOT=Path('/home/user/projects/collusion-sprint')
STAGE=Path('/tmp/collusion-phase4f')
def now():return datetime.now(timezone.utc).isoformat()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,indent=2)+'\n').encode()
def newfile(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(content)

def main():
    processes=subprocess.run(['ps','-eo','pid=,args='],check=True,capture_output=True,text=True).stdout.splitlines()
    active=[line for line in processes if ('scripts/v4_runner.py run' in line or 'scripts/run_v4_study.py ' in line)]
    if active:raise RuntimeError('Strict V4 process still active; no files changed')
    with ExitStack() as run_locks, (ROOT/'runs/.v4-dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledgerpath=ROOT/'runs/phase4-budget.json';original_bytes=ledgerpath.read_bytes();original=json.loads(original_bytes)
        freeze=json.loads((ROOT/'docs/v4-freeze.json').read_text())
        if sha(original_bytes)!=freeze['artifacts']['runs/phase4-budget.json']:raise RuntimeError('Original ledger differs from its frozen hash')
        for relative,expected_hash in freeze['artifacts'].items():
            if sha((ROOT/relative).read_bytes())!=expected_hash:raise RuntimeError('Changed strict frozen artifact: '+relative)
        for run_id in original['allocations']:
            run_lock=run_locks.enter_context((ROOT/'runs'/run_id/'.lock').open('r'))
            fcntl.flock(run_lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        # Held through inventory and retirement; direct original runners need exclusive locks.
        newledger=json.loads((STAGE/'phase4f-budget.json').read_text())
        expected={name.replace('v4-','v4f-',1):name for name in original['allocations']}
        if set(newledger['allocations'])!=set(expected):raise RuntimeError('Continuation does not preserve every original allocation')
        for name,source in expected.items():
            a=newledger['allocations'][name];old=original['allocations'][source]
            if a['source_run_id']!=source or any(a[k]!=old[k] for k in ['cohort','seed','repeats','model','max_total_usd']):raise RuntimeError('Changed fixed design/ceiling')
            expected_config=json.loads((ROOT/old['config']).read_text())
            expected_config['source_run_id']=source
            if 'qualification_run_id' in expected_config:expected_config['qualification_run_id']=expected_config['qualification_run_id'].replace('v4-','v4f-',1)
            expected_config['budget_binding']={'ledger':str(ROOT/'runs/phase4f-budget.json'),'run_id':name}
            if json.loads((STAGE/'configs'/f'{name}.json').read_text())!=expected_config:raise RuntimeError('Changed continuation request configuration')
        if any(newledger[k]!=original[k] for k in ['authorized_total_usd','historical_allocated_usd','phase_max_usd']):raise RuntimeError('Changed global ceiling')
        archive=ROOT/'evidence/v4f-closeout/phase4-budget.original.json'
        inventory_path=ROOT/'evidence/v4f-closeout/strict-final-inventory.json'
        closepath=ROOT/'docs/v4-strict-closeout-record.json';newledgerpath=ROOT/'runs/phase4f-budget.json'
        destinations=[archive,inventory_path,closepath,newledgerpath]+[ROOT/a['config'] for a in newledger['allocations'].values()]
        if any(p.exists() for p in destinations):raise RuntimeError('Refuse repeated closeout or overwrite')
        started=now();files={};runs=[]
        for name,a in original['allocations'].items():
            folder=ROOT/'runs'/name
            for p in sorted(folder.rglob('*')):
                if p.is_file() and not p.is_symlink() and p.suffix not in ('.pyc','.lock') and not any(x.startswith('.') or x=='__pycache__' for x in p.relative_to(folder).parts):
                    b=p.read_bytes();files[str(p.relative_to(ROOT))]={'sha256':sha(b),'bytes':len(b)}
            requests=list((folder/'calls').glob('*/request.json'));responses=list((folder/'calls').glob('*/response.json'))
            config=json.loads((ROOT/a['config']).read_text());summary=json.loads((folder/'summary.json').read_text())
            episode_statuses={}
            for p in (folder/'episodes').glob('*.json'):
                status=json.loads(p.read_text())['status'];episode_statuses[status]=episode_statuses.get(status,0)+1
            runs.append({'run_id':name,'calls':len(requests),'responses':len(responses),'reserved_usd':len(requests)*config['reserved_usd_per_call'],'never_requested_slots':config['max_calls']-len(requests),'summary_status':summary['status'],'episode_statuses':episode_statuses})
        finished=now()
        inventory={'snapshot_started_at':started,'snapshot_finished_at':finished,'strict_v4_finished':True,'files':files,'runs':runs,'no_effect_aggregates_inspected':True}
        inventory_bytes=encode(inventory)
        retired=json.loads(original_bytes)
        for a in retired['allocations'].values():a['status']='retired_consolidated_into_v4f'
        retired.update(retired_at=finished,replacement_ledger=str(newledgerpath),retirement_reason='Consolidated unique original+continuation call slots; no duplicated reserve or resampling. Original ledger archived.')
        retired_bytes=encode(retired)
        closure={'closed_at':finished,'strict_v4_finished':True,'source_run_ids':list(original['allocations']),
                 'original_ledger_sha256':sha(original_bytes),'retired_ledger_sha256':sha(retired_bytes),
                 'original_ledger_archive':str(archive),'strict_final_inventory':str(inventory_path),'strict_final_inventory_sha256':sha(inventory_bytes),
                 'original_unique_calls':sum(r['calls'] for r in runs),'maximum_remaining_unique_calls':sum(r['never_requested_slots'] for r in runs),
                 'maximum_total_unique_calls':1388,'consolidated_phase_ceiling_usd':8.328,'historical_allocated_usd':1.594,'total_active_allocation_usd':9.922,
                 'new_calls_authorized_by_original_discretionary_budget':True,'no_effect_aggregates_inspected_at_closeout':True,
                 'note':'Strict run directories are unchanged. Consolidated V4F ceiling includes all original dispatched calls; estimates must not add strict and reused continuation costs twice.'}
        newfile(archive,original_bytes);newfile(inventory_path,inventory_bytes);newfile(closepath,encode(closure))
        for name,a in newledger['allocations'].items():newfile(ROOT/a['config'],(STAGE/'configs'/f'{name}.json').read_bytes())
        temporary=ledgerpath.with_name('phase4-budget.retired.tmp')
        newfile(temporary,retired_bytes);os.replace(temporary,ledgerpath)
        newfile(newledgerpath,(STAGE/'phase4f-budget.json').read_bytes())
        print(json.dumps({'closed_at':finished,'strict_calls':closure['original_unique_calls'],'maximum_new_calls':closure['maximum_remaining_unique_calls'],'total_unique_limit':1388,'total_active_ceiling_usd':9.922,'inventory_sha256':sha(inventory_bytes)}))

if __name__=='__main__':main()
