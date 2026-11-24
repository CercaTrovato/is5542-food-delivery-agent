# IS5542 Group 24 · v4 录制演讲稿

依据最新 v4 PPT，15 页一一对应。英文主稿约 1,478 词；按每分钟 110–125 词并计入换页及视频并行口播，估算 12:32–14:04。这是计算估算，未计时彩排，不是课程硬性时长限制。

正文可直接照读；操作提示、中文对照和备查段不读入英文录像。第 7、8 页先读播放前段，再播放视频并读播放段，最后读播放后段；视频时间与同步口播重叠，不再整段额外相加。两段视频分别为 21.1 秒和 30.3 秒。没有分配成员、发言顺序或出镜任务。

第 14 页默认只读短段；其详细备查段可跳过。下表在约每分钟 115 词基础上逐页向上取整到 5 秒，含额外缓冲；实际可按语速调整。

| PPT 页 | 内容 | 英文词数 | 建议区间 |
|---|---|---|---|
| 01 | 项目定位 | 78 | 00:00–00:45 |
| 02 | 一条投诉需要哪些信息 | 103 | 00:45–01:45 |
| 03 | 先认清保障，再判断资格 | 93 | 01:45–02:40 |
| 04 | 从诉求到实际状态的完整流程 | 113 | 02:40–03:45 |
| 05 | 可信字段与明确的演示规则 | 101 | 03:45–04:40 |
| 06 | 模型、工具、状态与人工各管什么 | 104 | 04:40–05:40 |
| 07 | 正常申请、批准与回显 | 77 | 05:40–06:30 |
| 08 | 有依据地沿原工单重审 | 96 | 06:30–07:30 |
| 09 | 正式比较怎样设计 | 105 | 07:30–08:30 |
| 10 | 通过、失败和政策待核分开看 | 145 | 08:30–09:50 |
| 11 | 按观察条件比较市场流程 | 100 | 09:50–10:45 |
| 12 | 成本是多少，省多少人工才值得 | 173 | 10:45–12:20 |
| 13 | 先修具体缺陷，再做试点 | 107 | 12:20–13:20 |
| 14 | 附录：复核口径备查 | 36 | 13:20–13:45 |
| 15 | 来源、贡献与结束 | 47 | 13:45–14:15 |

顾客端：https://ord001-group24.surge.sh/

审核端：https://ord001-group24.surge.sh/review



## 第 01 页 · Food Delivery Complaint Assistant


操作提示：展示封面，面向镜头开场；用 we 代表项目团队，不逐个报成员姓名。


### 英文口播


Hello everyone. We are Group 24, and our project is a Food Delivery Complaint Assistant.

We focus on a practical question: how can an assistant handle a delivery complaint correctly, explain its decision, and help the customer continue when human review is needed? Our course prototype connects conversation, verified order facts, business rules, and human approval. It uses simulated orders and coupons.

I’ll introduce the workflow, show two recorded demonstrations, and then discuss our evaluation and business-value analysis.


### 中文对照


大家好，我们是第 24 组。我们的项目是外卖投诉处理助手。

我们想解决一个具体问题：顾客投诉外卖迟到时，助手怎样做出正确判断、解释原因，并在需要人工时帮助顾客继续处理？这个课程原型把对话、可信订单事实、业务规则和人工审批接在一起，使用的是模拟订单和补偿券。

接下来先介绍业务流程，再看两段运行演示，最后讨论评测结果和业务价值。



## 第 02 页 · The anatomy of a complaint


操作提示：按左→中→右指示顾客问题、订单事实和人工审核；不要只朗读三个框的标题。


### 英文口播


A customer asks, ‘My order is late. Can I claim compensation?’ That sounds simple, but the system first needs to identify the order and the guarantee that applies to it.

The customer needs a clear explanation and a useful next step. The system needs ownership, delivery times, payment, and previous ticket history. A human reviewer also needs the earlier conversation, especially when the customer disputes a decision.

If those facts or that context are lost, even a fluent answer can leave the complaint unresolved. Our workflow keeps the information attached to the same order as responsibility moves between the assistant and the reviewer.


### 中文对照


