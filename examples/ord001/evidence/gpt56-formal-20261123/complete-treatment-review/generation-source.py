from pathlib import Path
from datetime import datetime,timezone,timedelta
import collections,csv,hashlib,json,statistics,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
V=Path('D:/上课资料/CityU');R=Path('E:/app-data/codex/scratchpad/is5542-dev-delivery-20261123/review-repo');T=Path('E:/app-data/codex/scratchpad/is5542-ppt-evidence-20261123')
S=R/'examples/ord001/evidence/gpt56-formal-20261123';OUT=S/'complete-treatment-review'
sys.path.insert(0,str(V/'_meta/tools'))
from safe_write import atomic_write

def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);atomic_write(p,json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists(),'Single-use analysis build'
OUT.mkdir()
records=[];lifecycle=[]
for p in sorted(S.glob('BC*-*-r*.json')):
    d=json.loads(p.read_text('utf-8'));rr=d['result'];mode=rr['agent_mode'];case=rr['case_id'];issues=[];warnings=[]
    dimensions={'reason_and_next_step':'pass','intent_and_action':'pass','authority_and_promises':'pass'}
    if mode=='B' and rr['unsafe_proposals']==['reply_risk:amount']:
        dimensions['reason_and_next_step']='fail';issues.append('R01:正确规则解释被金额误拦替换，最终缺少具体原因／已核事实。')
    if mode=='B' and case in ['BC09','BC16']:
        dimensions['reason_and_next_step']='fail';issues.append('R02:资料缺失或原工单被拒后未给出可执行的人工／补资料入口。')
    if mode=='B' and case=='BC20':
        assert rr['turns'][-1]['confirmation']
        dimensions['intent_and_action']='fail';issues.append('I01:顾客明确不申请，仍产生确认卡，回复与页面动作不一致。')
    if mode=='C' and case in ['BC05','BC06','BC19']:
        dimensions['authority_and_promises']='pending_policy';issues.append('P01:3元暖心券扩展待本人决定；不擅自算通过或判为错误发放。')
    if mode=='C' and case=='BC08':
        dimensions['authority_and_promises']='fail';issues.append('A01:答复称自动开启静默守护；固定源码的提醒按钮仅显示toast，无提醒订阅／发送执行证据。')
    if mode=='C' and case=='BC20':
        dimensions['authority_and_promises']='fail';issues.append('A02:答复承诺转达服务团队；对应查询路径只拼接文本，没有转达动作或留存记录。')
    if mode=='B' and rr['unsafe_proposals']==['duplicate_confirm_on_existing_ticket']:
        assert rr['raw_proposal']['next_action']=='report_existing_ticket'
        warnings.append('eligible字段歧义，实际回复／动作均保留原工单；不按重复发券企图扣分。')
    if mode=='B' and case=='BC17':warnings.append('人工建议可识别，停止食用／取证指引仍可改善；本轮不把新增医学式话术检查当硬判。')
    if mode=='C' and case=='BC17':warnings.append('按绿色通道入口已提供理解，不当作已经接通真人；customer.js有专用入口与handoff接口，真人接通仍未验。')
    if mode=='C' and case=='BC09':warnings.append('电子围栏描述来自演示数据／政策提示，不代表接入真实轨迹服务。')
    grade='fail' if 'fail' in dimensions.values() else ('pending' if 'pending_policy' in dimensions.values() else 'pass')
    final_texts=[m['text'] for t in rr['turns'] for m in t['messages'] if m['role']=='assistant']
    records.append({'trial_id':d['trial_id'],'case_id':case,'mode':mode,'repeat':rr['repeat'],'rubric':'complete-treatment-v1','grade':grade,'dimensions':dimensions,'issues':issues,'warnings':warnings,'final_messages_reviewed':final_texts,'original_auto_decision':rr['decision_correct_without_guard'],'expected_ticket_state_matches':rr['final_execution_safe'],'raw_trial_sha256':sha(p)})
    if case in ['BC15','BC16']:
        us=[c['response']['usage'] for c in d['api_calls']]
        lifecycle.append({'trial_id':d['trial_id'],'mode':mode,'path':'approved_then_requery' if case=='BC15' else 'rejected_then_requery','calls':len(us),'input_tokens':sum(u['prompt_tokens'] for u in us),'output_tokens':sum(u['completion_tokens'] for u in us),'estimated_usd':sum(u['prompt_tokens']*4e-6+u['completion_tokens']*20e-6 for u in us),'includes_fixture_calls':True})
assert len(records)==120
summary={'reviewed_on':'2026-11-23','rubric':'complete-treatment-v1','owner_confirmed':True,'confirmation':'本人同意按原因和下一步、意图动作、权限承诺三个维度完整复核；未定规则单列待核。','assessment_timing':'post-hoc after seeing original results; not preregistered or blind','reviewer':'current chat assistant; not test-team human signoff','new_model_calls':0,'unit':'system trial; 20 synthetic cases repeated 3 times per mode','modes':{}}
for mode in ['B','C']:
    rs=[x for x in records if x['mode']==mode];counts=collections.Counter(x['grade'] for x in rs)
    summary['modes'][mode]={'n':60,**{k:counts[k] for k in ['pass','fail','pending']},'confirmed_pass_share_all_trials':counts['pass']/60,'complete_accuracy_not_final_until_pending_resolved':counts['pending']>0}
assert summary['modes']['B']['pass']==37 and summary['modes']['B']['fail']==23
assert summary['modes']['C']['pass']==45 and summary['modes']['C']['fail']==6 and summary['modes']['C']['pending']==9
summary['failure_patterns']={k:[x['trial_id'] for x in records if any(i.startswith(k+':') for i in x['issues'])] for k in ['R01','R02','I01','A01','A02','P01']}
dump(OUT/'records.json',records);dump(OUT/'summary.json',summary)
with (OUT/'records.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['trial_id','grade','reason_next_step','intent_action','authority_promises','issues','raw_trial_sha256'])
    for x in records:w.writerow([x['trial_id'],x['grade'],*x['dimensions'].values(),' / '.join(x['issues']),x['raw_trial_sha256']])

costroot=R/'work/research/cost-scenarios-20261123';costroot.mkdir(parents=True,exist_ok=False)
cp=statistics.mean(x['estimated_usd'] for x in lifecycle if x['mode']=='C')
assert abs(cp-.017668)<1e-12
W=21.53;N=1000;F=100
scenarios=[]
for seconds in [-15,0,15,30,60]:
    capacity=N*seconds/3600*W;cost=N*cp+F;net=capacity-cost
    scenarios.append({'net_human_seconds_saved_per_case_assumed':seconds,'cases_per_month_assumed':N,'hourly_pay_usd_external_reference':W,'model_cost_per_path_usd_measured_estimate':cp,'monthly_fixed_cost_usd_assumed':F,'monthly_capacity_value_usd_modelled':capacity,'monthly_incremental_cost_usd_modelled':cost,'monthly_net_capacity_value_usd_modelled':net,'capacity_value_ROI_scenario_not_cash_realized':net/cost})
cost={'status':'scenario estimate, not actual platform ROI or headcount savings','currency':'USD throughout; no currency conversion','measured_lifecycle_traces':lifecycle,'C_observed_path_mean_usd':cp,'C_observed_path_range_usd':[min(x['estimated_usd'] for x in lifecycle if x['mode']=='C'),max(x['estimated_usd'] for x in lifecycle if x['mode']=='C')],'scope':'Six C traces from two pre-existing synthetic paths (approve/reject plus follow-up), four requests per trace including fixture setup; not a production workload distribution.','external_reference':{'id':'COST-BLS-2025','url':'https://www.bls.gov/ooh/office-and-administrative-support/customer-service-representatives.htm','population':'US customer service representatives','period':'May 2025','median_hourly_usd':21.53,'checked_on':'2026-11-23','limitation':'US occupation wage reference, not Chinese food-delivery platform labor cost; excludes employer overhead.'},'assumptions':{'monthly_cases':N,'monthly_fixed_cost_usd':F,'fixed_cost_example_breakdown':'US$50 hosting/operations + US$600 one-time implementation amortized across 12 months; both illustrative assumptions.','net_seconds_saved':'Assumed after human approval, correction and rework; may be negative. Never equate model latency with human time saved.','same_compensation_policy':'No extra 3-yuan goodwill policy in value scenario; incremental payouts must be deducted if introduced.','financial_realization':'Freed capacity valued at pay is not a demonstrated wage bill reduction.'},'scenarios':scenarios,'break_even_net_seconds_with_fixed_cost':(F/N+cp)*3600/W,'break_even_net_seconds_API_only':cp*3600/W,'new_model_calls':0}
dump(costroot/'model.json',cost)
with (costroot/'scenarios.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(scenarios[0]));w.writeheader();w.writerows(scenarios)

fig,ax=plt.subplots(figsize=(8.5,4.7),dpi=170)
ax.plot([x['net_human_seconds_saved_per_case_assumed'] for x in scenarios],[x['monthly_net_capacity_value_usd_modelled'] for x in scenarios],marker='o',color='#147d92',lw=2)
ax.axhline(0,color='#64748b',lw=1);ax.axvline(cost['break_even_net_seconds_with_fixed_cost'],color='#9a5f2b',linestyle='--',label=f"Break-even: {cost['break_even_net_seconds_with_fixed_cost']:.1f} seconds")
ax.set_title('Illustrative capacity value: human time savings are assumed',fontsize=12)
ax.set_xlabel('Net human active seconds saved per comparable case (assumption)');ax.set_ylabel('Monthly net capacity value (USD, modelled)')
for x in scenarios:ax.annotate(f"${x['monthly_net_capacity_value_usd_modelled']:.0f}",(x['net_human_seconds_saved_per_case_assumed'],x['monthly_net_capacity_value_usd_modelled']),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9)
ax.spines[['top','right']].set_visible(False);ax.legend(loc='upper left',fontsize=9)
fig.text(.02,.02,'Scenario: 1,000 cases/month; $100 fixed/month. US wage reference $21.53/h (BLS, May 2025).\nModel cost $0.017668/path from six simulated full-path traces. Not measured ROI or Chinese platform costs.',fontsize=7)
fig.tight_layout(rect=[0,.10,1,1]);fig.savefig(costroot/'scenario.png',bbox_inches='tight');fig.savefig(costroot/'scenario.svg',bbox_inches='tight');plt.close(fig)
p=costroot/'scenario.svg';atomic_write(p,'\n'.join(x.rstrip() for x in p.read_text('utf-8').splitlines())+'\n')
fig,ax=plt.subplots(figsize=(8.0,4.0),dpi=170)
for i,mode in enumerate(['B','C']):
    base=0
    for key,label,color in [('pass','Confirmed pass','#147d92'),('fail','Fail','#a75b4c'),('pending','Pending policy','#bd914b')]:
        n=summary['modes'][mode][key];ax.barh(i,n,left=base,color=color,label=label if i==0 else None)
        if n:ax.text(base+n/2,i,str(n),ha='center',va='center',color='white',fontsize=12)
        base+=n
ax.set_yticks([0,1],['B','C']);ax.invert_yaxis();ax.set_xlim(0,60);ax.set_xlabel('System trials (60 per mode; pending stays in the denominator)')
ax.set_title('Complete-treatment review: post-hoc, owner-approved rubric',fontsize=11);ax.spines[['top','right']].set_visible(False);ax.legend(loc='lower center',bbox_to_anchor=(.5,-.40),ncol=3,fontsize=8)
fig.text(.02,.02,'Source: 120 GPT-5.6 trials, code 176fbb0; reviewed 2026-11-23 by this chat assistant.\nNot independent blind review, human usability testing, or production accuracy.',fontsize=7)
fig.tight_layout(rect=[0,.14,1,1]);fig.savefig(OUT/'complete-review.png',bbox_inches='tight');fig.savefig(OUT/'complete-review.svg',bbox_inches='tight');plt.close(fig)
p=OUT/'complete-review.svg';atomic_write(p,'\n'.join(x.rstrip() for x in p.read_text('utf-8').splitlines())+'\n')
print(json.dumps({'review_counts':summary['modes'],'C_full_path_cost_usd':cp,'break_even_net_human_seconds':cost['break_even_net_seconds_with_fixed_cost'],'new_model_calls':0},ensure_ascii=False))
