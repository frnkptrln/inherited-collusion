import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('format_runner_tests',ROOT/'scripts/v4f_runner.py')
f=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(f)

class CountBackend(f.v4.V3MockBackend):
    def __init__(self):self.calls=0
    def complete(self,*args):self.calls+=1;return super().complete(*args)

class UnresolvedBackend:
    def complete(self,*args):raise TimeoutError('Synthetic provider timeout; no network')

class TruncatedBackend(CountBackend):
    def complete(self,*args):
        response=super().complete(*args);response['finish_reason']='length';return response

class FormatTests(unittest.TestCase):
    def make_source(self,base,seed=201,stage='donors',complete=False):
        source=Path(base)/f'v4-main-test-{seed}'
        cfg=f.v4.load_config('mock',None,'main',seed)
        f.v4.run(source,cfg,seed,'main',stage)
        if complete:
            template=f.read(source/'reviews'/f's{seed}-annotations.template.json')
            template.update(reviewer='software test only',reviewed_at=f.now())
            for roles in template['annotations'].values():
                for note in roles.values():
                    for key in f.v4.ANNOTATION_FLAGS:note[key]=False
                    for key in f.v4.ANNOTATION_EVIDENCE:note[key]='Simulated annotation; no scientific inference.'
            f.immutable_json(source/'reviews'/f's{seed}-annotations.json',template)
            f.v4.run(source,cfg,seed,'main','all',stop_after=1)
        config={**cfg,'source_run_id':source.name,'qualification_run_id':'v4f-qualification-test-902'}
        return source,config
    def prepare(self,base,source,cfg,seed=201):
        target=Path(base)/f'v4f-main-test-{seed}'
        f.prepare(target,source,cfg,seed,'main',{'version':'format-test-not-research'})
        return target
    def test_exact_envelope_and_strict_json(self):
        body='{"task":"T1","reason":"literal"}'
        for text,kind in ((body,'bare_json'),(' \n```json\n'+body+'\n```\t','single_json_fence'),('```json\r\n'+body+'\r\n```','single_json_fence')):
            self.assertEqual(f.envelope(text)[0],kind)
            self.assertEqual(f.parse_object(text)['task'],'T1')
        invalid=['prefix\n```json\n'+body+'\n```','```json\n'+body+'\n```\npostscript','```\n'+body+'\n```','```JSON\n'+body+'\n```','```json '+body+'```','```json\n'+body+'\n```\n```json\n{}\n```','```json\n{"task":"T1","task":"T2"}\n```','```json\n{"task":"T1","x":NaN}\n```','```json\n{"task":"T1","x":1e999}\n```','```json\n[]\n```','```json\n{"task":"T1","note":"nested ``` marker"}\n```']
        for text in invalid:
            with self.subTest(text=text),self.assertRaises(ValueError):f.parse_object(text)
    def test_same_parser_at_probe_action_note_and_successor_boundaries(self):
        cp=f.v4.probe_checkpoint(201);expect=f.v4.probe_expected(cp)
        value={'task':expect['actions']['A'],'joint_assignment':expect['actions'],'total_cost':expect['total_cost']}
        response={'text':'```json\n'+json.dumps(value)+'\n```','finish_reason':'stop'}
        self.assertTrue(all(f.v4.parse_probe(response,cp,'A',expect)[1].values()))
        self.assertEqual(f.v3.parse_action(response,cp)['task'],value['task'])
        note={'text':'```json\n'+json.dumps({'task':value['task'],'note':'Do not edit this exact payload.'})+'\n```','finish_reason':'stop'}
        self.assertEqual(f.v4.parse_action(note,cp,donor=True)['note'],'Do not edit this exact payload.')
        bad=copy.deepcopy(response);bad['text']='```json\n'+json.dumps({**value,'total_cost':value['total_cost']+1})+'\n```'
        self.assertFalse(all(f.v4.parse_probe(bad,cp,'A',expect)[1].values()))
        response['finish_reason']='length'
        with self.assertRaises(ValueError):f.v4.parse_action(response,cp)
    def test_replay_bytes_gate_recomputation_and_no_redispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,stage='probes')
            path=source/'calls/s201-probe-B-comprehension/response.json';raw=f.read(path);raw['text']='```json\n'+raw['text']+'\n```';f.atomic_json(path,raw)
            oldgate=f.read(source/'gates/s201-probes.json');oldgate['passed']=False;f.atomic_json(source/'gates/s201-probes.json',oldgate)
            target=self.prepare(tmp,source,cfg);backend=CountBackend()
            self.assertFalse((target/'gates/s201-probes.json').exists())
            result=f.run(target,cfg,201,'main','probes',backend=backend)
            self.assertEqual(backend.calls,0);self.assertTrue(result['technical_gates']['probes'])
            self.assertEqual(path.read_bytes(),(target/'calls/s201-probe-B-comprehension/response.json').read_bytes())
            receipt=f.read(target/'parse_receipts/s201-probe-B-comprehension.json')
            self.assertEqual((receipt['execution_source'],receipt['parsing_envelope']),('inherited_v4','single_json_fence'))
            self.assertFalse(f.read(source/'gates/s201-probes.json')['passed'])
    def test_inherited_annotations_acknowledge_old_successor_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,complete=True);target=self.prepare(tmp,source,cfg);backend=CountBackend()
            result=f.run(target,cfg,201,'main','all',backend=backend,stop_after=1)
            self.assertEqual(backend.calls,0);self.assertEqual(result['new_reserved_calls'],0)
            receipt=f.read(target/'reviews/s201-annotations.completion.json')
            self.assertEqual(receipt['kind'],'inherited_pre_successor_annotation')
            self.assertEqual(receipt['inherited_successor_invocations'],2)
            self.assertNotIn('successor_requests_observed',receipt)
            self.assertEqual(receipt['new_successor_requests_at_inheritance'],0)
            original=source/'reviews/s201-annotations.recorded.json'
            self.assertEqual(original.read_bytes(),(target/'original_reviews'/original.name).read_bytes())
    def test_new_calls_only_after_exact_replay_and_count_inherited_reservations(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,complete=True);target=self.prepare(tmp,source,cfg);backend=CountBackend()
            result=f.run(target,cfg,201,'main','all',backend=backend,stop_after=2)
            self.assertEqual((backend.calls,result['inherited_reserved_calls'],result['new_reserved_calls']),(2,24,2))
            limited={**cfg,'max_calls':26};calls=f.V4FCalls(target,limited,backend)
            with self.assertRaisesRegex(RuntimeError,'Budget exhausted'):calls.call('never-dispatched',[{'role':'user','content':'x'}],{'kind':'probe','expected':'T1'})
            self.assertEqual(backend.calls,2)
    def test_no_ambiguous_request_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,stage='probes')
            (source/'calls/s201-probe-A-comprehension/response.json').unlink()
            target=self.prepare(tmp,source,cfg);backend=CountBackend()
            result=f.run(target,cfg,201,'main','probes',backend=backend)
            self.assertEqual(backend.calls,0);self.assertEqual(result['status'],'unresolved_provider_call')
    def test_unresolved_tail_keeps_valid_prefix_without_any_new_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,complete=True)
            original=f.read(source/'manifest.json')['config']
            with self.assertRaisesRegex(RuntimeError,'Provider call'):
                f.v4.run(source,original,201,'main','all',backend=UnresolvedBackend())
            prefix={p.name:p.read_bytes() for p in (source/'episodes').glob('*.json')}
            self.assertEqual(len(prefix),1)
            target=self.prepare(tmp,source,cfg);backend=CountBackend()
            for stage in ('probes','donors','all'):
                result=f.run(target,cfg,201,'main',stage,backend=backend)
                self.assertEqual(result['status'],'unresolved_provider_call')
            self.assertEqual(result['completed_episodes'],1)
            self.assertEqual(result['unresolved_calls'],1)
            self.assertEqual(backend.calls,0)
            self.assertEqual(prefix,{p.name:p.read_bytes() for p in (target/'episodes').glob('*.json')})
            calls=f.V4FCalls(target,cfg,backend)
            with self.assertRaisesRegex(f.CachedReplayStopped,'every new call'):
                calls.call('different-never-dispatched',[{'role':'user','content':'test'}],{'kind':'probe'})
            self.assertFalse((target/'calls/different-never-dispatched/request.json').exists())
            again=f.run(target,cfg,201,'main','all',backend=backend,stop_after=1)
            self.assertEqual((again['completed_episodes'],backend.calls),(1,0))
    def test_truncated_tail_does_not_prevent_cached_prefix_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,complete=True)
            original=f.read(source/'manifest.json')['config']
            with self.assertRaisesRegex(RuntimeError,'Incomplete provider'):
                f.v4.run(source,original,201,'main','all',backend=TruncatedBackend())
            target=self.prepare(tmp,source,cfg);backend=CountBackend()
            self.assertTrue(f.run(target,cfg,201,'main','probes',backend=backend)['technical_gates']['probes'])
            f.run(target,cfg,201,'main','donors',backend=backend)
            with self.assertRaisesRegex(RuntimeError,'Incomplete provider'):
                f.run(target,cfg,201,'main','all',backend=backend)
            result=f.summarize(target)
            self.assertEqual((result['completed_episodes'],result['status'],backend.calls),(1,'incomplete_generation',0))
    def test_reused_generation_tampering_fails_without_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,stage='probes');target=self.prepare(tmp,source,cfg)
            path=target/'calls/s201-probe-A-comprehension/request.json';value=f.read(path);value['temperature']=.77;f.atomic_json(path,value)
            backend=CountBackend()
            with self.assertRaisesRegex(ValueError,'bytes changed'):f.run(target,cfg,201,'main','probes',backend=backend)
            self.assertEqual(backend.calls,0)
    def test_source_mutation_and_early_receipt_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source,cfg=self.make_source(tmp,complete=True)
            path=source/'reviews/s201-annotations.completion.json';r=f.read(path);r['at']='2999-01-01T00:00:00+00:00';f.atomic_json(path,r)
            target=self.prepare(tmp,source,cfg);backend=CountBackend()
            with self.assertRaisesRegex(ValueError,'predates'):f.run(target,cfg,201,'main','all',backend=backend)
            self.assertEqual(backend.calls,0)
            (source/'unplanned-file.txt').write_text('drift')
            with self.assertRaisesRegex(ValueError,'inventory changed'):f.verify_copies(target,full_source=True)
    def test_hf_dispatch_requires_complete_eighteen_run_barrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json';f.atomic_json(path,{'preparation_manifest':str(Path(tmp)/'missing.json')})
            with self.assertRaises(FileNotFoundError):f.check_barrier(Path(tmp),{'backend':'hf','budget_binding':{'ledger':str(path)}})
            f.atomic_json(path,{'allocations':{}})
            with self.assertRaisesRegex(ValueError,'both qualifications'):f.finalize_preparation(path)

