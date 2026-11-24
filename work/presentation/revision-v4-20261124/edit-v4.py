from pathlib import Path
import json,shutil,hashlib,subprocess
import win32com.client
S=Path(__file__).parent;A=Path('D:/上课资料/CityU/IS5542_GenAI_in_Business/assignment/graded/A01-genai-project');O=S/'candidate';O.mkdir(exist_ok=True)
src=A/'submission/IS5542-Group24-REVIEW-v3.pptx';dest=O/'IS5542-Group24-v4.pptx'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='81e2470f080185568cc6b1c037673643841011bb5cc04c92ee550359e837ea29'
shutil.copy2(src,dest);d=json.loads((A/'work/presentation/final-review-20261124/content-and-notes.json').read_text('utf-8'))
customer='https://ord001-group24.surge.sh/';reviewer=customer+'review'
notes={
1:'Food Delivery Complaint Assistant, Group 24. Course prototype using simulated orders and coupons. The presentation covers the business workflow, two recorded demonstrations, evaluation results and a break-even scenario.',
2:'An illustrative late-delivery complaint connects three roles: the customer provides the request, tools supply authorized order facts, and the reviewer makes an accountable decision. Research source: Jacky business materials.',
3:'Guarantees are identified by platform, entitlement and version. Meituan standard and Black Gold benefits are separate; Taobao merchant-gifted and purchased cover are separate. JD on-time coupon cover uses the order label and latest estimated arrival time. Jacky v1.6 and official terms were checked on 24 Nov 2026.',
4:'Workflow: understand the request, verify ownership and order facts, evaluate the rule, obtain customer confirmation, review and display the stored result. Reconsideration applies to rejected, uncompensated tickets with verifiable new information or a prior error, a recorded reason and the original ticket. R002 can change the integer amount within 1–20 yuan and the paid-amount cap. Each order has one successful compensation.',
5:'demo-v1 requires a delivered order and late_seconds > 1800. The standard coupon is 10 yuan. Customer confirmation and human approval precede issue. All amounts use trusted payment as a cap; payment and amount validation occur before issue. The extra 3-yuan offer remains a policy decision and its nine evaluation responses are labelled pending.',
6:'The recordings use DeepSeek Flash. Formal B/C evaluation uses GPT-5.6 Sol, reasoning none, temperature 0.35, output limit 800, timeout 30 seconds and zero retries. Code 176fbb0, STP disabled. LangChain connects model/tools; LangGraph manages branches, state and waits. The prototype uses Starlette/Uvicorn, SQLite, a Surge entry and Quick Tunnel to the developer laptop.',
7:'Customer demo: '+customer+'\nDeepSeek Flash recording, 21.1 seconds, code 176fbb0. ORD001: paid CNY58, expected18:00, delivered18:50, delay50minutes. The customer confirms T0001, the reviewer approves, and the customer sees a CNY10 simulated coupon. Narrate the silent clip while following the order and ticket.',
8:'Review console: '+reviewer+'\nDeepSeek Flash recording, 30.3 seconds, code 176fbb0. ORD008: paid CNY36, expected18:00, delivered18:31, delay31minutes. T0001 is rejected, the conversation continues through H0001, and R002 records new gate/signature information and a reason before approving CNY15 on the same ticket. Narrate the silent clip.',
9:'20 synthetic cases x B/C x 3 repeats =120 system trials. The systems share model configuration, authorized facts, tools and execution protections. C additionally uses intent handling, order-number fallback and food-safety preprocessing. This is a configured-system comparison. The complete-treatment rubric was selected after the runs and evaluates reason/next step, intent/action and authority/promises.',
10:'60 trials per mode. B:37 pass,23 fail. C:45 pass,6 fail,9 policy pending. Confirmed pass shares are61.7% and75.0% of all60. Ticket-state match is60/60 for each mode. Mean server/model processing times are3.605s and3.254s. Scored-dialogue cost estimates are US$0.439012/60 and US$0.524388/60. The failure categories are shown on slide13.',
11:'Qualitative comparison based on team observations dated11Nov2026, public terms, prototype service-layer runs and the two recordings. Platform samples include old completed orders and a Taobao delivery6minutes early. The matrix lists observed order context, eligibility explanations and handoff/status entries.',
12:'Runtime costs: GPT-5.6 formal evaluation,259 requests including234 scored,24fixture and1preflight, estimated US$1.058140 from token prices. Developer estimate for DeepSeek development/demo: CNY1–5. Current prototype hosting/storage: CNY0 incremental cash, using an existing laptop and free services.\nUSD monthly scenario: N=1000 comparable cases, c=US$0.017668 per full path from six C traces, W=US$21.53/hour (BLS May2025), F=US$100/month assumed (50operations +600setup/12). Required net human saving=(F/N+c)*3600/W=19.6751seconds per case. The next measurement is net active labor time, including review, correction and rework.\nSupplier billing examples: Shuishou4500–6000CNY/person-month, or1500/store-month including1000chats; USOLINK after-sales1200/month starting for up to2000chats or dedicated5500/person-month starting; DFKefu1100/month for up to600chats and temporary25/hour starting. Compare configuration, coverage and volume before selecting a local cost input.',
13:'Priorities follow the observed cases: B14 amount-mention false blocks,6 unclear continuation paths,3 unwanted confirmation cards; C6 unsupported reminder/relay promises and9 goodwill-policy cases pending. Resolve the policy, correct affected behavior and retest those paths. A later pilot measures usability, payments and local labor time/cost.',
14:'Complete pass means all three rubric dimensions pass. Pending means a policy decision is required, with the trial retained in the60-trial denominator. Ticket-state match and all-three-repeat pass are separate measures. B passes all3 repeats in12/20 cases; C in15/20, with3 case groups pending. The deterministic guard suite covers9 permission, amount and duplicate-prevention groups. Run:gpt56-formal-20261123, code176fbb0, GPT-5.6 Sol, demo-v1 +human-review-v1.',
15:'Sources: Jacky business/guarantee/cost research; team platform observations; formal run records and post-run labels; official platform terms; BLS wage data and supplier pricing. Contributions listed on this slide correspond to those work areas.\nCustomer demo: '+customer+'\nReview console: '+reviewer
}
scripts=[
'我们的项目是外卖投诉处理助手，目标是让复杂投诉得到正确、安全、可继续的处理。顾客可能没有说清订单，也可能不理解补偿条件，或者在驳回后仍需要人工帮助。这个课程原型把语言理解、可信订单数据、规则和人工审核接在一起。下面依次介绍业务问题、两段演示、正式比较和成本情景。演示使用模拟订单与补偿券。',
'“我的外卖迟到了，能补偿吗？”处理这句话需要认准订单，核实送达时间，再确认适用的权益。顾客需要具体原因和下一步，客服需要可靠事实以及前面的对话。我们的处理链保留这些信息，让每个决定都能回到对应的订单和工单。',
'Jacky 的材料将六项保障按版本列出。美团普通准时宝和黑金权益分别处理，淘宝的商家赠送保障和用户购买服务也分别处理。京东准时保以订单标识和预计最晚送达时间为依据，旧的二十分钟免单保留为历史版本。先识别订单权益，再解释适用条件，是这部分的业务原则。',
'流程按职责分成三个区域。模型理解诉求，可信工具检查订单归属和事实；程序判断延误条件，顾客确认提交；人工审核后，系统返回存储的工单状态。资料不足或存在争议时，系统说明原因并交接上下文。已驳回且尚未补偿的申请，可以凭可核实的新信息或原处理错误，由人工写明原因并沿原工单重审。',
'订单归属和状态用于访问控制，预计与实际送达时间用于计算延误，实付金额用于限制补偿，工单和对话历史用于保持上下文。演示资格要求已经送达且严格超过三十分钟。标准金额为十元模拟券，经顾客确认和人工审批后发放。主管可改为一到二十的整数，所有金额均受实付上限约束。额外三元暖心券的九次回复继续列为政策待核。',
'LangChain 连接模型和工具，LangGraph 管理分支、状态以及顾客和人工等待。语言模型负责理解与表达，工具提供授权事实，程序规则和工单存储控制实际动作。录屏使用 DeepSeek Flash，正式 B/C 比较使用相同配置的 GPT-5.6 Sol。C 还带有意图处理、单号兜底和食安前置逻辑，因此评测对象是两套配置后的系统。',
'这一页给出顾客端网址，可以从这里进入示例。录屏约二十一秒，跟随同一笔 ORD001 和同一张 T0001：实付五十八元，预计十八点送达，实际十八点五十，延误五十分钟。顾客确认后进入待审，普通客服批准十元模拟券，顾客端随后显示结果。',
'这一页给出审核端网址。第二段录屏约三十秒，ORD008 实付三十六元，预计十八点、实际十八点三十一。申请先被驳回，随后通过 H0001 转人工。主管 R002 记录新信息和重审原因，沿原 T0001 批准十五元，顾客端收到更新后的状态。',
'正式比较包含二十个模拟案例、B/C 两种模式、每个案例三轮，共一百二十次系统试跑。两边共享模型配置、授权数据、工具和执行保护。B 根据工具事实和政策生成建议，C 使用显式规则以及意图和兜底处理。运行后采用完整处理标准，按原因与下一步、意图与动作、权限与承诺三个维度复核。',
'B 的六十次中，三十七次通过、二十三次未通过；C 的六十次中，四十五次通过、六次未通过、九次政策待核。已确认通过占比分别是百分之六十一点七和百分之七十五。两种模式的工单终态都匹配六十次，完整处理复核进一步识别了解释、确认卡和操作承诺方面的问题。平均系统处理时间分别是三点六零五秒和三点二五四秒，费用按同一正式对话口径估算。',
'这张表根据十一月十一日的页面记录，比较订单关联、补偿解释和人工或进度入口。美团与京东使用旧订单样本，淘宝样本提前六分钟送达。三家平台都展示了相关入口与订单信息；我们的原型展示了归属检查、规则、顾客确认和工单状态之间的衔接。',
'成本分为现有运行费用和月度情景。正式 GPT-5.6 运行二百五十九个模型请求，按用量报价估算约一点零五八一四美元；开发者估算 DeepSeek 联调和演示花费一到五元人民币。当前原型复用个人电脑和免费托管服务。月度美元情景假设一千条相似链路，每条模型成本零点零一七六六八美元，时薪参考二十一点五三美元，固定增量成本一百美元。盈亏平衡需要每条链净省约十九点七秒人工时间。下一步测量应覆盖审批、纠错和返工后的净人工时间。供应商报价则按席、按店或按会话分别比较。',
'改进重点来自具体案例。B 有十四次解释误拦、六次继续路径不清和三次反意图弹卡；C 有六次提醒或转达承诺需要落实，以及九次政策待核。先解决政策和这些具体行为，再复测受影响的路径。后续试点继续测量可用性、支付流程和本地人工时间与成本。',
'完整通过要求三个维度都通过；政策待核保留在六十次的分母中。工单终态匹配与三轮全部通过分别统计：B 有十二种题型三轮全过，C 有十五种，另有三种题型政策待核。九组守卫检查覆盖权限、金额和防重复。所有指标都能回到同一版本的运行记录。',
'最后列出来源和分工。Jacky 提供业务、规则和成本资料，林提供平台观察，李宗谦负责实现、部署和录屏，A 与 gaga 提供试用反馈，本人整合评测证据和演示材料。页面下方是顾客端和审核端网址，可分别查看投诉处理与人工审核流程。'
]
for k in notes:
 urls=[x for x in d['speaker_notes'][str(k)].splitlines() if x.startswith('https://')]
 d['speaker_notes'][str(k)]=notes[k]+('\n\nSources:\n'+'\n'.join(urls) if urls else '')
