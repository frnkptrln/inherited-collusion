#!/usr/bin/env python3
"""Read-only validation of the template edition against approved V6 content."""
import argparse, hashlib, json
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
B=Path(__file__).resolve().parent
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--docx',type=Path,default=B.parent/'inherited-collusion-submission.docx');ap.add_argument('--out',type=Path);a=ap.parse_args()
 old=json.loads((B/'verified-v6-input.json').read_text());new=json.loads((B/'report-input.json').read_text());mapping=json.loads((B/'content-mapping.json').read_text());checks=[]
 assert sha(B/'verified-v6-input.json')=='0c2de397b7cdc5d65bca42b3ea901a348f6a049f175af29f7866608d0e26a8ce'
 for k in ['title','subtitle','author','affiliation','abstract','evidence_inputs','follow_up']:assert old[k]==new[k],k
 for m in mapping['mapping']:
  b=dict(new['blocks'][m['new_block']]);assert b.pop('baseline_block')==m['baseline_block'];assert b==old['blocks'][m['baseline_block']],m
 expected=set(range(len(old['blocks'])))-set(mapping['removed_only_main_headings'])
 assert expected=={m['baseline_block'] for m in mapping['mapping']}
 for typ,count in [('table',13),('figure',3)]:
  before=[b for b in old['blocks'] if b['type']==typ];after=[{k:v for k,v in b.items() if k!='baseline_block'} for b in new['blocks'] if b['type']==typ];assert before==after and len(after)==count
 with ZipFile(a.docx) as z,ZipFile(B/'personal-apart-template.docx') as t:
  doc=ET.fromstring(z.read('word/document.xml'));alltext='\n'.join(''.join(p.xpath('.//w:t/text()',namespaces=W)) for p in doc.xpath('//w:p',namespaces=W))
  for b in new['blocks']:
   if b['type'] in ['p','heading','caption']:assert b['text'] in alltext,b['text'][:50]
  for bad in ['PROJECT TITLE','Author name 1','Summarize your project','How to use this template','All results and claims were independently verified']:
   assert bad not in alltext,bad
  changed=[n for n in t.namelist() if t.read(n)!=z.read(n)]
  assert set(changed)=={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
  figures=[b for b in new['blocks'] if b['type']=='figure']
  for i,b in enumerate(figures,1):assert hashlib.sha256(z.read(f'word/media/v4-figure-{i}.png')).hexdigest()==b['sha256']
 result={'status':'PASS','baseline_sha256':sha(B/'verified-v6-input.json'),'input_sha256':sha(B/'report-input.json'),'docx_sha256':sha(a.docx),'mapped_blocks':len(mapping['mapping']),'scientific_tables':13,'figures':3,'abstract_words':len(new['abstract'].split()),'unchanged_evidence_bindings':len(old['evidence_inputs']),'only_changed_template_parts':changed,'all_mapped_prose_and_tables_unchanged':True,'all_scientific_figure_bytes_unchanged':True,'template_placeholders_absent':True}
 if a.out:a.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
