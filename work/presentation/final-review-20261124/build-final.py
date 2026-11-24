from pathlib import Path
import json,shutil,hashlib
import win32com.client
S=Path(__file__).parent; R=S/'repo'; OUT=S/'candidate'; OUT.mkdir(exist_ok=True)
V2=Path('D:/上课资料/CityU/IS5542_GenAI_in_Business/assignment/graded/A01-genai-project/submission/IS5542-Group24-DRAFT-v2.pptx')
DEST=OUT/'IS5542-Group24-REVIEW-v3.pptx'
assert hashlib.sha256(V2.read_bytes()).hexdigest()=='a74e365ef9807008277e10ae249f9947a47482f609329ba9bd794a309c00f6c3'
shutil.copy2(V2,DEST)
C={'navy':'132432','navy2':'203B4C','ink':'142A38','muted':'627584','line':'D7E1E7','paper':'F7F9FA','white':'FFFFFF','gold':'FFBD45','pale':'FFF0CF','light':'D9E5EC','green':'267F70','fail':'B25F51'}
def rgb(v):
 v=C.get(v,v).lstrip('#');return int(v[0:2],16)+(int(v[2:4],16)<<8)+(int(v[4:6],16)<<16)
def pt(x):return x*.75
pp=win32com.client.DispatchEx('PowerPoint.Application');p=pp.Presentations.Open(str(DEST),False,False,False)
def txt(s,v,x,y,w,h,z=26,color='ink',bold=False,align=1):
 q=s.Shapes.AddTextbox(1,pt(x),pt(y),pt(w),pt(h));q.Name=v[:45].replace('\n',' ')
 tf=q.TextFrame;tf.AutoSize=0;q.TextFrame2.AutoSize=0;tf.MarginLeft=0;tf.MarginRight=0;tf.MarginTop=0;tf.MarginBottom=0;tf.WordWrap=-1;tf.VerticalAnchor=3
 tr=tf.TextRange;tr.Text=v;tr.Font.Name='Arial';tr.Font.Size=pt(z);tr.Font.Bold=-1 if bold else 0;tr.Font.Color.RGB=rgb(color)
 tr.ParagraphFormat.Alignment=align;tr.ParagraphFormat.SpaceBefore=0;tr.ParagraphFormat.SpaceAfter=0
 q.Left=pt(x);q.Top=pt(y);q.Width=pt(w);q.Height=pt(h)
 return q
def rect(s,x,y,w,h,fill='white',line=None,round=False):
 q=s.Shapes.AddShape(5 if round else 1,pt(x),pt(y),pt(w),pt(h));q.Fill.ForeColor.RGB=rgb(fill);q.Line.Visible=-1 if line else 0
 if line:q.Line.ForeColor.RGB=rgb(line);q.Line.Weight=1
 return q
def rule(s,x,y,w,color='line'):
 q=s.Shapes.AddLine(pt(x),pt(y),pt(x+w),pt(y));q.Line.ForeColor.RGB=rgb(color);q.Line.Weight=.8;return q
def icon(s,name,x,y,size=42,gold=False):
 path=R/'work/presentation/redesign-20261123/assets/icons-png'/f'{name}-{"gold" if gold else "ink"}.png'
 return s.Shapes.AddPicture(str(path),False,True,pt(x),pt(y),pt(size),pt(size))
def arrow(s,a,b):
 q=s.Shapes.AddConnector(1,a.Left+a.Width/2,a.Top+a.Height,b.Left+b.Width/2,b.Top);q.Line.ForeColor.RGB=rgb('muted');q.Line.Weight=1.8;q.Line.EndArrowheadStyle=3;return q
def norm(t):return t.replace('\r','\n').replace('\v','\n')
def find(s,needle):
 for q in s.Shapes:
  if q.HasTextFrame and q.TextFrame.HasText and needle in norm(q.TextFrame.TextRange.Text):return q
 raise RuntimeError('Text missing: '+needle)
def replace(s,old,new,size=None):
 q=find(s,old);q.TextFrame.TextRange.Text=new
 if size:q.TextFrame.TextRange.Font.Size=pt(size)
 return q
def body(s):
 for i in range(s.Shapes.Count,0,-1):
  q=s.Shapes(i)
  if 165<=q.Top/.75<666:q.Delete()