for entry,script in zip(d['speech'],scripts):entry['script']=script
d['version']='v4';d['sources'].update(customer_demo=customer,review_console=reviewer)
pp=win32com.client.DispatchEx('PowerPoint.Application');p=pp.Presentations.Open(str(dest),False,False,False)
links=[]
def norm(t):return t.replace('\r','\n').replace('\v','\n')
def get(s,text):
 for q in s.Shapes:
  if q.HasTextFrame and q.TextFrame.HasText and text in norm(q.TextFrame.TextRange.Text):return q
 raise RuntimeError('Missing '+text)
def rep(n,old,new):get(p.Slides(n),old).TextFrame.TextRange.Text=new
def link(n,q,url):links.append({'command':'set','path':f'/slide[{n}]/shape[@id={q.Id}]','props':{'link':url,'tooltip':url}})
def add(s,text,x,y,w,h):
 q=s.Shapes.AddTextbox(1,x*.75,y*.75,w*.75,h*.75);f=q.TextFrame;f.AutoSize=0;q.TextFrame2.AutoSize=0;f.MarginLeft=f.MarginRight=f.MarginTop=f.MarginBottom=0;f.VerticalAnchor=3
 f.TextRange.Text=text;f.TextRange.Font.Name='Arial';f.TextRange.Font.Size=18;f.TextRange.Font.Color.RGB=0x382A14;q.Left=x*.75;q.Top=y*.75;q.Width=w*.75;q.Height=h*.75;return q