顾客问：“我的外卖迟到了，能补偿吗？”这句话很简单，但系统首先要确定是哪笔订单，以及这笔订单适用什么保障。

顾客需要具体解释和下一步；系统需要订单归属、送达时间、实付金额和已有工单。发生争议时，人工还需要前面的对话。

如果事实或上下文在交接时丢失，回复再流畅，投诉也可能停在那里。我们的流程让这些信息始终跟着同一笔订单，在助手和人工之间继续传递。



## 第 03 页 · Different guarantees, different conditions


操作提示：依次指出美团两种权益、淘宝两种服务、京东当前券保障；旧免单只作版本区别。


### 英文口播


Our research shows why identifying the guarantee matters. Meituan’s standard and Black Gold benefits are separate. Taobao also distinguishes merchant-gifted cover from services purchased by the customer.

JD’s on-time coupon guarantee depends on the order label and the latest estimated arrival time. We keep it separate from the historical free-order promotion.

The business principle is to check the order’s entitlement before explaining eligibility. For our prototype, we use one clearly defined demonstration policy, which I’ll explain shortly. This gives us a stable rule to implement and test, while keeping the platform-specific guarantees separate.


### 中文对照


调研说明，不能看到“外卖迟到”就直接套同一个赔付标准。美团普通准时宝和黑金权益要分开，淘宝商家赠送保障和顾客购买的服务也要分开。

京东当前的准时保券保障要看订单标识和预计最晚送达时间，不能和历史免单活动混用。

这里提炼出的业务原则是：先确认订单权益，再解释资格。为了让实现和评测有稳定依据，我们的原型采用一套明确的演示规则；各平台的保障仍分别记录。



## 第 04 页 · Complaint handling workflow


操作提示：按编号 1–6 走图；强调顾客确认与人工批准是两个不同动作。


### 英文口播


The workflow has six steps. The model understands the complaint, and a trusted tool verifies order ownership and facts. The program then evaluates the delay rule. If an application is appropriate, the customer confirms submission before a ticket enters human review. The final reply reads the stored ticket status.

When facts are missing or a decision is disputed, the handoff preserves the order and conversation. A rejected ticket with no compensation issued can be reconsidered if there is verifiable new information or an earlier processing error. The reviewer records the reason and reuses the original ticket.

This makes the customer’s request, the reviewer’s decision, and the system’s actual state traceable through one process.


### 中文对照


流程分六步：模型理解投诉，可信工具核实订单归属和事实，程序判断延误条件；符合申请条件时，顾客先确认提交，再进入人工审核，最后从存储中读取真实工单状态并回复。

顾客确认和人工批准是两个不同动作。缺资料或有争议时，订单与对话一起交接。已经驳回、但还没发过补偿的工单，如果出现可核实的新信息，或者原处理有错，可以由人工记明原因，沿原工单重审。

这样，顾客请求、人工决定和最终状态都能在同一条处理链中追溯。



## 第 05 页 · Verified data before compensation


操作提示：指向 > 30 min，明确 exactly 30 does not qualify；金额不能超实付。


### 英文口播


Each trusted field has a specific job. Ownership controls access. Expected and actual delivery times determine the delay. The paid amount sets a compensation ceiling, while ticket and dialogue history preserve context.

Our demo policy requires a delivered order and a delay strictly greater than thirty minutes. Exactly thirty minutes does not qualify. The standard amount is a ten-yuan simulated coupon, issued only after customer confirmation and human approval.

A supervisor can approve an integer amount from one to twenty yuan, within the paid-amount cap. Each order can receive compensation successfully once. These checks control what the system can actually issue.


### 中文对照


可信字段各有用途：订单归属控制访问，预计和实际送达时间计算延误，实付金额限制补偿上限，工单与对话历史保存上下文。

演示规则要求订单已经送达，而且严格超过三十分钟；恰好三十分钟不符合。标准补偿是十元模拟券，必须经过顾客确认和人工批准。

主管可以批准一到二十元的整数金额，但不能超过实付。同一订单最多成功补偿一次。这些条件约束的是实际发放动作。



## 第 06 页 · A controlled agent architecture