def title(s,old,new,size=50):return replace(s,old,new,size)
def table(s,rows,x,y,widths,heights,z=24):
 q=s.Shapes.AddTable(len(rows),len(rows[0]),pt(x),pt(y),pt(sum(widths)),pt(sum(heights)));t=q.Table
 for c,w in enumerate(widths,1):t.Columns(c).Width=pt(w)
 for r,h in enumerate(heights,1):
  t.Rows(r).Height=pt(h)
  for c,v in enumerate(rows[r-1],1):
   cell=t.Cell(r,c);sh=cell.Shape;sh.Fill.ForeColor.RGB=rgb('navy' if r==1 else ('white' if r%2==0 else 'paper'))
   f=sh.TextFrame;f.MarginLeft=pt(12);f.MarginRight=pt(12);f.MarginTop=pt(5);f.MarginBottom=pt(5);f.VerticalAnchor=3
   tr=f.TextRange;tr.Text=v;tr.Font.Name='Arial';tr.Font.Size=pt(z);tr.Font.Bold=0;tr.Font.Color.RGB=rgb('white' if r==1 else 'ink');tr.ParagraphFormat.SpaceAfter=0
   for b in [1,2,3,4]:cell.Borders(b).ForeColor.RGB=rgb('line');cell.Borders(b).Weight=.5
 return q
def note(s,text):
 for q in s.NotesPage.Shapes:
  if q.Type==14 and q.PlaceholderFormat.Type==2:q.TextFrame.TextRange.Text=text;return
 raise RuntimeError('Missing notes placeholder')
