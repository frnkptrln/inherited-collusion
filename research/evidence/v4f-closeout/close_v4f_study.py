"""After all dispatchers exit, seal the final V4F state without altering its ledger."""
import fcntl,hashlib,json,shlex,subprocess
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
ROOT=Path('/home/user/projects/collusion-sprint')
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(x):return (json.dumps(x,indent=2)+'\n').encode()
def require_no_active_dispatchers():
    rows=subprocess.run(['ps','-eo','args='],check=True,capture_output=True,text=True).stdout.splitlines()
    for row in rows:
        try:parts=shlex.split(row)
        except ValueError:continue
        if any(Path(part).name in ('run_v4f_study.py','v4f_runner.py') for part in parts):
            raise RuntimeError('V4F dispatcher/runner process still active; closure refused')
def main():
    require_no_active_dispatchers()
    ledgerpath=ROOT/'runs/phase4f-budget.json';ledger=json.loads(ledgerpath.read_text());freeze=json.loads((ROOT/'docs/v4f-freeze.json').read_text())
    freeze_sha=sha(ROOT/'docs/v4f-freeze.json')
    if len(ledger['allocations'])!=18:raise RuntimeError('Closure requires all18 fixed allocations')
    inventory_path=ROOT/'evidence/v4f-closeout/amended-final-inventory.json';record_path=ROOT/'docs/v4f-closeout-record.json'
    if inventory_path.exists() or record_path.exists():raise RuntimeError('Refuse repeated closure')
    if sha(ledgerpath)!=freeze['ledger_sha256']:raise RuntimeError('Frozen ledger changed')
    for path,h in freeze['artifacts'].items():
        if sha(Path(path))!=h:raise RuntimeError('Frozen artifact changed: '+path)
    with ExitStack() as locks:
        for name in sorted(ledger['allocations']):
            stream=locks.enter_context((ROOT/'runs'/name/'.lock').open('r'));fcntl.flock(stream,fcntl.LOCK_SH|fcntl.LOCK_NB)
        require_no_active_dispatchers()
        started=now();files={};runs=[]
        for name,a in sorted(ledger['allocations'].items()):
            folder=ROOT/'runs'/name;s=json.loads((folder/'summary.json').read_text())
            if s['status'] not in ('completed','technical_validation_failed','unresolved_provider_call','model_identity_mismatch','incomplete_generation','usage_validation_failed'):
                raise RuntimeError('Nonterminal case status: '+name+' '+s['status'])
            cfg=Path(a['config']);cfg=cfg if cfg.is_absolute() else ROOT/cfg;config=json.loads(cfg.read_text())
            requests=list((folder/'calls').glob('*/request.json'));responses=list((folder/'calls').glob('*/response.json'))
            if len(requests)>config['max_calls']:raise RuntimeError('Fixed call limit exceeded')
            request_ids={p.parent.name for p in requests};response_ids={p.parent.name for p in responses}
            if not response_ids<=request_ids:raise RuntimeError('Response without reserved request: '+name)
            provenance=json.loads((folder/'source_provenance.json').read_text())
            inherited=sum('request.json' in files for files in provenance['copied_calls'].values())
            if s['reserved_calls']!=len(requests) or s['responses']!=len(responses) or s['inherited_reserved_calls']!=inherited or s['new_reserved_calls']!=len(requests)-inherited:
                raise RuntimeError('Final summary call counts differ from immutable files: '+name)
            statuses={}
            for path in (folder/'episodes').glob('*.json'):
                status=json.loads(path.read_text())['status'];statuses[status]=statuses.get(status,0)+1
            for p in sorted(folder.rglob('*')):
                if p.is_symlink():raise RuntimeError('Symlink in research run')
                if p.is_file() and p.suffix not in ('.pyc','.lock') and not any(x.startswith('.') or x=='__pycache__' for x in p.relative_to(folder).parts):
                    files[str(p.relative_to(ROOT))]={'sha256':sha(p),'bytes':p.stat().st_size}
            runs.append({'run_id':name,'source_run_id':a['source_run_id'],'status':s['status'],'requests':len(requests),'responses':len(responses),'inherited_requests':s['inherited_reserved_calls'],'new_requests':len(requests)-s['inherited_reserved_calls'],'episode_statuses':statuses,'unrequested_slots':config['max_calls']-len(requests)})
        require_no_active_dispatchers()
        if sha(ledgerpath)!=freeze['ledger_sha256'] or sha(ROOT/'docs/v4f-freeze.json')!=freeze_sha:raise RuntimeError('Ledger/freeze changed during snapshot')
        for path,h in freeze['artifacts'].items():
            if sha(Path(path))!=h:raise RuntimeError('Frozen artifact changed during snapshot: '+path)
        ended=now();inventory={'snapshot_started_at':started,'snapshot_finished_at':ended,'all_run_locks_held_shared':True,'files':files,'runs':runs}
        payload=encode(inventory);inventory_path.parent.mkdir(parents=True,exist_ok=True)
        with inventory_path.open('xb') as f:f.write(payload)
        record={'closed_at':ended,'all_dispatchers_confirmed_finished_by_operator':True,'no_dispatcher_or_runner_process_observed':True,'all_run_locks_verified_idle':True,'dataset':'V4F post-start format amendment','run_count':len(runs),'unique_requests_including_v4_once':sum(r['requests'] for r in runs),'returned_responses':sum(r['responses'] for r in runs),'new_v4f_requests':sum(r['new_requests'] for r in runs),'inherited_v4_requests':sum(r['inherited_requests'] for r in runs),'inventory':str(inventory_path),'inventory_sha256':hashlib.sha256(payload).hexdigest(),'ledger_sha256':sha(ledgerpath),'freeze_sha256':freeze_sha,'frozen_artifacts_unchanged':True,'no_model_level_effect_aggregation_before_closure':True,'partial_case_visibility_disclosure':'docs/v4f-outcome-visibility-note.json','future_calls_policy':'No further calls are planned in these allocations. Frozen ledger retained verbatim for reproducibility; no retries or new slots authorized by this closure.'}
        with record_path.open('xb') as f:f.write(encode(record))
        print(json.dumps({k:record[k] for k in ('closed_at','unique_requests_including_v4_once','returned_responses','new_v4f_requests','inventory_sha256')}))
if __name__=='__main__':main()