try:
 for s in p.Slides:
  for q in list(s.Shapes):
   if q.HasTextFrame and q.TextFrame.HasText:
    t=q.TextFrame.TextRange.Text
    if 'IS5542  /  GROUP 24  /  REVIEW v3' in t:q.TextFrame.TextRange.Text='IS5542  /  GROUP 24'
 get(p.Slides(1),'Official member details').Delete()
 rep(7,'DeepSeek Flash · code','Customer demo: '+customer);link(7,get(p.Slides(7),'Customer demo:'),customer)
 rep(7,'Paid CNY 58','Paid CNY 58\nDelay 50 min\nDeepSeek Flash · 21.1 s')
 rep(8,'DeepSeek Flash · code','Review console: '+reviewer);link(8,get(p.Slides(8),'Review console:'),reviewer)
 rep(8,'Paid CNY 36','Paid CNY 36 · delay 31 min\nHandoff H0001 · 30.3 s')
 rep(10,'Complete handling needs','Complete-handling outcomes')
 rep(10,'Post-hoc assistant review','Post-run review · 60 trials per mode · fixed code 176fbb0')
 rep(10,'C: 9 policy-pending','Expected ticket-state match: B 60/60 · C 60/60')
 rep(11,'Team observations:','Team observations: 11 Nov 2026 · samples include old orders and an early delivery.')
 rep(12,'Costs and conditional','Runtime costs and break-even scenario')
 rep(12,'Developer estimate, not','Developer estimate for development and demonstrations')
 rep(12,'Human time savings are unmeasured.','Next measurement: net human time per case, including review and rework.')
 rep(13,'05  LIMITATIONS AND NEXT STEPS','05  NEXT STEPS')
 rep(13,'Known gaps and next steps','Priorities from the evaluation')
 rep(13,'Synthetic orders and coupons;','120 real-model trials on synthetic orders and coupon workflows.')
 rep(14,'Definitions and evidence boundaries','Evaluation definitions')
 # Table cells: report observed content and definitions directly.
 replacements={
 10:{'Mean system time (no human wait)':'Mean system processing time'},
 11:{'Human service / status':'Handoff / status entry','Contact options seen; full journey unobserved':'Online and phone contact options','Tools/status visible; human contact unobserved':'Tools and service-status entry','Rules and consent traceable; known reply defects remain':'Traceable rules and customer consent'},
 14:{'Evidence boundary':'Evidence','Unresolved policy; keep in N=60':'Awaiting policy decision','9 C replies mention the extra 3-yuan offer; no issue click tested':'9 C responses mention the extra 3-yuan offer','B 60/60 and C 60/60; insufficient for complete handling':'B 60/60 and C 60/60 matched expected ticket states','All 3 repeats pass, not just match':'Complete pass in all 3 repeats','120 records; post-hoc assistant labels':'120 records; post-run rubric','Offline guard suite 9/9 is separate from model quality':'9/9 permission, amount and duplicate-prevention groups'}
 }
 for n,changes in replacements.items():
  for q in p.Slides(n).Shapes:
   if not q.HasTable:continue
   for r in range(1,q.Table.Rows.Count+1):
    for c in range(1,q.Table.Columns.Count+1):
     tr=q.Table.Cell(r,c).Shape.TextFrame.TextRange;t=norm(tr.Text)
     if t in changes:tr.Text=changes[t]
 s=p.Slides(15);get(s,'I used OpenAI Codex').Delete();get(s,'Official names, IDs').Delete()
 rep(15,'BLS + supplier pricing; scopes kept separate','BLS wage data and supplier pricing')
 q=add(s,'Customer demo: '+customer,66,583,1148,37);link(15,q,customer)
 q=add(s,'Review console: '+reviewer,66,626,1148,37);link(15,q,reviewer)
 for i in range(1,16):
  for q in p.Slides(i).NotesPage.Shapes:
   if q.Type==14 and q.PlaceholderFormat.Type==2:q.TextFrame.TextRange.Text=d['speaker_notes'][str(i)]
 # Remove maker-attribution metadata if any; retain ordinary project properties.
 for key in ['Author','Comments']:
  prop=p.BuiltInDocumentProperties(key)
  if any(t in str(prop.Value).lower() for t in ['openai','codex','chatgpt','generated with']):prop.Value=''
 p.Save()
finally:p.Close();pp.Quit()
(S/'links.json').write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run(['officecli','open',str(dest)],check=True)
subprocess.run(['officecli','batch',str(dest),'--input',str(S/'links.json'),'--stop-on-error','--json'],check=True)
subprocess.run(['officecli','close',str(dest)],check=True)
(O/'content-and-notes-v4.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# IS5542 Group 24 中文逐页讲稿 · v4','','顾客端：'+customer,'审核端：'+reviewer,'']
for entry in d['speech']:md += [f"## 第{entry['slide']:02d}页 · {entry['title']}",'',entry['script'],'']
(O/'IS5542-Group24-Speaker-Script-ZH-v4.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(dest)
