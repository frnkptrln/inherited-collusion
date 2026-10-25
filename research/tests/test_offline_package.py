"""Synthetic-only package invariants; never reads or analyzes live outcomes."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
p=load('package_under_test',ROOT/'scripts/package_v4_study.py')
v=load('verify_under_test',ROOT/'scripts/verify_offline_package.py')

def put(path,text='Synthetic software fixture, not a research result.\n'):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)

def fake_project(root):
    for name in p.REQUIRED_FILES:put(root/name)
    for name in p.REQUIRED_DIRECTORIES:put(root/name/'synthetic.txt')
    put(root/'runs/phase4-budget.json',json.dumps({'allocations':{}}))
    return root

class PackageTests(unittest.TestCase):
    def test_complete_inventory_and_no_silent_omission(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);project=fake_project(root/'project')
            put(project/'requirements-extra.txt','test==1\n')
            with contextlib.redirect_stdout(io.StringIO()):archive=p.build(project,root/'out')
            manifest=v.extract_verified(archive,root/'extracted')
            self.assertTrue(set(p.REQUIRED_FILES)<=set(manifest['files']))
            self.assertIn('requirements-extra.txt',manifest['files'])
            (project/'output/report-v4/source/build_report.py').unlink()
            with self.assertRaisesRegex(ValueError,'sources/results missing'):p.build(project,root/'missing')
            self.assertFalse((root/'missing/inherited-collusion-v4-research-package.zip').exists())

    def test_symlink_roots_and_unsafe_ledger_paths_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);project=fake_project(root/'project')
            (project/'vendor').symlink_to(root,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):p.build(project,root/'out')
            (project/'vendor').unlink()
            put(project/'runs/phase4-budget.json',json.dumps({'allocations':{'../../elsewhere':{}}}))
            with self.assertRaisesRegex(ValueError,'Unsafe'):p.build(project,root/'out')

    def test_archive_tampering_traversal_duplicates_and_links_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for kind in ('traversal','duplicate','symlink','hash'):
                archive=root/(kind+'.zip');body=b'fixture'
                manifest={'schema_version':1,'files':{'data.txt':{'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}}}
                with warnings.catch_warnings(),zipfile.ZipFile(archive,'w') as z:
                    warnings.simplefilter('ignore',UserWarning)
                    z.writestr(v.MANIFEST,json.dumps(manifest));z.writestr('data.txt',body if kind!='hash' else b'changed')
                    if kind=='traversal':z.writestr('../escape',b'unsafe')
                    if kind=='duplicate':z.writestr('data.txt',body)
                    if kind=='symlink':
                        info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'data.txt')
                with self.subTest(kind=kind),self.assertRaises(ValueError):v.extract_verified(archive,root/kind)
                self.assertFalse((root/kind).exists())

    def test_extracted_byte_drift_and_extra_files_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);project=fake_project(root/'project')
            with contextlib.redirect_stdout(io.StringIO()):archive=p.build(project,root/'out')
            v.extract_verified(archive,root/'extract')
            put(root/'extract/unlisted.txt')
            with self.assertRaisesRegex(ValueError,'inventory'):v.verify_extracted(root/'extract')
            (root/'extract/unlisted.txt').unlink();put(root/'extract/README.md','changed')
            with self.assertRaisesRegex(ValueError,'byte hash'):v.verify_extracted(root/'extract')

    def test_original_reads_network_subprocess_and_credentials_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/'original';put(original/'marker','private')
            out=root/'logs';out.mkdir()
            checks=["open("+repr(str(original/'marker'))+").read()",'__import__("socket").socket()',
                    '__import__("subprocess").run(["echo","unexpected"])']
            for index,expression in enumerate(checks):
                script=root/f'denied{index}.py';put(script,expression)
                with self.assertRaises(RuntimeError):v.isolated_run(script,[],original,root,out,f'guard{index}')
                self.assertIn('PermissionError',(out/f'guard{index}.stderr.txt').read_text())
            script=root/'stdlib.py';put(script,'import os,sys,json\nassert sys.flags.isolated and sys.flags.no_site\nassert "PYTHONPATH" not in os.environ and "HF_TOKEN" not in os.environ\nprint(json.dumps({"stdlib":True}))\n')
            v.isolated_run(script,[],original,root,out,'stdlib')

    def test_only_explicit_differences_are_normalized(self):
        value={'analyzed_at':'now','nested':{'analyzed_at':'must remain'},'path':'/old/project/file','note':'prefix /old/project/file'}
        result=v.comparable(value,[Path('/old/project')])
        self.assertNotIn('analyzed_at',result)
        self.assertEqual(result['nested']['analyzed_at'],'must remain')
        self.assertEqual(result['path'],'<PROJECT>/file')
        self.assertEqual(result['note'],'prefix /old/project/file')

    def test_full_mock_zip_reproduces_both_populations_without_original(self):
        fixture=load('package_cohort_fixture',ROOT/'tests/v4f_fixtures.py')
        f=fixture.f
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);project=root/'original';project.mkdir()
            env=fixture.full_cohort(project)
            for name,cfg in env['configs'].items():
                a=f.read(env['ledger'])['allocations'][name]
                f.run(project/'runs'/name,cfg,a['seed'],a['cohort'],'probes',backend=fixture.FixtureBackend())
            sources=ROOT/'scripts'
            for name in ('analyze_v4_study.py','analyze_v4f_study.py','strict_bounds.py','v4_runner.py'):
                shutil.copy2(sources/name,project/'scripts'/name)
            shutil.copytree(ROOT/'inherited_collusion',project/'inherited_collusion',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            shutil.copy2(ROOT/'scripts/verify_offline_package.py',project/'scripts/verify_offline_package.py')
            shutil.copy2(ROOT/'scripts/package_v4_study.py',project/'scripts/package_v4_study.py')
            for suffix in ('v4','v4f'):
                source=ROOT/'evidence'/f'{suffix}-independent/check_results.py'
                destination=project/'evidence'/f'{suffix}-independent/check_results.py';destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
            logs=root/'generation-logs';logs.mkdir();unrelated=root/'nonexistent-original'
            strict=project/'output/analysis-v4/analysis.json';amended=project/'output/analysis-v4f/analysis.json'
            for name,dest,extra in [('analyze_v4_study.py',strict,[]),('analyze_v4f_study.py',amended,['--strict-analysis',strict])]:
                v.isolated_run(project/'scripts'/name,['--project',project,'--out',dest,*extra],unrelated,project,logs,name)
            for suffix,analysis in [('v4',strict),('v4f',amended)]:
                v.isolated_run(project/'evidence'/f'{suffix}-independent/check_results.py',['--project',project,'--final-analysis',analysis,'--out',project/'output'/f'independent-{suffix}'],unrelated,project,logs,suffix)
            for name in p.REQUIRED_FILES:
                if not (project/name).exists():put(project/name)
            for name in p.REQUIRED_DIRECTORIES:
                if not (project/name).exists():put(project/name/'synthetic.txt')
            with contextlib.redirect_stdout(io.StringIO()):archive=p.build(project,root/'package')
            extracted=root/'extracted';v.extract_verified(archive,extracted)
            project.rename(root/'original-unavailable')
            result=v.verify(extracted,project,root/'verification')
            self.assertTrue(result['both_populations_recomputed'])
            self.assertEqual(len(result['independent_checks']),2)
            self.assertTrue(all(c['passed'] for c in result['independent_checks']))

if __name__=='__main__':unittest.main()
