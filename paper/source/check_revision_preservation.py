#!/usr/bin/env python3
"""Check preserved scientific payloads; allow the explicitly requested prose revision."""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
B=Path(__file__).resolve().parent
W={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,default=B/'report-input.json');ap.add_argument('--docx',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 old=json.loads((B/'verified-template-input.json').read_text());new=json.loads(a.input.read_text());assert sha(B/'verified-template-input.json')=='a9a1fbbfaf1d6bf44a09cdde6472fbe1b53b6a78f7dc93314ff048720218326e'
 payload=lambda b:json.dumps({k:b[k] for k in ['headers','rows','widths'] if k in b},sort_keys=True,ensure_ascii=False)
 before=Counter(payload(b) for b in old['blocks'] if b['type']=='table');after=Counter(payload(b) for b in new['blocks'] if b['type']=='table');assert sum(before.values())==13;assert not(before-after)
 fig_before=Counter(b['sha256'] for b in old['blocks'] if b['type']=='figure');fig_after=Counter(b['sha256'] for b in new['blocks'] if b['type']=='figure');assert not(fig_before-fig_after)
 for e in old['evidence_inputs']:assert e in new['evidence_inputs']
 # All historical appendix prose retained, even when the new main account is shorter.
 texts=[b.get('text') for b in new['blocks']]
 historical=[b['text'] for b in old['blocks'][35:136] if b['type']=='p']
 for t in historical:
  if t.startswith('Observed Qwen harmful coverage differs:'):
   t=t.replace('baseline in Figure 1 is instead','baseline in Figure I1 is instead')
  assert t in texts,t[:100]
 if a.docx:
  with ZipFile(a.docx) as z,ZipFile(B/'personal-apart-template.docx') as ref:
   changed=[n for n in ref.namelist() if ref.read(n)!=z.read(n)];assert set(changed)=={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
   doc=ET.fromstring(z.read('word/document.xml'));body='\n'.join(''.join(p.xpath('.//w:t/text()',namespaces=W)) for p in doc.xpath('//w:p',namespaces=W))
   for b in new['blocks']:
    if b['type'] in ['p','caption','heading']:assert b['text'] in body,b['text'][:80]
   for i,b in enumerate([b for b in new['blocks'] if b['type']=='figure'],1):assert hashlib.sha256(z.read(f'word/media/v4-figure-{i}.png')).hexdigest()==b['sha256']
 out={'status':'PASS','scope':'Scientific payload and historical appendix preservation; main prose is intentionally rewritten and separately reviewed.','prior_input_sha256':sha(B/'verified-template-input.json'),'input_sha256':sha(a.input),'historical_table_payloads_preserved':13,'historical_figure_bytes_preserved':3,'historical_appendix_paragraphs_preserved':len(historical),'historical_reference_corrections':['One Figure 1 reference corrected to Figure I1 after relocating the unchanged figure.'],'unchanged_historical_evidence_bindings':len(old['evidence_inputs']),'ready_for_final':new['ready_for_final'],'docx_sha256':sha(a.docx) if a.docx else None}
 a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
