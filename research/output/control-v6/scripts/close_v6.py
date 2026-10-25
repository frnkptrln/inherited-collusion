"""Close every V6 allocation and seal raw inventory before condition analysis."""
from pathlib import Path
from contextlib import ExitStack
import argparse,datetime,hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from inherited_collusion.storage import RunLock,read,immutable_json

def inventory(project):
    return {str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest()
            for run in sorted((project/'runs').glob('v6-*')) for p in sorted(run.rglob('*'))
            if p.is_file() and p.name!='.lock'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,default=ROOT);args=parser.parse_args();root=args.project.resolve()
    ledger=read(root/'runs/phase6-budget.json');freeze=read(root/'docs/v6-freeze.json')
    for path,h in freeze['artifacts'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest()==h,'Frozen source/input changed: '+path
    with ExitStack() as stack:
        stack.enter_context(RunLock(root/'runs/.v6-lifecycle'))
        for name in ledger['allocations']:stack.enter_context(RunLock(root/'runs'/name))
        rows=[];costs=[];reserved=[];unresolved=[];unverified_cost_responses=[]
        for name,a in ledger['allocations'].items():
            run=root/'runs'/name;summary=read(run/'summary.json')
            assert summary['status'] in ('completed','successor_schema_failed','unresolved_provider_call','model_identity_failed','incomplete_generation','usage_validation_failed','budget_exhausted'),(name,'not terminal')
            starts=list((run/'invocation_logs').glob('*.start.json'))
            assert starts,'No dispatcher receipt: '+name
            for s in starts:assert s.with_name(s.name.replace('.start.json','.result.json')).exists(),'Worker not returned'
            req=list((run/'calls').glob('*/request.json'));resp=list((run/'calls').glob('*/response.json'))
            cfg=read(root/a['config'])
            reserved.append(len(req)*cfg['reserved_usd_per_call'])
            for p in resp:
                v=read(p).get('usage',{}).get('estimated_cost')
                if type(v) in (int,float) and math.isfinite(v) and v>=0:
                    costs.append(v)
                    if v>cfg['reserved_usd_per_call']+1e-12:unverified_cost_responses.append(str(p.relative_to(root)))
                else:unverified_cost_responses.append(str(p.relative_to(root)))
            unresolved.extend(str(p.relative_to(root)) for p in req if not p.with_name('response.json').exists())
            rows.append({'run':name,'status':summary['status'],'requests':len(req),'responses':len(resp)})
        record={'schema_version':6,'state':'CLOSED_NO_FURTHER_DISPATCH','closed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':rows,'raw_inventory':inventory(root),'new_returned_response_estimate_usd':math.fsum(costs),'known_prior_returned_response_estimate_usd':2.891585085,'known_project_returned_response_estimate_usd':2.891585085+math.fsum(costs),'new_reserved_usd':math.fsum(reserved),'combined_conservative_ceiling_usd':14.736,'unresolved_requests':unresolved,'unverified_cost_responses':unverified_cost_responses,'returned_cost_coverage_complete':not unverified_cost_responses,'not_invoice':True,'visibility_attestation':{'operator':'Codex root agent','aggregate_condition_outcomes_not_inspected_before_close':True,'technical_counts_status_cost_only':True,'attestation_not_programmatic_proof':True}}
        immutable_json(root/'docs/v6-closeout-record.json',record)
        print(json.dumps({k:v for k,v in record.items() if k not in ('raw_inventory','runs')}))
if __name__=='__main__':main()
