#!/usr/bin/env python3
"""Seal V5 raw evidence before aggregate condition analysis."""
import argparse
from contextlib import ExitStack
from datetime import datetime,timezone
import hashlib
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(Path(__file__).resolve().parent)]
from inherited_collusion.storage import read,immutable_json,RunLock
from analyze_v5_study import inventory,SEEDS,MODELS,raw_usage_check

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=ROOT);a=p.parse_args();project=a.project.resolve()
    with ExitStack() as stack:
        stack.enter_context(RunLock(project/'runs/.v5-lifecycle'))
        for alias in MODELS:
            for seed in SEEDS:stack.enter_context(RunLock(project/'runs'/f'v5-main-{alias}-{seed}'))
        ledger=read(project/'runs/phase5-budget.json');costs=[];runs=[];missing_cost_responses=0
        for alias in MODELS:
            for seed in SEEDS:
                name=f'v5-main-{alias}-{seed}';root=project/'runs'/name
                if not (root/'summary.json').exists():raise ValueError('Every fixed case must have a terminal summary')
                # The dispatcher completion receipt is a durable proof that its worker returned.
                for started in (root/'invocation_logs').glob('*.start.json'):
                    ended=started.with_name(started.name.removesuffix('.start.json')+'.result.json')
                    if not ended.exists():raise ValueError('Invocation has not returned: '+str(started))
                receipts=[read(p) for p in (root/'invocation_logs').glob('*-all.result.json')]
                if not receipts:raise ValueError('No finished all-stage worker: '+name)
                requests=list((root/'calls').glob('*/request.json'));responses=list((root/'calls').glob('*/response.json'))
                for path in responses:
                    cost=raw_usage_check(read(path),read(root/'manifest.json')['config'])
                    if type(cost) in (int,float) and math.isfinite(cost) and cost>=0:costs.append(cost)
                    else:missing_cost_responses+=1
                summary=read(root/'summary.json')
                if summary['status'] not in ('completed','probe_schema_failed','donor_technical_failed','successor_schema_failed','unresolved_provider_call','model_identity_failed','incomplete_generation','usage_validation_failed','budget_exhausted'):raise ValueError('Run is not terminal: '+name+' '+summary['status'])
                runs.append({'run':name,'status':summary['status'],'requests':len(requests),'responses':len(responses),'summary_sha256':hashlib.sha256((root/'summary.json').read_bytes()).hexdigest()})
        record={'schema_version':5,'closed_at':datetime.now(timezone.utc).isoformat(),'state':'CLOSED_NO_FURTHER_DISPATCH','raw_inventory':inventory(project),'runs':runs,'returned_response_cost_estimate_usd':math.fsum(costs) if costs else None,'known_previous_returned_response_estimate_usd':1.922675947,'known_project_returned_response_estimate_usd':1.922675947+math.fsum(costs),'new_allocated_ceiling_usd':4.896,'retained_old_allocations_usd':9.922,'combined_allocations_usd':14.818,'not_invoice':True,'missing_cost_responses':missing_cost_responses,'cost_estimate_complete_for_returned_responses':missing_cost_responses==0,'outcome_visibility_operator_attestation':{'operator':'Codex root agent','attests_no_aggregate_v5_outcomes_examined_before_closure':True,'not_programmatically_proven':True,'permitted_visibility':'Pre-successor task and donor diagnostics plus technical counts, status and cost only.'}}
        immutable_json(project/'docs/v5-closeout-record.json',record)
        print({k:record[k] for k in ('closed_at','returned_response_cost_estimate_usd','known_project_returned_response_estimate_usd','combined_allocations_usd')})
if __name__=='__main__':main()
