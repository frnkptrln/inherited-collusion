"""Write the single local V7 design seal after all offline review gates pass."""
import datetime,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import v7_runner as runner
from inherited_collusion.storage import read,digest,immutable_json

def main():
    assert not list((ROOT/'runs').glob('v7-*/calls/*/request.json')),'Paid request already exists'
    assert not (ROOT/'docs/v7-freeze.json').exists(),'Freeze is immutable'
    protocol=read(ROOT/'docs/v7-protocol.json');ledger=read(ROOT/'runs/phase7-budget.json')
    runner.validate_protocol(protocol)
    assert read(ROOT/'evidence/preflight/independent-input-check.json')['success']
    review=read(ROOT/'evidence/preflight/root-validation.json')
    assert review['success'] and review['paid_calls']==0 and review['dispatch_authorized']
    budget=read(ROOT/'evidence/preflight/budget-provenance.json')
    assert budget['success'] and budget['historical_conservative_exposure_usd']==12.374
    for a in ledger['allocations'].values():
        c=read(ROOT/a['config']);runner.validate_config(c);runner.load_inputs(c)
    files=[]
    for directory in ('scripts','inherited_collusion','tests','configs','inputs','schedules','evidence/preflight'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend([ROOT/'docs/v7-protocol.json',ROOT/'runs/phase7-budget.json'])
    _,package,source=runner.sources()
    value={'schema_version':7,'frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'FROZEN_BEFORE_FIRST_V7_DISPATCH','protocol_hash':digest(protocol),'source_hash':source,'package_source_hash':package,'ledger_sha256':runner.sha(ROOT/'runs/phase7-budget.json'),'config_digests':{n:a['config_digest'] for n,a in ledger['allocations'].items()},'artifacts':{str(p.relative_to(ROOT)):runner.sha(p) for p in sorted(set(files))},'prior_outcomes_known':True,'new_outcomes_seen':False,'local_clock_not_external_registration':True}
    immutable_json(ROOT/'docs/v7-freeze.json',value)
    for name,a in ledger['allocations'].items():runner.validate_barrier(ROOT/'runs'/name,read(ROOT/a['config']),protocol)
    print(json.dumps({'frozen_at':value['frozen_at'],'artifacts':len(value['artifacts']),'new_requests':0,'combined_ceiling_usd':13.206}))
if __name__=='__main__':main()
