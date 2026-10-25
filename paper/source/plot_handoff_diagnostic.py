#!/usr/bin/env python3
"""Plot the preserved post-hoc baseline diagnostic, validating embedded raw rows."""
import argparse,hashlib,json,math,subprocess
from collections import Counter
from pathlib import Path
import reportlab
from reportlab.graphics import renderPDF,renderSVG
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing,String
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ARMS=('facts_only','matched','verified')
METRICS=(('joint_harm_n','Joint harmful allocation','harmful_joint'),('duplicate_episode_n','Duplicate task claim','violations'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--diagnostic',type=Path,required=True);ap.add_argument('--sha256',required=True);ap.add_argument('--outdir',type=Path,required=True);ap.add_argument('--pdftoppm',type=Path);a=ap.parse_args()
 assert sha(a.diagnostic)==a.sha256,'diagnostic hash mismatch';j=json.loads(a.diagnostic.read_text());assert j['passed'];assert j['analysis_type']=='POSTHOC_DIAGNOSTIC_NOT_PRESPECIFIED'
 rs=[r for r in j['results'] if r['population']=='V4F_post_start_amended'];assert len(rs)==2
 labels={'Qwen/Qwen3.6-35B-A3B':'Qwen3.6-35B-A3B','openai/gpt-oss-120b':'GPT-OSS-120B'}
 panels=[]
 for r in rs:
  rows=r['audited_raw_rows'];seeds=r['baseline_comparison_seeds'];assert len(rows)==len(seeds)*6
  assert set(x['seed'] for x in rows)==set(seeds)
  for arm in ARMS:
   part=[x for x in rows if x['condition']==arm];assert set(Counter(x['seed'] for x in part).values())=={2};g=r['arms'][arm];assert len(part)==g['episodes']
   assert sum(bool(x['harmful_joint']) for x in part)==g['joint_harm_n'];assert sum(x['violations']>0 for x in part)==g['duplicate_episode_n']
   for metric in ['total_reward','outsider_loss']:assert math.isclose(sum(x[metric] for x in part)/len(part),g['means'][metric],abs_tol=1e-10)
  panels.append({'model':r['model'],'label':labels[r['model']],'seeds':seeds,'arms':r['arms']})
 fontdir=Path(reportlab.__file__).parent/'fonts'
 for name,file in [('Chart','Vera.ttf'),('ChartBold','VeraBd.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fontdir/file)))
 d=Drawing(468,323)
 for row,p in enumerate(panels):
  for col,(key,label,_) in enumerate(METRICS):
   x=34+col*234;y=193-row*143;n=p['arms']['matched']['episodes']
   d.add(String(x,y+110,p['label'],fontName='ChartBold',fontSize=10))
   d.add(String(x,y+96,label,fontName='Chart',fontSize=9))
   d.add(String(x,y+83,f'{len(p["seeds"])} common cases; {n} episodes per arm',fontName='Chart',fontSize=8,fillColor=colors.HexColor('#374151')))
   c=VerticalBarChart();c.x=x;c.y=y;c.width=182;c.height=70;c.data=[tuple(p['arms'][arm][key]/n for arm in ARMS)]
   c.categoryAxis.categoryNames=['Facts only','Both notes','Notes + verify'];c.categoryAxis.labels.fontName='Chart';c.categoryAxis.labels.fontSize=8;c.categoryAxis.labels.boxAnchor='n';c.categoryAxis.labels.dy=-4;c.categoryAxis.strokeColor=colors.HexColor('#9CA3AF')
   c.valueAxis.valueMin=0;c.valueAxis.valueMax=1;c.valueAxis.valueStep=.5;c.valueAxis.labelTextFormat=lambda v:f'{100*v:.0f}%';c.valueAxis.labels.fontName='Chart';c.valueAxis.labels.fontSize=8;c.valueAxis.strokeColor=colors.HexColor('#9CA3AF');c.valueAxis.visibleGrid=True;c.valueAxis.gridStrokeColor=colors.HexColor('#E5E7EB');c.valueAxis.gridStrokeWidth=.4
   c.barWidth=30;c.groupSpacing=12;c.barLabelFormat=lambda v,den=n:f'{round(v*den)}/{den}';c.barLabels.fontName='Chart';c.barLabels.fontSize=8;c.barLabels.dy=2;c.barLabels.boxAnchor='s'
   for i,color in enumerate(['#64748B','#B45309','#0F766E']):c.bars[(0,i)].fillColor=colors.HexColor(color);c.bars[(0,i)].strokeColor=None
   d.add(c)
 d.add(String(0,17,'Post-hoc common-case diagnostic from the format-expanded handoff audit.',fontName='Chart',fontSize=8))
 d.add(String(0,5,'Two draws per case. Labels give events / valid episodes in this common-case subset.',fontName='Chart',fontSize=8))
 a.outdir.mkdir(parents=True,exist_ok=True);stem=a.outdir/'handoff-diagnostic';renderPDF.drawToFile(d,str(stem.with_suffix('.pdf')));renderSVG.drawToFile(d,str(stem.with_suffix('.svg')))
 files=[stem.with_suffix('.pdf'),stem.with_suffix('.svg')]
 if a.pdftoppm:subprocess.run([str(a.pdftoppm),'-singlefile','-png','-r','300',str(stem.with_suffix('.pdf')),str(stem)],check=True);files.append(stem.with_suffix('.png'))
 proof={'diagnostic_sha256':a.sha256,'script_sha256':sha(Path(__file__)),'selection':'Saved post-hoc diagnostic; format-expanded population only; common verification cases in both original objectives and both repeats, with both facts-only draws present; no new selection by outcome values.','raw_row_counts_recomputed':True,'panels':panels,'files':[{'path':p.name,'sha256':sha(p)} for p in files]};stem.with_suffix('.audit.json').write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'status':'PASS','panels':len(panels),'raw_rows':sum(len(x['seeds'])*6 for x in panels)}))
if __name__=='__main__':main()
