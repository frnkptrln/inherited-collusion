#!/usr/bin/env python3
"""Offline, exact-decimal reconciliation; writes only beside this script.

No SDK, network, model request, retry, job, or old-ledger mutation is performed.
V4F is the canonical consolidated V4/V4F population. Every original V4 call
artifact is required to remain byte-identical in V4F before deduplication.
"""
import argparse
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path

D = Decimal
HERE = Path(__file__).resolve().parent
ORIGINAL = Path('/home/user/projects/collusion-sprint')
WORKSPACE = HERE.parent.parent
V6 = WORKSPACE / 'output/control-v6'
MODES = ('harmful', 'legitimate')
ROLES = ('A', 'B')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true', help='Compare recomputed bytes with saved result; do not write.')
    args = parser.parse_args()
    hashes = {}
    def raw(path):
        path = Path(path).resolve()
        payload = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(payload).hexdigest()
        return payload
    def read(path):
        return json.loads(raw(path), parse_float=D)
    def dec(value):
        return D(str(value))
    def require(test, reason):
        if not test:
            raise ValueError(reason)
    def serial(value):
        if isinstance(value, D):
            return format(value, 'f')
        raise TypeError(type(value).__name__)
    # Preserve old files and bind the calculation to their exact bytes.
    for relative in ['runs/budget-ledger.json','runs/phase3-budget.json',
                     'runs/phase4-budget.json','runs/phase4f-budget.json','runs/phase5-budget.json',
                     'docs/v3-closeout-record.json','docs/v4-strict-closeout-record.json',
                     'docs/v4f-closeout-record.json','docs/v5-closeout-record.json']:
        read(ORIGINAL / relative)
    read(V6 / 'runs/phase6-budget.json')
    close6 = read(V6 / 'docs/v6-closeout-record.json')
    require(close6['state'] == 'CLOSED_NO_FURTHER_DISPATCH', 'V6 is not closed')
    require(read(ORIGINAL/'docs/v5-closeout-record.json')['state'] == 'CLOSED_NO_FURTHER_DISPATCH', 'V5 is not closed')
    close4 = read(ORIGINAL/'docs/v4f-closeout-record.json')
    require(close4['all_dispatchers_confirmed_finished_by_operator'] and close4['all_run_locks_verified_idle'], 'V4F closure absent')
    preserved_v4_files = 0
    for run in sorted((ORIGINAL/'runs').glob('v4-*')):
        target = run.with_name(run.name.replace('v4-', 'v4f-', 1))
        for source in sorted(run.glob('calls/*/*.json')):
            if source.name in ('request.json','response.json','dispatch.json'):
                destination = target / source.relative_to(run)
                require(destination.exists() and raw(source) == raw(destination), 'V4/V4F deduplication mismatch: '+str(source))
                preserved_v4_files += 1
    require(preserved_v4_files == 3235, 'Original V4 inventory changed')
    groups = {
        'initial': [ORIGINAL/'runs'/name for name in ['hf-pilot-v1','hf-pilot-table-v1','hf-pilot-thinking-v1']],
        'v3': sorted((ORIGINAL/'runs').glob('v3-pilot-*')),
        'v4f': sorted((ORIGINAL/'runs').glob('v4f-*')),
        'v5': sorted((ORIGINAL/'runs').glob('v5-main-*')),
        'v6': sorted((V6/'runs').glob('v6-*')),
    }
    def expected_ids(group, manifest, run):
        seed = manifest.get('seed') or manifest.get('seeds',[None])[0]
        require(type(seed) is int, 'Missing seed: '+str(run))
        prefix = f's{seed}'
        if group == 'v6':
            read(run/'schedule.json')
            return {f'{prefix}-{m}-{c}-r{r}-{a}' for m in MODES for c in ('verified','tie_first','tie_last') for r in (0,1) for a in ROLES}
        if group == 'v5':
            read(run/'schedule.json')
            ids = {f'{prefix}-{s}-probe-{a}' for s in ('symmetric','unique') for a in ROLES}
            ids |= {f'{prefix}-{s}-{m}-p0-{kind}-{a}' for s in ('symmetric','unique') for m in MODES for kind in ('action','note') for a in ROLES}
            ids |= {f'{prefix}-{s}-{m}-{c}-r{r}-{a}' for s in ('symmetric','unique') for m in MODES for c in ('facts_only','matched','verified') for r in (0,1) for a in ROLES}
            return ids
        ids = {f'{prefix}-probe-{a}-{kind}' for a in ROLES for kind in ('comprehension','note_T1','note_T2')}
        if group == 'v4f' and manifest['cohort'] == 'qualification':
            return ids
        kind = 'plan' if group == 'initial' else 'action'
        ids |= {f'{prefix}-{m}-{p}-{k}-{a}' for m in MODES for p in ('p0','p1') for k in (kind,'note') for a in ROLES}
        if group == 'initial':
            source = raw(run/'source_snapshot/runner.py').decode()
            conditions = None
            for node in ast.parse(source).body:
                if isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONDITIONS' for t in node.targets):
                    conditions = ast.literal_eval(node.value)
            require(conditions is not None, 'Missing frozen initial conditions')
            ids |= {f'{prefix}-{m}-{c}-{a}' for m in MODES for c in conditions for a in ROLES}
        else:
            sourcefile = 'v3_runner.py' if group=='v3' else 'v4f_runner.py'
            raw(run/'source_snapshot'/sourcefile)
            ids |= {f'{prefix}-{m}-{c}-r{r}-{a}' for m in MODES for c in manifest['conditions'] for r in range(manifest['successor_repeats']) for a in ROLES}
        return ids
    totals = {'requests':0,'responses':0,'retained_dispatched_reservation_usd':D(0),
              'known_returned_estimate_usd':D(0),'unresolved_reservation_usd':D(0)}
    phases = {}; runs=[]; unresolved=[]
    for group, paths in groups.items():
        subtotal = {k:0 if k in ('requests','responses') else D(0) for k in totals}
        for run in paths:
            manifest = read(run/'manifest.json'); config = manifest['config']
            summary = read(run/'summary.json')
            if group in ('initial','v3'):
                require(summary['status']=='validation_failed', 'Old pilot is not stopped')
            expected = expected_ids(group, manifest, run)
            require(len(expected)==config['max_calls'], 'Constructed planned IDs disagree with frozen cap')
            requests = sorted(run.glob('calls/*/request.json'))
            actual = {p.parent.name for p in requests}
            require(actual <= expected, 'Unexpected call IDs: '+str(actual-expected))
            reserve = D(0); cost = D(0); responses=0; unknown=D(0)
            for request in requests:
                req = read(request); dispatch = read(request.with_name('dispatch.json'))
                amount = dec(dispatch['reserved_usd'])
                require(req['id']==request.parent.name and amount==dec(config['reserved_usd_per_call']), 'Identity or reservation mismatch')
                reserve += amount
                response = request.with_name('response.json')
                if response.exists():
                    usage = read(response).get('usage',{})
                    estimate = usage.get('estimated_cost')
                    require(estimate is not None and dec(estimate).is_finite() and D(0)<=dec(estimate)<=amount, 'Missing or excessive returned cost')
                    cost += dec(estimate); responses += 1
                else:
                    unknown += amount
                    unresolved.append({'request':str(request.resolve()), 'reserved_usd':amount})
            # V5 unused allocations were already released before V6; never release twice.
            previous_retained = reserve if group=='v5' else dec(config['max_total_usd'])
            release = previous_retained-reserve
            absent = sorted(expected-actual)
            rounding_headroom = dec(config['max_total_usd'])-len(expected)*dec(config['reserved_usd_per_call'])
            runrecord = {'group':group,'run':str(run.resolve()),'requests':len(requests),'responses':responses,
                'planned_calls':len(expected),'retained_dispatched_reservation_usd':reserve,
                'known_returned_estimate_usd':cost,'unresolved_reservation_usd':unknown,
                'previous_retained_allocation_usd':previous_retained,'newly_released_usd':release,
                'never_dispatched_call_ids':absent,'never_dispatched_slot_value_usd':len(absent)*dec(config['reserved_usd_per_call']),
                'allocation_rounding_headroom_usd':rounding_headroom,
                'never_dispatched_release_already_counted_before_v6':group=='v5'}
            runs.append(runrecord)
            for k in subtotal: subtotal[k] += runrecord[k]
        phases[group]=subtotal
        for k in totals: totals[k]+=subtotal[k]
    require(totals['requests']==2217 and totals['responses']==2212, 'Historical call population changed')
    require(totals['retained_dispatched_reservation_usd']==D('12.374'), 'Historical reservation differs')
    require(totals['unresolved_reservation_usd']==D('.034') and len(unresolved)==5, 'Unresolved exposure differs')
    release=sum((r['newly_released_usd'] for r in runs),D(0))
    require(release==D('2.362'), 'Never-dispatched/rounding release differs')
    require(sum((r['previous_retained_allocation_usd'] for r in runs),D(0))==D('14.736'), 'Previous combined ceiling differs')
    prices=read(HERE/'current-provider-pricing.json')
    pricing=[]
    for record in prices['models']:
        model=record['id']; metadata=record['provider_metadata']; price=metadata['pricing']
        is_qwen=model.startswith('Qwen/')
        reserve=D('.010') if is_qwen else D('.002')
        calls=64 if is_qwen else 96
        maximum=((D(10000)+D(2048))*dec(price['input'])+D(8192)*dec(price['output']))/D(1000000)
        require(metadata['provider']=='deepinfra' and metadata['status']=='live' and maximum<=reserve, 'Current catalog exceeds planned reservation')
        require(metadata['context_length']>=10000+2048+8192, 'Context cap insufficient')
        pricing.append({'model':model,'provider':'deepinfra','input_usd_per_million':dec(price['input']),
            'output_usd_per_million':dec(price['output']),'max_request_bytes':10000,'assumed_framing_tokens':2048,
            'max_completion_tokens':8192,'maximum_estimated_cost_usd':maximum,
            'reserved_usd_per_call':reserve,'max_calls':calls,'reserved_new_phase_usd':reserve*calls,
            'reservation_margin_usd':reserve-maximum,'passes':True})
    raw(V6/'scripts/v6_runner.py');raw(V6/'scripts/v5_runner.py')
    raw(V6/'inherited_collusion/backends.py')
    raw(HERE/'fetch_pricing.py');raw(Path(__file__))
    new=sum((p['reserved_new_phase_usd'] for p in pricing),D(0))
    require(new==D('.832'), 'New phase budget differs')
    combined=totals['retained_dispatched_reservation_usd']+new
    require(combined==D('13.206') and combined<=15, 'Project budget exceeded')
    result={'status':'PASS','schema_version':1,'authorization':'User authorized discretionary use within cumulative USD15 and requested best scientific revision.',
        'canonical_original_root':str(ORIGINAL),'canonical_v6_root':str(V6),
        'old_ledgers_mutated':False,'live_model_calls_or_jobs_started':False,'invoice_or_balance_verified':False,
        'interpretation':'All dispatched requests retain their full original reservation; only never-dispatched slots and unused rounding headroom are retired. No inference of invoice payments is made.',
        'v4_deduplication':{'checked_files':preserved_v4_files,'mismatches':0,'canonical_population':'V4F includes inherited V4 once'},
        'previous_combined_ceiling_usd':D('14.736'),'newly_released_never_dispatched_and_headroom_usd':release,
        'historical_totals':totals,'phases':phases,'runs':runs,'unresolved_requests':unresolved,
        'pricing_source':prices['source'],'pricing_checked_at':prices['checked_at'],'pricing_checks':pricing,
        'new_max_calls':160,'new_reserved_envelope_usd':new,'combined_ceiling_usd':combined,
        'remaining_unallocated_usd':D(15)-combined,
        'runner_gate_comparison':{'reference':'V6 uses V5 response validation with identical byte/token bounds and model/provider reserves.',
            'before_dispatch':['Exact config and freeze verification','max(raw,NFC) serialized message bytes <=10000','Positive per-call reserve','Request persisted before dispatch','No replay of unresolved requests'],
            'after_response':['Raw response saved before parsing','Prompt usage <= message bytes +2048','Completion usage <=8192','Returned estimated cost <= per-call reserve','Model identity and raw usage fields agree'],
            'limitation':'These are accounting assumptions and local stop guards, not a provider-enforced dollar billing cap. The 2048 framing allowance is an explicit assumption.'},
        'input_sha256':dict(sorted(hashes.items()))}
    payload=json.dumps(result,indent=2,sort_keys=True,default=serial)+'\n'
    destination=HERE/'reconciliation.json'
    if args.verify:
        require(destination.read_text()==payload,'Saved reconciliation differs from recomputation')
    else:
        destination.write_text(payload)
    print(json.dumps({'status':'PASS','verification_only':args.verify,'result':str(destination),
        'input_files_hashed':len(hashes),'requests':totals['requests'],'historical_reserved_usd':str(totals['retained_dispatched_reservation_usd']),
        'new_envelope_usd':str(new),'combined_ceiling_usd':str(combined),'sha256':hashlib.sha256(payload.encode()).hexdigest()}))

if __name__=='__main__':
    main()
