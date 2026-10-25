#!/usr/bin/env python3
"""Copy retained report inputs, deny original-root/network access, rebuild DOCX.

No experiment code is executed. Rendering is deliberately outside this check.
"""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
from zipfile import ZipFile
BUILD=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project-root',type=Path,required=True);ap.add_argument('--docx',type=Path,required=True);ap.add_argument('--out',type=Path,default=BUILD/'portable-rebuild.json');args=ap.parse_args()
 root=args.project_root.resolve();spec=json.loads((BUILD/'report-input.json').read_text())
 with tempfile.TemporaryDirectory(prefix='v6-report-portable-') as tmp:
  copy=Path(tmp)/'project';s=copy/'output/report-v6/source';s.mkdir(parents=True)
  for f in BUILD.iterdir():
   if f.is_file() and f.suffix in {'.py','.json','.docx','.txt','.md'}:shutil.copy2(f,s/f.name)
  rels={x['path'] for x in spec['evidence_inputs']}|{x['path'] for x in spec['blocks'] if x['type']=='figure'}
  for f in json.loads((root/'output/report-v6/figures/v6-safe-conventions.audit.json').read_text())['files']:rels.add('output/report-v6/figures/'+f['path'])
  for rel in sorted(rels):
   d=copy/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,d)
  original_input=sha(s/'report-input.json')
  code=r'''
import sys,os,runpy
from pathlib import Path
copy=Path(sys.argv[1]).resolve(); source=copy/'output/report-v6/source'
blocked=[Path(p).resolve() for p in sys.argv[2:]]
def hook(event,args):
 if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
  p=Path(os.fsdecode(args[0])).resolve()
  if not p.is_relative_to(copy) and any(p.is_relative_to(x) for x in blocked):raise RuntimeError('Original report/evidence access denied')
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn'}:raise RuntimeError('Network and child processes denied')
sys.addaudithook(hook);sys.dont_write_bytecode=True;sys.path.insert(0,str(source))
sys.argv=[str(source/'prepare_final_input.py'),'--project-root',str(copy),'--final']
runpy.run_path(sys.argv[0],run_name='__main__')
sys.argv=[str(source/'build_report.py'),'--project-root',str(copy),'--artifact-root',str(copy),'--input',str(source/'report-input.json'),'--out',str(copy/'rebuilt.docx')]
runpy.run_path(sys.argv[0],run_name='__main__')
'''
  result=subprocess.run([sys.executable,'-I','-B','-c',code,str(copy),str(root),str(BUILD.parent),'/home/user/projects/collusion-sprint'],capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stderr or result.stdout)
  new_input=sha(s/'report-input.json')
  with ZipFile(args.docx) as old,ZipFile(copy/'rebuilt.docx') as new:
   assert old.namelist()==new.namelist(),'DOCX member inventory changed'
   changed=[name for name in old.namelist() if old.read(name)!=new.read(name)]
  assert new_input==original_input and not changed,'Portable rebuild differs'
  proof={'status':'PASS','input_sha256':original_input,'rebuilt_input_sha256':new_input,'original_docx_sha256':sha(args.docx),'source_sha256':sha(Path(__file__)),'copied_evidence_files':len(rels),'docx_members_compared':len(old.namelist()),'changed_docx_members':changed,'original_project_and_report_reads_denied':True,'network_and_child_processes_denied_in_rebuild':True,'isolated_python':True,'pdf_render_repeated':False,'scope':'Exact input bytes and DOCX package-member bytes reproduce from portable copies. This is not a full research ZIP verification.'}
  args.out.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
