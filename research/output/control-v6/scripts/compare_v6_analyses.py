"""Compare two separately implemented V6 calculations without model calls."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--out',type=Path);a=p.parse_args();r=a.project.resolve()
    ap=r/'analysis/v6-analysis.json';bp=r/'analysis/independent-raw-check.json';aa=json.loads(ap.read_text());bb=json.loads(bp.read_text())
    assert bb['success'] and not bb['errors'],'Independent raw checker failed'
    checked=0
    def equal(x,y):
        nonlocal checked
        checked+=1
        if x is None or y is None:assert x is y,(x,y)
        elif isinstance(x,(int,float)) and isinstance(y,(int,float)):assert math.isclose(x,y,abs_tol=1e-9,rel_tol=1e-12),(x,y)
        else:assert x==y,(x,y)
    key=lambda x:tuple(x[k] for k in ('alias','seed','mode','condition','repeat'))
    raw={key(e):e for e in bb['episodes']};equal(len(aa['rows']),len(raw));equal(aa['eligible_joint_episodes'],bb['valid_episodes'])
    for e in aa['rows']:
        b=raw[key(e)];equal(e['actions'],b['actions'])
        for m,value in b['metrics'].items():equal(e['rule_adherence' if m=='orientation_adherence' else m],value)
    groups={(g['alias'],g['mode'],g['condition'],g['population']):g for g in bb['groups']}
    for g in aa['groups']:
        b=groups[g['alias'],g['mode'],g['condition'],g['scope']]
        equal(g['seeds'],b['case_seeds']);equal(g['episodes'],b['n_episodes'])
        for k,v in g['metrics'].items():equal(v,b['means'][k])
        for k,v in g['counts'].items():equal(v,b['binary_counts'][k])
        if g['condition']!='verified':
            equal(g['rule_adherence_count'],b['binary_counts']['orientation_adherence'])
            equal(g['rule_adherence_rate'],b['means']['orientation_adherence'])
    contrasts={(x['alias'],x['mode'],x['name']):x for x in bb['contrasts']}
    for x in aa['contrasts']:
        y=contrasts[x['alias'],x['mode'],x['name']]
        equal(x['seeds'],y['case_seeds']);equal(x['n_cases'],y['n_cases'])
        for m,v in x['metrics'].items():
            equal(v['estimate'],y['metrics'][m]['estimate'])
            for i in range(2):equal(v['finite_completion_bounds'][i],y['metrics'][m]['completion_bounds'][i])
            for row in x['per_case']:equal(row[m],y['metrics'][m]['case_effects'][str(row['seed'])])
    close=json.loads((r/'docs/v6-closeout-record.json').read_text())
    result={'success':True,'matched_checks':checked,'eligible_episodes':aa['eligible_joint_episodes'],'mismatches':0,'analysis_sha256':sha(ap),'independent_check_sha256':sha(bp),'closeout_sha256':sha(r/'docs/v6-closeout-record.json'),'comparison_script_sha256':sha(Path(__file__)),'both_checkers_written_and_frozen_before_dispatch':True,'comparison_wrapper_created_during_execution_without_outcome_inspection':True,'provider_returned_cost_estimate_usd':close['new_returned_response_estimate_usd'],'independent_token_price_estimate_usd':bb['returned_usage_estimate_usd'],'cost_difference_usd':close['new_returned_response_estimate_usd']-bb['returned_usage_estimate_usd']}
    out=a.out or r/'analysis/independent-crosscheck.json'
    if out.exists():assert json.loads(out.read_text())==result,'Changed existing comparison'
    else:out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
