#!/usr/bin/env python3
"""Bounded fixed-cohort V7 dispatcher; one invocation per case, no retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inherited_collusion.storage import RunLock, immutable_json, read
import v7_runner as runner


def plan(project, model=None, seeds=None, python=None):
    project=Path(project).resolve()
    runner.require(project==runner.ROOT.resolve(), 'Use the dispatcher belonging to this V7 project')
    runner.require(not (project/'docs/v7-closeout-record.json').exists(), 'V7 is permanently closed')
    if seeds is not None:
        allowed=set(runner.CASES[model]) if model else set().union(*map(set,runner.CASES.values()))
        runner.require(len(seeds)==len(set(seeds)) and set(seeds)<=allowed, 'Seeds outside the fixed unique cohort')
    protocol=read(project/'docs/v7-protocol.json');items=[]
    for alias, cohort in runner.CASES.items():
        for seed in cohort:
            if model and model!=alias or seeds is not None and seed not in seeds:continue
            name=f'v7-{alias}-{seed}';root=project/'runs'/name;config_path=project/'configs'/f'{name}.json'
            config={**read(config_path),'backend':'hf'}
            runner.validate_barrier(root,config,protocol)
            runner.load_inputs(config)
            command=[os.path.abspath(python or sys.executable),'-B',str(project/'scripts/v7_runner.py'),'run',
                     '--backend','hf','--approval',str(config_path),'--protocol',str(project/'docs/v7-protocol.json'),'--out',str(root)]
            items.append((name,root,command))
    runner.require(bool(items), 'No fixed cases selected')
    return items


def execute(item, stamp, project):
    name,root,command=item;folder=root/'invocation_logs';folder.mkdir(parents=True,exist_ok=True)
    prefix=folder/(stamp+'-all')
    immutable_json(Path(str(prefix)+'.start.json'), {'at':runner.now(),'run':name,'command':command})
    with Path(str(prefix)+'.stdout.log').open('x') as out, Path(str(prefix)+'.stderr.log').open('x') as err:
        try:
            completed=subprocess.run(command,cwd=project,stdout=out,stderr=err,check=False)
            receipt={'run':name,'returncode':completed.returncode,'at':runner.now()}
        except OSError as error:
            receipt={'run':name,'returncode':None,'at':runner.now(),'launch_error_type':type(error).__name__}
    immutable_json(Path(str(prefix)+'.result.json'),receipt)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--model',choices=tuple(runner.CASES))
    p.add_argument('--seeds',type=int,nargs='+');p.add_argument('--max-parallel',type=int,default=4)
    p.add_argument('--python',type=Path);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    runner.require(1<=a.max_parallel<=4,'Parallel case limit must be1..4')
    project=a.project.resolve()
    with RunLock(project/'runs/.v7-lifecycle'):
        items=plan(project,a.model,a.seeds,a.python)
        if a.dry_run:
            print(json.dumps({'cases':len(items),'runs':[r[0] for r in items],'paid_calls':0}));return 0
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');failed=False
        with ThreadPoolExecutor(max_workers=a.max_parallel) as pool:
            for future in as_completed([pool.submit(execute,item,stamp,project) for item in items]):
                receipt=future.result();print(json.dumps(receipt),flush=True);failed |= receipt['returncode']!=0
        return 2 if failed else 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,FileNotFoundError,KeyError) as error:
        print('V7 dispatcher blocked: '+type(error).__name__+': '+str(error),file=sys.stderr);raise SystemExit(2)