操作提示：顺着模型→工具→规则→工单→人工→回复讲；演示 DeepSeek 与评测 GPT 分开读。


### 英文口播


LangChain connects the language model to tools. LangGraph manages the branches, stored state, and pauses for customer or human input. The model interprets the request and explains the outcome; order tools provide authorized facts, and program rules constrain the action.

We chose this separation because conversation benefits from flexible language understanding, while timing, permission, and payment limits need consistent checks.

The recordings use DeepSeek Flash. The formal comparison uses GPT-5.6 Sol with the same configuration for both modes. C also includes intent handling, order-number fallback, and food-safety preprocessing. The evaluation therefore compares two configured systems, rather than isolating the effect of one rule node.


### 中文对照


LangChain 负责把语言模型和工具接起来，LangGraph 负责分支、保存状态，以及等待顾客和人工输入。模型理解诉求、组织解释；订单工具提供授权事实，程序规则约束实际动作。

这样分工的原因是：对话需要灵活理解自然语言，时间、权限和金额上限则需要一致的检查。

录屏使用 DeepSeek Flash；正式比较使用 GPT-5.6 Sol，两种模式的模型配置相同。C 还加入意图处理、单号兜底和食安前置逻辑，因此比较的是两套配置后的系统，不能把全部差异只归因于一个规则节点。



## 第 07 页 · ORD001: confirmation to approval


操作提示：先说播放前段，再点击视频。从首帧完整播放 21.1 秒；边播边读播放段，最后说播放后段。不要同时点击网址启动另一轮模型请求。


### 英文口播


[播放前，不读方括号]


Let’s follow the normal journey. Order O-R-D zero zero one was fifty minutes late, with fifty-eight yuan paid. The recording follows one order and one ticket.


[播放时，不读方括号]


The assistant checks the order. The customer confirms the request, creating pending ticket T zero zero zero one. A human reviewer approves ten yuan, and the customer then sees the issued simulated coupon.


[播放后，不读方括号]


The final message reflects the stored approval, so a proposed amount is not confused with an issued coupon.


### 中文对照


先看正常链路。ORD001 延误五十分钟，实付五十八元。录屏始终跟随同一笔订单和同一张工单。

助手查单，顾客确认，生成待审的 T0001；人工批准十元，顾客端随后显示已发放的模拟券。

最后回复读取的是已经保存的批准状态，把建议金额和实际发放区分开。



## 第 08 页 · ORD008: reconsideration on the same ticket


操作提示：先交代订单事实，再完整播放 30.3 秒。播放段按驳回→人工交接→主管重审顺序读；结尾保留 original ticket。


### 英文口播


[播放前，不读方括号]


The second recording shows a disputed decision. Order O-R-D zero zero eight was thirty-one minutes late, with thirty-six yuan paid. The first application was rejected, and no coupon was issued.


[播放时，不读方括号]


The customer continues through handoff H zero zero zero one. Verifiable new information is provided for review. Supervisor R zero zero two records the reconsideration reason and approves fifteen yuan. The original ticket, T zero zero zero one, is retained, and the customer sees the updated result.


[播放后，不读方括号]


The important step is a reasoned review of the existing case, with the same payment ceiling and one-compensation limit.


### 中文对照


第二段是有争议的处理。ORD008 延误三十一分钟、实付三十六元。第一次申请被驳回，当时没有发券。

顾客通过 H0001 继续人工咨询，补充可核实的新信息。主管 R002 记录重审理由，批准十五元；仍沿原来的 T0001，顾客端收到更新结果。

这里的重点是有依据地重审原案件，同时继续遵守实付上限和同单一次补偿限制。



## 第 09 页 · Two systems, one shared test set


操作提示：用 20×2×3 解释 120；三项复核维度说完整，明确复核标准在运行后采用。


### 英文口播


For the formal evaluation, we used twenty synthetic cases, two modes, and three repeats per case: one hundred and twenty system trials in total. Both modes share the model configuration, authorized facts, tools, customer confirmation, and execution protections.

B reasons over the policy using tool results. C adds explicit rules together with the intent and fallback logic described earlier.

