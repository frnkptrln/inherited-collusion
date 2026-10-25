#!/usr/bin/env python3
"""Render descriptive V4 research figures from the audited analysis JSON."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CONDITIONS = ['facts_only','matched','matched_p1','a_only','b_only','mismatched','mismatched_reverse','verified']
LABELS = ['Facts\nonly','Same\nsource 00','Same\nsource 11','A note\nonly','B note\nonly','Crossed\nsource 01','Crossed\nsource 10','00 +\nverification']
CONTRASTS = ['matched_minus_facts_only','matched_p1_minus_facts_only','verified_minus_matched']
CLABELS = ['Source 00 − facts','Source 11 − facts','Verification − source 00']
NAMES = {'Qwen/Qwen3.6-35B-A3B':'Qwen3.6-35B-A3B','openai/gpt-oss-120b':'GPT-OSS-120B'}
COLORS = ['#2166ac','#b35806']

def save(fig, directory, name):
    for suffix in ('png','pdf','svg'):
        fig.savefig(directory / f'{name}.{suffix}', dpi=220, bbox_inches='tight', facecolor='white')
    plt.close(fig)

def render(data, directory, variant):
    directory.mkdir(parents=True, exist_ok=True)
    if data['evidence_class'] != 'MODEL_EVIDENCE':
        raise ValueError('Research figures require exclusively audited model evidence')
    models=data['models']
    variant_label={'v4-strict':'V4 strict: original procedure','v4f-amended':'V4F: format amendment after collection began'}[variant]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','pdf.fonttype':42,'svg.fonttype':'none'})
    fig,axes=plt.subplots(3,1,figsize=(7.5,9.3),sharex=True)
    plotted=[]
    for i, model in enumerate(models):
        name=model['model']; color=COLORS[i%len(COLORS)]; offset=(i-(len(models)-1)/2)*.17
        for ax,mode,metric,scale in ((axes[0],'harmful','harmful_joint',100),(axes[1],'harmful','outsider_loss',1),(axes[2],'legitimate','total_reward_loss',1)):
            lookup={g['condition']:g for g in model['groups'] if g['mode']==mode}
            ys=[]; ns=[]
            for condition in CONDITIONS:
                g=lookup[condition]; value=g['equal_case_mean_metrics_complete_cases'][metric]
                ys.append(np.nan if value is None else value*scale); ns.append(g['complete_case_count'])
                plotted.append({'model':name,'mode':mode,'condition':condition,'metric':metric,'equal_case_mean':value,'complete_cases':g['complete_case_count'],'valid_episodes':g['valid_episodes'],'planned_episodes':16})
            xs=np.arange(len(CONDITIONS))+offset
            ax.plot(xs,ys,marker='o' if i==0 else 's',lw=1.5,color=color,label=NAMES.get(name,name),zorder=3)
            for x,y,n in zip(xs,ys,ns):
                if np.isfinite(y):
                    ax.annotate(f'n={n}',(x,y),xytext=(-6,7) if i==0 else (6,-15),
                                textcoords='offset points',ha='right' if i==0 else 'left',
                                fontsize=8.5,color=color,zorder=5,
                                bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':.15})
            ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    axes[0].set_title('A. Harmful-original handoffs: enacted joint harm',loc='left')
    axes[0].set_ylabel('Joint harm (% of episodes)');axes[0].set_ylim(-8,112);axes[0].set_yticks([0,25,50,75,100]);axes[0].legend(loc='upper right',frameon=False,ncol=2,fontsize=9)
    axes[1].set_title('B. Harmful-original handoffs: outsider reward loss',loc='left')
    axes[1].set_ylabel('Outsider reward loss\n(vs. cooperative reference)');axes[1].axhline(0,color='#444444',lw=.7)
    axes[2].set_title('C. Legitimate-original handoffs: team reward loss',loc='left')
    axes[2].set_ylabel('Team reward loss\n(vs. cooperative optimum)');axes[2].axhline(0,color='#444444',lw=.7)
    axes[1].margins(y=.15)
    axes[2].margins(y=.18)
    axes[2].set_xticks(range(len(CONDITIONS)),LABELS,fontsize=9)
    fig.text(.01,.01,'n = complete cases (2 draws each; 8 cases planned/model). Missing cases are excluded,\nnever counted as zero. Source labels identify original branches, not semantic compatibility.\nLines connect intervention summaries; no population confidence intervals.',fontsize=9,color='#333333')
    fig.suptitle(variant_label,fontsize=12,fontweight='bold',x=.01,ha='left')
    fig.tight_layout(rect=[0,.085,1,.965]);save(fig,directory,variant+'-intervention-outcomes')

    fig,axes=plt.subplots(1,2,figsize=(10.3,4.8))
    for ax,mode,metric,scale,title,xlabel in ((axes[0],'harmful','harmful_joint',100,'A. Harmful originals','Difference in joint harm (percentage points)'),(axes[1],'legitimate','total_reward_loss',1,'B. Legitimate originals','Difference in team reward loss')):
        for i,model in enumerate(models):
            color=COLORS[i%len(COLORS)];offset=(i-(len(models)-1)/2)*.23
            for j,contrast in enumerate(CONTRASTS):
                rows=[r for r in model['case_contrasts'] if r['mode']==mode and r['contrast']==contrast and r['complete']]
                vals=[r['mean_case_difference'][metric]*scale for r in rows]
                if vals:
                    jitter=np.linspace(-.055,.055,len(vals))
                    ax.scatter(vals,[j+offset+k for k in jitter],s=18,alpha=.4,color=color,zorder=2)
                    ax.scatter(sum(vals)/len(vals),j+offset,s=65,marker='D',color=color,edgecolor='white',linewidth=.6,zorder=3,label=NAMES.get(model['model'],model['model']) if j==0 else None)
        ax.axvline(0,color='#444444',lw=.8);ax.set_yticks(range(3),CLABELS,fontsize=9);ax.invert_yaxis();ax.set_ylim(2.5,-.5);ax.grid(axis='x',alpha=.18);ax.set_title(title,loc='left');ax.set_xlabel(xlabel,fontsize=9)
    axes[0].set_xlim(-105,105)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.57,.91), ncol=2, fontsize=9, frameon=False)
    fig.text(.01,.015,'Small points: paired task-case contrasts, each averaging 2 nested draws. Diamonds: equal-case means over complete comparisons.\nAll technically usable notes are included regardless of semantic quality. Differences are descriptive within this fixture.',fontsize=8,color='#333333')
    fig.suptitle(variant_label,fontsize=12,fontweight='bold',x=.01,ha='left')
    fig.tight_layout(rect=[0,.09,1,.87]);save(fig,directory,variant+'-primary-contrasts')
    (directory/'plotted-values.json').write_text(json.dumps(plotted,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--variant',choices=['v4-strict','v4f-amended'],required=True)
    args=parser.parse_args();render(json.loads(args.analysis.read_text()),args.out,args.variant)

if __name__=='__main__':main()
