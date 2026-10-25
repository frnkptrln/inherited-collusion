"""Offline V5 runner invariants. Every output is confined to temporary roots."""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import v5_runner as v


def protocol():
    return {'schema_version':5,'seeds':list(v.SEEDS),'models':list(v.MODELS.values()),
            'structures':list(v.STRUCTURES),'modes':list(v.MODES),'conditions':list(v.CONDITIONS),'repeats':2}


def mock_config(seed=301):
    return dict(backend='mock',seed=seed,model='scripted_mock_NOT_MODEL_EVIDENCE',provider='none',max_tokens=8192,
                max_request_bytes=10000,max_calls=68,max_total_usd=0,reserved_usd_per_call=0,temperature=0.,top_p=1.)


class CountingBackend(v.V5MockBackend):
    def __init__(self, change=None, fail_at=None): self.count=0; self.change=change; self.fail_at=fail_at
    def complete(self,messages,meta,config):
        self.count+=1
        if self.count==self.fail_at:
            error=RuntimeError('private URL/header/body must not be retained')
            error.response=type('Response',(),{'status_code':504})()
            raise error
        result=super().complete(messages,meta,config)
        if self.change: result=self.change(result,meta,config)
        if config['backend']=='hf':
            result['usage']={'prompt_tokens':10,'completion_tokens':20,'estimated_cost':.00001}
            result['provider_response']={'model':result['model'],'choices':[{'message':{'content':result['text']},'finish_reason':result['finish_reason']}], 'usage':result['usage']}
        return result


