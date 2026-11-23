"""Editable figure source; no model or network calls. Run from any cwd with matplotlib."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
repo=Path(__file__).resolve().parents[3]
review=repo/'examples/ord001/evidence/gpt56-formal-20261123/complete-treatment-review'
model=json.loads((root/'model.json').read_text('utf-8'))
summary=json.loads((review/'summary.json').read_text('utf-8'))
scenarios=model['scenarios']
fig,ax=plt.subplots(figsize=(8.5,4.7),dpi=170)
ax.plot([x['net_human_seconds_saved_per_case_assumed'] for x in scenarios],[x['monthly_net_capacity_value_usd_modelled'] for x in scenarios],marker='o',color='#147d92',lw=2)
ax.axhline(0,color='#64748b',lw=1)
ax.axvline(model['break_even_net_seconds_with_fixed_cost'],color='#9a5f2b',linestyle='--',label=f"Break-even: {model['break_even_net_seconds_with_fixed_cost']:.1f} seconds")
ax.set_title('Illustrative capacity value: human time savings are assumed',fontsize=12)
ax.set_xlabel('Net human active seconds saved per comparable case (assumption)');ax.set_ylabel('Monthly net capacity value (USD, modelled)')
for x in scenarios:ax.annotate(f"USD {x['monthly_net_capacity_value_usd_modelled']:.0f}",(x['net_human_seconds_saved_per_case_assumed'],x['monthly_net_capacity_value_usd_modelled']),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
ax.spines[['top','right']].set_visible(False);ax.legend(loc='upper left',fontsize=9)
fig.text(.02,.02,'Scenario: 1,000 cases/month; USD 100 fixed/month. US wage reference: USD 21.53/hour (BLS, May 2025).\nModel cost: USD 0.017668/path from six simulated full-path traces. Not measured ROI or Chinese platform costs.',fontsize=7)
fig.tight_layout(rect=[0,.10,1,1]);fig.savefig(root/'scenario.png',bbox_inches='tight');fig.savefig(root/'scenario.svg',bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(figsize=(8.0,3.6),dpi=170)
for i,mode in enumerate(['B','C']):
    base=0
    for key,label,color in [('pass','Confirmed pass','#147d92'),('fail','Fail','#a75b4c'),('pending','Pending policy','#bd914b')]:
        n=summary['modes'][mode][key];ax.barh(i,n,left=base,color=color,label=label if i==0 else None)
        if n:ax.text(base+n/2,i,str(n),ha='center',va='center',color='white',fontsize=12)
        base+=n
ax.set_yticks([0,1],['B','C']);ax.invert_yaxis();ax.set_xlim(0,60)
ax.set_xlabel('System trials (60 per mode; pending stays in the denominator)')
ax.set_title('Complete-treatment review: post-hoc, owner-approved rubric',fontsize=11)
ax.spines[['top','right']].set_visible(False)
fig.legend(loc='lower center',bbox_to_anchor=(.5,.13),ncol=3,fontsize=8)
fig.text(.02,.02,'Source: 120 GPT-5.6 trials, code 176fbb0; reviewed 2026-11-23 by this chat assistant.\nNot independent blind review, human usability testing, or production accuracy.',fontsize=7)
fig.tight_layout(rect=[0,.21,1,1]);fig.savefig(review/'complete-review.png',bbox_inches='tight');fig.savefig(review/'complete-review.svg',bbox_inches='tight');plt.close(fig)
for p in [root/'scenario.svg',review/'complete-review.svg']:
    p.write_text('\n'.join(x.rstrip() for x in p.read_text('utf-8').splitlines())+'\n','utf-8')