repo='https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/930609bf8c669d14c1073907b997364ec3d3ff85/'
refs={
 'policy':repo+'work/spec/human-review-boundaries.md',
 'review':repo+'work/eval/gpt56-complete-review-2026-11-23.md',
 'records':repo+'examples/ord001/evidence/gpt56-formal-20261123/complete-treatment-review/records.json',
 'profile':repo+'examples/ord001/evidence/gpt56-formal-20261123/profile.json',
 'results':repo+'work/eval/gpt56-results-2026-11-23.md',
 'market':repo+'work/research/market-comparison-2026-11-23.md',
 'cost':repo+'work/presentation/cost-value-scenarios-2026-11-23.md',
 'jd':'https://help.jd.com/user/issue/321-4495.html',
 'bls':'https://www.bls.gov/ooh/office-and-administrative-support/customer-service-representatives.htm',
 'shuishou':'https://shuishoukefu.com/blog/decision-guide/cs-outsourcing-17/',
 'usolink':'https://www.usolink.com/?page_id=1058',
 'df':'https://dfkefu.com/pricing.html',
 'canvas':'https://canvas.cityu.edu.hk/courses/71410/assignments/340779'
}
speech=[
('项目定位',45,'我们的项目是外卖投诉处理助手。我们关注的不是能否回答一句问题，而是一笔复杂投诉能不能得到正确、安全、可继续的处理。顾客可能没有说清订单，也可能不理解补偿条件，或者在申请被驳回后仍需要人工帮助。这个课程原型把自然语言理解、可信订单数据、规则和人工审核接在一起。下面先介绍业务问题，再看两段真实模型演示，最后用正式比较和成本情景说明目前能支持哪些判断。所有订单和补偿券都是模拟的。'),
('业务问题与用户',50,'“我的外卖迟到了，能补偿吗？”这句话看起来简单，但处理它需要先认准订单，核实送达时间，再确认适用哪一版权益。顾客需要具体原因和下一步，客服需要拿到可靠事实以及前面的对话。如果信息在这些环节之间丢失，机器人即使回答得流畅，也可能给错建议，或者让人工从头再问。我们的目标就是让这条处理链保留上下文，并让每个决定能回到对应的订单和工单。'),
('保障版本差异',55,'Jacky 的最新版材料把六项保障分开了。美团普通准时宝和黑金权益不能共用金额；淘宝的商家赠送保障和用户购买服务也需要区分。京东现在以带标识的准时保作为公开条款参照，旧的二十分钟免单只作历史版本。这里最重要的业务原则是先识别订单权益，再解释条件。我们没有把不同截图里的金额和分钟档位拼成统一规则，本组超过三十分钟、十元模拟券的规则也不是任何平台的通用政策。'),
('完整服务流程',55,'这张图按职责分成三个区域。首先模型理解顾客的自由表达，可信工具检查订单归属和事实。然后程序判断延误条件，让顾客明确确认提交。最后人工审核，系统把实际工单状态返回给顾客。资料不足或出现争议时，需要解释原因并把前情交给人工。对于已经驳回但还没有补偿的申请，只有可核实的新信息或原处理错误，才允许人工写明原因后沿原工单重审。'),
('数据与演示规则',50,'系统用订单归属和状态控制访问，用预计与实际送达时间计算延误，用实付金额限制补偿，用工单和对话历史保持上下文。演示资格要求已经送达，而且严格超过三十分钟，恰好三十分钟不符合。标准金额是十元模拟券，需要顾客确认和人工审批。主管改额只能用一到二十的整数，并且不能超过实付；标准十元也要受这个上限约束。额外三元暖心券还没有纳入已确认范围，因此相关九次回复在结果中继续单列待核。'),
('架构与模型',65,'这里把模型、工具和程序的职责分开。LangChain 负责模型和工具连接，LangGraph 管理分支、保存状态以及等待顾客或人工。语言模型理解和表达，查单工具提供授权事实，程序规则和工单存储限制实际动作。开发录屏使用 DeepSeek Flash，正式 B/C 比较使用 GPT-5.6 Sol，两种正式模式配置相同。它们在意图处理、兜底和食安前置处理上仍有差异，所以后面比较的是两套配置后的系统，不能把所有变化只归因于一个规则节点。'),
('正常链路演示',55,'这一段是开发提供的 DeepSeek 录屏，长度约二十一秒。请跟着同一笔 ORD001 和同一张 T0001：订单实付五十八元，预计十八点送达，实际十八点五十，晚了五十分钟。顾客确认后工单进入待审，普通客服批准标准十元模拟券，顾客端最后显示已通过。请注意“待审”和“已发放”是两个状态；片段里显示的结算和到账仍是模拟系统状态。这里验证的是这条演示链，不是正式一百二十次实验的成绩。'),
('重审与人工边界演示',65,'第二段约三十秒，演示 ORD008 被驳回后的人工接续。我们按视频核对，这笔订单实付三十六元，预计十八点、实际十八点三十一，延误三十一分钟。顾客转人工后，处理上下文保留，主管 R002 记录了门禁签收新信息和重审原因，沿原 T0001 批准十五元，人工会话编号是 H0001。十五元没有超过实付，也没有创建第二次成功补偿。旁白采用这些画面事实，不采用另一份文字材料中不一致的数字。'),
('正式比较方法',65,'正式实验已经完成：二十个模拟业务案例，两种模式，每个案例各跑三轮，共一百二十次系统试跑。B 由模型根据工具事实和政策生成建议，C 使用显式规则，并带有自己的意图和兜底处理。两边使用相同的 GPT-5.6 配置、授权数据和最终执行保护，每次使用隔离状态。完整处理标准是在运行后由本人确认，再由项目会话助手按原因与下一步、意图与动作、权限与承诺三个维度复核。因此这是事后复核，不是预注册的单因素实验，也不是一百二十名真人的使用测试。'),
('正式结果与业务含义',75,'按完整处理口径，B 的六十次里有三十七次通过、二十三次未通过；C 有四十五次通过、六次未通过，还有九次等待三元政策确认。图中待核没有删除，也没有改成通过。只看工单终态，两边都是六十次全部匹配，但这会漏掉解释误拦、只查单却弹确认卡，以及没有执行的操作承诺。系统平均耗时分别约三点六零五秒和三点二五四秒，不含人工等待。单次正式对话模型费用是按用量和报价估算，不是账单实扣。我们的结论是终态检查不足以代表完整服务质量，不能写成 C 百分之百正确。'),
('受限市场比较',55,'市场比较使用林在十一月十一日采集的页面记录，不把它改写成今天的新实测。三家平台都已有订单上下文、补偿解释或人工入口的证据。美团和京东主要是旧订单，淘宝样本还提前六分钟送达，条件并不一致。因此这张表只能比较可见功能和解释方式，不能给赔付成功率或准确率排名。本系统的优势主张也限定为流程可追溯、规则和人工边界能检查，同时保留已经发现的答复缺陷。'),
('成本与有条件价值',90,'成本分三层看。正式 GPT-5.6 运行共二百五十九个模型请求，包含预置和预检，按 Token 报价估算约一点零五八一四美元。开发者报告 DeepSeek 联调和演示约消耗一到五元人民币，原型托管和存储没有新增现金支出，但复用电脑和免费服务不等于生产零成本。右侧是单独的美元情景：每月一千条相似链路，每条模型成本零点零一七六六八美元，美国时薪参考二十一点五三美元，固定增量成本假设一百美元。需要平均净省约十九点七秒人工时间才能覆盖这些成本，实际人工节省尚未测量。Jacky 补到的国内供应商按席、按店或按会话收费，服务范围不同，不能直接拼成我们的每单人工成本或真实 ROI。'),
('局限与下一步',65,'剩余问题已经比较具体。B 的失败包括十四次金额提及被误拦、六次没有清楚的继续路径和三次反意图弹卡；C 有六次没有落实的提醒或转达承诺，以及九次额外政策待核。下一步应先修这些具体问题，再只复测受影响的路径。三元扩展由本人决定，不能因为公开平台有三元权益就自动批准本组功能。真人可用性、真实支付结果和本地人工节省仍未验证。以后迁移到电商售后，也需要替换数据接口和政策，而不是把这次课程结果直接推广。'),
('指标与证据备查',45,'这页用于答疑。完整通过要求三个维度都满足；政策未定继续保留在总分母。工单状态匹配和三轮一致分别报告，一致的错误仍然是错误。九组离线边界检查支持权限、金额和防重复的确定性断言，不替代真实模型的完整处理质量。正式运行绑定一七六 fbb 零代码和两版演示政策，原始记录、复核标签和源码诊断分别保留，便于追查具体案例。'),
('来源、贡献与结束',40,'最后列出本次使用的来源和实际收到的工作。Jacky 提供业务与规则及成本资料，林提供此前的平台观察，李宗谦负责实现、部署和开发录屏，A 与 gaga 提供既有试用反馈，本人统筹正式证据和演示整合。正式英文姓名、学号和贡献表述仍请本人及组员最后确认。这份材料使用 OpenAI Codex 辅助制作。我们希望交付的是一条能够被检查的投诉处理链，并且清楚说明它在哪些地方有效、在哪些地方仍然会出错。')]

