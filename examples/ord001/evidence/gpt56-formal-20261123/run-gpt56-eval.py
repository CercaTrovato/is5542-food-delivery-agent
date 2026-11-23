# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["langgraph==1.2.19", "langchain==1.4.9", "langchain-openai==1.7.4", "starlette==1.10.0", "httpx==0.28.1", "python-multipart==0.0.20"]
# ///
"""Caller-only profile adapter and incremental journal; frozen business source is unchanged."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, hashlib, json, os, sys, threading, time, traceback
import httpx

TASK=Path('E:/app-data/codex/scratchpad/is5542-agent-verification-20261123')
CODE=TASK/'code/examples/ord001'
OUT=TASK/'gpt56-formal'
ENV=Path('E:/app-data/codex/scratchpad/is5542-ord001-openai-studio/.env')
REPO=Path('E:/app-data/codex/scratchpad/is5542-dev-delivery-20261123/review-repo')
for k in ['ORD001_MODEL_CONFIG','ORD001_CHAT_MODEL','DEEPSEEK_API_KEY','LANGSMITH_API_KEY','LANGCHAIN_API_KEY']:
    os.environ.pop(k,None)
os.environ.update(ORD001_STP_AUTO='0',LANGSMITH_TRACING='false',LANGCHAIN_TRACING='false',LANGCHAIN_TRACING_V2='false')
sys.path.insert(0,str(CODE))
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import ord001_bc_runner as runner

def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    tmp=p.with_suffix(p.suffix+'.pending')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
    os.replace(tmp,p)

env_before=sha(ENV)
parsed={}
for line in ENV.read_text('utf-8-sig').splitlines():
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line:continue
    k,v=line.split('=',1);parsed[k.strip()]=v.strip().strip('"').strip("'")
KEY=parsed['OPENAI_API_KEY']
BASE=parsed.get('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')
assert httpx.URL(BASE).host=='api.openai.com' and BASE=='https://api.openai.com/v1'
assert KEY and len(KEY)>20
parsed.clear()
def clean(obj):
    if isinstance(obj,str):return obj.replace(KEY,'[REDACTED]')
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items() if k.lower() not in ['authorization','api_key']}
    if isinstance(obj,list):return [clean(x) for x in obj]
    return obj

ap=argparse.ArgumentParser();ap.add_argument('--inspect-only',action='store_true');ap.add_argument('--execute',action='store_true')
args=ap.parse_args()
assert args.inspect_only != args.execute
PROFILE={'requested_model':'gpt-5.6-sol','user_selected_model':'GPT-5.6','base_url':BASE,'api':'chat.completions','reasoning_effort':'none','temperature':0.35,'max_completion_tokens':800,'timeout_seconds':30,'max_retries':0,'store':False,'stream':False,'source_code_commit':'176fbb0264203b53e7ed8c68760a75243e5b113b','policy':'demo-v1 + human-review-v1','stp_auto_approve':False,'planned_system_trials':120,'modes':['B','C'],'repeats':3,'design_note':'Full configured-system comparison; C has regex fallback and special-issue preprocessing as well as explicit rules. Not a single-factor ablation.','budget':'user authorized no monetary limit for this batch','pricing_checked_on':'2026-11-23','pricing_source':'https://developers.openai.com/api/docs/models/gpt-5.6-sol','usd_per_million_tokens':{'input':4,'cached_input':0.4,'output':20},'fixture_note':'Existing runner uses live model setup in BC15/16; setup cost counted separately, preconditions checked before the scored dialogue.'}
active={'trial_id':'parameter_inspection','phase':'none','steps':[],'fixture_checked':False,'case':None}
wire=[];lock=threading.RLock();sequence=0

def append_jsonl(path,obj):
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(clean(obj),ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

def on_request(request):
    global sequence
    assert args.execute
    assert request.url.host=='api.openai.com' and request.url.path=='/v1/chat/completions'
    payload=json.loads(request.content)
    for k,v in [('model','gpt-5.6-sol'),('temperature',0.35),('reasoning_effort','none'),('max_completion_tokens',800),('store',False)]:assert payload.get(k)==v,(k,payload.get(k))
    with lock:
        sequence+=1
        record={'call_id':sequence,'trial_id':active['trial_id'],'phase':active['phase'],'started_at':stamp(),'request_payload':payload,'status':'started'}
        request.extensions['eval_call']=record;request.extensions['eval_start']=time.perf_counter()
        wire.append(record);append_jsonl(OUT/'api-events.jsonl',record)

def on_response(response):
    record=response.request.extensions['eval_call']
    response.read()
    try:body=response.json()
    except Exception:body={'non_json_response':response.text[:2000]}
    record.update(finished_at=stamp(),http_status=response.status_code,latency_ms=round((time.perf_counter()-response.request.extensions['eval_start'])*1000),response=clean(body),request_id=response.headers.get('x-request-id'),status='response')
    with lock:append_jsonl(OUT/'api-events.jsonl',record)

client=httpx.Client(timeout=30,follow_redirects=False,event_hooks={'request':[on_request],'response':[on_response]})
def new_model():
    return ChatOpenAI(model='gpt-5.6-sol',base_url=BASE,api_key=KEY,reasoning_effort='none',temperature=0.35,max_completion_tokens=800,timeout=30,max_retries=0,store=False,stream_usage=False,use_responses_api=False,http_client=client)

probe=new_model()
payload=probe._get_request_payload([HumanMessage(content='Reply OK')])
inspect={k:payload.get(k) for k in ['model','temperature','reasoning_effort','max_completion_tokens','store','stream']}
assert all(inspect[k]==PROFILE[k] for k in ['temperature','reasoning_effort','max_completion_tokens','store'])
assert inspect['model']=='gpt-5.6-sol'
if args.inspect_only:
    print(json.dumps({'wire_payload_without_network':inspect,'source_env_unchanged':sha(ENV)==env_before,'model_calls':0},ensure_ascii=False));sys.exit(0)

OUT.mkdir(exist_ok=False)
frozen=json.loads((REPO/'work/eval/bc-formal-plan-2026-11-23.json').read_text('utf-8'))
assert runner.DEFAULT_CASES==frozen['cases'] and len(frozen['cases'])==20
source_receipt=json.loads((TASK/'execution-receipt.json').read_text('utf-8'))
for f in source_receipt['source_files']:assert sha(TASK/'code'/f['path'])==f['sha256']
PROFILE.update(created_at=stamp(),harness_sha256=sha(Path(__file__)),case_bank_sha256=hashlib.sha256(json.dumps(frozen['cases'],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),source_files=source_receipt['source_files'],packages={'langgraph':'1.2.19','langchain':'1.4.9','langchain-openai':'1.7.4'})
save(OUT/'profile.json',PROFILE);save(OUT/'frozen-cases.json',frozen['cases'])

OriginalService=runner.DemoService
class ProfileService(OriginalService):
    def __init__(self,*a,**kw):
        kw.pop('model_config_path',None);kw.update(model=new_model(),model_label='openai:gpt-5.6-sol',stp_auto_approve=False)
        super().__init__(*a,**kw);self.model_params=PROFILE.copy()
    def send_message(self,thread_id,customer_id,message,*a,**kw):
        active['phase']='fixture_setup' if thread_id=='setup-th' else 'scored_dialogue'
        case=active['case']
        if thread_id!='setup-th' and case and case.get('setup') and not active['fixture_checked']:
            actual=[x['status'] for x in self.store.tickets(customer_id=customer_id)]
            expected='approved' if case['setup']=='approved_ORD001' else 'rejected'
            active['fixture_checked']=True
            active['steps'].append({'step':'fixture_precondition','expected':expected,'actual':actual})
            if actual != [expected]:raise RuntimeError('Fixture precondition not established; scored dialogue not started')
        result=super().send_message(thread_id,customer_id,message,*a,**kw)
        active['steps'].append({'step':'send_message','phase':active['phase'],'thread':thread_id,'customer_id':customer_id,'message':message,'result':result})
        return result
    def confirm(self,thread_id,*a,**kw):
        active['phase']='fixture_setup' if thread_id=='setup-th' else 'scored_dialogue'
        result=super().confirm(thread_id,*a,**kw);active['steps'].append({'step':'confirm','phase':active['phase'],'result':result});return result
    def decide(self,*a,**kw):
        result=super().decide(*a,**kw);active['steps'].append({'step':'decide','phase':active['phase'],'result':result});return result
runner.DemoService=ProfileService

try:
    active.update(trial_id='preflight',phase='connectivity_check')
    preflight=probe.invoke([HumanMessage(content='Reply OK')])
    returned=preflight.response_metadata.get('model_name','')
    assert returned.startswith('gpt-5.6-sol'),returned
    save(OUT/'preflight.json',{'response':preflight.model_dump(mode='json'),'expected_model':'gpt-5.6-sol','payload_parameters':inspect,'counted_in_formal_trials':False})
    print(json.dumps({'event':'preflight_ok','returned_model':returned,'started_at':stamp()},ensure_ascii=False),flush=True)
except Exception as e:
    save(OUT/'preflight-failure.json',{'type':type(e).__name__,'error':clean(str(e)),'at':stamp(),'wire_calls':clean(wire),'formal_trials_started':0})
    print(json.dumps({'event':'preflight_failed','type':type(e).__name__,'error':clean(str(e))},ensure_ascii=False),flush=True);sys.exit(2)

results=[]
for case in frozen['cases']:
    for rep in range(1,4):
        for mode in ['B','C']:
            trial_id=f"{case['id']}-{mode}-r{rep}"
            assert not (OUT/(trial_id+'.json')).exists()
            active.update(trial_id=trial_id,phase='trial_start',steps=[],fixture_checked=False,case=case)
            start=time.perf_counter();call_start=len(wire)
            item={'trial_id':trial_id,'case_id':case['id'],'agent_mode':mode,'repeat':rep,'started_at':stamp(),'status':'running'}
            append_jsonl(OUT/'trial-events.jsonl',item)
            try:
                result=runner.run_single_case(case,mode,rep,None)
                item.update(status='completed',result=result)
            except Exception as e:
                item.update(status='failed',error_type=type(e).__name__,error=clean(str(e)),traceback=clean(traceback.format_exc()))
            calls=clean(wire[call_start:])
            item.update(finished_at=stamp(),wall_elapsed_ms=round((time.perf_counter()-start)*1000),steps=clean(active['steps']),api_calls=calls)
            save(OUT/(trial_id+'.json'),clean(item));append_jsonl(OUT/'trial-events.jsonl',item)
            results.append(item)
            print(json.dumps({'event':'trial_done','done':len(results),'total':120,'trial_id':trial_id,'status':item['status'],'api_calls':len(calls),'decision_correct':item.get('result',{}).get('decision_correct_without_guard'),'final_state_matches':item.get('result',{}).get('final_execution_safe')},ensure_ascii=False),flush=True)
            save(OUT/'progress.json',{'completed_attempts':len(results),'total':120,'failed':sum(x['status']=='failed' for x in results),'model_requests':len(wire),'updated_at':stamp()})

assert len(results)==120
unchanged=sha(ENV)==env_before and all(sha(TASK/'code'/f['path'])==f['sha256'] for f in source_receipt['source_files'])
assert unchanged
save(OUT/'complete.json',{'completed_at':stamp(),'planned_system_trials':120,'attempts':120,'completed':sum(x['status']=='completed' for x in results),'failed':sum(x['status']=='failed' for x in results),'total_model_requests_including_preflight_and_fixtures':len(wire),'original_env_and_52_business_source_files_unchanged':unchanged,'profile_sha256':sha(OUT/'profile.json'),'trial_result_hashes':{x['trial_id']:sha(OUT/(x['trial_id']+'.json')) for x in results}})
print(json.dumps({'event':'complete','attempts':120,'failed':sum(x['status']=='failed' for x in results),'model_requests':len(wire)},ensure_ascii=False),flush=True)
