#!/usr/bin/env python3
"""Bundle closed V6 evidence with every byte of the reviewed V5 archive.

Standard library only; never dispatches inference or runs the analyses. Final
packaging requires sealed V6 raw data, final analysis/checks, and report sources.
"""
import argparse
import io
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

MANIFEST = 'PACKAGE-MANIFEST-v6.json'
BASE_MANIFEST = 'PACKAGE-MANIFEST-v5.json'
BASE_SHA256 = '1a07ea5fa12e3ea13b80cdaa943d4c75f99533232799ad8336b343f99709737d'
HISTORY = 'evidence/reviewed-v5-baseline'
STUDY = 'output/control-v6'
REPORT = 'output/report-v6'
ANALYSIS = STUDY + '/analysis/v6-analysis.json'
CHECK = STUDY + '/analysis/independent-raw-check.json'
CROSSCHECK = STUDY + '/analysis/independent-crosscheck.json'
RUN_IDS = tuple([f'v6-qwen-{s}' for s in (301, 303, 304, 306)] + [f'v6-gptoss-{s}' for s in range(301, 307)])
REQUIRED_STUDY = (
    'scripts/v6_runner.py', 'scripts/run_v6_study.py', 'scripts/close_v6.py',
    'scripts/analyze_v6_study.py', 'scripts/check_v6_raw.py', 'scripts/compare_v6_analyses.py',
    'scripts/v5_runner.py', 'scripts/v5_scenario.py',
    'docs/v6-protocol.json', 'docs/v6-freeze.json', 'docs/v6-closeout-record.json',
    'runs/phase6-budget.json', 'analysis/v6-analysis.json',
    'analysis/independent-raw-check.json', 'analysis/independent-crosscheck.json',
)
REQUIRED_REPORT = (
    'inherited-collusion-v6.pdf', 'inherited-collusion-v6.docx',
    'inherited-collusion-v6.audit.json', 'source/build_report.py',
    'source/prepare_final_input.py', 'source/report-input.json',
    'source/official-template.docx', 'source/requirements-report.txt',
    'source/dependency-versions.json', 'source/README.md', 'source/artifact.md',
    'source/plot_v6_results.py', 'source/visual-review.json',
    'source/v5-reviewed-input.json', 'source/literature-retrieval-2026-10-25.json',
    'figures/v6-safe-conventions.png', 'figures/v6-safe-conventions.pdf',
    'figures/v6-safe-conventions.svg', 'figures/v6-safe-conventions.audit.json',
)
STUDY_ALLOW = ('README.md', 'scripts', 'tests', 'inherited_collusion', 'docs', 'configs', 'inputs', 'evidence', 'analysis')
REPORT_ALLOW = ('source', 'figures', 'renders', 'rendered', 'pages', *REQUIRED_REPORT[:3])
OMIT_COMPONENTS = {'__pycache__', 'node_modules', 'venv', 'env', 'cache',
                   'draft-layout', 'synthetic-figures', 'test-build', 'testbuild', 'tempbuild-root', 'history-v5'}