After the runs, we reviewed complete handling using three dimensions: the explanation and next step, agreement between intent and action, and authority and promises. A trial passes only when all three pass. This lets us examine what the customer actually receives, beyond the final ticket-state label.


### 中文对照


正式比较采用二十个模拟案例、两种模式，每题各重复三轮，总共一百二十次系统试跑。两边共享模型配置、授权事实、工具、顾客确认和执行保护。

B 读取工具结果并根据政策推理；C 加入显式规则，以及前面提到的意图和兜底逻辑。

运行后，我们从三个维度复核完整处理：原因和下一步、意图和动作是否一致、权限和承诺是否成立。三个维度都通过才算完整通过，因此评测能看到顾客实际得到什么，而不只看最后的工单标签。



## 第 10 页 · Complete-handling outcomes


操作提示：先报两条色条，再指 60/60，最后简述耗时和成本；不要把 C 的 9 次待核并入通过。


### 英文口播


Each mode has sixty trials. B passed thirty-seven and failed twenty-three. C passed forty-five, failed six, and has nine trials pending a policy decision. The confirmed pass shares are sixty-one point seven percent and seventy-five percent, using all sixty trials as the denominator.

The pending C responses concern an extra three-yuan goodwill offer whose scope remains undecided. We keep those trials visible rather than counting them as passes.

Both systems matched the expected ticket state in all sixty trials. Yet the fuller review found missing explanations, unwanted confirmation cards, and unsupported promises. A correct database state alone does not establish correct complaint handling.

Average system processing time was about three point six seconds for B and three point three for C. Estimated model cost per scored case was approximately zero point seven three US cents for B and zero point eight seven cents for C.


### 中文对照


每种模式都有六十次。B 通过三十七次、未通过二十三次；C 通过四十五次、未通过六次，还有九次等待政策决定。以全部六十次为分母，已确认通过占比分别是百分之六十一点七和百分之七十五。

C 的九次待核涉及额外三元暖心券，当前范围还没有决定，因此保留待核，不并入通过。

两边工单终态都是六十次全部匹配，但完整复核仍发现解释缺失、反意图弹确认卡，以及未落实的承诺。这说明数据库状态正确，还不足以说明投诉处理完整。

平均系统处理时间，B 约三点六秒、C 约三点三秒；每个计分案例的模型成本，B 约零点七三美分、C 约零点八七美分。



## 第 11 页 · Market comparison


操作提示：横向概括三类观察，不逐格照读；先交代旧单和提前送达样本，避免把观察差异讲成产品排名。


### 英文口播


The market comparison looks at order context, eligibility explanations, and human-service or status entries. It uses team observations from November eleventh, together with public terms and our prototype records.

The Meituan and JD samples involved old completed orders. The Taobao order arrived six minutes early. Those conditions matter when interpreting the replies.

The platforms already show order information and service entries. Our prototype focuses on making the connection between verified facts, an explicit rule, customer consent, and the resulting ticket easy to trace. The table compares observed workflows; the different order conditions do not support a ranking of compensation success.


### 中文对照


市场比较围绕三件事：订单上下文、资格解释，以及人工或进度入口。材料来自十一月十一日的组员观察、公开条款和我们的运行记录。

美团和京东使用旧的已完成订单，淘宝样本则提前六分钟送达，理解回复时必须保留这些条件。

平台本身已经有订单信息和客服入口。我们的原型重点是把可信事实、明确规则、顾客确认和最终工单连接得可追溯。这里比较的是已观察到的流程，不同订单条件不足以支持赔付成功率排名。



## 第 12 页 · Runtime costs and break-even scenario


操作提示：左边是观测／自报，右边是假设情景；1.058140 可口头约 1.06 美元。19.7 秒是所需门槛，不是已测节省。


### 英文口播


On the left are observed or reported costs. The formal GPT evaluation used two hundred and fifty-nine model requests, including setup. The token-price estimate was about one US dollar and six cents. The developer estimated one to five yuan for DeepSeek development and demonstrations. Hosting used an existing laptop and free services, with no new cash spend reported for the prototype.

