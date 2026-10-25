#!/usr/bin/env python3
"""Execute one frozen V4 stage, without retries or automatic annotation."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from inherited_collusion.storage import digest,read,atomic_json
import v4_runner as runner


def validate_freeze():
    freeze=read(ROOT/'docs/v4-freeze.json')
    _,package_hash,source_hash=runner.sources()
    if freeze['source_hash']!=source_hash or freeze['package_source_hash']!=package_hash:
        raise ValueError('V4 source changed after freeze')
    for relative,expected in freeze['artifacts'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Frozen V4 artifact changed: {relative}')
    ledger=read(ROOT/'runs/phase4-budget.json')
    for name,allocation in ledger['allocations'].items():
        config={**read(ROOT/allocation['config']),'backend':'hf'}
        runner.validate_budget_binding(ROOT/'runs'/name,config,[allocation['seed']],allocation['repeats'])
    return ledger,source_hash,digest(read(ROOT/'docs/v4-protocol.json'))


def eligible(name,allocation,stage,source_hash,protocol_hash):
    root=ROOT/'runs'/name
    config={**read(ROOT/allocation['config']),'backend':'hf'}
    if allocation['cohort']=='main':
        try: runner.validate_qualification(root,config,protocol_hash,source_hash)
        except (ValueError,KeyError,TypeError,FileNotFoundError) as error:return False,'qualification not eligible: '+type(error).__name__
    if (root/'summary.json').exists():
        summary=read(root/'summary.json')
        if summary.get('status') in ('technical_validation_failed','model_identity_mismatch','incomplete_generation','unresolved_provider_call','usage_validation_failed'):
            return False,summary['status']
    if stage=='all' and allocation['cohort']=='main':
        review=root/'reviews'/f"s{allocation['seed']}-annotations.json"
        if not review.exists():return False,'content annotation not completed'
    return True,'eligible'


def dispatch(name,allocation,stage):
    logdir=ROOT/'runs/v4-dispatch';logdir.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    prefix=logdir/f'{stamp}-{name}-{stage}'
    cmd=[str(ROOT/'.venv/bin/python'),'-B','scripts/v4_runner.py','run','--backend','hf','--approval',allocation['config'],'--protocol','docs/v4-protocol.json','--out',str(ROOT/'runs'/name),'--seeds',str(allocation['seed']),'--cohort',allocation['cohort'],'--stage',stage]
    atomic_json(prefix.with_suffix('.json'),{'started_at':stamp,'run_id':name,'command':cmd,'stage':stage})
    with prefix.with_suffix('.stdout.log').open('w') as out,prefix.with_suffix('.stderr.log').open('w') as err:
        process=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=err,check=False)
    summary=read(ROOT/'runs'/name/'summary.json') if (ROOT/'runs'/name/'summary.json').exists() else {}
    result={'run_id':name,'stage':stage,'returncode':process.returncode,'status':summary.get('status','no_summary'),'calls':summary.get('reserved_calls',0),'episodes':summary.get('episodes',0),'log_prefix':str(prefix)}
    atomic_json(prefix.with_suffix('.completed.json'),result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cohort',choices=('qualification','main'),required=True)
    p.add_argument('--stage',choices=('probes','donors','all'),required=True)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if not 1<=args.workers<=8:raise ValueError('Use1..8 workers')
    if args.cohort=='qualification' and args.stage!='probes':raise ValueError('Qualification is six probes only')
    ledger,source_hash,protocol_hash=validate_freeze(); selected=[]
    for name,allocation in ledger['allocations'].items():
        if allocation['cohort']!=args.cohort:continue
        allowed,reason=eligible(name,allocation,args.stage,source_hash,protocol_hash)
        if allowed:selected.append((name,allocation))
        else:print(json.dumps({'run_id':name,'skipped':reason}),flush=True)
    print(json.dumps({'cohort':args.cohort,'stage':args.stage,'eligible':len(selected),'execute':args.execute}),flush=True)
    if not args.execute:return
    with (ROOT/'runs/.v4-dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(dispatch,name,allocation,args.stage) for name,allocation in selected]
            for future in as_completed(futures):print(json.dumps(future.result()),flush=True)

if __name__=='__main__':main()