SECRET = re.compile(rb'hf_[A-Za-z0-9]{20,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entry(data):
    return {'sha256': sha(data), 'bytes': len(data)}


def relative(name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('Unsafe package-relative path')
    p = PurePosixPath(name)
    if not p.parts or p.is_absolute() or str(p) != name or any(x in ('.', '..') for x in p.parts) or ':' in p.parts[0]:
        raise ValueError('Unsafe package-relative path')
    return name


def permitted(name):
    p = PurePosixPath(relative(name))
    if any(x.startswith('.') or x in OMIT_COMPONENTS for x in p.parts):
        return False
    if p.suffix.lower() in ('.pyc', '.pyo', '.lock', '.zip'):
        return False
    return p.name.lower() not in ('credentials', 'credentials.json', 'token', 'token.json', 'auth.json', 'id_rsa', 'id_ed25519')


def check_content(name, data, historical=False):
    # Historical contents were already inventoried; do not silently omit a
    # historical file merely because a new report cleanup rule would match it.
    if not historical and not permitted(name):
        raise ValueError('Disallowed evidence file: ' + name)
    relative(name)
    if SECRET.search(data):
        raise ValueError('Possible credential in ' + name + '; secret value not printed')


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def inventory_zip(path, manifest_name):
    with zipfile.ZipFile(path) as z:
        infos = z.infolist(); names = [i.filename for i in infos]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member')
        for info in infos:
            relative(info.filename)
            if info.is_dir() or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError('Nonregular ZIP member')
        raw = z.read(manifest_name); manifest = json.loads(raw)
        if manifest.get('schema_version') != 1 or not isinstance(manifest.get('files'), dict) or not manifest['files']:
            raise ValueError('Invalid package manifest')
        if set(names) != set(manifest['files']) | {manifest_name}:
            raise ValueError('ZIP inventory mismatch')
        files = {}
        for name, expected in manifest['files'].items():
            data = z.read(relative(name)); check_content(name, data, historical=True)
            if entry(data) != expected:
                raise ValueError('ZIP file hash/size mismatch: ' + name)
            files[name] = data
        for name in manifest.get('required_files', []):
            if relative(name) not in files:
                raise ValueError('Required file absent: ' + name)
        for directory in manifest.get('required_nonempty_directories', []):
            if not any(n.startswith(relative(directory) + '/') for n in files):
                raise ValueError('Required directory empty: ' + directory)
    return manifest, raw, files


def collect(root, allowed, prefix):
    files, sources = {}, {}
    for name in allowed:
        path = root / relative(name)
        if path.is_symlink():
            raise ValueError('Evidence symlink: ' + name)
        if not path.exists():
            continue
        candidates = [path] if path.is_file() else sorted(path.rglob('*'))
        for p in candidates:
            key = p.relative_to(root).as_posix()
            if not permitted(key):
                continue
            if p.is_symlink():
                raise ValueError('Evidence symlink: ' + key)
            if p.is_file():
                data = p.read_bytes(); full = prefix + '/' + key
                check_content(full, data); files[full] = data; sources[full] = p
    return files, sources


def check_closed(contents):
    def read(name):
        return json.loads(contents[STUDY + '/' + name])
    closure = read('docs/v6-closeout-record.json')
    if closure.get('state') != 'CLOSED_NO_FURTHER_DISPATCH' or not closure.get('closed_at'):
        raise ValueError('V6 must be closed before packaging')
    if {r['run'] for r in closure['runs']} != set(RUN_IDS) or len(closure['runs']) != len(RUN_IDS):
        raise ValueError('V6 closure must include all ten fixed cases')
    if set(read('runs/phase6-budget.json')['allocations']) != set(RUN_IDS):
        raise ValueError('V6 allocation cohort changed')
    raw = {n[len(STUDY)+1:]: sha(b) for n, b in contents.items()
           if any(n.startswith(STUDY + '/runs/' + r + '/') for r in RUN_IDS)}
    if raw != closure['raw_inventory']:
        raise ValueError('V6 raw data differ from the sealed inventory')
    for r in RUN_IDS:
        for suffix in ('manifest.json', 'summary.json', 'schedule.json'):
            if STUDY + '/runs/' + r + '/' + suffix not in contents:
                raise ValueError('Missing V6 run artifact: ' + r + '/' + suffix)
        if STUDY + '/configs/' + r + '.json' not in contents:
            raise ValueError('Missing V6 configuration: ' + r)
    freeze = read('docs/v6-freeze.json')
    if sha(contents[STUDY + '/runs/phase6-budget.json']) != freeze['ledger_sha256']:
        raise ValueError('V6 frozen budget changed')
    for name, expected in freeze['artifacts'].items():
        full = STUDY + '/' + relative(name)
        if full not in contents or sha(contents[full]) != expected:
            raise ValueError('V6 frozen artifact missing or changed: ' + name)
    analysis, check = json.loads(contents[ANALYSIS]), json.loads(contents[CHECK])
    if analysis.get('schema_version') != 6 or analysis.get('evidence_class') != 'V6_FIXED_HANDOFF_SHARED_CONVENTION':
        raise ValueError('Final V6 analysis missing or simulated')
    if analysis.get('closeout_sha256') != sha(contents[STUDY + '/docs/v6-closeout-record.json']):
        raise ValueError('V6 analysis closeout binding mismatch')
    if check.get('success') is not True or check.get('preflight_only') is not False or check.get('errors') != []:
        raise ValueError('Final V6 raw check has not passed')
    if check.get('checker_sha256') != sha(contents[STUDY + '/scripts/check_v6_raw.py']):
        raise ValueError('V6 checker source binding mismatch')
    cross = json.loads(contents[CROSSCHECK])
    if cross.get('success') is not True or cross.get('mismatches') != 0:
        raise ValueError('V6 independent crosscomparison has not passed')
    for key, name in (('analysis_sha256', ANALYSIS), ('independent_check_sha256', CHECK),
                      ('closeout_sha256', STUDY + '/docs/v6-closeout-record.json'),
                      ('comparison_script_sha256', STUDY + '/scripts/compare_v6_analyses.py')):
        if cross.get(key) != sha(contents[name]):
            raise ValueError('V6 crosscomparison evidence binding mismatch: ' + key)
    return closure



def check_report(contents):
    """Require final content/visual receipts bound to these exact report bytes."""
    prefix = REPORT + '/'; source = prefix + 'source/'
    spec = json.loads(contents[source + 'report-input.json'])
    audit = json.loads(contents[prefix + 'inherited-collusion-v6.audit.json'])
    visual = json.loads(contents[source + 'visual-review.json'])
    def text_values(value):
        if isinstance(value, str):yield value
        elif isinstance(value, dict):
            for item in value.values():yield from text_values(item)
        elif isinstance(value, list):
            for item in value:yield from text_values(item)
    unresolved = re.compile(r'\b(PENDING|TODO|TBD)\b|\[\[', re.I)
    if spec.get('ready_for_final') is not True or unresolved.search('\n'.join(text_values(spec))):
        raise ValueError('Report input is not final or retains unresolved markers')
    abstract_words = len(spec.get('abstract', '').split())
    if not 150 <= abstract_words <= 250 or audit.get('abstract_words') != abstract_words or visual.get('abstract_words') != abstract_words:
        raise ValueError('Final abstract length or review count mismatch')
    if (audit.get('draft') is not False or audit.get('rendered') is not True or
        audit.get('visual_review_status') != 'PASS' or audit.get('visual_review_required') is not False):
        raise ValueError('Final rendered/visual report audit missing')
    for key, name in (('input_sha256', source + 'report-input.json'),
                      ('builder_sha256', source + 'build_report.py'),
                      ('source_sha256', source + 'official-template.docx')):
        if audit.get(key) != sha(contents[name]):
            raise ValueError('Report source binding mismatch: ' + key)
    required_inputs = {ANALYSIS, CHECK, CROSSCHECK, STUDY + '/docs/v6-closeout-record.json',
                       STUDY + '/docs/v6-freeze.json', STUDY + '/docs/v6-protocol.json'}
    for owner in (spec, audit):
        records = owner.get('evidence_inputs', [])
        if not required_inputs <= {row['path'] for row in records}:
            raise ValueError('Report does not bind every required V6 result/protocol/closure')
        for row in records:
            name = relative(row['path'])
            if name not in contents or sha(contents[name]) != row['sha256']:
                raise ValueError('Report evidence input changed: ' + name)
    artifacts = {row['path']: row for row in audit.get('artifact_files', [])}
    visual_artifacts = {row['path']: row for row in visual.get('artifacts', [])}
    for name in REQUIRED_REPORT[:2]:
        for records in (artifacts, visual_artifacts):
            row = records.get(name)
            if row is None or row.get('sha256') != sha(contents[prefix + name]) or row.get('bytes') != len(contents[prefix + name]):
                raise ValueError('Final PDF/DOCX review binding mismatch: ' + name)
    reviews = {row['path']: row for row in audit.get('final_reviews', [])}
    if reviews.get('source/visual-review.json', {}).get('sha256') != sha(contents[source + 'visual-review.json']):
        raise ValueError('Visual review is not bound by the final audit')
    for name, row in reviews.items():
        full = prefix + relative(name)
        if full not in contents or sha(contents[full]) != row['sha256']:
            raise ValueError('Final report review missing or changed: ' + name)
    pages = visual.get('total_pages')
    if (visual.get('status') != 'PASS' or visual.get('input_sha256') != sha(contents[source + 'report-input.json']) or
        type(pages) is not int or pages < 1 or visual.get('pages_inspected') != list(range(1, pages + 1)) or
        audit.get('pages') != pages):
        raise ValueError('All-page visual review is not final and complete')
    main_pages = visual.get('main_pages')
    if type(main_pages) is not int or not 0 < main_pages <= 8 or main_pages > pages or audit.get('main_pages') != main_pages:
        raise ValueError('Final main-page limit or review count mismatch')
    images = visual.get('page_images', [])
    if sorted(row['page'] for row in images) != list(range(1, pages + 1)):
        raise ValueError('Visual review page-image inventory incomplete')
    for row in images:
        name = relative(row.get('path'))
        if name != 'renders/page-' + str(row['page']) + '.png' or prefix + name not in contents or sha(contents[prefix + name]) != row['sha256']:
            raise ValueError('Reviewed page image path/hash mismatch')
    figure_audit = json.loads(contents[prefix + 'figures/v6-safe-conventions.audit.json'])
    for key, name in (('analysis_sha256', ANALYSIS),
                      ('closure_sha256', STUDY + '/docs/v6-closeout-record.json'),
                      ('script_sha256', source + 'plot_v6_results.py')):
        if figure_audit.get(key) != sha(contents[name]):
            raise ValueError('V6 figure source/evidence binding mismatch: ' + key)
    figure_files = {row['path']: row for row in figure_audit.get('files', [])}
    for extension in ('png', 'pdf', 'svg'):
        name = 'v6-safe-conventions.' + extension
        if figure_files.get(name, {}).get('sha256') != sha(contents[prefix + 'figures/' + name]):
            raise ValueError('Final scientific figure missing or changed: ' + name)
    for owner in (spec, audit):
        for row in owner.get('supplementary_inputs', []):
            full = source + relative(row['path'])
            if full not in contents or sha(contents[full]) != row['sha256']:
                raise ValueError('Report supplementary input missing or changed: ' + row['path'])
    for row in audit.get('figures', []):
        name = relative(row['path'])
        if name not in contents or sha(contents[name]) != row['sha256']:
            raise ValueError('Report scientific figure missing or changed: ' + name)
    with zipfile.ZipFile(io.BytesIO(contents[prefix + 'inherited-collusion-v6.docx'])) as z:
        import xml.etree.ElementTree as ET
        text = ''.join(ET.fromstring(z.read('word/document.xml')).itertext())
        if unresolved.search(text):
            raise ValueError('Final DOCX retains unresolved markers')
    if not contents[prefix + 'inherited-collusion-v6.pdf'].startswith(b'%PDF-'):
        raise ValueError('Final report PDF header missing')


def baseline_receipt(data, expected_sha):
    value = json.loads(data)
    needed = ('package_inventory_verified', 'v5_substantive_json_equal',
              'v5_independent_check_passed', 'v5_independent_substantive_json_equal',
              'both_populations_recomputed', 'posthoc_substantive_json_equal',
              'posthoc_independent_check_passed')
    if value.get('archive_sha256') != expected_sha or any(value.get(k) is not True for k in needed):
        raise ValueError('Historical V5 verification receipt does not bind this passing baseline')
    if value.get('models_called') is not False:
        raise ValueError('Historical receipt is not an offline analysis verification')
    return value


def entry_text():
    return '''# Start here: V6 shared convention control

This is the current research package. Read `output/report-v6/inherited-collusion-v6.pdf`
(or the editable `.docx`) for the combined research account. V6 is a separately
frozen follow-up using the complete available symmetric V5 donor cohort; it is
not an independent replication or evidence of spontaneous collusion.

- V6 protocol, execution freeze, budget and closure: `output/control-v6/docs/`.
- Exact fixed inputs and original provenance: `output/control-v6/inputs/`.
- New raw calls, saved episodes and per-case status: `output/control-v6/runs/`.
- Final arithmetic analysis and independent checks: `output/control-v6/analysis/`.
- Portable report sources, template, figures and requirements: `output/report-v6/source/`.
- Prior V4/V4F/V5 reports and every original data/source byte remain in this archive.
  The old root README is `evidence/reviewed-v5-baseline/files/README.md`.

From the extracted archive root, Python 3 with only its standard library can
reproduce V6 without inference or an account:

    python -I -S -B scripts/verify_v6_package.py --archive /path/to/this.zip --out /tmp/v6-verification

Add `--recheck-history` to also reconstruct and rerun the original V5 package's
strict V4, amended V4F, post-hoc and V5 offline checks in separate processes.
The existing byte-bound V5 offline PASS receipt is retained under
`evidence/reviewed-v5-baseline/offline-verification.json`.

The verifier checks every inventoried file and compares both V6 JSON outputs
exactly, including all rows, denominators and missingness bounds. Trusted-code
Python audit hooks deny the original source directories, networking and child
processes inside V6 analyses. This is not an operating-system security sandbox.
Report/figure rebuilding needs separately listed libraries and external PDF
rendering tools; statistical reproduction does not need them. No model call is
part of offline verification.

`PACKAGE-MANIFEST-v6.json` inventories every file except itself. Its external
SHA256 and the complete ZIP SHA256 are supplied with the final delivery.
The unchanged `PACKAGE-MANIFEST-v5.json` is historical, not the inventory of this
expanded package. No earlier result has been relabeled as V6.
'''


def build(study, report, baseline, old_receipt, destination, expected_base_sha=BASE_SHA256, scripts=None):
    study, report, baseline, old_receipt, destination = map(lambda p: Path(p).resolve(), (study, report, baseline, old_receipt, destination))
    # Check closure existence before touching any current calls or results.
    if not (study / 'docs/v6-closeout-record.json').is_file():
        raise ValueError('V6 has not closed; current outcomes will not be read')
    if sha(baseline.read_bytes()) != expected_base_sha:
        raise ValueError('Reviewed V5 archive SHA256 mismatch')
    old_manifest, old_raw, old = inventory_zip(baseline, BASE_MANIFEST)
    receipt_data = old_receipt.read_bytes(); baseline_receipt(receipt_data, expected_base_sha)
    allowed = [*STUDY_ALLOW, 'runs/phase6-budget.json', *('runs/' + r for r in RUN_IDS)]
    allowed.extend(p.name for p in study.glob('requirements*.txt'))
    current, sources = collect(study, allowed, STUDY)
    report_files, report_sources = collect(report, REPORT_ALLOW, REPORT)
    current.update(report_files); sources.update(report_sources)
    required = [*(STUDY + '/' + n for n in REQUIRED_STUDY), *(REPORT + '/' + n for n in REQUIRED_REPORT)]
    missing = sorted(set(required) - set(current))
    if missing:
        raise ValueError('Final V6 reproducibility artifacts missing: ' + ', '.join(missing))
    check_closed(current)
    scripts = Path(scripts).resolve() if scripts else Path(__file__).resolve().parent
    for name in ('package_v6_study.py', 'verify_v6_package.py', 'test_v6_packaging.py'):
        path = scripts / name; key = ('tests/' if name.startswith('test_') else 'scripts/') + name
        current[key] = path.read_bytes(); sources[key] = path; required.append(key)
    for name in ('README.md', 'validation.json'):
        path = scripts / name
        if path.is_file():
            key = 'evidence/v6-packaging/' + name
            current[key] = path.read_bytes(); sources[key] = path
    files = dict(old); files[BASE_MANIFEST] = old_raw
    for name, data in current.items():
        if name in files or name.startswith(HISTORY + '/'):
            raise ValueError('V6 additions collide with preserved history: ' + name)
        check_content(name, data); files[name] = data
    if 'README.md' not in old:
        raise ValueError('Baseline root README missing')
    old_readme = HISTORY + '/files/README.md'
    files[old_readme] = old['README.md']
    files['V6-START-HERE.md'] = entry_text().encode()
    files['README.md'] = b'# Inherited Collusion: current V6 research package\n\nStart with [V6-START-HERE.md](V6-START-HERE.md) and the [V6 report](output/report-v6/inherited-collusion-v6.pdf).\n\nThe byte-preserved [prior V5 README](evidence/reviewed-v5-baseline/files/README.md) describes the earlier package. All historical raw evidence, analyses and report sources remain available.\n'
    files[HISTORY + '/offline-verification.json'] = receipt_data
    check_report(files)
    required += ['V6-START-HERE.md', old_readme, BASE_MANIFEST, HISTORY + '/offline-verification.json']
    manifest = {
        'schema_version': 1, 'study_version': 6, 'created_at': datetime.now(timezone.utc).isoformat(),
        'source_project': old_manifest['source_project'], 'source_workspace': str(study.parent.parent),
        'source_study': str(study), 'source_report': str(report),
        'project': 'Inherited Collusion — A Causal Audit of Agent Handoffs',
        'current_entry': 'V6-START-HERE.md',
        'baseline': {'archive_sha256': expected_base_sha, 'manifest_path': BASE_MANIFEST,
                     'manifest_sha256': sha(old_raw), 'inventoried_files': len(old), 'zip_members': len(old) + 1,
                     'preserved_overrides': {'README.md': old_readme},
                     'offline_verification_path': HISTORY + '/offline-verification.json',
                     'offline_verification_sha256': sha(receipt_data),
                     'preservation_rule': 'All baseline ZIP member bytes are retained, including its manifest. Only the root README is relocated to the explicit historical path.'},
        'required_files': sorted(set(required) | set(old_manifest.get('required_files', []))),
        'required_nonempty_directories': old_manifest.get('required_nonempty_directories', []),
        'reproduction': {'analysis': ANALYSIS, 'independent_check': CHECK, 'crosscheck': CROSSCHECK,
                         'allowed_v6_json_differences': [], 'models_called': False},
        'exclusions': 'Secrets, environment/cache/lock files, redundant ZIPs, draft or synthetic report layouts; no historical baseline entry is removed.',
        'files': {n: entry(data) for n, data in sorted(files.items())},
    }
    raw = json_bytes(manifest); destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'inherited-collusion-v6-research-package.zip'
    fd, temp = tempfile.mkstemp(dir=destination, suffix='.zip.tmp'); os.close(fd); temp = Path(temp)
    try:
        with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.writestr(MANIFEST, raw)
            for n, data in sorted(files.items()):
                if n in sources and sources[n].read_bytes() != data:
                    raise ValueError('Source changed during packaging: ' + n)
                z.writestr(n, data)
        if sha(baseline.read_bytes()) != expected_base_sha or old_receipt.read_bytes() != receipt_data:
            raise ValueError('Historical input changed during packaging')
        written, written_raw, written_files = inventory_zip(temp, MANIFEST)
        if written_raw != raw or written_files != files:
            raise ValueError('Archive readback mismatch')
        os.replace(temp, archive)
    finally:
        temp.unlink(missing_ok=True)
    (destination / MANIFEST).write_bytes(raw)
    # User-facing copies are the exact report bytes inventoried in the ZIP.
    for name in REQUIRED_REPORT[:3]:
        (destination / name).write_bytes(files[REPORT + '/' + name])
    (destination / 'V6-START-HERE.md').write_bytes(files['V6-START-HERE.md'])
    (destination / (archive.stem + '.sha256')).write_text(sha(archive.read_bytes()) + '  ' + archive.name + '\n')
    print(json.dumps({'archive': str(archive), 'sha256': sha(archive.read_bytes()), 'files': len(files),
                      'baseline_inventoried_files_preserved': len(old), 'baseline_zip_members_preserved': len(old) + 1,
                      'readback_verified': True}))
    return archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', type=Path, required=True); p.add_argument('--report', type=Path, required=True)
    p.add_argument('--base-archive', type=Path, required=True); p.add_argument('--base-verification', type=Path, required=True)
    p.add_argument('--base-sha256', default=BASE_SHA256); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); build(a.study, a.report, a.base_archive, a.base_verification, a.out, a.base_sha256)


if __name__ == '__main__':
    main()