On the right, we ask what labor saving would cover the costs. The illustrative monthly scenario assumes one thousand comparable cases, one hundred US dollars of fixed incremental cost, and a wage reference of twenty-one dollars and fifty-three cents per hour. Model cost per full path is about one point seven seven US cents, calculated from six simulated paths.

Under these inputs, each case would need to save nineteen point seven net human seconds to break even. That is a required threshold, not a measured saving. The next measurement must include review, correction, and rework. Local supplier quotations can help replace the wage assumption once service coverage and billing units are aligned.


### 中文对照


左边是已经观测或自报的成本。正式 GPT 评测包含准备在内共二百五十九次模型请求，按 Token 单价估算约一点零六美元。开发者估计 DeepSeek 联调和演示花费一到五元人民币；当前原型复用个人电脑和免费服务，报告没有新增托管现金支出。

右边反过来问：每次要省多少人工，才覆盖这些成本？月度示例假设一千条相似处理链、固定增量成本一百美元，时薪参考二十一点五三美元；从六条模拟完整路径计算，模型成本约每条一点七七美分。

在这些输入下，每条需要净省十九点七秒人工时间才能盈亏平衡。这是需要达到的门槛，不是已经测得的节省。下一步应把审核、纠错和返工都纳入人工时间。等服务范围和计费单位对齐后，再用本地供应商报价替换假设。



## 第 13 页 · Priorities from the evaluation


操作提示：按三列报问题和动作；后续试点是未来工作，不说已经完成。


### 英文口播


Our next steps come directly from the observed failures. B had fourteen false blocks triggered by amount mentions, six unclear continuation paths, and three unwanted confirmation cards. These need clearer explanations and better agreement between the customer’s intent and the interface action.

C made six unsupported reminder or message-relay promises. Those promises need to match an actual action, or be removed. The nine goodwill cases also require a policy decision before the affected paths are retested.

A later pilot should measure human usability, real-payment behavior, and local labor time and cost. These are the inputs needed to move from a working course prototype toward an operational service.


### 中文对照


下一步直接从发现的失败出发。B 有十四次因金额提及触发的误拦、六次继续路径不清，以及三次反意图弹卡，需要改进具体解释，并让界面动作与顾客意图一致。

C 有六次提醒或转达承诺缺少实际动作，应当接上动作，或者去掉相应承诺。九次暖心券案例也要先决定政策，再复测受影响路径。

后续试点再测人工使用体验、真实支付表现和本地人工时间与成本。这些才是从课程原型继续走向实际服务需要补上的输入。



## 第 14 页 · Evaluation definitions


操作提示：附录默认简述，不重复读整张表；详细口径段只在需要解释时选读。


### 英文口播


This appendix records the definitions behind the results. Complete handling requires all three review dimensions to pass. Policy-pending trials stay in the denominator. A complete pass in all three repeats is reported separately from ticket-state agreement.


### 中文对照


附录保留了结果对应的定义：完整处理要求三个复核维度都通过；政策待核仍保留在分母中，三轮都完整通过和工单终态匹配也分别统计。


### 备查段（默认不读）


Across all three repeats, B passed twelve of the twenty case groups. C passed fifteen, with three groups still pending policy clarification. The separate nine-group guard check covers permission, amount limits, and duplicate prevention.


如果需要展开：三轮都完整通过的题型，B 为二十组中的十二组，C 为十五组，另有三组政策待核。独立列出的九组守卫检查覆盖权限、金额和防重复。



## 第 15 页 · Sources and team contributions


操作提示：不逐人宣称本人已验收；指两端网址作收尾，不为录制作业现场访问或重新运行服务。


### 英文口播


Our sources and contributions are listed here, together with the customer and review-console links.

To conclude, the prototype makes complaint decisions traceable from order facts through customer confirmation and human review. The evaluation identifies the specific behaviors and policy questions we need to improve next. Thank you.


### 中文对照


这里列出了来源和各项贡献，下方保留顾客端和审核端入口。

我们的原型把订单事实、顾客确认、人工审核和最终结果连接起来，使投诉决定可以追溯。评测也明确指出了下一步要修的具体行为和政策问题。谢谢大家。
