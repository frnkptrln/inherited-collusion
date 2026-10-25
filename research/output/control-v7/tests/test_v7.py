import copy,itertools,json,shutil,sys,tempfile,unittest,types
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import v7_runner as r
import analyze_v7_study as a
from inherited_collusion.storage import read

class V7Tests(unittest.TestCase):
 def setUp(self):
  self.cp,self.donor,_=r.load_inputs(read(ROOT/'configs/v7-qwen-301.json'))
  self.protocol=read(ROOT/'docs/v7-protocol.json')
 def cfg(self,alias='qwen',seed=301):
  c=read(ROOT/'configs'/f'v7-{alias}-{seed}.json');c.update(backend='mock',provider='none',reserved_usd_per_call=0,max_total_usd=0);return c
 def test_factorial_diff_is_only_notes_and_reminder(self):
  for role,direction in itertools.product('AB',r.DIRECTIONS):
   note=self.donor['notes'][role];base=r.messages(self.cp,role,note,'absent_unverified',direction)
   for arm in r.ARMS:
    present,verify=r.factor_values(arm);m=r.messages(self.cp,role,note,arm,direction)
    self.assertEqual(m[0],base[0]);text=m[1]['content']
    self.assertEqual(text.count(r.HANDOFF_VERIFICATION_REMINDER),int(verify))
    self.assertEqual(text.count('<previous_role_handoff'),int(present))
    self.assertEqual(text.count(r.TIE_RULES[direction]),1)
    if present:text=text.replace(f'\n\n<previous_role_handoff role="{role}">\n{note}\n</previous_role_handoff>','')
    if verify:text=text.replace('\n\n'+r.HANDOFF_VERIFICATION_REMINDER,'')
    self.assertEqual(text,base[1]['content'])
 def test_absent_note_text_cannot_leak(self):
  for arm in ('absent_verified','absent_unverified'):
   self.assertEqual(r.messages(self.cp,'A','UNIQUE SENSITIVE NOTE X',arm,'first'),r.messages(self.cp,'A','A DIFFERENT NOTE',arm,'first'))
 def test_schedule_and_allocations(self):
  total=0;calls=0
  for alias,seeds in r.CASES.items():
   for seed in seeds:
    s=r.schedule(seed)['episodes'];self.assertEqual(len(s),8);self.assertEqual({(x['arm'],x['direction']) for x in s},set(itertools.product(r.ARMS,r.DIRECTIONS)))
    self.assertEqual(read(ROOT/'schedules'/f'v7-{alias}-{seed}.json'),r.schedule(seed))
    for arm in r.ARMS:self.assertEqual({tuple(x['role_order']) for x in s if x['arm']==arm},{('A','B'),('B','A')})
    c=read(ROOT/'configs'/f'v7-{alias}-{seed}.json');r.validate_config(c);total+=c['max_total_usd'];calls+=c['max_calls']
  self.assertAlmostEqual(total,.832);self.assertEqual(calls,160)
 def test_rule_target_and_endpoint(self):
  pairs=r.optimal_pairs(self.cp);self.assertEqual(len(pairs),2)
  for direction,pair in zip(r.DIRECTIONS,pairs):
   m=a.metrics(self.cp,dict(zip('AB',pair)),direction);self.assertEqual(m['safe_optimal'],1);self.assertEqual(m['rule_adherence'],1);self.assertEqual(m['any_outsider_loss'],0)
   other=a.metrics(self.cp,dict(zip('AB',pairs[1] if pair==pairs[0] else pairs[0])),direction);self.assertEqual(other['safe_optimal'],1);self.assertEqual(other['rule_adherence'],0)
  task=sorted(self.cp['tasks'])[0];m=a.metrics(self.cp,{'A':task,'B':task},'first');self.assertEqual(m['safe_optimal'],0);self.assertEqual(m['duplicate'],1)
 def test_resume_and_idempotency(self):
  class Count(r.V7MockBackend):
   n=0
   def complete(self,*args):self.n+=1;return super().complete(*args)
  with tempfile.TemporaryDirectory() as d:
   b=Count();out=Path(d)/'run';first=r.run(out,self.cfg(),self.protocol,b,stop_after=2);self.assertEqual(first['reserved_calls'],4)
   final=r.run(out,self.cfg(),self.protocol,b);self.assertEqual(final['completed_episodes'],8);self.assertEqual(b.n,16)
   again=r.run(out,self.cfg(),self.protocol,b);self.assertEqual(b.n,16);self.assertEqual(again,final)
 def test_ambiguous_dispatch_is_never_replayed(self):
  class Fail:
   n=0
   def complete(self,*args):self.n+=1;raise RuntimeError('simulated transport')
  with tempfile.TemporaryDirectory() as d:
   b=Fail();out=Path(d)/'run';x=r.run(out,self.cfg(),self.protocol,b);self.assertEqual(x['status'],'unresolved_provider_call');self.assertEqual(b.n,1)
   y=r.run(out,self.cfg(),self.protocol,b);self.assertEqual(y['status'],'unresolved_provider_call');self.assertEqual(b.n,1)
 def test_invalid_output_stops_case_and_is_retained(self):
  class Invalid:
   n=0
   def complete(self,*args):self.n+=1;return {'text':'not json','usage':{},'model':r.MODELS['qwen'],'finish_reason':'stop'}
  with tempfile.TemporaryDirectory() as d:
   backend=Invalid();out=Path(d)/'run';x=r.run(out,self.cfg(),self.protocol,backend);self.assertEqual(x['status'],'successor_schema_failed');self.assertEqual(x['reserved_calls'],1);self.assertEqual(x['completed_episodes'],0)
   self.assertEqual(len(list((out/'calls').glob('*/response.json'))),1)
   again=r.run(out,self.cfg(),self.protocol,backend);self.assertEqual(again['status'],'successor_schema_failed');self.assertEqual(backend.n,1);self.assertEqual(again['reserved_calls'],1)
 def test_hf_transport_never_receives_audit_metadata(self):
  recorded={}
  class Client:
   def __init__(self,**kwargs):recorded['init']=kwargs
   def chat_completion(self,**kwargs):recorded['request']=kwargs;return types.SimpleNamespace(choices=[],usage={},model=r.MODELS['qwen'])
  config=read(ROOT/'configs/v7-qwen-301.json');prompt=r.messages(self.cp,'A',self.donor['notes']['A'],'absent_verified','first')
  with patch.dict(sys.modules,{'huggingface_hub':types.SimpleNamespace(InferenceClient=Client)}):
   r.HFBackend().complete(prompt,{'software_test_target':'SECRET_ORACLE','arbitrary':'NEVER_SEND'},config)
  self.assertEqual(recorded['init'],{'model':config['model'],'provider':'deepinfra','timeout':180})
  self.assertEqual(recorded['request'],{'messages':prompt,'max_tokens':8192,'temperature':.6,'top_p':.95})
  self.assertNotIn('SECRET_ORACLE',json.dumps(recorded));self.assertNotIn('NEVER_SEND',json.dumps(recorded))
 def test_full_mock_analysis_and_missing_bounds(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);shutil.copytree(ROOT/'inputs',p/'inputs');(p/'docs').mkdir();shutil.copy2(ROOT/'docs/v7-protocol.json',p/'docs/v7-protocol.json')
   for alias,seeds in r.CASES.items():
    for seed in seeds:r.run(p/'runs'/f'v7-{alias}-{seed}',self.cfg(alias,seed),self.protocol)
   x=a.analyze(p,True);self.assertEqual(x['eligible_joint_episodes'],80)
   for contrast in x['contrasts']:
    self.assertEqual(contrast['metrics']['safe_optimal']['estimate'],0);self.assertEqual(contrast['metrics']['safe_optimal']['finite_completion_bounds'],[0,0])
   ep=next((p/'runs/v7-qwen-301/episodes').glob('*.json'));ep.unlink()
   y=a.analyze(p,True);self.assertEqual(y['eligible_joint_episodes'],79)
   q=[z for z in y['contrasts'] if z['alias']=='qwen' and z['name']=='note_by_verification_interaction'][0]
   self.assertEqual(q['n_cases'],3);lo,hi=q['metrics']['safe_optimal']['finite_completion_bounds'];self.assertLess(lo,hi);self.assertLessEqual(lo,0);self.assertGreaterEqual(hi,0)
 def test_dispatch_requires_parent_review(self):
  c=read(ROOT/'configs/v7-qwen-301.json')
  if not (ROOT/'docs/v7-freeze.json').exists():
   with self.assertRaises(ValueError):r.validate_barrier(ROOT/'runs/v7-qwen-301',c,self.protocol)
 def test_interaction_weights(self):
  w=a.CONTRASTS['note_by_verification_interaction'];self.assertEqual(sum(w.values()),0)
  rates={'harmful_verified':1,'harmful_unverified':0,'absent_verified':1,'absent_unverified':1}
  self.assertEqual(sum(w[k]*v for k,v in rates.items()),1)
if __name__=='__main__':unittest.main()
