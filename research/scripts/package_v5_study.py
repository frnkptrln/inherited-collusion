#!/usr/bin/env python3
"""Package the closed V5 control and retain every reviewed V4 baseline byte.

Stdlib only. This does not run models, analyses, or document rendering. The
baseline is a verified input archive, not a regenerated interpretation of V4.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

MANIFEST = 'PACKAGE-MANIFEST-v5.json'
BASE_MANIFEST = 'PACKAGE-MANIFEST-v4.json'
BASE_SHA256 = '849a7088e524d2a01ca84d9d8fbe95c4f55000313d06e9e3162c85127c8e555d'
HISTORY = 'evidence/reviewed-v4-baseline'
RUN_IDS = tuple(f'v5-main-{model}-{seed}' for model in ('qwen', 'gptoss') for seed in range(301, 307))
REQUIRED = (
    'scripts/package_v5_study.py', 'scripts/verify_v5_package.py',
    'scripts/verify_offline_package.py', 'evidence/oct24-review/verify_reviewed_package.py',
    'evidence/oct24-review/baseline_diagnostic.py', 'evidence/oct24-review/check_baseline.py',
    'evidence/oct24-review/baseline-diagnostic.json',
    'scripts/v5_runner.py', 'scripts/v5_scenario.py', 'scripts/analyze_v5_study.py',
    'scripts/check_v5_raw.py', 'scripts/run_v5_study.py', 'scripts/close_v5_study.py',
    'docs/v5-protocol.json', 'docs/v5-freeze.json', 'docs/v5-closeout-record.json',
    'runs/phase5-budget.json', 'output/analysis-v5/analysis.json',
    'output/independent-v5/independent-check.json',
    'output/report-v5/inherited-collusion-v5.docx',
    'output/report-v5/inherited-collusion-v5.pdf',
    'output/report-v5/inherited-collusion-v5.audit.json',
    'output/report-v5/source/build_report.py', 'output/report-v5/source/report-input.json',
    'output/report-v5/source/official-template.docx',
    'output/report-v5/source/prepare_final_input.py', 'output/report-v5/source/artifact.md',
    'output/report-v5/source/requirements-report.txt',
    'output/report-v5/source/dependency-versions.json', 'output/report-v5/source/README.md',
    'requirements-research.txt', 'requirements-analysis.txt',
)
ALLOWED = (
    'README.md', 'inherited_collusion', 'scripts', 'tests', 'configs', 'docs', 'vendor', 'evidence',
    'output/report', 'output/report-v4', 'output/report-v5', 'output/analysis',
    'output/analysis-v4', 'output/analysis-v4f', 'output/analysis-v5',
    'output/independent-v4', 'output/independent-v4f', 'output/independent-v5',
    'output/figures-v4-strict', 'output/figures-v4f-amended', 'output/figures-v5',
    'runs/budget-ledger.json', 'runs/phase3-budget.json', 'runs/phase4f-budget.json',
    'runs/phase5-budget.json', 'runs/v5-dispatch',
)
SECRET = re.compile(rb'hf_[A-Za-z0-9]{20,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}')


def sha(content):
    return hashlib.sha256(content).hexdigest()


def relative(name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('Unsafe package-relative path')
    path = PurePosixPath(name)
    if path.is_absolute() or str(path) != name or any(p in ('.', '..') for p in path.parts) or ':' in path.parts[0]:
        raise ValueError('Unsafe package-relative path')
    return name


def permitted(name):
    path = PurePosixPath(relative(name))
    if any(p.startswith('.') or p in ('__pycache__', 'node_modules', 'venv', 'env', 'cache') for p in path.parts):
        return False
    if path.suffix.lower() in ('.pyc', '.pyo', '.lock', '.zip'):
        return False
    if path.name.lower() in ('credentials', 'credentials.json', 'token', 'token.json', 'auth.json', 'id_rsa', 'id_ed25519'):
        return False
    return True


def entry(content):
    return {'sha256': sha(content), 'bytes': len(content)}


def check_content(name, content):
    if not permitted(name):
        raise ValueError('Disallowed evidence file: ' + name)
    if SECRET.search(content):
        raise ValueError('Possible credential in ' + name + '; secret value not printed')


def read_baseline(path, expected_sha):
    if sha(path.read_bytes()) != expected_sha:
        raise ValueError('Reviewed V4 baseline archive digest mismatch')
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate baseline ZIP member')
        for info in infos:
            relative(info.filename)
            if info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('Nonregular baseline ZIP member')
        raw_manifest = z.read(BASE_MANIFEST)
        manifest = json.loads(raw_manifest)
        if manifest.get('schema_version') != 1 or not manifest.get('files'):
            raise ValueError('Invalid baseline manifest')
        if set(names) != set(manifest['files']) | {BASE_MANIFEST}:
            raise ValueError('Baseline inventory mismatch')
        contents = {}
        for name, expected in manifest['files'].items():
            content = z.read(relative(name))
            check_content(name, content)
            if entry(content) != expected:
                raise ValueError('Baseline file digest mismatch: ' + name)
            contents[name] = content
        for name in manifest.get('required_files', []):
            if relative(name) not in contents:
                raise ValueError('Baseline required file absent: ' + name)
        for directory in manifest.get('required_nonempty_directories', []):
            if not any(name.startswith(relative(directory) + '/') for name in contents):
                raise ValueError('Baseline required directory empty: ' + directory)
    return manifest, raw_manifest, contents


def current_files(project):
    result = {}
    allowed = [*ALLOWED, *('runs/' + name for name in RUN_IDS)]
    allowed += [p.name for p in project.glob('requirements*.txt')]
    for name in allowed:
        path = project / relative(name)
        if path.is_symlink():
            raise ValueError('Evidence symlink not permitted: ' + name)
        if not path.exists():
            continue
        candidates = [path] if path.is_file() else sorted(path.rglob('*'))
        for candidate in candidates:
            key = candidate.relative_to(project).as_posix()
            if not permitted(key):
                continue
            if candidate.is_symlink():
                raise ValueError('Evidence symlink not permitted: ' + key)
            if candidate.is_file():
                data = candidate.read_bytes()
                check_content(key, data)
                result[key] = data
    return result


def check_closed(project, contents):
    ledger = json.loads(contents['runs/phase5-budget.json'])
    if set(ledger.get('allocations', {})) != set(RUN_IDS):
        raise ValueError('Expected exactly the twelve fixed V5 allocations')
    closure = json.loads(contents['docs/v5-closeout-record.json'])
    if closure.get('state') != 'CLOSED_NO_FURTHER_DISPATCH' or not closure.get('closed_at'):
        raise ValueError('V5 must be closed before packaging')
    if {row['run'] for row in closure['runs']} != set(RUN_IDS) or len(closure['runs']) != len(RUN_IDS):
        raise ValueError('Incomplete V5 closure')
    inventory = closure['raw_inventory']
    actual = {name: sha(data) for name, data in contents.items()
              if any(name.startswith('runs/' + run + '/') for run in RUN_IDS)}
    if actual != inventory:
        raise ValueError('V5 raw evidence differs from sealed inventory')
    for run in RUN_IDS:
        for suffix in ('manifest.json', 'summary.json', 'schedule.json'):
            if 'runs/' + run + '/' + suffix not in contents:
                raise ValueError('V5 case artifact missing: ' + run + '/' + suffix)
        config = 'configs/v5/' + run + '.json'
        if config not in contents:
            raise ValueError('V5 config absent: ' + config)
    freeze = json.loads(contents['docs/v5-freeze.json'])
    if sha(contents['runs/phase5-budget.json']) != freeze['ledger_sha256']:
        raise ValueError('V5 frozen budget changed')
    for name, expected in freeze['artifacts'].items():
        relative(name)
        if name not in contents or sha(contents[name]) != expected:
            raise ValueError('Frozen V5 artifact absent or changed: ' + name)


def build(project, base_archive, destination, expected_base_sha=BASE_SHA256):
    project, base_archive, destination = Path(project).resolve(), Path(base_archive).resolve(), Path(destination).resolve()
    baseline, raw_manifest, old = read_baseline(base_archive, expected_base_sha)
    current = current_files(project)
    missing = [name for name in REQUIRED if name not in current]
    if missing:
        raise ValueError('Final V5 reproducibility sources/results missing: ' + ', '.join(missing))
    check_closed(project, current)
    files = dict(old)
    overrides = {}
    for name, data in current.items():
        if name.startswith(HISTORY + '/'):
            raise ValueError('Reserved baseline-history prefix already exists in project')
        if name in old and data != old[name]:
            preserved = HISTORY + '/files/' + name
            files[preserved] = old[name]
            overrides[name] = preserved
        files[name] = data
    history_manifest = HISTORY + '/' + BASE_MANIFEST
    files[history_manifest] = raw_manifest
    required = sorted(set(REQUIRED) | set(baseline.get('required_files', [])) | {history_manifest})
    manifest = {
        'schema_version': 1, 'study_version': 5,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_project': str(project),
        'project': 'Inherited Collusion — A Causal Audit of Agent Handoffs',
        'author': 'Frank Peterlein', 'affiliation': 'Independent researcher',
        'description': 'Reviewed V4/V4F history, explicit post-hoc baseline diagnostic, and separately frozen V5 structural control. Shared generations are counted once; software mocks are not research evidence.',
        'baseline': {'archive_sha256': expected_base_sha, 'manifest_path': history_manifest,
                     'manifest_sha256': sha(raw_manifest), 'files': len(old),
                     'preserved_overrides': dict(sorted(overrides.items())),
                     'preservation_rule': 'Every baseline file is byte-identical at its original path unless preserved_overrides names its archived historical path.'},
        'excluded': 'Credentials, environment directories, caches, hidden files, unrelated jobs, previous ZIP bundles.',
        'required_files': required,
        'required_nonempty_directories': baseline.get('required_nonempty_directories', []),
        'reproduction_scope': 'Strict V4, V4F, post-hoc diagnostic, and V5 analyses and independent raw checks use isolated stdlib Python. Figures and reports have separately recorded dependencies; PDF rendering also needs external tools.',
        'files': {name: entry(data) for name, data in sorted(files.items())},
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'inherited-collusion-v5-research-package.zip'
    with tempfile.NamedTemporaryFile(dir=destination, suffix='.zip.tmp', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr(MANIFEST, manifest_bytes)
            for name, data in sorted(files.items()):
                # Freeze the initial read and also reject mutations while packaging.
                if name in current and (project / name).read_bytes() != data:
                    raise ValueError('Source changed during packaging: ' + name)
                z.writestr(name, data)
        if sha(base_archive.read_bytes()) != expected_base_sha:
            raise ValueError('Baseline archive changed during packaging')
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None or set(z.namelist()) != set(files) | {MANIFEST} or len(z.namelist()) != len(files) + 1:
                raise ValueError('Written ZIP integrity/inventory mismatch')
            for name, expected in manifest['files'].items():
                if entry(z.read(name)) != expected:
                    raise ValueError('Written ZIP content mismatch: ' + name)
        os.replace(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)
    (destination / MANIFEST).write_bytes(manifest_bytes)
    archive_sha = sha(archive.read_bytes())
    (destination / (archive.stem + '.sha256')).write_text(archive_sha + '  ' + archive.name + '\n')
    result = {'archive': str(archive), 'files': len(files), 'bytes': archive.stat().st_size,
              'sha256': archive_sha, 'baseline_files_preserved': len(old),
              'baseline_historical_overrides': len(overrides), 'readback_verified': True}
    print(json.dumps(result))
    return archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--base-archive', type=Path, required=True)
    p.add_argument('--base-sha256', default=BASE_SHA256)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    build(a.project, a.base_archive, a.out, a.base_sha256)


if __name__ == '__main__':
    main()