class CohortBarrierTests(unittest.TestCase):
    def test_all18_prepared_retired_and_global_old_model_blockers(self):
        from v4f_fixtures import full_cohort
        with tempfile.TemporaryDirectory() as tmp:
            cohort=full_cohort(tmp)
            seal=f.read(cohort['preparation']);self.assertEqual(len(seal['prepared_runs']),18)
            name='v4f-main-qwen-201';cfg={**cohort['configs'][name],'backend':'hf'}
            root=cohort['project']/'runs'/name
            f.check_barrier(root,cfg)
            archive=cohort['project']/'docs/original-ledger.json';original_archive=f.read(archive)
            bad=copy.deepcopy(original_archive);bad['allocations']['v4-main-qwen-201']['config_digest']='wrong'
            f.atomic_json(archive,bad)
            with self.assertRaisesRegex(ValueError,'archived authorized allocation'):f.preparation_payload(cohort['ledger'])
            f.atomic_json(archive,original_archive)
            # A blocker in another original case must stop this model, even
            # though it has not yet appeared in any copied derivative folder.
            other=cohort['sources']['v4f-main-qwen-208']
            f.immutable_json(other/'calls/global-test/model_identity_error.json',{'status':'software_test_marker'})
            with self.assertRaisesRegex(ValueError,'blocks this model'):f.check_barrier(root,cfg)
            f.check_barrier(root,cfg,new_call=False)
            safe={**cohort['configs']['v4f-main-gptoss-201'],'backend':'hf'}
            f.check_barrier(cohort['project']/'runs/v4f-main-gptoss-201',safe)
            # Restore only our disposable fixture, then retirement drift fails.
            (other/'calls/global-test/model_identity_error.json').unlink()
            (other/'calls/global-test').rmdir()
            old=cohort['project']/'runs/phase4-budget.json';value=f.read(old)
            value['allocations']['v4-main-qwen-201']['status']='allocated';f.atomic_json(old,value)
            with self.assertRaisesRegex(ValueError,'Retired source ledger changed'):f.check_barrier(root,cfg)
            with self.assertRaisesRegex(ValueError,'still executable'):f.finalize_preparation(cohort['ledger'])
    def test_fixed_dispatch_plan_never_omits_preparation_or_retries_failures(self):
        from v4f_fixtures import full_cohort
        with tempfile.TemporaryDirectory() as tmp:
            cohort=full_cohort(tmp);project=cohort['project'];protocol=project/'docs/protocol.json'
            spec=importlib.util.spec_from_file_location('test_v4f_dispatcher',project/'scripts/run_v4f_study.py')
            dispatcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(dispatcher)
            self.assertEqual(len(dispatcher.plan(project,cohort['ledger'],protocol,'prepare')),18)
            with self.assertRaisesRegex(ValueError,'all18'):dispatcher.plan(project,cohort['ledger'],protocol,'prepare',model='qwen')
            self.assertEqual(len(dispatcher.plan(project,cohort['ledger'],protocol,'qualification')),2)
            self.assertEqual(len(dispatcher.plan(project,cohort['ledger'],protocol,'probes')),16)
            root=project/'runs/v4f-main-qwen-201';f.atomic_json(root/'summary.json',{'status':'technical_validation_failed'})
            planned=dispatcher.plan(project,cohort['ledger'],protocol,'probes')
            self.assertEqual(len(planned),15);self.assertNotIn(root.name,{name for name,_,_ in planned})
            f.atomic_json(root/'summary.json',{'status':'unresolved_provider_call'})
            self.assertIn(root.name,{name for name,_,_ in dispatcher.plan(project,cohort['ledger'],protocol,'donors')})
            self.assertEqual(dispatcher.plan(project,cohort['ledger'],protocol,'all'),[])
            cohort['preparation'].unlink()
            with self.assertRaisesRegex(ValueError,'Finalize all18'):dispatcher.plan(project,cohort['ledger'],protocol,'probes')

if __name__=='__main__':unittest.main()
