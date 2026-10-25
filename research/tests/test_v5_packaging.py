"""Synthetic-only archive/orchestration tests; no live outcomes or model calls.

Tiny deterministic analysis programs below exercise the full verifier pipeline.
They are deliberately not substitutes for a final real archive reproduction.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE if (HERE / 'package_v5_study.py').is_file() else HERE.parent / 'scripts'
CORE = SCRIPTS / 'verify_offline_package.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load('v5_packager_test', SCRIPTS / 'package_v5_study.py')
v = load('v5_verifier_test', SCRIPTS / 'verify_v5_package.py')


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, indent=2) + '\n'
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value)


ARGUMENTS = '''import argparse,hashlib,json,os,socket,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',type=Path);p.add_argument('--out',type=Path)
p.add_argument('--strict-analysis',type=Path);p.add_argument('--final-analysis',type=Path)
p.add_argument('--diagnostic',type=Path);p.add_argument('--diagnostic-script',type=Path);p.add_argument('--analysis',type=Path)
a=p.parse_args()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\\n')
'''


def synthetic_project(base):
    project = base / 'original'
    for name in p.REQUIRED:
        put(project / name, 'SYNTHETIC SOFTWARE FIXTURE, NOT A RESEARCH RESULT\n')
    put(project / 'README.md', 'original reviewed text\n')
    put(project / 'scripts/verify_offline_package.py', CORE.read_bytes())
    put(project / 'scripts/verify_v5_package.py', (SCRIPTS / 'verify_v5_package.py').read_bytes())
    put(project / 'scripts/package_v5_study.py', (SCRIPTS / 'package_v5_study.py').read_bytes())
    strict = {'analyzed_at': 'old', 'synthetic_value': 7}
    put(project / 'output/analysis-v4/analysis.json', strict)
    strict_sha = p.sha((project / 'output/analysis-v4/analysis.json').read_bytes())
    put(project / 'output/analysis-v4f/analysis.json', {'analyzed_at': 'old', 'synthetic_value': 8,
        'strict_planned_completion_bounds': {'input_analysis_sha256': strict_sha, 'value': 9}})
    put(project / 'scripts/analyze_v4_study.py', ARGUMENTS + "save(a.out,{'analyzed_at':'new','synthetic_value':7})\n")
    put(project / 'scripts/analyze_v4f_study.py', ARGUMENTS + "save(a.out,{'analyzed_at':'new','synthetic_value':8,'strict_planned_completion_bounds':{'input_analysis_sha256':digest(a.strict_analysis),'value':9}})\n")
    for suffix in ('v4', 'v4f'):
        put(project / f'evidence/{suffix}-independent/check_results.py', ARGUMENTS + "save(a.out/'independent-check.json',{'passed':True,'mismatches':[]})\n")
    diagnostic = project / 'evidence/oct24-review/baseline_diagnostic.py'
    put(diagnostic, ARGUMENTS + "save(a.out/'baseline-diagnostic.json',{'generated_at':'new','passed':True,'script_sha256':digest(Path(__file__)),'synthetic_value':10})\n")
    put(project / 'evidence/oct24-review/baseline-diagnostic.json', {
        'generated_at': 'old', 'passed': True, 'script_sha256': p.sha(diagnostic.read_bytes()), 'synthetic_value': 10})
    put(project / 'evidence/oct24-review/check_baseline.py', ARGUMENTS + "save(a.out,{'passed':True,'mismatches':[],'raw_row_checks':0})\n")
    model_result = {'schema_version': 5, 'generated_at': 'old',
        'evidence_class': 'POSTHOC_MOTIVATED_PROSPECTIVELY_FROZEN_CONTROL',
        'synthetic_fixture_only': True, 'synthetic_value': 11}
    put(project / v.ANALYSIS, model_result)
    # Explicitly exercise denied original reads/network/child execution in the
    # isolated analysis process; no attempted connection leaves the process.
    guard = f'''assert sys.flags.isolated and sys.flags.no_site
assert 'HF_TOKEN' not in os.environ and 'PYTHONPATH' not in os.environ
for operation in (lambda:open({str(project / 'README.md')!r}).read(),lambda:socket.socket(),lambda:subprocess.run(['echo','unexpected'])):
 try:operation()
 except PermissionError:pass
 else:raise AssertionError('Expected isolation failure')
value=json.loads((a.project/'{v.ANALYSIS}').read_text());value['generated_at']='new';save(a.out,value)
'''
    put(project / 'scripts/analyze_v5_study.py', ARGUMENTS + guard)
    checker = ARGUMENTS + '''raw=a.project/'runs/v5-main-qwen-301/summary.json'
save(a.out,{'checked_at':'new','passed':True,'mismatches':[],'raw_rows_checked':0,
 'checker_sha256':digest(Path(__file__)),'analysis_sha256':digest(a.analysis),
 'input_sha256':{str(a.analysis.resolve()):digest(a.analysis),str(raw):digest(raw)},'synthetic_value':12})
'''
    put(project / 'scripts/check_v5_raw.py', checker)
    for run in p.RUN_IDS:
        for suffix in ('manifest.json', 'summary.json', 'schedule.json'):
            put(project / 'runs' / run / suffix, {'synthetic': True, 'status': 'completed'})
        put(project / 'configs/v5' / (run + '.json'), {'synthetic': True})
    put(project / 'runs/phase5-budget.json', {'allocations': {name: {} for name in p.RUN_IDS}})
    historical_ledgers = ('runs/budget-ledger.json', 'runs/phase3-budget.json', 'runs/phase4f-budget.json')
    for name in historical_ledgers:
        put(project / name, {'synthetic_historical_allocation': True})
    put(project / 'docs/v5-freeze.json', {'ledger_sha256': p.sha((project / 'runs/phase5-budget.json').read_bytes()),
        'artifacts': {name: p.sha((project / name).read_bytes())
                      for name in ('scripts/v5_runner.py', *historical_ledgers)}})
    raw_inventory = {file.relative_to(project).as_posix(): p.sha(file.read_bytes())
        for run in p.RUN_IDS for file in (project / 'runs' / run).rglob('*') if file.is_file()}
    put(project / 'docs/v5-closeout-record.json', {'state': 'CLOSED_NO_FURTHER_DISPATCH',
        'closed_at': 'synthetic', 'runs': [{'run': name} for name in p.RUN_IDS], 'raw_inventory': raw_inventory})
    raw = project / 'runs/v5-main-qwen-301/summary.json'
    analysis = project / v.ANALYSIS
    put(project / v.CHECK, {'checked_at': 'old', 'passed': True, 'mismatches': [], 'raw_rows_checked': 0,
        'checker_sha256': p.sha((project / 'scripts/check_v5_raw.py').read_bytes()),
        'analysis_sha256': p.sha(analysis.read_bytes()),
        'input_sha256': {str(analysis): p.sha(analysis.read_bytes()), str(raw): p.sha(raw.read_bytes())}, 'synthetic_value': 12})
    base_names = [path.relative_to(project).as_posix() for path in project.rglob('*')
                  if path.is_file() and 'v5' not in path.relative_to(project).as_posix() and path.name != 'phase5-budget.json']
    baseline = {'schema_version': 1, 'files': {name: p.entry((project / name).read_bytes()) for name in base_names},
        'required_files': ['README.md'], 'required_nonempty_directories': ['scripts']}
    archive = base / 'reviewed-v4.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr(p.BASE_MANIFEST, json.dumps(baseline))
        for name in base_names:
            z.writestr(name, (project / name).read_bytes())
    return project, archive


class PackageTests(unittest.TestCase):
    def make_archive(self, project, baseline, out):
        with contextlib.redirect_stdout(io.StringIO()):
            return p.build(project, baseline, out, p.sha(baseline.read_bytes()))

    def test_preserves_every_baseline_byte_and_only_allowlisted_new_files(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp);project, baseline = synthetic_project(base)
            put(project / 'README.md', 'new control text\n')
            put(project / '.env', 'secret omitted')
            put(project / 'scripts/__pycache__/x.pyc', 'omitted')
            put(project / 'runs/unrelated-job/response.json', '{}')
            put(project / 'output/unrelated/private.txt', 'omitted')
            archive = self.make_archive(project, baseline, base / 'bundle')
            core = v.load_core(CORE)
            manifest = core.extract_verified(archive, base / 'extracted')
            self.assertGreater(v.check_baseline_preserved(core, base / 'extracted', manifest), 0)
            self.assertEqual((base / 'extracted/README.md').read_text(), 'new control text\n')
            old = manifest['baseline']['preserved_overrides']['README.md']
            self.assertEqual((base / 'extracted' / old).read_text(), 'original reviewed text\n')
            self.assertFalse(any(name.endswith('.pyc') or 'unrelated' in name or '.env' in name for name in manifest['files']))
            self.assertIn('output/report-v5/source/requirements-report.txt', manifest['files'])

    def test_missing_closeout_or_changed_raw_and_frozen_sources_fail_closed(self):
        for kind in ('closeout', 'raw', 'frozen', 'historical_ledger', 'report', 'template', 'input_builder', 'template_contract'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                base = Path(temp);project, baseline = synthetic_project(base)
                if kind == 'closeout': (project / 'docs/v5-closeout-record.json').unlink()
                elif kind == 'raw': put(project / 'runs/v5-main-qwen-301/summary.json', {'changed': True})
                elif kind == 'frozen': put(project / 'scripts/v5_runner.py', 'changed')
                elif kind == 'historical_ledger': put(project / 'runs/phase4f-budget.json', {'changed': True})
                elif kind == 'template': (project / 'output/report-v5/source/official-template.docx').unlink()
                elif kind == 'input_builder': (project / 'output/report-v5/source/prepare_final_input.py').unlink()
                elif kind == 'template_contract': (project / 'output/report-v5/source/artifact.md').unlink()
                else: (project / 'output/report-v5/source/build_report.py').unlink()
                with self.assertRaises(ValueError):self.make_archive(project, baseline, base / 'bundle')
                self.assertFalse((base / 'bundle/inherited-collusion-v5-research-package.zip').exists())

    def test_secret_symlink_and_wrong_baseline_digest_rejected(self):
        for kind in ('secret', 'symlink', 'digest'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                base = Path(temp);project, baseline = synthetic_project(base)
                if kind == 'secret':put(project / 'docs/sensitive.txt', 'hf_' + 'A' * 24)
                elif kind == 'symlink':(project / 'scripts/link.py').symlink_to(CORE)
                with self.assertRaises(ValueError):
                    if kind == 'digest':p.build(project, baseline, base / 'bundle', '0' * 64)
                    else:self.make_archive(project, baseline, base / 'bundle')

    def test_full_synthetic_pipeline_when_original_directory_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp);project, baseline = synthetic_project(base)
            archive = self.make_archive(project, baseline, base / 'bundle')
            project.rename(base / 'original-unavailable')
            result = v.verify(archive, project, base / 'verification', CORE)
            self.assertTrue(result['both_populations_recomputed'])
            self.assertTrue(result['posthoc_independent_check_passed'])
            self.assertTrue(result['v5_independent_substantive_json_equal'])
            self.assertTrue(result['original_project_read_access_denied'])
            self.assertFalse(result['models_called'])

    def test_numeric_difference_is_not_normalized_and_mock_result_rejected(self):
        a = {'schema_version': 5, 'generated_at': 'old', 'evidence_class': 'POSTHOC_MOTIVATED_PROSPECTIVELY_FROZEN_CONTROL', 'n': 3}
        v.compare_v5_analysis(a, {**a, 'generated_at': 'new'})
        with self.assertRaises(ValueError):v.compare_v5_analysis(a, {**a, 'n': 4})
        mock = {**a, 'evidence_class': 'SOFTWARE_TEST_ONLY_NOT_RESEARCH_RESULTS'}
        with self.assertRaises(ValueError):v.compare_v5_analysis(mock, mock)

    def test_old_verification_source_cannot_be_replaced_by_a_history_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp);project, baseline = synthetic_project(base)
            name = 'evidence/oct24-review/verify_reviewed_package.py'
            put(project / name, 'different old verifier\n')
            archive = self.make_archive(project, baseline, base / 'bundle')
            core = v.load_core(CORE);extracted = base / 'extracted'
            manifest = core.extract_verified(archive, extracted)
            self.assertIn(name, manifest['baseline']['preserved_overrides'])
            with self.assertRaisesRegex(ValueError, 'byte hash mismatch'):
                v.check_baseline_preserved(core, extracted, manifest)

    def test_v5_checker_wrong_input_binding_or_raw_hash_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp);project, baseline = synthetic_project(base)
            archive = self.make_archive(project, baseline, base / 'bundle')
            core = v.load_core(CORE);extracted = base / 'extracted';core.extract_verified(archive, extracted)
            old = json.loads((project / v.CHECK).read_text())
            analysis = base / 'recomputed.json';put(analysis, json.loads((project / v.ANALYSIS).read_text()))
            new = json.loads(json.dumps(old));new['input_sha256'] = {str(analysis): p.sha(analysis.read_bytes()),
                str(extracted / 'runs/v5-main-qwen-301/summary.json'): p.sha((project / 'runs/v5-main-qwen-301/summary.json').read_bytes())}
            v.compare_v5_checks(core, old, new, project, extracted, extracted / v.ANALYSIS, analysis)
            new['input_sha256'][str(analysis)] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'another analysis'):v.compare_v5_checks(core, old, new, project, extracted, extracted / v.ANALYSIS, analysis)
            new['input_sha256'][str(analysis)] = p.sha(analysis.read_bytes())
            new['input_sha256'][str(extracted / 'runs/v5-main-qwen-301/summary.json')] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'differs'):v.compare_v5_checks(core, old, new, project, extracted, extracted / v.ANALYSIS, analysis)


if __name__ == '__main__':
    unittest.main()
