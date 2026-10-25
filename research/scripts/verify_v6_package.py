#!/usr/bin/env python3
"""Verify every archive byte and reproduce V6 in separate isolated processes.

The guards deny original source-directory access, sockets and child processes
inside trusted analysis programs. They are not an OS adversarial-code sandbox.
Optional --recheck-history reconstructs the byte-preserved original V5 archive
and invokes its unchanged offline verifier. No inference is performed.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


def load_packager():
    path = Path(__file__).resolve().with_name('package_v6_study.py')
    spec = importlib.util.spec_from_file_location('v6_package_inventory', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


p = load_packager()
WRAPPER = r'''
import json,os,runpy,sys
from pathlib import Path
script,arguments,roots=json.loads(sys.argv[1])
blocked=tuple(Path(root).resolve() for root in roots)
def guard_path(value):
 if not isinstance(value,(str,bytes,os.PathLike)):return
 candidate=Path(os.fsdecode(value)).resolve()
 for root in blocked:
  if candidate==root or root in candidate.parents:raise PermissionError('Original source access denied')
def audit(event,args):
 if event in ('open','os.listdir','os.scandir') and args:guard_path(args[0])
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn','os.posix_spawnp') or event.startswith('os.exec'):raise PermissionError('Network/process access denied')
sys.addaudithook(audit)
sys.argv=[script]+arguments
runpy.run_path(script,run_name='__main__')
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def equal_json(saved, computed, label):
    if canonical(saved) != canonical(computed):
        raise ValueError(label + ' differs; no V6 fields or numerical differences are ignored')


def verify_tree(root, manifest):
    names = {q.relative_to(root).as_posix() for q in root.rglob('*') if q.is_file() or q.is_symlink()}
    if names != set(manifest['files']) | {p.MANIFEST}:
        raise ValueError('Extracted inventory changed')
    for name, expected in manifest['files'].items():
        path = root / p.relative(name)
        if path.is_symlink() or p.entry(path.read_bytes()) != expected:
            raise ValueError('Extracted file changed: ' + name)


def extract(archive, root):
    manifest, raw, files = p.inventory_zip(archive, p.MANIFEST)
    if manifest.get('study_version') != 6:
        raise ValueError('Not a V6 package')
    root.mkdir(parents=True, exist_ok=False)
    for name, data in {p.MANIFEST: raw, **files}.items():
        path = root / p.relative(name); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
    verify_tree(root, manifest)
    return manifest, files


def preserved_baseline(root, manifest):
    reference = manifest['baseline']; name = p.relative(reference['manifest_path'])
    raw = (root / name).read_bytes()
    if name != p.BASE_MANIFEST or p.sha(raw) != reference['manifest_sha256']:
        raise ValueError('Historical V5 manifest binding mismatch')
    baseline = json.loads(raw); overrides = reference['preserved_overrides']
    if set(overrides) != {'README.md'} or overrides['README.md'] != p.HISTORY + '/files/README.md':
        raise ValueError('Only the historical root README may be relocated')
    if reference['inventoried_files'] != len(baseline['files']) or reference['zip_members'] != len(baseline['files']) + 1:
        raise ValueError('Historical baseline count mismatch')
    for old_name, expected in baseline['files'].items():
        name = p.relative(overrides.get(old_name, old_name))
        if name not in manifest['files'] or p.entry((root / name).read_bytes()) != expected:
            raise ValueError('Historical V5 member lost or changed: ' + old_name)
    receipt_path = p.relative(reference['offline_verification_path']); data = (root / receipt_path).read_bytes()
    if p.sha(data) != reference['offline_verification_sha256']:
        raise ValueError('Historical verification receipt changed')
    receipt = p.baseline_receipt(data, reference['archive_sha256'])
    return baseline, receipt


def isolated(script, args, blocked, cwd, logs, label):
    logs.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([str(script), [str(x) for x in args], [str(x) for x in blocked]])
    env = {'PATH': os.defpath, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    with (logs / (label + '.stdout.txt')).open('wb') as stdout, (logs / (label + '.stderr.txt')).open('wb') as stderr:
        result = subprocess.run([str(Path(sys.executable).resolve()), '-I', '-S', '-B', '-c', WRAPPER, payload],
                                cwd=cwd, env=env, stdout=stdout, stderr=stderr, check=False)
    if result.returncode != 0:
        raise ValueError(label + ' failed; see preserved stdout/stderr logs')


def recheck_history(root, manifest, baseline, temp, logs):
    archive = temp / 'reconstructed-v5.zip'
    overrides = manifest['baseline']['preserved_overrides']
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(p.BASE_MANIFEST, (root / p.BASE_MANIFEST).read_bytes())
        for name in baseline['files']:
            z.writestr(name, (root / overrides.get(name, name)).read_bytes())
    # Byte-exact members, rather than ZIP container metadata/compression, are
    # the preservation contract. The temporary ZIP consequently has a new SHA.
    p.inventory_zip(archive, p.BASE_MANIFEST)
    out = temp / 'historical-recheck'
    with (logs / 'historical-recheck.stdout.txt').open('wb') as stdout, (logs / 'historical-recheck.stderr.txt').open('wb') as stderr:
        r = subprocess.run([str(Path(sys.executable).resolve()), '-I', '-S', '-B',
                            str(root / 'scripts/verify_v5_package.py'), '--archive', str(archive),
                            '--original', baseline['source_project'], '--out', str(out)],
                           cwd=root, env={'PATH': os.defpath, 'LANG': 'C.UTF-8'},
                           stdout=stdout, stderr=stderr, check=False)
    if r.returncode:
        raise ValueError('Historical offline reproduction failed; see preserved logs')
    result = json.loads((out / 'offline-verification.json').read_text())
    p.baseline_receipt(json.dumps(result).encode(), p.sha(archive.read_bytes()))
    shutil.copytree(out, logs / 'historical-recheck')
    return {'recomputed': True, 'byte_exact_baseline_members': len(baseline['files']) + 1,
            'source_archive_sha256': manifest['baseline']['archive_sha256'],
            'reconstructed_archive_sha256': p.sha(archive.read_bytes()),
            'receipt': 'historical-recheck/offline-verification.json',
            'receipt_sha256': p.sha((out / 'offline-verification.json').read_bytes())}


def verify(archive, out, recheck=False):
    archive, out = Path(archive).resolve(), Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Verification output directory must be new or empty')
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='collusion-v6-offline-') as folder:
        temp = Path(folder); root = temp / 'project'; work = temp / 'recomputed'; work.mkdir()
        manifest, files = extract(archive, root)
        for name in ('verify_v6_package.py', 'package_v6_study.py'):
            if Path(__file__).with_name(name).read_bytes() != (root / 'scripts' / name).read_bytes():
                raise ValueError('Verifier source is not the archived source: ' + name)
        baseline, prior_receipt = preserved_baseline(root, manifest)
        p.check_closed(files)
        p.check_report(files)
        blocked = [manifest[k] for k in ('source_project', 'source_workspace', 'source_study', 'source_report')]
        for b in blocked:
            path = Path(b)
            if not path.is_absolute() or path == Path('/') or path == temp or path in root.parents:
                raise ValueError('Invalid original-directory isolation boundary')
        analysis = work / 'v6-analysis.json'; check = work / 'independent-raw-check.json'
        study = root / p.STUDY
        isolated(study / 'scripts/analyze_v6_study.py', ['--project', study, '--out', analysis], blocked, root, out, 'v6-analysis')
        isolated(study / 'scripts/check_v6_raw.py', ['--root', study, '--output', check], blocked, root, out, 'v6-independent')
        cross = work / 'independent-crosscheck.json'
        isolated(study / 'scripts/compare_v6_analyses.py', ['--project', study, '--out', cross], blocked, root, out, 'v6-crosscomparison')
        equal_json(json.loads(files[p.CROSSCHECK]), json.loads(cross.read_text()), 'V6 crosscomparison')
        saved_analysis, new_analysis = json.loads(files[p.ANALYSIS]), json.loads(analysis.read_text())
        saved_check, new_check = json.loads(files[p.CHECK]), json.loads(check.read_text())
        equal_json(saved_analysis, new_analysis, 'V6 analysis')
        equal_json(saved_check, new_check, 'Independent V6 raw check')
        if new_check.get('success') is not True or new_check.get('preflight_only') is not False or new_check.get('errors') != []:
            raise ValueError('Independent V6 verification failed')
        if new_check.get('checker_sha256') != p.sha(files[p.STUDY + '/scripts/check_v6_raw.py']):
            raise ValueError('Independent V6 source hash mismatch')
        history = recheck_history(root, manifest, baseline, temp, out) if recheck else {
            'recomputed': False, 'byte_bound_prior_pass_retained': True,
            'receipt_sha256': manifest['baseline']['offline_verification_sha256']}
        verify_tree(root, manifest)
        for name in ('v6-analysis.json', 'independent-raw-check.json', 'independent-crosscheck.json'):
            shutil.copyfile(work / name, out / ('recomputed-' + name))
        result = {
            'schema_version': 1, 'verified_at': datetime.now(timezone.utc).isoformat(),
            'passed': True, 'archive_sha256': p.sha(archive.read_bytes()),
            'manifest_sha256': p.sha((root / p.MANIFEST).read_bytes()),
            'package_inventory_verified': True, 'packaged_files': len(files),
            'baseline_inventoried_files_preserved_byte_exact': len(baseline['files']),
            'baseline_zip_members_preserved_byte_exact': len(baseline['files']) + 1,
            'historical_v5_offline_pass_retained': True, 'historical_reproduction': history,
            'v6_analysis_recomputed': True, 'v6_analysis_exact_json_equal': True,
            'v6_independent_recomputed': True, 'v6_independent_exact_json_equal': True,
            'v6_crosscomparison_recomputed': True, 'v6_crosscomparison_exact_json_equal': True,
            'v6_allowed_json_differences': [],
            'v6_analysis_packaged_sha256': p.sha(files[p.ANALYSIS]),
            'v6_analysis_recomputed_sha256': p.sha(analysis.read_bytes()),
            'v6_check_packaged_sha256': p.sha(files[p.CHECK]),
            'v6_check_recomputed_sha256': p.sha(check.read_bytes()),
            'verifier_sha256': p.sha(Path(__file__).read_bytes()),
            'original_source_directories_read_access_denied': blocked,
            'network_and_subprocess_creation_denied_in_v6_analysis': True,
            'isolated_stdlib_python': True, 'models_called': False,
            'isolation_scope': 'Python audit hooks in trusted analysis processes; not an OS adversarial-code sandbox.',
            'not_checked': 'This run does not rerender figures, DOCX or PDF; sources and requirements are inventoried.',
        }
        (out / 'offline-verification.json').write_bytes(p.json_bytes(result))
        return result



def finalize_delivery(archive, verification, destination):
    """Explicitly publish a small hash-bound delivery after successful verification."""
    archive, verification, destination = map(lambda q: Path(q).resolve(), (archive, verification, destination))
    result = json.loads((verification / 'offline-verification.json').read_text())
    if result.get('passed') is not True or result.get('archive_sha256') != p.sha(archive.read_bytes()):
        raise ValueError('Delivery requires the passing receipt for these exact ZIP bytes')
    manifest, raw, contents = p.inventory_zip(archive, p.MANIFEST)
    destination.mkdir(parents=True, exist_ok=True)
    objects = {archive.name: archive.read_bytes(), p.MANIFEST: raw,
               'offline-verification.json': (verification / 'offline-verification.json').read_bytes(),
               'V6-START-HERE.md': contents['V6-START-HERE.md']}
    for name in p.REQUIRED_REPORT[:3]:objects[name] = contents[p.REPORT + '/' + name]
    objects[archive.stem + '.sha256'] = (p.sha(objects[archive.name]) + '  ' + archive.name + '\n').encode()
    for name, data in objects.items():
        (destination / name).write_bytes(data)
        if (destination / name).read_bytes() != data:raise ValueError('Delivery readback failed: ' + name)
    delivery = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                'current_entry': 'V6-START-HERE.md', 'study_version': 6,
                'offline_verification_passed': True, 'models_called_by_packaging': False,
                'archive_sha256': result['archive_sha256'],
                'files': {name: p.entry(data) for name, data in sorted(objects.items())}}
    (destination / 'DELIVERY-MANIFEST.json').write_bytes(p.json_bytes(delivery))
    if json.loads((destination / 'DELIVERY-MANIFEST.json').read_text()) != delivery:
        raise ValueError('Delivery manifest readback failed')
    return delivery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--recheck-history', action='store_true')
    parser.add_argument('--delivery', type=Path, help='After PASS, write portable report copies, ZIP, SHA and delivery manifest here')
    args = parser.parse_args(); result = verify(args.archive, args.out, args.recheck_history)
    if args.delivery:finalize_delivery(args.archive, args.out, args.delivery)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
