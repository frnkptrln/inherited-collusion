#!/usr/bin/env python3
"""Bundle allowlisted project evidence, excluding environments and credentials."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

REQUIRED_FILES = (
    'README.md', 'requirements-research.txt', 'requirements-analysis.txt',
    'scripts/package_v4_study.py', 'scripts/verify_offline_package.py',
    'scripts/analyze_v4_study.py', 'scripts/analyze_v4f_study.py',
    'scripts/strict_bounds.py', 'scripts/plot_v4_study.py', 'scripts/plot_v4_fixture.py',
    'scripts/v4_runner.py', 'scripts/v4f_runner.py',
    'evidence/v4-independent/check_results.py', 'evidence/v4f-independent/check_results.py',
    'output/analysis-v4/analysis.json', 'output/analysis-v4f/analysis.json',
    'output/independent-v4/independent-check.json', 'output/independent-v4f/independent-check.json',
    'output/report-v4/inherited-collusion-v4.docx', 'output/report-v4/inherited-collusion-v4.pdf',
    'output/report-v4/inherited-collusion-v4.audit.json',
    'output/report-v4/source/build_report.py', 'output/report-v4/source/report-input.json',
    'output/report-v4/source/official-template.docx', 'output/report-v4/source/requirements-report.txt',
    'output/report-v4/source/dependency-versions.json', 'output/report-v4/source/README.md',
    'docs/analysis-environment.json', 'docs/v4f-freeze.json', 'docs/v4f-preparation.json', 'docs/v4-strict-closeout-record.json',
)
REQUIRED_DIRECTORIES = ('inherited_collusion', 'tests', 'output/figures-v4-strict', 'output/figures-v4f-amended')

def require_relative(value):
    if not isinstance(value,str) or not value:raise ValueError('Unsafe package-relative path')
    path=Path(value)
    if not path.parts or path.is_absolute() or str(path)!=value or '\\' in value or any(p in ('..','.') for p in path.parts) or ':' in path.parts[0]:
        raise ValueError('Unsafe package-relative path')
    return path

def build(project, destination):
    project=project.resolve();destination.mkdir(parents=True,exist_ok=True)
    ledger=json.loads((project/'runs/phase4-budget.json').read_text())
    allowed=['README.md','requirements-research.txt','inherited_collusion','scripts','tests','configs','docs','vendor','evidence',
             'output/report','output/report-v4','output/analysis','output/analysis-v4','output/analysis-v4f','output/v3-pilot-analysis.json',
             'output/independent-v4','output/independent-v4f','output/figures-v4-strict','output/figures-v4f-amended',
             'runs/budget-ledger.json','runs/phase3-budget.json','runs/phase4-budget.json','runs/phase4f-budget.json',
             'runs/hf-pilot-v1','runs/hf-pilot-table-v1','runs/hf-pilot-thinking-v1',
             'runs/v3-pilot-qwen-901','runs/v3-pilot-deepseek-901','runs/v3-dispatch','runs/v4-dispatch','runs/v4f-dispatch']
    allowed += ['runs/'+name for name in ledger['allocations']]
    allowed += [str(p.relative_to(project)) for p in project.glob('requirements*.txt')]
    if (project/'runs/phase4f-budget.json').exists():
        continuation=json.loads((project/'runs/phase4f-budget.json').read_text())
        allowed += ['runs/'+name for name in continuation['allocations']]
    files={}
    token_pattern=re.compile(rb'hf_[A-Za-z0-9]{20,}')
    for relative in allowed:
        path=project/require_relative(relative)
        if path.is_symlink():raise ValueError(f'Symlink not permitted in evidence package: {relative}')
        if not path.exists():continue
        candidates=[path] if path.is_file() else sorted(path.rglob('*'))
        for candidate in candidates:
            rel=candidate.relative_to(project)
            if any(part.startswith('.') or part=='__pycache__' for part in rel.parts):continue
            if candidate.suffix in ('.pyc','.lock','.zip'):continue
            if candidate.is_symlink():raise ValueError(f'Symlink not permitted in evidence package: {rel}')
            if not candidate.is_file():continue
            content=candidate.read_bytes()
            if token_pattern.search(content):raise ValueError(f'Possible credential in {rel}; no secret value printed')
            files[str(rel)]={'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
    missing=[name for name in REQUIRED_FILES if name not in files]
    missing += [name+'/' for name in REQUIRED_DIRECTORIES if not any(p.startswith(name+'/') for p in files)]
    if missing:raise ValueError('Final reproducibility sources/results missing: '+', '.join(missing))
    manifest={'schema_version':1,'created_at':datetime.now(timezone.utc).isoformat(),
              'project':'Inherited Collusion — A Causal Audit of Agent Handoffs',
              'author':'Frank Peterlein','affiliation':'Independent researcher',
              'description':'Original strict V4 evidence, explicitly post-start V4F format continuation, and historical failed pilots; shared generations are not independent replications. No mock output is a research finding.',
              'excluded':'Local authentication, .venv, caches, hidden files, unrelated jobs, previous ZIP bundles.',
              'required_files':list(REQUIRED_FILES), 'required_nonempty_directories':list(REQUIRED_DIRECTORIES),
              'reproduction_scope':'Core analyses and independent checks are stdlib-only; figure/report requirements are included separately. PDF rendering additionally requires external LibreOffice/Poppler.',
              'files':dict(sorted(files.items()))}
    manifest_bytes=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    archive=destination/'inherited-collusion-v4-research-package.zip'
    with tempfile.NamedTemporaryFile(dir=destination,suffix='.zip.tmp',delete=False) as stream:temporary=Path(stream.name)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            z.writestr('PACKAGE-MANIFEST-v4.json',manifest_bytes)
            for relative,expected in sorted(files.items()):
                content=(project/relative).read_bytes()
                if len(content)!=expected['bytes'] or hashlib.sha256(content).hexdigest()!=expected['sha256']:
                    raise ValueError(f'Source changed during packaging: {relative}')
                z.writestr(relative,content)
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:raise ValueError('ZIP integrity check failed')
            if len(z.namelist())!=len(files)+1 or set(z.namelist()) != set(files)|{'PACKAGE-MANIFEST-v4.json'}:raise ValueError('Archive inventory mismatch')
            for relative,expected in files.items():
                content=z.read(relative)
                if len(content)!=expected['bytes'] or hashlib.sha256(content).hexdigest()!=expected['sha256']:
                    raise ValueError(f'Archive content mismatch: {relative}')
        os.replace(temporary,archive)
    finally:
        temporary.unlink(missing_ok=True)
    (destination/'PACKAGE-MANIFEST-v4.json').write_bytes(manifest_bytes)
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    (destination/'inherited-collusion-v4-research-package.sha256').write_text(f'{sha}  {archive.name}\n')
    print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size,'sha256':sha,'readback_verified':True}))
    return archive

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();build(args.project,args.out)
