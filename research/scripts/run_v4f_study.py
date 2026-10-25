#!/usr/bin/env python3
"""Bounded V4F phase dispatcher. No retries; exact fixed ledger allocations only."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

# Fatal provider states still need later stages to reconstruct their cached
# valid prefix. The runner blocks all affected new dispatches itself.
FAILURES={'technical_validation_failed'}

def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def plan(project,ledger_path,protocol_path,stage,model=None,seeds=None):
    project,ledger_path,protocol_path=Path(project).resolve(),Path(ledger_path).resolve(),Path(protocol_path).resolve()
    ledger=read(ledger_path);freeze=read(ledger['freeze_record'])
    if freeze['ledger_sha256']!=sha(ledger_path):raise ValueError('Ledger changed after freeze')
    artifacts=freeze.get('artifacts',{})
    if artifacts.get(str(Path(__file__).resolve()))!=sha(__file__):raise ValueError('Dispatcher itself is not bound by the execution freeze')
    if any(not Path(p).is_absolute() or sha(p)!=value for p,value in artifacts.items()):raise ValueError('Frozen execution artifact changed')
    if stage=='prepare' and (model or seeds):raise ValueError('Preparation must include all18 allocations')
    if stage!='prepare' and not Path(ledger['preparation_manifest']).exists():raise ValueError('Finalize all18 preparations before execution')
    commands=[]
    for name,allocation in sorted(ledger['allocations'].items(),key=lambda item:(item[1]['seed'],item[0])):
        cohort=allocation.get('cohort',allocation.get('phase'))
        if stage=='qualification' and cohort!='qualification':continue
        if stage in ('probes','donors','all') and cohort!='main':continue
        if model and f'-{model}-' not in name:continue
        if seeds and allocation['seed'] not in seeds:continue
        root=ledger_path.parent/name;cfg=Path(allocation['config']);cfg=cfg if cfg.is_absolute() else project/cfg
        config=read(cfg)
        if config['source_run_id']!=allocation['source_run_id'] or config['budget_binding']!={'ledger':str(ledger_path),'run_id':name}:raise ValueError('Allocation configuration binding mismatch')
        summary=read(root/'summary.json') if (root/'summary.json').exists() else {}
        if stage!='prepare' and summary.get('status') in FAILURES:continue
        if stage=='all':
            seed=allocation['seed'];old=root/'original_reviews'/f's{seed}-annotations.recorded.json';new=root/'reviews'/f's{seed}-annotations.json'
            if not (old.exists() or new.exists()):continue
        cmd=[str(project/'.venv/bin/python'),'-B',str(project/'scripts/v4f_runner.py'),'prepare' if stage=='prepare' else 'run','--backend','hf','--approval',str(cfg),'--protocol',str(protocol_path),'--out',str(root),'--cohort',cohort,'--seed',str(allocation['seed'])]
        if stage=='prepare':cmd+=['--source',str(ledger_path.parent/allocation['source_run_id'])]
        else:cmd+=['--stage','probes' if stage=='qualification' else stage]
        commands.append((name,root,cmd))
    if stage=='prepare' and len(commands)!=18:raise ValueError('Exactly18 preparation commands are required')
    return commands

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--ledger',type=Path);parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--stage',choices=('prepare','qualification','probes','donors','all','status'),required=True)
    parser.add_argument('--model',choices=('qwen','gptoss'));parser.add_argument('--seeds',type=int,nargs='+');parser.add_argument('--max-parallel',type=int,default=8);parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args();ledger=args.ledger or args.project/'runs/phase4f-budget.json'
    if not 1<=args.max_parallel<=8 or args.seeds and (len(set(args.seeds))!=len(args.seeds) or any(s not in range(201,209) for s in args.seeds)):raise SystemExit('Use max-parallel1..8 and unique fixed main seeds201..208')
    if args.stage=='status':
        for name in sorted(read(ledger)['allocations']):
            path=ledger.parent/name/'summary.json';s=read(path) if path.exists() else {}
            print(json.dumps({'run':name,'status':s.get('status','not_started'),'inherited_calls':s.get('inherited_reserved_calls'),'new_calls':s.get('new_reserved_calls'),'episodes':s.get('episodes')}))
        return 0
    commands=plan(args.project,ledger,args.protocol,args.stage,args.model,args.seeds)
    if args.dry_run:
        for name,root,cmd in commands:print(json.dumps({'run':name,'command':cmd}))
        return 0
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    def execute(item):
        name,root,cmd=item;logs=root/'invocation_logs';logs.mkdir(parents=True,exist_ok=True)
        prefix=logs/f'{stamp}-{args.stage}'
        with Path(str(prefix)+'.stdout.log').open('x') as out,Path(str(prefix)+'.stderr.log').open('x') as err:
            completed=subprocess.run(cmd,cwd=args.project,stdout=out,stderr=err,check=False)
        Path(str(prefix)+'.result.json').write_text(json.dumps({'run':name,'at':stamp,'stage':args.stage,'returncode':completed.returncode,'command':cmd})+'\n')
        return name,completed.returncode
    bad=False
    with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
        futures=[pool.submit(execute,item) for item in commands]
        for future in as_completed(futures):
            name,code=future.result();print(json.dumps({'run':name,'returncode':code}),flush=True);bad|=code!=0
    return 2 if bad else 0
if __name__=='__main__':raise SystemExit(main())
