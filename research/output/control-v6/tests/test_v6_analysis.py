import itertools,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_v6_study import bounds,metrics,METRICS,CONTRASTS
from inherited_collusion.storage import read

class AnalysisTests(unittest.TestCase):
    def test_all_exact_optima_no_harm(self):
        for path in (ROOT/'inputs/v5').glob('*/checkpoint.json'):
            cp=read(path);out=[metrics(cp,dict(zip('AB',pair))) for pair in itertools.product(sorted(cp['tasks']),repeat=2)]
            safe=[m for m in out if m['safe_optimal']]
            self.assertEqual(len(safe),2)
            self.assertTrue(all(not m['duplicate'] and not m['any_outsider_loss'] and m['total_reward_loss']==0 for m in safe))
            self.assertTrue(any(m['any_outsider_loss'] and not m['harmful_joint'] for m in out))
    def test_missing_does_not_become_safe_or_zero(self):
        ranges={301:{'safe_optimal':[0,1]}}
        weights=CONTRASTS['average_tie_minus_verified']
        self.assertEqual(bounds({},[301],'harmful',weights,'safe_optimal',ranges),[-1.,1.])
        index={(301,'harmful','verified',r):{'safe_optimal':1} for r in range(2)}
        self.assertEqual(bounds(index,[301],'harmful',weights,'safe_optimal',ranges),[-1.,0.])
        for a in ('tie_first','tie_last'):
            for r in range(2):index[301,'harmful',a,r]={'safe_optimal':1}
        self.assertEqual(bounds(index,[301],'harmful',weights,'safe_optimal',ranges),[0.,0.])
    def test_bounds_equal_exhaustive_completions(self):
        seeds=[301,303];ranges={s:{'safe_optimal':[0,1]} for s in seeds};weights=CONTRASTS['average_tie_minus_verified']
        idx={(s,'harmful',a,r):{'safe_optimal':int(s==301)} for s in seeds for a in weights for r in range(2)}
        missing=[(301,'harmful','verified',0),(303,'harmful','tie_first',1),(303,'harmful','tie_last',1)]
        for k in missing:del idx[k]
        values=[]
        for fill in itertools.product((0,1),repeat=len(missing)):
            full={**idx,**{k:{'safe_optimal':v} for k,v in zip(missing,fill)}}
            values.append(bounds(full,seeds,'harmful',weights,'safe_optimal',ranges)[0])
        self.assertEqual(bounds(idx,seeds,'harmful',weights,'safe_optimal',ranges),[min(values),max(values)])
if __name__=='__main__':unittest.main()
