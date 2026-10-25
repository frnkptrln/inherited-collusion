"""Verify a final package and reproduce analyses without live-project reads.

Stdlib only. Optional figure/PDF rendering is a separate documented step.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile

MANIFEST='PACKAGE-MANIFEST-v4.json'
WRAPPER=r'''
import os,runpy,sys
blocked=os.path.realpath(sys.argv[1]); script=sys.argv[2];args=sys.argv[3:]
def audit(event,values):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn','os.exec'):
        raise PermissionError('Offline verification forbids networking and child processes')
    if event in ('open','os.listdir','os.scandir') and values and isinstance(values[0],(str,bytes,os.PathLike)):
        path=os.path.realpath(os.fsdecode(values[0]))
        if path==blocked or path.startswith(blocked+os.sep):
            raise PermissionError('Offline verification forbids reading original project: '+path)
sys.addaudithook(audit)
sys.argv=[script]+args
runpy.run_path(script,run_name='__main__')
'''

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_name(name):
    if not isinstance(name,str) or not name or '\\' in name:raise ValueError('Unsafe archive path')
    path=PurePosixPath(name)
    if path.is_absolute() or not path.parts or str(path)!=name or any(p in ('.','..') for p in path.parts) or ':' in path.parts[0]:raise ValueError('Unsafe archive path')
    return name

def validate_manifest(value):
    if value.get('schema_version')!=1 or not isinstance(value.get('files'),dict) or not value['files']:raise ValueError('Invalid or empty package manifest')
    for name,entry in value['files'].items():
        safe_name(name)
        if name==MANIFEST or not isinstance(entry,dict) or type(entry.get('bytes')) is not int or entry['bytes']<0 or not isinstance(entry.get('sha256'),str) or len(entry['sha256'])!=64 or any(c not in '0123456789abcdef' for c in entry['sha256']):raise ValueError('Invalid manifest file entry')
    for name in value.get('required_files',[]):
        safe_name(name)
        if name not in value['files']:raise ValueError('Required package source missing: '+name)
    for name in value.get('required_nonempty_directories',[]):
        safe_name(name)
        if not any(p.startswith(name+'/') for p in value['files']):raise ValueError('Required package directory empty: '+name)
    return value

def verify_bytes(content,entry,name):
    if len(content)!=entry['bytes'] or hashlib.sha256(content).hexdigest()!=entry['sha256']:raise ValueError('Package byte hash mismatch: '+name)

def extract_verified(archive,target):
    """Reject unsafe paths, duplicates and symlinks before writing any member."""
    archive,target=Path(archive),Path(target)
    if target.exists() and any(target.iterdir()):raise ValueError('Extraction directory must be empty')
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP entry')
        for info in infos:
            safe_name(info.filename)
            kind=stat.S_IFMT(info.external_attr>>16)
            if info.is_dir() or kind not in (0,stat.S_IFREG):raise ValueError('Nonregular ZIP entry')
        manifest=validate_manifest(json.loads(z.read(MANIFEST)))
        if set(names)!=set(manifest['files'])|{MANIFEST}:raise ValueError('ZIP inventory differs from manifest')
        for name,entry in manifest['files'].items():verify_bytes(z.read(name),entry,name)
        target.mkdir(parents=True,exist_ok=True)
        for name in names:
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(z.read(name))
    return verify_extracted(target)

def verify_extracted(root):
    root=Path(root).resolve()
    if (root/MANIFEST).is_symlink():raise ValueError('Manifest must not be a symlink')
    manifest=validate_manifest(json.loads((root/MANIFEST).read_text()))
    actual=set()
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError('Extracted package contains a symlink')
        if path.is_file():actual.add(str(path.relative_to(root)))
    if actual!=set(manifest['files'])|{MANIFEST}:raise ValueError('Extracted inventory differs from manifest')
    for name,entry in manifest['files'].items():verify_bytes((root/name).read_bytes(),entry,name)
    return manifest

def normalize(value,roots):
    if isinstance(value,dict):return {k:normalize(v,roots) for k,v in value.items()}
    if isinstance(value,list):return [normalize(v,roots) for v in value]
    if isinstance(value,str):
        for root in roots:
            text=str(root)
            if value==text or value.startswith(text+os.sep):return '<PROJECT>'+value[len(text):]
    return value

def comparable(value,roots):
    value=normalize(value,roots)
    value.pop('analyzed_at',None)
    if 'strict_planned_completion_bounds' in value:value['strict_planned_completion_bounds'].pop('input_analysis_sha256',None)
    return value

def isolated_run(script,args,original,cwd,out,label):
    executable=Path(sys.executable).resolve()
    if executable.is_relative_to(original):raise ValueError('Use a Python installation outside the original project')
    # -I ignores PYTHONPATH/user site; -S prevents site startup imports.
    # No inherited HF credentials are passed to the subprocess.
    result=subprocess.run([str(executable),'-I','-S','-B','-c',WRAPPER,str(original),str(script),*map(str,args)],cwd=cwd,env={'PATH':os.defpath,'LANG':'C.UTF-8'},text=True,capture_output=True)
    (out/(label+'.stdout.txt')).write_text(result.stdout);(out/(label+'.stderr.txt')).write_text(result.stderr)
    if result.returncode:raise RuntimeError(label+' failed offline; see saved diagnostics')

def verify(extracted,original,out):
    extracted,original,out=Path(extracted).resolve(),Path(original).resolve(),Path(out).resolve()
    if extracted==original or extracted.is_relative_to(original) or out.is_relative_to(extracted) or out.is_relative_to(original):raise ValueError('Extraction and outputs must be outside original project; outputs outside extraction')
    if out.exists() and any(out.iterdir()):raise ValueError('Choose an empty verification output directory')
    manifest=verify_extracted(extracted);out.mkdir(parents=True,exist_ok=True)
    strict,amended=out/'strict-recomputed.json',out/'amended-recomputed.json'
    for script,destination,extra in [('analyze_v4_study.py',strict,[]),('analyze_v4f_study.py',amended,['--strict-analysis',strict])]:
        isolated_run(extracted/'scripts'/script,['--project',extracted,'--out',destination,*extra],original,extracted,out,script)
    comparisons=[]
    for label,saved,new in [('strict',extracted/'output/analysis-v4/analysis.json',strict),('amended',extracted/'output/analysis-v4f/analysis.json',amended)]:
        first,second=json.loads(saved.read_text()),json.loads(new.read_text())
        if comparable(first,[original,extracted])!=comparable(second,[original,extracted]):raise ValueError(label+' reanalysis differs beyond analysis timestamps, rebased root paths and verified strict-input digest')
        comparisons.append({'population':label,'substantive_json_equal':True,'packaged_sha256':digest(saved),'recomputed_sha256':digest(new)})
    old_f=json.loads((extracted/'output/analysis-v4f/analysis.json').read_text());new_f=json.loads(amended.read_text())
    if old_f['strict_planned_completion_bounds']['input_analysis_sha256']!=digest(extracted/'output/analysis-v4/analysis.json'):raise ValueError('Packaged strict bounds input hash mismatch')
    if new_f['strict_planned_completion_bounds']['input_analysis_sha256']!=digest(strict):raise ValueError('Recomputed strict bounds input hash mismatch')
    checks=[]
    for suffix,analysis in [('v4',strict),('v4f',amended)]:
        target=out/('independent-'+suffix)
        isolated_run(extracted/'evidence'/f'{suffix}-independent/check_results.py',['--project',extracted,'--final-analysis',analysis,'--out',target],original,extracted,out,'independent-'+suffix)
        value=json.loads((target/'independent-check.json').read_text())
        if value.get('passed') is not True or value.get('mismatches')!=[]:raise ValueError('Independent raw crosscheck failed')
        checks.append({'population':suffix,'passed':True,'result_sha256':digest(target/'independent-check.json')})
    verify_extracted(extracted)
    report={'both_populations_recomputed':True,'package_inventory_verified':True,'packaged_files':len(manifest['files']),
            'original_project_read_access_denied':True,'network_and_subprocess_creation_denied_in_analysis':True,'isolated_stdlib_python':True,'models_called':False,
            'comparisons':comparisons,'independent_checks':checks,'allowed_differences':['top-level analysis timestamps','project-prefix path rebasing','strict-input digest, independently verified for each output'],
            'not_checked':'Figure/PDF rendering needs separately recorded optional libraries and external rendering tools.'}
    (out/'offline-verification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    p=argparse.ArgumentParser(description=__doc__);source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--extracted',type=Path);source.add_argument('--archive',type=Path)
    p.add_argument('--original',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.archive:
        with tempfile.TemporaryDirectory(prefix='collusion-offline-') as tmp:
            extract_verified(a.archive,Path(tmp)/'project');result=verify(Path(tmp)/'project',a.original,a.out)
            result['archive_sha256']=digest(a.archive);(a.out/'offline-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    else:result=verify(a.extracted,a.original,a.out)
    print(json.dumps(result))
if __name__=='__main__':main()
