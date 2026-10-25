#!/usr/bin/env python3
"""Stage the fixed v3 cases; no retries and no cloud jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from inherited_collusion.storage import digest, read, atomic_json
from inherited_collusion.v3_runner import validate_budget_binding


def validate_freeze():
    freeze=read(ROOT/'docs/v3-freeze.json')
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'inherited_collusion').glob('*.py'))}
    if digest(files)!=freeze['source_hash']: raise ValueError('Source changed after v3 freeze')
    for relative,expected in freeze['artifacts'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
            raise ValueError(f'Frozen artifact changed: {relative}')
    ledger=read(ROOT/'runs/phase3-budget.json')
    for run_id,allocation in ledger['allocations'].items():
        config={**read(ROOT/allocation['config']),'backend':'hf'}
        validate_budget_binding(ROOT/'runs'/run_id,config)
    return ledger


def eligible(run_id, allocation, stage):
    if allocation['phase']=='main':
        family='qwen' if 'Qwen/' in allocation['model'] else 'deepseek'
        pilot=ROOT/'runs'/f'v3-pilot-{family}-901'/'summary.json'
        if not pilot.exists() or not read(pilot).get('complete'):
            return False,'pilot not complete and reviewed'
    run=ROOT/'runs'/run_id
    if (run/'summary.json').exists():
        summary=read(run/'summary.json')
        if summary.get('status') in ('validation_failed','model_identity_mismatch','unresolved_provider_call','generation_limit_failure','incomplete_generation','model_blocked'):
            return False,summary['status']
    if stage=='all':
        review=run/'reviews'/f"s{allocation['seed']}-notes.json"
        recorded=review.with_name(review.stem+'.recorded.json')
        if not review.exists() and not recorded.exists(): return False,'note review missing'
    return True,'eligible'


def dispatch(run_id, allocation, stage):
    run=ROOT/'runs'/run_id
    run.mkdir(parents=True,exist_ok=True)
    logdir=ROOT/'runs'/'v3-dispatch'
    logdir.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    prefix=logdir/f'{stamp}-{run_id}-{stage}'
    command=[str(ROOT/'.venv/bin/python'),'-B','-m','inherited_collusion.v3_runner','run','--backend','hf','--approval',allocation['config'],'--protocol','docs/v3-protocol.json','--out',str(run),'--seeds',str(allocation['seed']),'--repeats',str(allocation['repeats']),'--stage',stage]
    atomic_json(prefix.with_suffix('.json'),{'run_id':run_id,'stage':stage,'command':command,'started_at':stamp,'status':'started'})
    with prefix.with_suffix('.stdout.log').open('w') as out,prefix.with_suffix('.stderr.log').open('w') as err:
        result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,check=False)
    summary=read(run/'summary.json') if (run/'summary.json').exists() else {}
    event={'run_id':run_id,'stage':stage,'returncode':result.returncode,'status':summary.get('status','no_summary'),'calls':summary.get('reserved_calls',0),'episodes':summary.get('episodes',0),'log_prefix':str(prefix)}
    atomic_json(prefix.with_suffix('.completed.json'),event)
    return event


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('pilot','main'),required=True)
    parser.add_argument('--stage',choices=('probes','donors','all'),required=True)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if not 1<=args.workers<=8: raise ValueError('Use 1..8 workers')
    ledger=validate_freeze()
    selected=[]
    for name,allocation in ledger['allocations'].items():
        if allocation['phase']!=args.phase: continue
        allow,reason=eligible(name,allocation,args.stage)
        if allow: selected.append((name,allocation))
        else: print(json.dumps({'run_id':name,'skipped':reason}),flush=True)
    print(json.dumps({'phase':args.phase,'stage':args.stage,'eligible':len(selected),'execute':args.execute}),flush=True)
    if not args.execute: return
    with (ROOT/'runs'/'.v3-dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(dispatch,name,allocation,args.stage) for name,allocation in selected]
            for future in as_completed(futures):
                print(json.dumps(future.result()),flush=True)


if __name__=='__main__': main()
