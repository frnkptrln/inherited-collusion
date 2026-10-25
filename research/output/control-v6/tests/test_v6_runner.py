"""Isolated V6 software tests; synthetic notes only, no inference or old writes."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import v6_runner as v
import run_v6_study as dispatcher
from v5_scenario import make_checkpoint


def protocol():
    return {'schema_version':6,'structure':'symmetric','cases':{k:list(s) for k,s in v.CASES.items()},
            'models':list(v.MODELS.values()),'modes':list(v.MODES),'conditions':list(v.CONDITIONS),
            'repeats':2,'tie_break_rules':v.TIE_RULES}


def fixture(base):
    project=base/'project';project.mkdir();configs={};allocations={}
    files,package_hash,source_hash=v.sources()
    for name,data in files.items():
        target=project/('scripts' if name.startswith(('v5_','v6_')) else 'inherited_collusion')/name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for name in ('run_v6_study.py','analyze_v6_study.py','check_v6_raw.py','close_v6.py'):
        (project/'scripts'/name).write_text('# synthetic software fixture\n')
    v.immutable_json(project/'docs/v6-protocol.json',protocol())
    copies={};old_inventory={}
    for alias,seeds in v.CASES.items():
        for seed in seeds:
            cp=make_checkpoint(seed,'symmetric');base_input=project/'inputs/v5'/f'{alias}-{seed}'
            v.immutable_json(base_input/'checkpoint.json',cp)
            for mode in v.MODES:
                donor_id=f's{seed}-symmetric-{mode}-p0';plan=cp['plans'][mode]['p0']
                notes={role:f'You take {plan[role]}; your partner takes {plan["B" if role=="A" else "A"]}. Synthetic fixture only.' for role in 'AB'}
                donor={'id':donor_id,'technical_passed':True,'checkpoint_hash':v.digest(cp),'notes':notes,'note_hashes':{r:v.digest(n) for r,n in notes.items()}}
                v.immutable_json(base_input/f'donor-{mode}.json',donor)
                for role in 'AB':
                    folder=base_input/'origin'/(donor_id+'-note-'+role)
                    v.immutable_json(folder/'request.json',{'id':donor_id+'-note-'+role})
                    v.immutable_json(folder/'response.json',{'model':v.MODELS[alias],'finish_reason':'stop','text':v.canonical({'task':plan[role],'note':notes[role]})})
                    baseline=base_input/'origin'/f's{seed}-symmetric-{mode}-verified-r0-{role}'
                    v.immutable_json(baseline/'request.json',{'messages':v.messages(cp,role,notes[role],'verified'),
                        'generation':{'model':v.MODELS[alias],'provider':'deepinfra','max_tokens':8192},'temperature':.6,'top_p':.95})
            name=f'v6-{alias}-{seed}';reserve=v.RESERVES[alias]
            c={'approved':True,'approved_by':'synthetic fixture','price_checked_at':'synthetic','backend':'hf','alias':alias,
               'model':v.MODELS[alias],'seed':seed,'provider':'deepinfra','max_tokens':8192,'max_request_bytes':10000,
               'max_calls':24,'temperature':.6,'top_p':.95,'max_total_usd':round(24*reserve,3),'reserved_usd_per_call':reserve,
               'input_usd_per_million':.1 if alias=='qwen' else .037,'output_usd_per_million':.95 if alias=='qwen' else .17,
               'reservation_basis_confirmed':True,'budget_binding':{'ledger':str(project/'runs/phase6-budget.json'),'run_id':name}}
            configs[name]=c;v.immutable_json(project/'configs'/f'{name}.json',c)
            allocations[name]={'model':c['model'],'seed':seed,'repeats':2,'status':'allocated','max_total_usd':c['max_total_usd'],
                               'config':f'configs/{name}.json','config_digest':v.config_digest(c)}
    for current,old in v.origin_paths().items():
        h=v.sha(project/current);copies[current]={'v5_path':old,'sha256':h};old_inventory[old]=h
    v.immutable_json(project/'evidence/preflight/budget-and-input-provenance.json',
        {'retained_total_usd':13.488,'retained_v5_all_dispatched_reservations_usd':3.566,
         'all_dispatched_calls_including_unresolved_reserved_in_full':True,'source_copies':copies})
    v.immutable_json(project/'evidence/preflight/v5-closeout-record.json',{'state':'CLOSED_NO_FURTHER_DISPATCH','raw_inventory':old_inventory})
    for name in ('v5-freeze.json','v5-protocol.json','independent-input-check.json','hf-preflight.json'):
        v.immutable_json(project/'evidence/preflight'/name,{'synthetic':True})
    v.immutable_json(project/'runs/phase6-budget.json',{'schema_version':1,'authorized_total_usd':15,
        'historical_allocated_usd':13.488,'phase_max_usd':1.248,'freeze_record':'docs/v6-freeze.json','allocations':allocations})
    artifacts={p.relative_to(project).as_posix():v.sha(p) for p in project.rglob('*') if p.is_file()}
    freeze={'source_hash':source_hash,'package_source_hash':package_hash,'protocol_hash':v.digest(protocol()),
        'ledger_sha256':v.sha(project/'runs/phase6-budget.json'),'config_digests':{n:v.config_digest(c) for n,c in configs.items()},'artifacts':artifacts}
    v.immutable_json(project/'docs/v6-freeze.json',freeze)
    return project,configs


class Backend(v.V6MockBackend):
    def __init__(self,fail_at=None,change=None):self.count=0;self.fail_at=fail_at;self.change=change
    def complete(self,prompt,meta,config):
        self.count+=1
        if self.count==self.fail_at:
            error=RuntimeError('PRIVATE URL HEADERS BODY')
            error.response=type('R',(),{'status_code':504})()
            raise error
        response=super().complete(prompt,meta,config)
        if config['backend']=='hf':
            response['usage']={'prompt_tokens':10,'completion_tokens':20,'estimated_cost':.00001}
            response['provider_response']={'model':response['model'],'usage':response['usage'],
                'choices':[{'message':{'content':response['text']},'finish_reason':response['finish_reason']}]}
        if self.change:response=self.change(response,meta)
        return response


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.project,self.configs=fixture(self.base);self.config=self.configs['v6-qwen-301'];self.root=self.project/'runs/v6-qwen-301'
        self.root_patch=patch.object(v,'ROOT',self.project);self.root_patch.start()
    def tearDown(self):self.root_patch.stop();self.temp.cleanup()

    def test_full_mock_resume_snapshot_and_role_counterbalance(self):
        config={**self.config,'backend':'mock','provider':'none','max_total_usd':0,'reserved_usd_per_call':0};b=Backend()
        first=v.run(self.root,config,protocol(),backend=b,stop_after=3)
        self.assertEqual((first['completed_episodes'],b.count),(3,6))
        stamps={p:p.read_bytes() for p in (self.root/'calls').glob('*/first_dispatch.json')}
        final=v.run(self.root,config,protocol(),backend=b);self.assertEqual((final['completed_episodes'],b.count),(12,24))
        v.run(self.root,config,protocol(),backend=b);self.assertEqual(b.count,24)
        for p,data in stamps.items():self.assertEqual(p.read_bytes(),data)
        for name in ('checkpoint.json','donor-harmful.json','donor-legitimate.json'):
            self.assertEqual((self.root/'input_snapshot'/name).read_bytes(),(self.project/'inputs/v5/qwen-301'/name).read_bytes())
        self.assertEqual((self.root/'source_snapshot/v6_runner.py').read_bytes(),(SCRIPTS/'v6_runner.py').read_bytes())
        schedule=v.read(self.root/'schedule.json')['episodes'];self.assertEqual(len(schedule),12)
        for mode in v.MODES:
            for arm in v.CONDITIONS:
                pair=[row['role_order'] for row in schedule if row['mode']==mode and row['condition']==arm]
                self.assertEqual(sorted(pair),[['A','B'],['B','A']])

    def test_baseline_exact_remove_only_intervention_and_note_unchanged(self):
        cp,donors,_=v.load_inputs(self.config)
        for donor in donors.values():
            for role in 'AB':
                baseline=v.messages(cp,role,donor['notes'][role],'verified')
                self.assertEqual(baseline,v.verified_messages(cp,role,donor['notes'][role],True))
                for arm,rule in v.TIE_RULES.items():
                    current=v.messages(cp,role,donor['notes'][role],arm)
                    self.assertEqual(current[0],baseline[0]);self.assertEqual(current[1]['content'].replace('\n\n'+rule,'',1),baseline[1]['content'])
                    self.assertLess(current[1]['content'].index(rule),current[1]['content'].index('<previous_role_handoff'))
                    self.assertIn(donor['notes'][role],current[1]['content'])
                    self.assertNotIn('T1',rule);self.assertNotIn('T2',rule)
        pairs=v.optimal_pairs(cp);self.assertEqual(len(pairs),2);self.assertNotEqual(pairs[0],pairs[-1])
        for pair in pairs:
            o=v.score(cp,dict(zip('AB',pair)));self.assertEqual(o['violations'],0);self.assertEqual(o['total_cost'],o['reference']['total_cost'])

    def test_hf_shaped_response_raw_before_parse_and_no_repair(self):
        def change(r,m):r['text']='{"task":"UNKNOWN"}';r['provider_response']['choices'][0]['message']['content']=r['text'];return r
        b=Backend(change=change);result=v.run(self.root,self.config,protocol(),backend=b)
        self.assertEqual(result['status'],'successor_schema_failed');self.assertEqual(b.count,1)
        raw=list((self.root/'calls').glob('*/response.json'));self.assertEqual(len(raw),1)
        self.assertEqual(v.read(raw[0])['text'],'{"task":"UNKNOWN"}')
        ep=list((self.root/'episodes').glob('*.json'));self.assertEqual(v.read(ep[0])['status'],'protocol_error');self.assertIsNone(v.read(ep[0])['outcome'])
        v.run(self.root,self.config,protocol(),backend=b);self.assertEqual(b.count,1)

    def test_ambiguous_tail_never_retried_and_valid_prefix_retained(self):
        b=Backend(fail_at=5);first=v.run(self.root,self.config,protocol(),backend=b)
        self.assertEqual((first['status'],first['completed_episodes'],first['reserved_calls'],first['responses']),('unresolved_provider_call',2,5,4))
        errors=list((self.root/'calls').glob('*/error.json'));self.assertEqual(v.read(errors[0])['status_code'],504)
        self.assertNotIn('PRIVATE',errors[0].read_text())
        next_backend=Backend();again=v.run(self.root,self.config,protocol(),backend=next_backend)
        self.assertEqual((again['completed_episodes'],again['reserved_calls'],next_backend.count),(2,5,0))
        calls=v.V6Calls(self.root,self.config,protocol(),next_backend)
        with self.assertRaises(v.CallStopped) as e:calls.call('new-id',[],{})
        self.assertEqual(e.exception.status,'unresolved_provider_call');self.assertEqual(next_backend.count,0)

    def test_model_stop_blocks_only_new_calls_but_preserves_other_case_cache(self):
        other=self.configs['v6-qwen-303'];other_root=self.project/'runs/v6-qwen-303';good=Backend()
        v.run(other_root,other,protocol(),backend=good,stop_after=1)
        def mismatch(r,m):r['model']='unexpected-model';return r
        bad=Backend(change=mismatch);result=v.run(self.root,self.config,protocol(),backend=bad)
        self.assertEqual(result['status'],'model_identity_failed');self.assertEqual(len(list((self.root/'calls').glob('*/response.json'))),1)
        resumed=Backend();again=v.run(other_root,other,protocol(),backend=resumed)
        self.assertEqual((again['completed_episodes'],again['status'],resumed.count),(1,'model_identity_failed',0))
        third=self.configs['v6-gptoss-301'];third_backend=Backend()
        v.run(self.project/'runs/v6-gptoss-301',third,protocol(),backend=third_backend,stop_after=1);self.assertEqual(third_backend.count,2)

    def test_usage_and_truncation_durable_hard_stop(self):
        for kind in ('usage','length'):
            with self.subTest(kind=kind):
                alias='qwen' if kind=='usage' else 'gptoss';cfg=self.configs[f'v6-{alias}-301'];root=self.project/'runs'/f'v6-{alias}-301'
                def change(r,m):
                    if kind=='usage':r['usage'].pop('estimated_cost')
                    else:r['finish_reason']='length'
                    return r
                b=Backend(change=change);result=v.run(root,cfg,protocol(),backend=b)
                self.assertEqual(result['status'],'usage_validation_failed' if kind=='usage' else 'incomplete_generation')
                self.assertEqual(len(list((root/'calls').glob('*/response.json'))),1)
                before=b.count;v.run(root,cfg,protocol(),backend=b);self.assertEqual(before,b.count)

    def test_freeze_config_source_and_input_mutations_block_before_call(self):
        targets=['inputs/v5/qwen-301/donor-harmful.json','scripts/check_v6_raw.py','configs/v6-gptoss-306.json',
                 'inputs/v5/gptoss-306/origin/s306-symmetric-legitimate-p0-note-B/response.json']
        for name in targets:
            path=self.project/name;before=path.read_bytes();path.write_bytes(before+b' ');b=Backend()
            with self.subTest(name=name),self.assertRaises(ValueError):v.run(self.root,self.config,protocol(),backend=b)
            self.assertEqual(b.count,0);path.write_bytes(before)
        bad_protocol=copy.deepcopy(protocol());bad_protocol['tie_break_rules']['tie_first']+=' changed'
        with self.assertRaises(ValueError):v.run(self.root,self.config,bad_protocol,backend=Backend())

    def test_budget_binding_and_total_rejected(self):
        config={**self.config,'max_total_usd':.25}
        with self.assertRaises(ValueError):v.validate_config(config)
        ledger=self.project/'runs/phase6-budget.json';value=v.read(ledger);value['historical_allocated_usd']=14
        v.atomic_json(ledger,value)
        with self.assertRaisesRegex(ValueError,'historical'):v.run(self.root,self.config,protocol(),backend=Backend())

    def test_closure_blocks_new_and_cached_mutation_including_lock_race(self):
        b=Backend();v.run(self.root,self.config,protocol(),backend=b,stop_after=1)
        before={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        original_lock=v.RunLock
        class RacingLock(original_lock):
            def __enter__(self):
                result=super().__enter__();v.immutable_json(self_project/'docs/v6-closeout-record.json',{'closed':True});return result
        self_project=self.project
        with patch.object(v,'RunLock',RacingLock),self.assertRaisesRegex(ValueError,'closed before'):v.run(self.root,self.config,protocol(),backend=b)
        after={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after);self.assertEqual(b.count,2)
        with self.assertRaisesRegex(ValueError,'permanently closed'):v.run(self.root,self.config,protocol(),backend=b)

    def test_dispatcher_preserves_venv_path_and_does_not_retry(self):
        executable=self.base/'venv/bin/python';executable.parent.mkdir(parents=True);executable.symlink_to(sys.executable)
        items=dispatcher.plan(self.project,model='qwen',seeds=[301],python=executable)
        self.assertEqual(items[0][2][0],str(executable));self.assertNotEqual(items[0][2][0],str(executable.resolve()))
        with patch.object(dispatcher.subprocess,'run',return_value=type('R',(),{'returncode':2})()) as called:
            receipt=dispatcher.execute(items[0],'synthetic-time',self.project)
        self.assertEqual(called.call_count,1);self.assertEqual(receipt['returncode'],2)
        self.assertEqual(len(list((self.root/'invocation_logs').glob('*.start.json'))),1)
        self.assertEqual(len(list((self.root/'invocation_logs').glob('*.result.json'))),1)
        with self.assertRaises(ValueError):dispatcher.plan(self.project,model='qwen',seeds=[302])


if __name__=='__main__':unittest.main()
