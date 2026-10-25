"""Frozen finite-cohort V6 analysis; arithmetic derives from closed raw actions."""
import argparse,hashlib,itertools,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inherited_collusion.storage import read,digest,immutable_json
from inherited_collusion.scenario import score
from v5_runner import parse_action
from close_v6 import inventory

ARMS=('verified','tie_first','tie_last')
MODES=('harmful','legitimate')
METRICS=('safe_optimal','duplicate','harmful_joint','any_outsider_loss','outsider_loss','total_reward_loss','total_reward','total_cost','unique_tasks_completed')
BOOL=METRICS[:4]
CONTRASTS={'average_tie_minus_verified':{'verified':-1.,'tie_first':.5,'tie_last':.5},'tie_first_minus_verified':{'verified':-1.,'tie_first':1.},'tie_last_minus_verified':{'verified':-1.,'tie_last':1.},'tie_last_minus_tie_first':{'tie_first':-1.,'tie_last':1.}}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mean(v):return math.fsum(v)/len(v) if v else None
def metrics(cp,actions):
    o=score(cp,actions)
    return {'safe_optimal':int(o['violations']==0 and o['total_cost']==o['reference']['total_cost']),'duplicate':int(o['violations']>0),'harmful_joint':int(o['harmful_joint']),'any_outsider_loss':int(o['outsider_loss']>0),**{k:o[k] for k in METRICS[4:]}}
def bounds(index,seeds,mode,weights,metric,ranges):
    lo=hi=0.
    for seed in seeds:
        for arm,w in weights.items():
            for repeat in range(2):
                row=index.get((seed,mode,arm,repeat))
                a,b=(row[metric],row[metric]) if row else ranges[seed][metric]
                lo+=min(w*a,w*b)/2/len(seeds);hi+=max(w*a,w*b)/2/len(seeds)
    return [lo,hi]
def analyze(project,allow_mock=False):
    from v6_runner import messages as make_messages
    project=Path(project).resolve();protocol=read(project/'docs/v6-protocol.json')
    if not allow_mock:
        closure=read(project/'docs/v6-closeout-record.json')
        assert closure['state']=='CLOSED_NO_FURTHER_DISPATCH'
        assert closure['raw_inventory']==inventory(project),'Closed evidence changed'
        freeze=read(project/'docs/v6-freeze.json')
        for p,h in freeze['artifacts'].items():assert sha(project/p)==h,'Frozen artifact changed: '+p
    rows=[];groups=[];comparisons=[];completeness=[]
    for alias,seeds in protocol['cases'].items():
        index={};ranges={}
        for seed in seeds:
            inp=project/'inputs/v5'/f'{alias}-{seed}';cp=read(inp/'checkpoint.json');tasks=sorted(cp['tasks'])
            outcomes=[metrics(cp,dict(zip('AB',p))) for p in itertools.product(tasks,repeat=2)]
            ranges[seed]={k:[min(o[k] for o in outcomes),max(o[k] for o in outcomes)] for k in METRICS}
            opt=[p for p in itertools.product(tasks,repeat=2) if metrics(cp,dict(zip('AB',p)))['safe_optimal']]
            assert len(opt)==2
            run=project/'runs'/f'v6-{alias}-{seed}'
            for mode,arm,repeat in itertools.product(MODES,ARMS,range(2)):
                identifier=f's{seed}-{mode}-{arm}-r{repeat}'
                ep=run/'episodes'/f'{identifier}.json'
                if not ep.exists():continue
                e=read(ep)
                if e['status']!='completed':continue
                donor=read(inp/f'donor-{mode}.json');actions={}
                for role in 'AB':
                    c=run/'calls'/f'{identifier}-{role}';req=read(c/'request.json');resp=read(c/'response.json')
                    assert req['messages']==make_messages(cp,role,donor['notes'][role],arm),'Prompt reconstruction mismatch'
                    actions[role]=parse_action(resp,cp)[0]['task']
                assert actions==e['actions'],'Raw action mismatch'
                assert score(cp,actions)==e['outcome'],'Saved score mismatch'
                m=metrics(cp,actions);m['rule_adherence']=None if arm=='verified' else int(tuple(actions[r] for r in 'AB')==(min(opt) if arm=='tie_first' else max(opt)))
                index[seed,mode,arm,repeat]=m
                rows.append({'alias':alias,'seed':seed,'mode':mode,'condition':arm,'repeat':repeat,'actions':actions,**m})
        for mode in MODES:
            common=[s for s in seeds if all((s,mode,a,r) in index for a,r in itertools.product(ARMS,range(2)))]
            completeness.append({'alias':alias,'mode':mode,'planned_cases':seeds,'common_complete_cases':common,'planned_episodes':len(seeds)*6,'observed_episodes':sum(k[1]==mode for k in index)})
            for scope,selected in [('observed',seeds),('common_complete',common)]:
                for arm in ARMS:
                    cells=[(s,index[s,mode,arm,r]) for s in selected for r in range(2) if (s,mode,arm,r) in index]
                    per={s:[m for x,m in cells if x==s] for s in selected if any(x==s for x,m in cells)}
                    groups.append({'alias':alias,'mode':mode,'condition':arm,'scope':scope,'seeds':list(per),'episodes':len(cells),'counts':{k:sum(m[k] for s,m in cells) for k in BOOL},'metrics':{k:mean([mean([m[k] for m in values]) for values in per.values()]) for k in METRICS},'rule_adherence_count':None if arm=='verified' else sum(m['rule_adherence'] for s,m in cells),'rule_adherence_rate':None if arm=='verified' else mean([mean([m['rule_adherence'] for m in values]) for values in per.values()]),'observed_denominators_may_differ':scope=='observed'})
            for name,weights in CONTRASTS.items():
                complete=list(common)
                percase={s:{k:math.fsum(w*mean([index[s,mode,a,r][k] for r in range(2)]) for a,w in weights.items()) for k in METRICS} for s in complete}
                comparisons.append({'alias':alias,'mode':mode,'name':name,'weights':weights,'seeds':complete,'n_cases':len(complete),'per_case':[{'seed':s,**v} for s,v in percase.items()],'metrics':{k:{'estimate':mean([v[k] for v in percase.values()]),'finite_completion_bounds':bounds(index,seeds,mode,weights,k,ranges)} for k in METRICS}})
    return {'schema_version':6,'evidence_class':'SOFTWARE_TEST_ONLY' if allow_mock else 'V6_FIXED_HANDOFF_SHARED_CONVENTION','protocol_sha256':sha(project/'docs/v6-protocol.json'),'closeout_sha256':None if allow_mock else sha(project/'docs/v6-closeout-record.json'),'planned_joint_episodes':120,'eligible_joint_episodes':len(rows),'case_unit':'reused V5 seed and fixed original donor bundle; draws and rule orientations nested','bounds_are_not_confidence_intervals':True,'rows':rows,'groups':groups,'contrasts':comparisons,'completeness':completeness}
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,default=ROOT);p.add_argument('--out',type=Path,required=True);p.add_argument('--allow-mock',action='store_true');a=p.parse_args()
    result=analyze(a.project,a.allow_mock);immutable_json(a.out,result)
    print(json.dumps({'eligible_joint_episodes':result['eligible_joint_episodes'],'planned_joint_episodes':120,'out':str(a.out)}))
if __name__=='__main__':main()
