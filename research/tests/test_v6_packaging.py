"""Synthetic-only tests. No live study results, providers or accounts are used."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE if (HERE / 'package_v6_study.py').exists() else HERE.parent / 'scripts'
spec = importlib.util.spec_from_file_location('v6_packager_tests', SCRIPTS / 'package_v6_study.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
spec = importlib.util.spec_from_file_location('v6_verifier_tests', SCRIPTS / 'verify_v6_package.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (list, dict)): value = p.json_bytes(value)
    if isinstance(value, bytes): path.write_bytes(value)
    else: path.write_text(value)


def receipt(archive_sha):
    return {'archive_sha256': archive_sha, 'models_called': False, **dict.fromkeys((
        'package_inventory_verified', 'v5_substantive_json_equal', 'v5_independent_check_passed',
        'v5_independent_substantive_json_equal', 'both_populations_recomputed',
        'posthoc_substantive_json_equal', 'posthoc_independent_check_passed'), True)}


def fixture(base):
    workspace = base / 'workspace'; study = workspace / 'output/control-v6'; report = workspace / 'output/report-v6'
    original = base / 'historical-original'; put(original / 'README.md', 'historical original sentinel')
    old_files = {'README.md': b'Original V5 entry; preserve these bytes.\n',
                 'historical/raw.json': b'{"synthetic": true, "value": 31}\n'}
    fake_old_verifier = '''import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--archive',type=Path);p.add_argument('--original');p.add_argument('--out',type=Path)
a=p.parse_args();a.out.mkdir(parents=True)
value=RECEIPT
value['archive_sha256']=hashlib.sha256(a.archive.read_bytes()).hexdigest()
(a.out/'offline-verification.json').write_text(json.dumps(value))
'''.replace('RECEIPT', repr(receipt('synthetic')))
    old_files['scripts/verify_v5_package.py'] = fake_old_verifier.encode()
    old = {'schema_version': 1, 'study_version': 5, 'source_project': str(original),
           'required_files': ['README.md'], 'files': {n: p.entry(b) for n, b in old_files.items()}}
    baseline = base / 'synthetic-v5.zip'
    with zipfile.ZipFile(baseline, 'w') as z:
        z.writestr(p.BASE_MANIFEST, p.json_bytes(old))
        for n, b in old_files.items(): z.writestr(n, b)
    prior = base / 'prior-pass.json'; put(prior, receipt(p.sha(baseline.read_bytes())))
    for name in p.REQUIRED_STUDY: put(study / name, 'SYNTHETIC FIXTURE ONLY\n')
    for name in p.REQUIRED_REPORT: put(report / name, 'SYNTHETIC FIXTURE ONLY\n')
    for run in p.RUN_IDS:
        for name in ('manifest.json', 'summary.json', 'schedule.json'):
            put(study / 'runs' / run / name, {'synthetic_fixture_only': True})
        put(study / 'configs' / (run + '.json'), {'synthetic_fixture_only': True})
    put(study / 'runs/phase6-budget.json', {'allocations': {r: {} for r in p.RUN_IDS}})
    put(study / 'docs/v6-protocol.json', {'synthetic_fixture_only': True})
    raw = {f.relative_to(study).as_posix(): p.sha(f.read_bytes()) for run in p.RUN_IDS
           for f in (study / 'runs' / run).rglob('*') if f.is_file()}
    put(study / 'docs/v6-closeout-record.json', {'state': 'CLOSED_NO_FURTHER_DISPATCH', 'closed_at': 'synthetic-only',
         'runs': [{'run': r} for r in p.RUN_IDS], 'raw_inventory': raw})
    analysis = {'schema_version': 6, 'evidence_class': 'V6_FIXED_HANDOFF_SHARED_CONVENTION',
                'synthetic_fixture_only': True, 'eligible_joint_episodes': 0, 'value': 7,
                'closeout_sha256': p.sha((study / 'docs/v6-closeout-record.json').read_bytes())}
    put(study / 'analysis/v6-analysis.json', analysis)
    guard = f'''import argparse,hashlib,json,os,socket,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',type=Path);p.add_argument('--root',type=Path);p.add_argument('--out',type=Path);p.add_argument('--output',type=Path)
a=p.parse_args()
assert sys.flags.isolated and sys.flags.no_site
assert 'HF_TOKEN' not in os.environ and 'PYTHONPATH' not in os.environ
for operation in (lambda:open({str(original / 'README.md')!r}).read(), lambda:os.listdir({str(workspace)!r}),lambda:open({str(study / 'docs/v6-protocol.json')!r}).read(),lambda:socket.socket(),lambda:subprocess.run(['echo','unexpected'])):
 try:operation()
 except PermissionError:pass
 else:raise AssertionError('Isolation failed')
'''
    put(study / 'scripts/analyze_v6_study.py', guard + 'a.out.write_text(json.dumps(' + repr(analysis) + '))\n')
    checker = guard + "a.output.write_text(json.dumps({'success':True,'errors':[],'preflight_only':False,'synthetic_fixture_only':True,'value':8,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}))\n"
    put(study / 'scripts/check_v6_raw.py', checker)
    put(study / 'analysis/independent-raw-check.json', {'success': True, 'errors': [], 'preflight_only': False,
         'synthetic_fixture_only': True, 'value': 8, 'checker_sha256': p.sha(checker.encode())})
    put(study / 'docs/v6-freeze.json', {'ledger_sha256': p.sha((study / 'runs/phase6-budget.json').read_bytes()),
         'artifacts': {name: p.sha((study / name).read_bytes()) for name in
                       ('scripts/analyze_v6_study.py', 'scripts/check_v6_raw.py', 'scripts/v6_runner.py', 'runs/phase6-budget.json')}})
    comparison_code = guard + "r=a.project; value={'success':True,'mismatches':0,'analysis_sha256':hashlib.sha256((r/'analysis/v6-analysis.json').read_bytes()).hexdigest(),'independent_check_sha256':hashlib.sha256((r/'analysis/independent-raw-check.json').read_bytes()).hexdigest(),'closeout_sha256':hashlib.sha256((r/'docs/v6-closeout-record.json').read_bytes()).hexdigest(),'comparison_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}; a.out.write_text(json.dumps(value))\n"
    put(study / 'scripts/compare_v6_analyses.py', comparison_code)
    put(study / 'analysis/independent-crosscheck.json', {'success': True, 'mismatches': 0,
         **{key: p.sha((study / name).read_bytes()) for key,name in (
             ('analysis_sha256','analysis/v6-analysis.json'), ('independent_check_sha256','analysis/independent-raw-check.json'),
             ('closeout_sha256','docs/v6-closeout-record.json'), ('comparison_script_sha256','scripts/compare_v6_analyses.py'))}})
    report_fixture(study, report)
    return study, report, baseline, prior


def report_fixture(study, report):
    evidence = [{'path': p.STUDY + '/' + name, 'sha256': p.sha((study / name).read_bytes())} for name in (
        'analysis/v6-analysis.json', 'analysis/independent-raw-check.json', 'analysis/independent-crosscheck.json',
        'docs/v6-protocol.json','docs/v6-freeze.json','docs/v6-closeout-record.json')]
    put(report / 'source/report-input.json', {'ready_for_final':True, 'synthetic_fixture_only':True, 'abstract':' '.join(['Synthetic']*200), 'blocks':[{'rows':[['nested','table'],['valid','structure']]}], 'evidence_inputs':evidence})
    put(report / 'inherited-collusion-v6.pdf', b'%PDF-SYNTHETIC-ONLY')
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:z.writestr('word/document.xml','<document><p>Synthetic software fixture only.</p></document>')
    put(report / 'inherited-collusion-v6.docx', data.getvalue())
    artifacts=[{'path':name,**p.entry((report / name).read_bytes())} for name in p.REQUIRED_REPORT[:2]]
    put(report / 'renders/page-1.png', b'SYNTHETIC-PAGE-FIXTURE')
    put(report / 'source/visual-review.json', {'status':'PASS','input_sha256':p.sha((report / 'source/report-input.json').read_bytes()),
        'artifacts':artifacts,'total_pages':1,'main_pages':1,'abstract_words':200,'pages_inspected':[1],
        'page_images':[{'page':1,'path':'renders/page-1.png','sha256':p.sha((report / 'renders/page-1.png').read_bytes())}]})
    put(report / 'figures/v6-safe-conventions.audit.json', {
        'analysis_sha256':p.sha((study / 'analysis/v6-analysis.json').read_bytes()),
        'closure_sha256':p.sha((study / 'docs/v6-closeout-record.json').read_bytes()),
        'script_sha256':p.sha((report / 'source/plot_v6_results.py').read_bytes()),
        'files':[{'path':'v6-safe-conventions.'+ext,**p.entry((report / ('figures/v6-safe-conventions.'+ext)).read_bytes())} for ext in ('png','pdf','svg')]})
    put(report / 'inherited-collusion-v6.audit.json', {'draft':False,'rendered':True,'visual_review_status':'PASS','visual_review_required':False,
        'input_sha256':p.sha((report / 'source/report-input.json').read_bytes()),'builder_sha256':p.sha((report / 'source/build_report.py').read_bytes()),
        'source_sha256':p.sha((report / 'source/official-template.docx').read_bytes()),'evidence_inputs':evidence,'artifact_files':artifacts,'pages':1,'main_pages':1,'abstract_words':200,
        'final_reviews':[{'path':'source/visual-review.json','sha256':p.sha((report / 'source/visual-review.json').read_bytes())}]})


class PackagingTests(unittest.TestCase):
    def build(self, args, out):
        with contextlib.redirect_stdout(io.StringIO()):
            return p.build(*args, out, expected_base_sha=p.sha(args[2].read_bytes()), scripts=SCRIPTS)

    def test_every_old_member_preserved_with_only_readme_relocated(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); args = fixture(base)
            put(args[0] / '.env', 'excluded'); put(args[0] / 'scripts/__pycache__/a.pyc', 'excluded')
            put(args[0] / 'runs/unrelated/request.json', '{}')
            put(args[1] / 'draft-layout/secret.txt', 'excluded')
            put(args[1] / 'source/history-v5/old.png', 'excluded')
            archive = self.build(args, base / 'bundle'); root = base / 'extracted'
            manifest, files = v.extract(archive, root); old, prior = v.preserved_baseline(root, manifest)
            self.assertEqual(len(old['files']), 3)
            self.assertIn(p.BASE_MANIFEST, files)
            self.assertEqual(files[p.HISTORY + '/files/README.md'], b'Original V5 entry; preserve these bytes.\n')
            self.assertIn(b'V6-START-HERE.md', files['README.md'])
            self.assertFalse(any('.env' in n or 'unrelated' in n or 'draft-layout' in n or '__pycache__' in n or 'history-v5' in n for n in files))
            self.assertEqual(manifest['baseline']['zip_members'], 4)

    def test_full_offline_reproduction_originals_absent_and_history_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); args = fixture(base); archive = self.build(args, base / 'bundle')
            (base / 'workspace').rename(base / 'workspace-unavailable')
            (base / 'historical-original').rename(base / 'old-unavailable')
            result = v.verify(archive, base / 'verification', recheck=True)
            self.assertTrue(result['passed'])
            self.assertTrue(result['v6_analysis_exact_json_equal'])
            self.assertTrue(result['v6_independent_exact_json_equal'])
            self.assertTrue(result['historical_reproduction']['recomputed'])
            self.assertFalse(result['models_called'])
            self.assertEqual(result['v6_allowed_json_differences'], [])

    def test_before_closure_no_current_calls_or_outcomes_are_opened(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); args = fixture(base); (args[0] / 'docs/v6-closeout-record.json').unlink()
            with patch.object(p, 'collect', side_effect=AssertionError('Current evidence read')):
                with self.assertRaisesRegex(ValueError, 'has not closed'):self.build(args, base / 'bundle')

    def test_missing_final_sources_and_tampered_seals_fail_closed(self):
        for change in ('raw', 'frozen', 'ledger', 'template', 'input_generator', 'report_pdf', 'check', 'closure_binding'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); args = fixture(base); study, report, _, _ = args
                if change == 'raw':put(study / 'runs' / p.RUN_IDS[0] / 'summary.json', {'changed': True})
                elif change == 'frozen':put(study / 'scripts/v6_runner.py', 'changed')
                elif change == 'ledger':put(study / 'runs/phase6-budget.json', {'allocations': {}})
                elif change == 'template':(report / 'source/official-template.docx').unlink()
                elif change == 'input_generator':(report / 'source/prepare_final_input.py').unlink()
                elif change == 'report_pdf':(report / 'inherited-collusion-v6.pdf').unlink()
                elif change == 'check':put(study / 'analysis/independent-raw-check.json', {'success': False})
                else:
                    a = json.loads((study / 'analysis/v6-analysis.json').read_text()); a['closeout_sha256'] = '0'*64
                    put(study / 'analysis/v6-analysis.json', a)
                with self.assertRaises(ValueError):self.build(args, base / 'bundle')

    def test_secret_symlink_and_wrong_baseline_receipt_rejected(self):
        for change in ('secret', 'symlink', 'receipt'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); args = fixture(base)
                if change == 'secret':put(args[0] / 'docs/bad.txt', 'hf_' + 'Q'*24)
                elif change == 'symlink':(args[0] / 'scripts/link.py').symlink_to(SCRIPTS / 'verify_v6_package.py')
                else:put(args[3], receipt('0'*64))
                with self.assertRaises(ValueError):self.build(args, base / 'bundle')

    def test_numeric_and_type_difference_never_normalized(self):
        with self.assertRaises(ValueError):v.equal_json({'n': 1}, {'n': 2}, 'count')
        with self.assertRaises(ValueError):v.equal_json({'n': 1}, {'n': True}, 'type')
        with self.assertRaises(ValueError):v.equal_json({'n': 1}, {'n': 1.0}, 'type')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); args = fixture(base)
            value = json.loads((args[0] / 'analysis/v6-analysis.json').read_text()); value['value'] = 9
            put(args[0] / 'analysis/v6-analysis.json', value)
            cross=json.loads((args[0]/'analysis/independent-crosscheck.json').read_text());cross['analysis_sha256']=p.sha((args[0]/'analysis/v6-analysis.json').read_bytes());put(args[0]/'analysis/independent-crosscheck.json',cross)
            report_fixture(args[0],args[1])
            archive = self.build(args, base / 'bundle')
            with self.assertRaisesRegex(ValueError, 'differs'):v.verify(archive, base / 'verification')

    def test_report_readiness_binding_visual_pages_and_delivery(self):
        for change in ('draft','pending','input_hash','missing_page','crosscheck_binding','pdf_hash'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                base=Path(tmp);args=fixture(base);study,report,_,_=args
                if change in ('draft','pending'):
                    path=report/'source/report-input.json';value=json.loads(path.read_text())
                    value.update({'ready_for_final':False} if change=='draft' else {'abstract':'PENDING final result'});put(path,value)
                elif change=='input_hash':
                    path=report/'inherited-collusion-v6.audit.json';value=json.loads(path.read_text());value['input_sha256']='0'*64;put(path,value)
                elif change=='missing_page':(report/'renders/page-1.png').unlink()
                elif change=='pdf_hash':put(report/'inherited-collusion-v6.pdf',b'%PDF-changed')
                else:
                    path=study/'analysis/independent-crosscheck.json';value=json.loads(path.read_text());value['analysis_sha256']='0'*64;put(path,value)
                with self.assertRaises(ValueError):self.build(args,base/'bundle')
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);args=fixture(base);archive=self.build(args,base/'bundle')
            v.verify(archive,base/'verification')
            delivery=v.finalize_delivery(archive,base/'verification',base/'delivery')
            for name,expected in delivery['files'].items():self.assertEqual(p.entry((base/'delivery'/name).read_bytes()),expected)
            self.assertTrue(delivery['offline_verification_passed'])
            receipt_path=base/'verification/offline-verification.json';value=json.loads(receipt_path.read_text());value['passed']=False;put(receipt_path,value)
            with self.assertRaises(ValueError):v.finalize_delivery(archive,base/'verification',base/'reject')

    def test_exact_reviewed_page_path_limits_and_placeholder_gate(self):
        for change in ('page_path','main_limit','main_mismatch','abstract_short','abstract_count','todo','tbd','brackets'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                base=Path(tmp);args=fixture(base);study,report,_,_=args
                visual_path=report/'source/visual-review.json';audit_path=report/'inherited-collusion-v6.audit.json';input_path=report/'source/report-input.json'
                visual=json.loads(visual_path.read_text());audit=json.loads(audit_path.read_text());spec=json.loads(input_path.read_text())
                if change=='page_path':
                    # The hash is still present in another report PNG, so hash
                    # membership alone would wrongly accept this page mapping.
                    put(report/'renders/page-999.png',(report/'renders/page-1.png').read_bytes())
                    visual['page_images'][0]['path']='renders/page-999.png'
                elif change=='main_limit':visual['main_pages']=audit['main_pages']=9
                elif change=='main_mismatch':audit['main_pages']=2
                elif change=='abstract_short':spec['abstract']='short';visual['abstract_words']=audit['abstract_words']=1
                elif change=='abstract_count':audit['abstract_words']=201
                else:spec['blocks'].append({'text':{'todo':'TODO result','tbd':'TBD result','brackets':'[[unresolved]]'}[change]})
                put(input_path,spec);audit['input_sha256']=visual['input_sha256']=p.sha(input_path.read_bytes())
                put(visual_path,visual);audit['final_reviews'][0]['sha256']=p.sha(visual_path.read_bytes());put(audit_path,audit)
                with self.assertRaisesRegex(ValueError,{'page_path':'page image path','main_limit':'main-page','main_mismatch':'main-page','abstract_short':'abstract','abstract_count':'abstract'}.get(change,'unresolved markers')):
                    self.build(args,base/'bundle')

    def test_bad_zip_inventory_and_extracted_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); args = fixture(base); archive = self.build(args, base / 'bundle')
            root = base / 'extracted'; manifest, _ = v.extract(archive, root)
            put(root / 'historical/raw.json', '{"changed":true}')
            with self.assertRaises(ValueError):v.verify_tree(root, manifest)
            with zipfile.ZipFile(archive, 'a') as z:z.writestr('../escape', 'bad')
            with self.assertRaises(ValueError):p.inventory_zip(archive, p.MANIFEST)


if __name__ == '__main__':unittest.main()