try:
 for s in p.Slides:
  for q in s.Shapes:
   if q.HasTextFrame and q.TextFrame.HasText:
    t=q.TextFrame.TextRange.Text
    if 'DRAFT' in t:q.TextFrame.TextRange.Text=t.replace('DRAFT','REVIEW v3')
 replace(p.Slides(1),'Member details pending','REVIEW v3 · Official member details to confirm',18)
 # Current guarantee, preserving the existing comparison layout.
 replace(p.Slides(3),'Specified-label promotion','On-time coupon guarantee',24)
 replace(p.Slides(3),'Order label +','Order label +\nlatest arrival estimate',24)
 replace(p.Slides(3),'Guarantee versions reported in team research','JD on-time coupon cover is distinct from the historical free-order promotion.',24)
 # Keep architecture diagram and replace obsolete configuration note.
 s=p.Slides(6)
 replace(s,'LangChain: model and tool connection','LangChain connects model/tools. LangGraph manages state and human waits.',25)
 replace(s,'LangGraph: branches','Demo: DeepSeek Flash   /   Formal comparison: GPT-5.6 Sol',26)
 replace(s,'Reported: openai:deepseek-flash','Formal settings: T=0.35 · 800 output tokens · 30 s timeout · no retries · code 176fbb0',20)
 # Native media is added with OfficeCLI after this edit/save phase.
 for num in [7,8]:
  s=p.Slides(num);body(s)
  txt(s,'DeepSeek Flash · code 176fbb0 · simulated orders and coupons',66,171,1148,33,23,'muted')
  if num==7:
   title(s,'ORD001:','ORD001: confirmation to approval',50)
   for i,(a,b) in enumerate([('01','Query ORD001'),('02','Confirm request'),('03','T0001 pending'),('04','Human approval'),('05','CNY 10 issued')]):
    txt(s,a,852,218+i*66,63,44,26,'muted',True);txt(s,b,923,213+i*66,290,54,27,'ink',True)
   txt(s,'Paid CNY 58\nDelay 50 min\n21.1 s clip, no audio',852,558,360,89,24,'muted')
  else:
   title(s,'Human review with','ORD008: reconsideration on the same ticket',45)
   ns=[]
   for i,(v,col) in enumerate([('Rejected T0001\nNo coupon issued','white'),('Verifiable new information\nHuman reason recorded','pale'),('R002 approves CNY 15\nOriginal T0001 retained','white')]):
    ns.append(rect(s,852,220+i*126,362,96,col,'line',True));txt(s,v,871,228+i*126,326,80,25)
   arrow(s,ns[0],ns[1]);arrow(s,ns[1],ns[2])
   txt(s,'Paid CNY 36 · delay 31 min\nHandoff H0001 · 30.3 s, no audio',852,608,362,46,21,'muted')
 # Configured-system comparison, not single factor.
 s=p.Slides(9);title(s,'A fair test','Two systems, one shared test set',50)
 replace(s,'Same model, authorized','Shared GPT-5.6 model, authorized facts, tools and execution protections',28)
 replace(s,'Shared scenario set','20 synthetic cases',27)
 replace(s,'Program evaluates','Rules plus intent and fallback logic',25)
 replace(s,'PLAN  10','COMPLETED  20 cases × B/C × 3 repeats = 120 system trials',26)
 # Result chart: editable native stacked segments, preserving all 60 per mode.
 s=p.Slides(10);body(s);replace(s,'04  EVIDENCE PENDING','04  INTERNAL EVALUATION',18)
 title(s,'Internal evaluation results','Complete handling needs more than state checks',46)
 txt(s,'Post-hoc assistant review · 60 trials per mode · fixed code 176fbb0',66,171,1148,41,26,'muted')
 for x,label,col in [(210,'Pass','green'),(420,'Fail','fail'),(620,'Policy pending','gold')]:rect(s,x,228,24,24,col);txt(s,label,x+36,219,230,43,24)
 for y,label,vals in [(287,'B',[37,23,0]),(389,'C',[45,6,9])]:
  txt(s,'Agent '+label,66,y+5,142,48,31,'ink',True);x=210
  for val,col in zip(vals,['green','fail','gold']):
   if val:
    w=780*val/60;rect(s,x,y,w,58,col);txt(s,str(val),x,y,w,58,32,'ink' if col=='gold' else 'white',True,2);x+=w
  txt(s,('61.7%' if label=='B' else '75.0%'),1023,y,191,49,38,'ink',True)
 txt(s,'Confirmed pass share',1010,446,205,33,19,'muted')
 txt(s,'C: 9 policy-pending trials stay in N=60. Ticket-state agreement: 60/60 for both.',66,481,1148,43,25)
 table(s,[['Measured / estimated metric','B','C'],['Mean system time (no human wait)','3.605 s','3.254 s'],['Estimated model cost per scored case','US$0.007317','US$0.008740']],66,542,[680,234,234],[37,39,39],23)
 # Limited market matrix.
 s=p.Slides(11);body(s);replace(s,'04  COMPARABLE EVIDENCE PENDING','04  QUALITATIVE MARKET COMPARISON',18)
 txt(s,'Team observations: 11 Nov 2026. Different order conditions; no accuracy or payout ranking.',66,168,1148,43,23,'muted')
 table(s,[['Service','Order context','Eligibility explanation','Human service / status'],['Meituan','Old order linked','Sample time-limit response; benefit version matters','Contact options seen; full journey unobserved'],['Taobao Instant\nCommerce','Order card and switch-order entry','Arrival times explained for a delivery 6 minutes early','Tools/status visible; human contact unobserved'],['JD Food Delivery','Order-selection card','Coupon cover kept separate from the old free-order offer','Hotline/chat/status entries seen'],['Our prototype','Clarification and ownership checks','Rules and consent traceable; known reply defects remain','Simulated state return and handoff guidance']],66,221,[190,256,365,337],[52,96,96,96,96],24)
 # Measured/modelled/reported costs kept separate.
 s=p.Slides(12);body(s);title(s,'Value hypotheses','Costs and conditional business value',48)
 txt(s,'OBSERVED OR REPORTED',66,181,535,36,21,'muted',True)
 for y,label,val,desc in [(238,'Formal GPT-5.6 evaluation','US$1.058140','Token-price estimate; 259 requests including setup'),(363,'DeepSeek development / demo','CNY 1–5','Developer estimate, not an itemised project invoice'),(488,'Prototype hosting and storage','CNY 0 new cash spend','Developer report; existing laptop and free services')]:
  txt(s,label,66,y,535,39,25,'ink',True);txt(s,val,66,y+43,535,45,34,'ink',True);txt(s,desc,66,y+89,535,47,21,'muted')
 txt(s,'ILLUSTRATIVE USD MONTHLY SCENARIO',657,181,557,36,20,'muted',True)
 table(s,[['Input','Value'],['Comparable cases / month','1,000 assumed'],['Model cost / full path','US$0.017668'],['US wage reference / hour','US$21.53'],['Fixed incremental cost / month','US$100 assumed']],657,235,[366,191],[44,53,53,53,53],23)
 txt(s,'19.7 net human seconds',657,516,557,62,38,'ink',True);txt(s,'per case to break even under these assumptions',657,578,557,43,24,'muted')
 txt(s,'Human time savings are unmeasured. Vendor quotes have different scopes. No realised ROI claim.',66,630,1148,32,23)
 # Concrete failure work; stay within the same 4-column roadmap.
 s=p.Slides(13);body(s);title(s,'Validation and next steps','Known gaps and next steps',50)
 txt(s,'Synthetic orders and coupons; real-model trials complete. Production outcomes remain unverified.',66,174,1148,63,27,'light')
 steps=[('01','Repair explanations','B: 14 false blocks\n6 unclear next steps\n3 unwanted cards','workflow'),('02','Validate promises','C: 6 unsupported\nreminder / relay\npromises','headset'),('03','Resolve policy','C: 9 goodwill cases\npending approval\nRetest affected paths','shield-check'),('LATER','Pilot and monitor','Human usability\nReal payments\nLocal time and costs','git-branch')]
 rule(s,143,347,996,'muted')
 for i,(idx,t,b,ic) in enumerate(steps):
  x=66+i*294;txt(s,idx,x,265,274,35,22,'light',True);rect(s,x+66,315,68,65,'navy');icon(s,ic,x+77,326,45,True);txt(s,t,x,402,274,50,28,'white',True);txt(s,b,x,476,274,120,25,'light').TextFrame.VerticalAnchor=1
 txt(s,'Later application: e-commerce after-sales, with new interfaces and revalidated policies.',66,622,1148,35,25,'white')
 # Definitions bind to the actual review rubric.
 s=p.Slides(14);body(s);title(s,'Measurement definitions','Definitions and evidence boundaries',49)
 table(s,[['Measure','Meaning','Evidence boundary'],['Complete pass','All three dimensions pass','Reason/next step, intent/action, authority/promises'],['Policy pending','Unresolved policy; keep in N=60','9 C replies mention the extra 3-yuan offer; no issue click tested'],['Ticket-state agreement','Match the frozen expected state','B 60/60 and C 60/60; insufficient for complete handling'],['Repeat result','All 3 repeats pass, not just match','B 12/20; C 15/20, with 3 case groups pending'],['Review and guard evidence','120 records; post-hoc assistant labels','Offline guard suite 9/9 is separate from model quality']],66,189,[240,448,460],[44,76,80,76,76,76],24)
 txt(s,'Run: gpt56-formal-20261123 · 176fbb0 · GPT-5.6 Sol · demo-v1 + human-review-v1',66,637,1148,25,20,'muted')
 # Evidence and real received contributions.
 s=p.Slides(15);body(s)
 srcs=[('book-open','Business and guarantees','Jacky v1.6 + official terms'),('shield-check','Formal run and review','120 records + complete-treatment-v1'),('receipt-text','Market observations','Team pages dated 11 Nov 2026'),('file-text','Cost references','BLS + supplier pricing; scopes kept separate')]
 for i,(ic,t,b) in enumerate(srcs):
  y=194+i*100;icon(s,ic,66,y+7,39);txt(s,t,125,y,424,41,27,'ink',True);txt(s,b,125,y+44,424,52,23,'muted')
 table(s,[['Work received','Contributor'],['Business / rules / cost research','Jacky'],['Prototype, deployment, recordings','LI Zongqian'],['Earlier market observations','Lin'],['Existing trial feedback','A + gaga'],['Evaluation evidence and presentation','Project owner']],587,201,[368,259],[45,60,60,60,60,70],23)
 txt(s,'Official names, IDs and final contribution wording to confirm',587,576,629,48,21,'muted')
 txt(s,'I used OpenAI Codex to assist with this assignment.',66,630,1148,34,24)
 # Concise English evidence notes + complete Chinese rehearsal text kept in companion file.
 notes={
 1:'Course prototype with simulated orders and coupons. Review candidate v3, not a submitted or owner-approved final. Formal member details remain to be confirmed.',
 2:'Illustrative complaint from Jacky business research. No market-size or observed loss estimate is asserted.',
 3:'Jacky latest source is v1.6, received 24 Nov 2026, 59,085 bytes, one table, no embedded images; ten HYPERLINK fields (not ordinary relationship entries). Meituan standard/member and Taobao gifted/purchased cover remain separate. JD current on-time coupon cover is distinct from historical 20-minute free-order promotion. Detailed screenshot amounts are not generalised.\n'+refs['jd'],
 4:'Selected manual-review workflow. Reconsideration requires a rejected, uncompensated ticket plus verifiable new information or prior error, human reason and original ticket. R002 alone may change integer amount 1–20 yuan within trusted payment. One successful compensation per order.\n'+refs['policy'],
 5:'demo-v1 requires delivered and late_seconds > 1800, default 10 yuan. Default amount also must not exceed payment. Missing/invalid payment blocks issue; do not silently reduce an invalid standard amount. Additional 3-yuan goodwill feature remains outside confirmed scope.\n'+refs['policy'],
 6:'Recorded demo uses DeepSeek Flash. Formal B/C: GPT-5.6 Sol, reasoning none, temperature 0.35, max output 800, timeout 30 seconds, retries 0. Fixed 176fbb0, manual approval enabled (STP false). LangChain/LangGraph, Starlette/Uvicorn, SQLite; prototype public entry via Surge and Quick Tunnel to developer laptop. No RAG, fine-tuning or automatic speech understanding is claimed.\n'+refs['profile'],
 7:'Developer recording, 21.1 seconds, H.264 1280x800, no audio. Code binding supplied by developer: 176fbb0. Actual visible order: ORD001, paid CNY58, expected18:00, delivered18:50, delay50minutes. T0001 pending then human approval and CNY10 simulated coupon. Not the GPT-5.6 formal test. Financial split labels in the UI are not presented as verified real settlement policy.',
 8:'Developer recording, 30.3 seconds, H.264 1280x800, no audio. The actual video shows ORD008 paid CNY36, expected18:00, delivered18:31, delay31minutes, T0001 rejected then reconsidered via H0001 by R002 to CNY15. The written reason mentions new gate/signature evidence and spilled soup. These visible values take precedence over inconsistent developer prose. No real payment or top-up after prior issue.\n'+refs['policy'],
 9:'20 synthetic cases x 2 modes x 3 repeats =120 system trials. Code176fbb0, same formal model config, isolated fixture store. Systems also differ in intent handling, regular-expression order fallback, food-safety preprocessing and fallback logic, so this is not a single-factor ablation. Post-hoc rubric confirmed by owner after the run, applied by project chat assistant; not preregistered, blind or human usability evaluation.\n'+refs['profile']+'\n'+refs['review'],
 10:'N=60 per mode including pending. B37 pass/23 fail; C45 pass/6 fail/9 pending. Shares61.7%/75.0% are confirmed complete passes out of60, not final accuracy after policy resolution. Original automated B39/C60 is retained in raw evidence but not used as overall correctness. Both final state60/60. B14 amount-mention false blocks,6 missing next steps,3 unwanted cards. C6 unsupported promises,9 goodwill policy pending. Mean system3.6048167/3.2537167 sec excludes human waiting. Scored dialogue costs0.439012/60 and0.524388/60 USD. No uncertainty significance claim from repeated synthetic cases.\n'+refs['review']+'\n'+refs['results'],
 11:'O=team observations11Nov2026, P=public policy, R=service-layer real-model test, D=developer recording. Old orders and an early delivery make payout-success or overall accuracy ranking invalid. Platform human contact and full payout journeys were not observed. The prototype has known response defects. Full12-cell evidence and source-page locators:\n'+refs['market'],
 12:'Cost layers: GPT formal evaluation total US$1.058140 for259 requests (234 scored,24fixtures,1preflight), token-price estimate not invoice. DeepSeek development/demo CNY1–5 is developer estimate. Hosting/storage incremental cash CNY0 is developer report using free entry/tunnel and personal laptop, not production zero cost. Scenario N1000/month, c0.017668 USD/full path from six C traces (BC15/16,4requests including fixture), W21.53 USD/hour (US BLS May2025), F100 USD/month assumed (50operations+600setup/12). Break-even=(F/N+c)*3600/W=19.6751 net human seconds. Human saving unmeasured; capacity value not demonstrated cash savings.\nNew local quote sources verified24Nov: Shuishou dedicated4500–6000CNY/person-month, gold shared1500CNY/store-month including1000chats; USOLINK after-sales shared1200CNY/month starting with <=2000chats, dedicated5500CNY/person-month starting; DFKefu1100CNY/month <=600chats, temporary25CNY/hour starting, service-hours inconsistency retained. Different scopes are not matched project labor costs. Beijing notice does not substantiate exact chart27 salary values, so these values are omitted.\n'+refs['cost']+'\n'+refs['bls']+'\n'+refs['shuishou']+'\n'+refs['usolink']+'\n'+refs['df'],
 13:'Known failures derive from existing post-hoc review, no new paid calls. If code changes, retest affected paths. Goodwill policy is an owner decision. Real human usability and payments remain unverified. No new full A/B/C or large benchmark is scheduled by this deck.\n'+refs['review'],
 14:'Rubric complete-treatment-v1: all reason/next-step, intent/action, authority/promises dimensions must pass. Preserve pending in denominator. Repeat consistency includes consistent errors. Offline deterministic guard9/9 is separate from real-model quality and human UAT. Original120SHA bindings and grade totals rechecked in production, not a new independent semantic assessment.\n'+refs['records']+'\n'+refs['profile'],
 15:'Contribution rows describe material received, not certified shares or assigned speakers. LI Zongqian English name is supplied by developer; all formal name/ID formatting and contribution text still require owner/team final check. System models are distinct from production assistance. Main public sources: JD official on-time cover; BLS occupation wages; supplier published pricing. Jacky v1.6 supplies pointers, not automatic verification. Canvas24Nov: Group Project /assignments/340779 shows28Nov11:59pm,20points,file upload,both video and slides,one group submission. No new hard video cap/rubric/peer form located in the four checked course surfaces.\n'+refs['canvas']+'\n'+refs['jd']+'\n'+refs['bls']}
 for i in range(1,16):note(p.Slides(i),notes[i])
 p.Save()
 data={'version':'REVIEW-v3','slides':len(speech),'speaker_notes':notes,'speech':[{'slide':i+1,'title':t,'estimated_seconds':sec,'script':v} for i,(t,sec,v) in enumerate(speech)],'sources':refs}
 (OUT/'content-and-notes.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 md=['# IS5542 Group 24 中文逐页讲稿 · REVIEW v3','','对应15页英文PPT；供本人审稿和彩排。时长为规划估计，未计时试讲。两段视频无音轨，须由演讲者同步讲解。正式姓名／学号与3元政策仍待本人确认，当前不标已提交。','']
 for i,(t,sec,v) in enumerate(speech,1):md += [f'## 第{i:02d}页 · {t}',f'建议约 {sec} 秒。', '',v,'']
 md += ['## 录制与提交核对','','Canvas本次已登录查看：Group Project入口为 https://canvas.cityu.edu.hk/courses/71410/assignments/340779 ，显示11月28日11:59pm，展示20分，录像和slides都上传至此，每组一次。页面未显式展示时区标签；按当前课程页面时间安排并在提交前确认。没有找到新的硬性视频时长或独立rubric；旧模板2/7/4/2分钟为结构指引。互评公告仍为稍后发布Google Form，未见实际表单。','本稿只安排已有内容与演示，不代表本人已审稿、已练习、录制完成或正式提交。']
 (OUT/'IS5542-Group24-Speaker-Script-ZH-v3.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 print(str(DEST))
finally:p.Close();pp.Quit()