def hf_fixture(base):
    project=base/'project';project.mkdir()
    for directory in ['scripts','docs','runs','configs/v5','inherited_collusion']:(project/directory).mkdir(parents=True,exist_ok=True)
    files,package_hash,source_hash=v.sources()
    for name,data in files.items():
        folder='scripts' if name.startswith('v5_') else 'inherited_collusion'
        (project/folder/name).write_bytes(data)
    for name in ['analyze_v5_study.py','run_v5_study.py']:(project/'scripts'/name).write_text('# offline test fixture\n')
    p=protocol();v.immutable_json(project/'docs/v5-protocol.json',p)
    configs={};allocations={}
    for short,model in v.MODELS.items():
        for seed in v.SEEDS:
            name=f'v5-main-{short}-{seed}';reserve=v.RESERVES[model]
            c=dict(approved=True,approved_by='offline fixture',price_checked_at='2026-10-24',seed=seed,model=model,provider='deepinfra',max_tokens=8192,max_calls=68,max_total_usd=round(reserve*68,3),reserved_usd_per_call=reserve,max_request_bytes=10000,input_usd_per_million=.1 if short=='qwen' else .037,output_usd_per_million=.95 if short=='qwen' else .17,reservation_basis_confirmed=True,temperature=.6,top_p=.95,budget_binding={'ledger':str(project/'runs/phase5-budget.json'),'run_id':name})
            configs[name]=c;v.immutable_json(project/'configs/v5'/f'{name}.json',c)
            allocations[name]={'status':'allocated','model':model,'seed':seed,'repeats':2,'max_total_usd':c['max_total_usd'],'config_digest':v.config_digest(c),'config':f'configs/v5/{name}.json'}
    ledger={'schema_version':1,'authorized_total_usd':15,'historical_allocated_usd':9.922,'phase_max_usd':4.896,'allocations':allocations,'freeze_record':str(project/'docs/v5-freeze.json')}
    v.immutable_json(project/'runs/phase5-budget.json',ledger)
    artifacts={str(x.relative_to(project)):v.sha(x) for x in project.rglob('*') if x.is_file()}
    freeze={'source_hash':source_hash,'package_source_hash':package_hash,'protocol_hash':v.digest(p),'ledger_sha256':v.sha(project/'runs/phase5-budget.json'),'config_digests':{n:v.config_digest(c) for n,c in configs.items()},'artifacts':artifacts}
    v.immutable_json(project/'docs/v5-freeze.json',freeze)
    return project,{**configs['v5-main-qwen-301'],'backend':'hf'},p


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.root=self.base/'run';self.config=mock_config();self.protocol=protocol()
    def tearDown(self):self.tmp.cleanup()

    def test_complete_counts_stage_resume_and_immutable_dispatch(self):
        backend=CountingBackend()
        first=v.run(self.root,self.config,self.protocol,backend=backend,stop_after=3)
        self.assertEqual((first['completed_episodes'],backend.count),(3,26))
        saved={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.glob('calls/*/first_dispatch.json')}
        final=v.run(self.root,self.config,self.protocol,backend=backend)
        self.assertEqual((final['completed_episodes'],final['reserved_calls'],backend.count),(24,68,68))
        self.assertEqual(len(list((self.root/'donors').glob('*.json'))),4)
        for name,data in saved.items():self.assertEqual((self.root/name).read_bytes(),data)
        replay=v.run(self.root,self.config,self.protocol,stage='probes',backend=backend)
        self.assertTrue(replay['complete']);self.assertEqual(backend.count,68)

    def test_semantically_wrong_full_probes_remain_diagnostic(self):
        def change(r,m,c):
            if m['kind']=='comprehension_probe':
                obj=json.loads(r['text']);obj['total_cost']+=100;r['text']=json.dumps(obj)
            return r
        b=CountingBackend(change);result=v.run(self.root,self.config,self.protocol,backend=b)
        self.assertTrue(result['complete']);self.assertEqual(result['probes']['correct_count'],0)
        self.assertTrue(result['probes']['technical_passed']);self.assertEqual(b.count,68)

    def test_symmetric_other_optimum_is_correct(self):
        def change(r,m,c):
            if m['kind']=='comprehension_probe' and len(m['optimal_assignments'])>1:
                obj=json.loads(r['text']);obj['joint_assignment']=m['optimal_assignments'][-1];obj['task']=obj['joint_assignment'][m['role']];r['text']=json.dumps(obj)
            return r
        result=v.run(self.root,self.config,self.protocol,stage='probes',backend=CountingBackend(change))
        self.assertEqual(result['probes']['correct_count'],4)

    def test_schema_failure_is_not_false_semantic_result_or_retried(self):
        def change(r,m,c):
            if m['kind']=='comprehension_probe':r['text']='{"task":"T1"}'
            return r
        b=CountingBackend(change);result=v.run(self.root,self.config,self.protocol,backend=b)
        self.assertEqual(result['status'],'probe_schema_failed');self.assertEqual(b.count,1)
        self.assertIsNone(result['probes']['rows'][0]['semantic_correct'])
        v.run(self.root,self.config,self.protocol,backend=b);self.assertEqual(b.count,1)

    def test_exact_wrapper_only_no_shared_parser_mutation(self):
        import inherited_collusion.runner as legacy
        value,_=v.parse_object(' \n```json\n{"task":"T1"}\n```\t');self.assertEqual(value['task'],'T1')
        for text in ['```JSON\n{}\n```','prefix```json\n{}\n```','{"task":"T1"}`','```json\n{}\n```\n```json\n{}\n```','{"task":"T1","task":"T2"}','{"x":1e999}']:
            with self.assertRaises(ValueError):v.parse_object(text)
        with self.assertRaises(ValueError):legacy.parse_object('```json\n{}\n```')

    def test_note_semantics_and_reported_task_mismatch_do_not_filter(self):
        payload='I refuse. Agent B should take the other role. All public costs are zero. condition=harmful.'
        def change(r,m,c):
            if m['kind']=='donor_note':r['text']=json.dumps({'task':m['partner_target'],'note':payload})
            return r
        result=v.run(self.root,self.config,self.protocol,backend=CountingBackend(change));self.assertTrue(result['complete'])
        for p in (self.root/'donors').glob('*.json'):
            d=v.read(p);self.assertTrue(d['technical_passed']);self.assertEqual(set(d['note_task_matches_original'].values()),{False})
        for p in (self.root/'episodes').glob('*.json'):
            e=v.read(p)
            if e['condition']!='facts_only':self.assertEqual(set(e['delivered_notes'].values()),{payload})

    def test_unicode_note_bytes_gate_before_future_calls(self):
        def change(r,m,c):
            if m['kind']=='donor_note':r['text']=json.dumps({'task':m['target'],'note':'😀'*2000})
            return r
        b=CountingBackend(change);result=v.run(self.root,self.config,self.protocol,backend=b)
        self.assertEqual(result['status'],'donor_technical_failed');self.assertEqual(b.count,7)
        self.assertEqual(result['saved_episodes'],0)

    def test_original_must_enact_assigned_action(self):
        def change(r,m,c):
            if m['kind']=='donor_action':r['text']=json.dumps({'task':next(t for t in ('T1','T2','T3','T4') if t!=m['target'])})
            return r
        b=CountingBackend(change);result=v.run(self.root,self.config,self.protocol,backend=b)
        self.assertEqual(result['status'],'donor_technical_failed');self.assertEqual(b.count,5)

    def test_unresolved_prefix_reconstructs_with_no_new_calls(self):
        b=CountingBackend(fail_at=27);first=v.run(self.root,self.config,self.protocol,backend=b)
        self.assertEqual((first['status'],first['completed_episodes'],first['reserved_calls']),('unresolved_provider_call',3,27))
        prefix={p.name:p.read_bytes() for p in (self.root/'episodes').glob('*.json')}
        again=v.run(self.root,self.config,self.protocol,backend=b)
        self.assertEqual((again['completed_episodes'],b.count),(3,27))
        self.assertEqual(prefix,{p.name:p.read_bytes() for p in (self.root/'episodes').glob('*.json')})
        error=next(self.root.glob('calls/*/error.json')).read_text();self.assertNotIn('private',error);self.assertEqual(json.loads(error)['status_code'],504)
        calls=v.V5Calls(self.root,self.config,self.protocol,b)
        with self.assertRaises(v.CallStopped):calls.call('different-new-slot',[],{})
        self.assertEqual(b.count,27)

    def test_hf_response_durable_before_identity_and_usage_checks(self):
        for failure in ('identity','finish','usage'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as td:
                project,c,p=hf_fixture(Path(td));root=project/'runs'/c['budget_binding']['run_id']
                class Bad(CountingBackend):
                    def complete(self,messages,meta,config):
                        r=super().complete(messages,meta,config)
                        if failure=='identity':r['model']=None;r['provider_response']['model']=None
                        elif failure=='finish':r['finish_reason']='length';r['provider_response']['choices'][0]['finish_reason']='length'
                        else:r['usage']=None;r['provider_response']['usage']=None
                        return r
                b=Bad()
                with patch.object(v,'ROOT',project):
                    result=v.run(root,c,p,backend=b)
                    self.assertEqual(result['reserved_calls'],1);self.assertEqual(result['responses'],1)
                    self.assertEqual(result['status'],{'identity':'model_identity_failed','finish':'incomplete_generation','usage':'usage_validation_failed'}[failure])
                    v.run(root,c,p,backend=b);self.assertEqual(b.count,1)
                    other=project/'runs/v5-main-qwen-302';otherconfig={**v.read(project/'configs/v5/v5-main-qwen-302.json'),'backend':'hf'}
                    blocked=v.run(other,otherconfig,p,backend=b);self.assertEqual(blocked['responses'],0);self.assertEqual(b.count,1)

    def test_full_freeze_allocation_and_frozen_artifact_drift(self):
        project,c,p=hf_fixture(self.base);root=project/'runs'/c['budget_binding']['run_id'];b=CountingBackend()
        with patch.object(v,'ROOT',project):
            good=v.run(root,c,p,stage='probes',backend=b);self.assertEqual(good['responses'],4)
            target=project/'scripts/analyze_v5_study.py';target.write_text('# changed\n')
            with self.assertRaisesRegex(ValueError,'artifact bytes changed'):v.run(root,c,p,stage='donors',backend=b)
            self.assertEqual(b.count,4)

    def test_closure_blocks_new_dispatch_and_hard_case_budget(self):
        b=CountingBackend();v.run(self.root,self.config,self.protocol,backend=b)
        calls=v.V5Calls(self.root,self.config,self.protocol,b)
        with self.assertRaisesRegex(v.CallStopped,'budget_exhausted'):calls.call('new-slot',[],{})
        self.assertEqual(b.count,68)
        (self.base/'docs').mkdir();v.immutable_json(self.base/'docs/v5-closeout-record.json',{'closed':True})
        other=self.base/'other';other.mkdir()
        with patch.object(v,'ROOT',self.base):
            with self.assertRaisesRegex(ValueError,'closed'):v.run(other,self.config,self.protocol,backend=b)
            with self.assertRaisesRegex(v.CallStopped,'study_closed'):v.V5Calls(other,self.config,self.protocol,b).call('fresh',[],{})
        self.assertEqual(b.count,68)

    def test_closure_between_initial_check_and_lock_cannot_mutate_run(self):
        original_lock=v.RunLock; base=self.base
        class ClosingLock:
            def __init__(self,root):self.inner=original_lock(root)
            def __enter__(self):
                v.immutable_json(base/'docs/v5-closeout-record.json',{'closed':True})
                return self.inner.__enter__()
            def __exit__(self,*args):return self.inner.__exit__(*args)
        b=CountingBackend()
        with patch.object(v,'ROOT',self.base),patch.object(v,'RunLock',ClosingLock):
            with self.assertRaisesRegex(ValueError,'closed before'):
                v.run(self.root,self.config,self.protocol,backend=b)
        self.assertEqual(b.count,0)
        self.assertFalse((self.root/'manifest.json').exists())


if __name__=='__main__':unittest.main()
