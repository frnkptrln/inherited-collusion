#!/usr/bin/env python3
"""Run fixed V5 case allocations with persistent CLI logs and no retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from inherited_collusion.storage import read,immutable_json,RunLock

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plan(project,stage,seeds=None,model=None):
    if (project/'docs/v5-closeout-record.json').exists():raise ValueError('V5 is permanently closed')
    ledger_path=project/'runs/phase5-budget.json';ledger=read(ledger_path)
    freeze=read(ledger['freeze_record'])
    if sha(ledger_path)!=freeze['ledger_sha256']:raise ValueError('Ledger changed after freeze')
    for p,h in freeze['artifacts'].items():
        path=Path(p) if Path(p).is_absolute() else project/p
        if sha(path)!=h:raise ValueError('Frozen input changed: '+p)
    if freeze['artifacts'].get('scripts/run_v5_study.py')!=sha(__file__):raise ValueError('Dispatcher is not frozen')
    commands=[]
    for name,entry in sorted(ledger['allocations'].items(),key=lambda x:(x[1]['seed'],x[0])):
        if seeds and entry['seed'] not in seeds:continue
        if model and f'-{model}-' not in name:continue
        config=project/entry['config'];root=project/'runs'/name
        command=[str(project/'.venv/bin/python'),'-B',str(project/'scripts/v5_runner.py'),'run','--backend','hf','--approval',str(config),'--protocol',str(project/'docs/v5-protocol.json'),'--out',str(root),'--seed',str(entry['seed']),'--stage',stage]
        commands.append((name,root,command))
    return commands

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--stage',choices=('probes','donors','all'),default='all');p.add_argument('--max-parallel',type=int,default=8);p.add_argument('--seeds',type=int,nargs='+');p.add_argument('--model',choices=('qwen','gptoss'));p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    if not 1<=a.max_parallel<=8:raise ValueError('Max parallel must be1..8')
    if a.seeds and (len(a.seeds)!=len(set(a.seeds)) or any(s not in range(301,307) for s in a.seeds)):raise ValueError('Only fixed unique seeds301..306')
    project=a.project.resolve()
    with RunLock(project/'runs/.v5-lifecycle'):
        items=plan(project,a.stage,a.seeds,a.model)
        if a.dry_run:
            print(json.dumps({'cases':len(items),'runs':[x[0] for x in items],'paid_calls':0}));return
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        def execute(item):
            name,root,command=item;folder=root/'invocation_logs';folder.mkdir(parents=True,exist_ok=True);prefix=folder/f'{stamp}-{a.stage}'
            immutable_json(Path(str(prefix)+'.start.json'),{'at':datetime.now(timezone.utc).isoformat(),'run':name,'command':command})
            with Path(str(prefix)+'.stdout.log').open('x') as out,Path(str(prefix)+'.stderr.log').open('x') as err:
                completed=subprocess.run(command,cwd=project,stdout=out,stderr=err,check=False)
            receipt={'run':name,'returncode':completed.returncode,'at':datetime.now(timezone.utc).isoformat()}
            immutable_json(Path(str(prefix)+'.result.json'),receipt);return receipt
        bad=False
        with ThreadPoolExecutor(max_workers=a.max_parallel) as pool:
            for future in as_completed([pool.submit(execute,item) for item in items]):
                receipt=future.result();print(json.dumps(receipt),flush=True);bad|=receipt['returncode']!=0
        raise SystemExit(2 if bad else 0)
if __name__=='__main__':main()
