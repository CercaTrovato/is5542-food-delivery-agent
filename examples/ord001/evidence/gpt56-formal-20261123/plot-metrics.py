"""Editable chart source. Requires matplotlib; reads only archived summary.json."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
summary=json.loads((root/'analysis/summary.json').read_text('utf-8'))
fig,axes=plt.subplots(1,3,figsize=(13.2,4.0),dpi=180)
modes=['B','C'];colors=['#64748b','#147d92']
values=[[60,60],[summary[m]['mean_system_ms']/1000 for m in modes],[summary[m]['scored_usage']['estimated_usd']/60*100 for m in modes]]
titles=['Observed ticket-state agreement','Mean system processing time','Estimated model cost per trial']
ylabels=['Trials matching expected state (of 60)','Seconds per trial (excludes human wait)','US cents per trial (scored dialogue only)']
for ax,vals,title,yl in zip(axes,values,titles,ylabels):
    ax.bar(modes,vals,color=colors,width=.52);ax.set_title(title,fontsize=10,pad=12)
    ax.set_xlabel('Configured system mode');ax.set_ylabel(yl,fontsize=8)
    ax.spines[['top','right']].set_visible(False);ax.set_ylim(0,max(vals)*1.2)
    for i,x in enumerate(vals):ax.text(i,x+max(vals)*.035,f'{x:.3f}' if title!=titles[0] else '60/60',ha='center',fontsize=10)
fig.suptitle('Internal live-model evaluation: 20 synthetic cases × 3 repeats per mode',fontsize=12)
fig.text(.03,.02,'Source: 2026-11-23 GPT-5.6 Sol run, code 176fbb0. Ticket state ≠ complete service correctness. Cost: published USD rates; not invoice.',fontsize=7)
fig.tight_layout(rect=[0,.07,1,.92]);fig.savefig(root/'ppt-metrics.png',bbox_inches='tight');fig.savefig(root/'ppt-metrics.svg',bbox_inches='tight');plt.close(fig)
svg=root/'ppt-metrics.svg'
svg.write_text('\n'.join(x.rstrip() for x in svg.read_text('utf-8').splitlines())+'\n','utf-8')
