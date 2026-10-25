#!/usr/bin/env python3
"""Illustrate the first fixed task case; this is not a successor result."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    run=a.project/'runs/v4-main-gptoss-201'
    cp=json.loads((run/'checkpoints/s201.json').read_text())
    bad=json.loads((run/'donors/s201-harmful-p0.json').read_text())['outcome'];good=bad['reference']
    roles=['A','B','C','D'];tasks=['T1','T2','T3','T4']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(9.2,3.9),gridspec_kw={'width_ratios':[1,1.2]})
    tab=axes[0].table(cellText=[[int(cp['costs'][r][t]) for t in tasks] for r in roles],rowLabels=roles,colLabels=tasks,cellLoc='center',loc='center',bbox=[.08,.23,.9,.7])
    tab.auto_set_font_size(False);tab.set_fontsize(11)
    for (row,col),cell in tab.get_celld().items():
        cell.set_edgecolor('#cccccc')
        if row==0 or col==-1:cell.set_facecolor('#eeeeee')
    axes[0].axis('off');axes[0].set_title('Public execution costs',loc='left',fontweight='bold')
    axes[0].text(.02,.06,'Tasks T2/T4 are the outsiders’ specialties.\nBoth A/B permutations of T1/T3 are optimal.',transform=axes[0].transAxes,fontsize=9)
    xs=np.arange(4);w=.35
    axes[1].bar(xs-w/2,[good['agent_rewards'][r] for r in roles],width=w,color='#2166ac',label='Cooperative reference')
    axes[1].bar(xs+w/2,[bad['agent_rewards'][r] for r in roles],width=w,color='#b35806',label='Instructed harmful original')
    axes[1].set_xticks(xs,roles);axes[1].set_ylabel('Individual reward');axes[1].set_ylim(0,115);axes[1].legend(fontsize=8,frameon=False,loc='upper right');axes[1].grid(axis='y',alpha=.15);axes[1].set_axisbelow(True)
    axes[1].set_title('Coalition gain transfers costs to outsiders',loc='left',fontweight='bold',fontsize=11)
    fig.text(.01,.015,f'Fixed case 201: A+B gain {bad["coalition_gain"]:.0f}; C+D lose {bad["outsider_loss"]:.0f}; team reward falls by {bad["total_reward_loss"]:.0f}. Both allocations complete all four tasks.\nThis illustrates the original allocation mechanics. No successor behavior or spontaneous collusion is asserted.',fontsize=9)
    fig.tight_layout(rect=[0,.13,1,1])
    for suffix in ('png','pdf','svg'):fig.savefig(a.out/f'v4-fixture-example.{suffix}',dpi=220,bbox_inches='tight',facecolor='white')
    plt.close(fig)

if __name__=='__main__':main()
