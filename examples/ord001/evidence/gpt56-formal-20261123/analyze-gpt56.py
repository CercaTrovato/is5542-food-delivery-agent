from pathlib import Path
import csv, hashlib, json, statistics

S=Path('E:/app-data/codex/scratchpad/is5542-agent-verification-20261123/gpt56-formal')
A=S/'analysis';A.mkdir(exist_ok=True)
rows=[];compact=[]
files=sorted(S.glob('BC*-*-r*.json'))
def usage(calls):
    out=dict(input_tokens=0,cached_input_tokens=0,output_tokens=0,total_tokens=0,known_usage_responses=0,unknown_usage_requests=0)
    for call in calls:
        u=(call.get('response') or {}).get('usage')
        if not u:out['unknown_usage_requests']+=1;continue
        out['known_usage_responses']+=1
        out['input_tokens']+=u.get('prompt_tokens',0);out['output_tokens']+=u.get('completion_tokens',0);out['total_tokens']+=u.get('total_tokens',0)
        out['cached_input_tokens']+=(u.get('prompt_tokens_details') or {}).get('cached_tokens',0)
    out['estimated_usd']=(out['input_tokens']-out['cached_input_tokens'])*4/1e6+out['cached_input_tokens']*.4/1e6+out['output_tokens']*20/1e6
    return out
for p in files:
    d=json.loads(p.read_text('utf-8'));r=d.get('result') or {};calls=d['api_calls'];scored=[x for x in calls if x['phase']=='scored_dialogue'];setup=[x for x in calls if x['phase']=='fixture_setup']
    row={k:d[k] for k in ['trial_id','case_id','agent_mode','repeat','status']}
    row.update(decision_correct_prelabel=r.get('decision_correct_without_guard') is True,final_state_matches_prelabel=r.get('final_execution_safe') is True,unsafe_proposal_recorded=bool(r.get('unsafe_proposals')),guard_intercept_recorded=bool(r.get('safety_intercepts')),system_latency_ms=r.get('system_latency_ms'),wall_elapsed_ms=d['wall_elapsed_ms'],scored_api_requests=len(scored),fixture_api_requests=len(setup),http_or_transport_errors=sum(x.get('http_status',0)!=200 for x in calls),length_limited_responses=sum(any(c.get('finish_reason')=='length' for c in (x.get('response') or {}).get('choices',[])) for x in calls),returned_models=','.join(sorted(set((x.get('response') or {}).get('model','') for x in calls))),error_type=d.get('error_type'),**usage(scored))
    rows.append(row)
    turns=[]
    for t in r.get('turns',[]):
        turns.append({'input':t.get('utterance',t.get('answer')),'outcome':t.get('outcome'),'reason':t.get('reason_code'),'assistant':[m['text'] for m in t.get('messages',[]) if m.get('role')=='assistant'],'confirmation':bool(t.get('confirmation')),'ticket':{k:v for k,v in (t.get('ticket') or {}).items() if k in ['ticket_id','order_id','status','coupon_issued_yuan']},'intercept':t.get('safety_intercept')})
    model_outputs=[]
    for c in scored:
        body=c.get('response') or {}
        for choice in body.get('choices',[]):
            msg=choice.get('message') or {};model_outputs.append({'call_id':c['call_id'],'content':msg.get('content'),'tools':msg.get('tool_calls'),'finish_reason':choice.get('finish_reason')})
    compact.append({'id':d['trial_id'],'status':d['status'],'proposal':r.get('raw_proposal'),'decision_label':r.get('decision_correct_without_guard'),'state_label':r.get('final_execution_safe'),'outcome':r.get('final_outcome'),'unsafe':r.get('unsafe_proposals'),'intercepts':r.get('safety_intercepts'),'turns':turns,'model_outputs':model_outputs,'error':d.get('error')})

def write(name,value): (A/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
write('review-all.json',compact)
allcalls={}
for line in (S/'api-events.jsonl').read_text('utf-8').splitlines():
    d=json.loads(line);allcalls[d['call_id']]=d
summary={}
for mode in ['B','C']:
    rs=[x for x in rows if x['agent_mode']==mode];cs=[c for c in allcalls.values() if '-'+mode+'-' in c['trial_id']];sc=[c for c in cs if c['phase']=='scored_dialogue'];fix=[c for c in cs if c['phase']=='fixture_setup'];lat=[x['system_latency_ms'] for x in rs if x['system_latency_ms'] is not None]
    summary[mode]={'attempts':len(rs),'completed':sum(x['status']=='completed' for x in rs),'failed':sum(x['status']=='failed' for x in rs),'prelabel_decision_correct':sum(x['decision_correct_prelabel'] for x in rs),'prelabel_final_state_matches':sum(x['final_state_matches_prelabel'] for x in rs),'unsafe_proposal_trials':sum(x['unsafe_proposal_recorded'] for x in rs),'guard_intercept_trials':sum(x['guard_intercept_recorded'] for x in rs),'API_errors_including_fixture':sum(x['http_or_transport_errors'] for x in rs),'length_limited_responses':sum(x['length_limited_responses'] for x in rs),'scored_api_requests':len(sc),'fixture_api_requests':len(fix),'latency_sample_count':len(lat),'mean_system_ms':statistics.mean(lat) if lat else None,'median_system_ms':statistics.median(lat) if lat else None,'p95_nearest_rank_system_ms':sorted(lat)[max(0,__import__('math').ceil(.95*len(lat))-1)] if lat else None,'scored_usage':usage(sc),'fixture_usage':usage(fix)}
summary['billing']={'total_requests':len(allcalls),'scored':usage([x for x in allcalls.values() if x['phase']=='scored_dialogue']),'fixture':usage([x for x in allcalls.values() if x['phase']=='fixture_setup']),'preflight':usage([x for x in allcalls.values() if x['phase']=='connectivity_check']),'all':usage(list(allcalls.values())),'note':'Usage-based USD estimate at 2026-11-23 published rates; not invoice. Unknown-usage failures may have unobserved billing.'}
summary['case_counts']={case:{mode:{'attempts':len(z:=[x for x in rows if x['case_id']==case and x['agent_mode']==mode]),'completed':sum(x['status']=='completed' for x in z),'prelabel_decision_correct':sum(x['decision_correct_prelabel'] for x in z),'prelabel_final_state_matches':sum(x['final_state_matches_prelabel'] for x in z)} for mode in ['B','C']} for case in sorted(set(x['case_id'] for x in rows))}
write('summary.json',summary)
for k in range(0,20,4):
    ids={f'BC{i:02}' for i in range(k+1,k+5)}
    write(f'review-{k+1:02}-{k+4:02}.json',[x for x in compact if x['id'].split('-')[0] in ids])
with (A/'trials.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['trial_id']);w.writeheader();w.writerows(rows)
print(json.dumps({k:v for k,v in summary.items() if k!='case_counts'},ensure_ascii=False))
