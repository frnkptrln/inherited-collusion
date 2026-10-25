#!/usr/bin/env python3
"""Rebuild the editable paper from declared inputs with original reads denied."""
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
from zipfile import ZipFile
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 spec=json.loads((B/'report-input.json').read_text());source_docx=B.parent/'inherited-collusion-revised.docx'
 assert spec['ready_for_final'] is True,'Final input required'
 with tempfile.TemporaryDirectory(prefix='apart-revision-portable-') as tmp:
  root=Path(tmp);paper=root/'paper';research=root/'research';shutil.copytree(B,paper/'source',ignore=shutil.ignore_patterns('__pycache__'))
  wanted={x['path'] for x in spec['evidence_inputs']}|{x['path'] for x in spec['blocks'] if x['type']=='figure' and not x.get('local_path')}
  for name in wanted:
   target=research/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.project_root/name,target)
  local={x['local_path'] for x in spec['blocks'] if x['type']=='figure' and x.get('local_path')}
  for name in local:
   target=paper/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(B.parent/name,target)
  wrapper=root/'guarded_build.py';wrapper.write_text('''import os,runpy,sys\nblocked=sys.argv[1:3]\nscript=sys.argv[3]\nsys.argv=sys.argv[3:]\ndef hook(event,args):\n if event in ('socket.connect','subprocess.Popen','os.system'): raise RuntimeError('forbidden operation '+event)\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  p=os.path.abspath(os.fsdecode(args[0]))\n  if any(p==v or p.startswith(v+os.sep) for v in blocked): raise RuntimeError('original root unavailable: '+p)\nsys.addaudithook(hook)\nrunpy.run_path(script,run_name='__main__')\n''')
  out=paper/'inherited-collusion-revised.docx'
  cmd=[sys.executable,'-I','-B',str(wrapper),str(B.parent.resolve()),str(a.project_root.resolve()),str(paper/'source/build_report.py'),'--project-root',str(research),'--out',str(out)]
  p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
  with ZipFile(source_docx) as x,ZipFile(out) as y:
   assert x.namelist()==y.namelist();assert all(x.read(n)==y.read(n) for n in x.namelist())
  result={'status':'PASS','input_sha256':sha(B/'report-input.json'),'builder_sha256':sha(B/'build_report.py'),'source_docx_sha256':sha(source_docx),'isolated_evidence_files':len(wanted),'local_figures':len(local),'all_docx_package_part_bytes_identical':True,'original_report_and_evidence_root_reads_denied':True,'network_and_subprocess_denied_inside_builder':True,'scope':'Editable DOCX package rebuild; PDF pixel identity is a separate render check.'}
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
