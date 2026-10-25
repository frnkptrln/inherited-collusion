#!/usr/bin/env python3
"""Reproducible scientific figure from a sealed, hash-pinned V6 analysis.

Uses the bundled ReportLab chart library; optional PNG export uses Poppler.
Rejects software-only data and independently checks every plotted count against
the analysis's individual rows. It does not perform inference or change data.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

import reportlab
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ARMS = ('verified','tie_first','tie_last')
MODELS = (('qwen','Qwen3.6-35B-A3B',4),('gptoss','GPT-OSS-120B',6))
MODES = (('harmful','Harmful original'),('legitimate','Legitimate original'))
PALETTE = ('#64748B','#2563EB','#0F766E')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_panels(data):
    if data.get('evidence_class') != 'V6_FIXED_HANDOFF_SHARED_CONVENTION':
        raise ValueError('Only real closed V6 data may be plotted')
    if not data.get('closeout_sha256'):
        raise ValueError('Missing data-closure binding')
    panels=[]
    for mode,mode_label in MODES:
        for alias,model_label,planned_cases in MODELS:
            groups=[]
            for arm in ARMS:
                matches=[g for g in data['groups'] if g['alias']==alias and g['mode']==mode and g['condition']==arm and g['scope']=='common_complete']
                if len(matches)!=1:
                    raise ValueError('Missing or duplicate common-case group')
                group=matches[0]
                rows=[r for r in data['rows'] if r['alias']==alias and r['mode']==mode and r['condition']==arm and r['seed'] in group['seeds']]
                counts=Counter(r['seed'] for r in rows)
                if any(n!=2 for n in counts.values()) or set(counts)!=set(group['seeds']):
                    raise ValueError('Each included case must have exactly two draws')
                if len(rows)!=group['episodes']:
                    raise ValueError('Episode denominator mismatch')
                value=sum(r['safe_optimal'] for r in rows)
                if value!=group['counts']['safe_optimal']:
                    raise ValueError('Safe-optimal count mismatch')
                rate=group['metrics']['safe_optimal']
                if rows and (not math.isfinite(rate) or abs(rate-value/len(rows))>1e-12):
                    raise ValueError('Safe-optimal rate mismatch')
                if not rows and rate is not None:
                    raise ValueError('Empty group is not a zero-rate observation')
                groups.append({'arm':arm,'seeds':group['seeds'],'episodes':len(rows),'safe_optimal':value,'rate':rate})
            if any(g['seeds']!=groups[0]['seeds'] for g in groups):
                raise ValueError('Different case sets across displayed arms')
            panels.append({'alias':alias,'model':model_label,'mode':mode,'mode_label':mode_label,'planned_cases':planned_cases,'seeds':groups[0]['seeds'],'groups':groups})
    return panels

def create_drawing(panels):
    font_dir=Path(reportlab.__file__).resolve().parent/'fonts'
    for name,file in [('ReportSans','Vera.ttf'),('ReportSansBold','VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name,str(font_dir/file)))
    drawing=Drawing(468,408)
    for index,panel in enumerate(panels):
        col=index%2;row=index//2
        left=34+col*234
        bottom=230-row*176
        drawing.add(String(left,bottom+136,panel['model'],fontName='ReportSansBold',fontSize=10.5,fillColor=colors.HexColor('#111827')))
        drawing.add(String(left,bottom+122,panel['mode_label'],fontName='ReportSans',fontSize=9.5))
        n=len(panel['seeds']);total=panel['groups'][0]['episodes']
        drawing.add(String(left,bottom+109,f'{n}/{panel["planned_cases"]} cases; {total} episodes per arm',fontName='ReportSans',fontSize=8.5,fillColor=colors.HexColor('#374151')))
        if not n:
            drawing.add(String(left+8,bottom+49,'No common complete cases',fontName='ReportSans',fontSize=9))
            continue
        chart=VerticalBarChart()
        chart.x=left;chart.y=bottom;chart.width=182;chart.height=94
        chart.data=[tuple(g['rate'] for g in panel['groups'])]
        chart.categoryAxis.categoryNames=['Verify only','Verify + first','Verify + last']
        chart.categoryAxis.labels.fontName='ReportSans';chart.categoryAxis.labels.fontSize=8
        chart.categoryAxis.labels.boxAnchor='n';chart.categoryAxis.labels.dy=-4
        chart.categoryAxis.strokeColor=colors.HexColor('#9CA3AF')
        chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=1;chart.valueAxis.valueStep=.25
        chart.valueAxis.labelTextFormat=lambda value:f'{value*100:.0f}%'
        chart.valueAxis.labels.fontName='ReportSans';chart.valueAxis.labels.fontSize=8
        chart.valueAxis.labels.dx=-3
        chart.valueAxis.strokeColor=colors.HexColor('#9CA3AF')
        chart.valueAxis.visibleGrid=True;chart.valueAxis.gridStrokeColor=colors.HexColor('#E5E7EB')
        chart.valueAxis.gridStrokeWidth=.4
        chart.barWidth=30;chart.groupSpacing=12
        chart.barLabelFormat=lambda value,den=total:f'{round(value*den)}/{den}'
        chart.barLabels.fontName='ReportSans';chart.barLabels.fontSize=8
        chart.barLabels.dy=2;chart.barLabels.boxAnchor='s'
        for i,color in enumerate(PALETTE):
            chart.bars[(0,i)].fillColor=colors.HexColor(color)
            chart.bars[(0,i)].strokeColor=None
        drawing.add(chart)
    drawing.add(String(0,25,'Safe optimum = distinct completion and globally minimum all-agent cost.',fontName='ReportSans',fontSize=8))
    drawing.add(String(0,13,'Fresh V6 calls only. Labels give safe episodes / valid episodes; two draws per case.',fontName='ReportSans',fontSize=8))
    drawing.add(String(0,1,'Common complete cases within model and original objective; no population confidence intervals.',fontName='ReportSans',fontSize=8))
    return drawing

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--analysis-sha256',required=True)
    parser.add_argument('--outdir',type=Path,required=True)
    parser.add_argument('--pdftoppm',type=Path,help='Optional Poppler executable for 300-dpi PNG export')
    args=parser.parse_args()
    if sha(args.analysis)!=args.analysis_sha256:
        raise SystemExit('Analysis hash mismatch')
    data=json.loads(args.analysis.read_text());panels=load_panels(data)
    args.outdir.mkdir(parents=True,exist_ok=True)
    drawing=create_drawing(panels)
    pdf=args.outdir/'v6-safe-conventions.pdf';svg=args.outdir/'v6-safe-conventions.svg'
    renderPDF.drawToFile(drawing,str(pdf))
    renderSVG.drawToFile(drawing,str(svg))
    files=[pdf,svg]
    if args.pdftoppm:
        prefix=args.outdir/'v6-safe-conventions'
        subprocess.run([str(args.pdftoppm),'-singlefile','-png','-r','300',str(pdf),str(prefix)],check=True)
        files.append(prefix.with_suffix('.png'))
    proof={'analysis_sha256':args.analysis_sha256,'closure_sha256':data['closeout_sha256'],'script_sha256':sha(Path(__file__)),'selection':'common_complete within each model and mode; all three fixed arms','case_counts_not_independent_draws':True,'panels':panels,'files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
    (args.outdir/'v6-safe-conventions.audit.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'panels':len(panels),'analysis_sha256':args.analysis_sha256,'outputs':[p.name for p in files]}))

if __name__=='__main__':
    main()
