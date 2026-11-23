# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["langgraph==1.2.19", "langchain==1.4.9", "langchain-openai==1.7.4", "starlette==1.10.0", "httpx==0.28.1", "python-multipart==0.0.20"]
# ///
from pathlib import Path
import json,sys
s=Path('E:/app-data/codex/scratchpad/is5542-agent-verification-20261123')
sys.path.insert(0,str(s/'code/examples/ord001'))
from ord001_web_graphs import reply_risk
b=json.loads((s/'gpt56-formal/BC05-B-r1.json').read_text('utf-8'))['result']
c=json.loads((s/'gpt56-formal/BC05-C-r1.json').read_text('utf-8'))['result']
ctext=next(m['text'] for m in c['turns'][0]['messages'] if m['role']=='assistant')
price=float(next(o for o in json.loads((s/'code/examples/ord001/demo-data.json').read_text('utf-8'))['orders'] if o['order_id']=='ORD003')['amount_yuan'])
out={'scope':'Two pure guard-function calls only; no model/API calls or application state writes. Business source unchanged.','B_30minute_explanation':{'raw_eligible':b['raw_proposal']['eligible'],'next_action':b['raw_proposal']['next_action'],'guard_on_legitimate_rule_explanation':reply_risk(b['raw_proposal']['reply'],allowed_amounts=set(),statuses=set(),order_prices={price}),'recorded_unsafe':b['unsafe_proposals']},'C_30minute_final_text':{'guard_on_returned_warm_coupon_text':reply_risk(ctext,allowed_amounts=set(),statuses=set(),order_prices={price}),'recorded_unsafe':c['unsafe_proposals'],'final_text':ctext},'source_observation':'B logs guard failures and replaces text with generic reply. C synthesis rejects unsafe text then returns base_text without rechecking or recording fallback; base_text may itself contain a 3-yuan goodwill extension.'}
assert out['B_30minute_explanation']['guard_on_legitimate_rule_explanation']=='amount'
assert out['C_30minute_final_text']['guard_on_returned_warm_coupon_text']=='amount'
(s/'gpt56-formal/analysis/scoring-diagnostic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(out,ensure_ascii=False))
