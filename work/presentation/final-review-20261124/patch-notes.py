from pathlib import Path
import json,subprocess
S=Path(__file__).parent; out=S/'candidate'; f=out/'content-and-notes.json';d=json.loads(f.read_text('utf-8'))
d['sources'].update(meituan='https://rules-center.meituan.com/m/detail/guize/374012?activeRule=1',taobao_gifted='https://terms.alicdn.com/legal-agreement/terms/suit_bu1_other/suit_bu1_other202108021609_91951.html',taobao_purchased='https://terms.alicdn.com/legal-agreement/terms/suit_bu1_other/suit_bu1_other201903201642_21599.html')
d['speaker_notes']['3']='Jacky v1.6 supplied separate guarantee versions and source locators. Its ten HYPERLINK fields were extracted; there are no embedded figures. Public terms were checked 24 Nov 2026. Meituan standard/member and Taobao gifted/purchased cover remain separate. JD current on-time coupon cover is distinct from its historical 20-minute free-order promotion. Detailed screenshot amounts are not generalised across all orders.\n'+'\n'.join(d['sources'][x] for x in ['jd','meituan','taobao_gifted','taobao_purchased'])
f.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
src=S/'build-final.py';t=src.read_text('utf-8');t=t.replace('no embedded images or active external hyperlink relationships','no embedded images; ten HYPERLINK fields (not ordinary relationship entries)');src.write_text(t,encoding='utf-8')
ops=[{'command':'set','path':'/slide[3]/notes','props':{'text':d['speaker_notes']['3']}}]
q=S/'patch-notes.json';q.write_text(json.dumps(ops,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run(['officecli','batch',str(out/'IS5542-Group24-REVIEW-v3.pptx'),'--input',str(q),'--stop-on-error','--json'],check=True)
subprocess.run(['officecli','close',str(out/'IS5542-Group24-REVIEW-v3.pptx')],check=True)
