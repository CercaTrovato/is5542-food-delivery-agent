# 现有15页PPT：可直接填入的英文文案与中文讲述线

承接已导出的可编辑v2，保留页数、叙事和设计。源PPTX SHA-256：`a74e365ef9807008277e10ae249f9947a47482f609329ba9bd794a309c00f6c3`；本批只核对XML内页码与文字，未改PPT文件、未冒称完成视觉排版。这里是填入成品的具体内容，不是新实验计划。

## 第2—3页：业务问题与保障差异

业务故事和5项保障分版本的结构可保留。不要补没有来源的影响人数、市场规模或赔付率。对保障金额和精确分钟边界，等Jacky定位原图／版本再写；已找到的官方总则链接不再标“完全缺来源”。

中文讲述：顾客只说“迟到了”还不够，我们需要知道是哪笔订单、适用哪种保障、用哪个时间比较。我们的演示规则是自定的，不把它包装成平台规则。

## 第6页：模型和架构

替换页底过时的“模型配置和守卫待验证”说明：

> Demo recording: DeepSeek Flash. Formal comparison: GPT-5.6 Sol, reasoning=none, temperature=0.35, 800 output tokens, 30-second timeout, no retries. Both modes use the same configuration.

讲者备注引用[实际运行profile](../../examples/ord001/evidence/gpt56-formal-20261123/profile.json)。保留模型、工具、规则、工单、人工的图，不新增未实现的RAG、微调、语音理解等能力。

中文讲述：录屏和正式对照用了不同模型，因此分别标识。B/C正式对照使用同一模型，语言模型查单和生成说明，程序保护最终申请与审批动作。

## 第9页：评测方法

页底原10题／60次计划改为：

> COMPLETED: 20 synthetic cases × 2 modes × 3 repeats = 120 system trials.

原“公平测试”标题建议改为：

> Two configured systems, one shared test set

正文保留同模型、授权事实、工具和执行保护；补一条说明：

> The systems also differ in intent handling and fallback logic. Results do not isolate one rule node.

备注：固定代码176fbb0、demo-v1＋human-review-v1、stp_auto_approve=false。样本是模拟业务案例，真实调用模型；不是120名真人，不是平台线上流量。三个复核维度为原因和下一步、意图动作、权限承诺，口径于运行后由本人确认。

## 第10页：内部结果

把EVIDENCE PENDING改为INTERNAL EVALUATION；删除“等待matched runs”的旧说明。保留现有六行表，用下面的简短数值：

| Metric | Agent B | Agent C | Evidence note |
|---|---|---|---|
| Complete handling | 37 pass / 23 fail | 45 pass / 6 fail / 9 pending | 60 trials each; post-hoc review |
| Unsupported action promises | 0 observed | 6 observed | Reminder / message relay |
| Unwanted confirmation cards | 3 | 0 | Explicit lookup-only request |
| Cases passing all 3 repeats | 12/20 | 15/20; 3 pending | Consistency alone is not correctness |
| Mean system time | 3.605 s | 3.254 s | Excludes human waiting |
| Model cost per scored case | USD 0.007317 | USD 0.008740 | Usage-based estimate |

页下注保留：

> Nine C trials await policy clarification. Both modes matched the expected ticket state in all 60 trials. State agreement is not complete handling accuracy.

下方复测表可填离线守卫：`176fbb0 / 9 groups passed offline / scripted boundary suite`；不能把9/9放进真实模型正确率。图若替代表格，可用[完整复核图](../../examples/ord001/evidence/gpt56-formal-20261123/complete-treatment-review/complete-review.png)，但仍保留耗时成本及限制。

中文讲述：只看工单状态，两边都是60/60；看顾客实际得到什么，才会发现解释被误拦、只查单却弹卡，以及没有执行的承诺。我们没有用自动脚本的65%对100%作为最终结论。

## 第11页：市场比较

使用[已填12格表的简版](../research/market-comparison-2026-11-23.md)，英文可压缩为：

| Service | Order context | Eligibility explanation | Human service / status |
|---|---|---|---|
| Meituan | Context shown for an old order | Time-limit response; benefit version matters | Contact options observed; full journey unobserved |
| Taobao Instant Commerce | Order card and switch-order entry | Arrival times explained for an early delivery | Tool/status entry visible; human contact unobserved |
| JD Food Delivery | Order selection card observed | Coupon guarantee and older promotion kept separate | Hotline/chat/status entries observed |
| Our prototype | Clarification and ownership checks verified | Rule and confirmation traces; known defects remain | Simulated ticket state and handoff guidance verified |

页下注：

> Platform observations: team records dated 11 Nov 2026. Different order conditions permit qualitative comparison, not a payout-success or accuracy ranking.

中文讲述：市场产品并非没有查单、时间解释或人工入口。我们展示的是可审计的补偿申请原型，以及它在限定场景下的行为；没有足够证据宣布优于平台。WOWService可在备注补公开架构参照，不把菜单A当现代美团系统。

## 第12页：成本与价值

标题建议为：

> What would need to be saved for the system to pay off?

“12-MONTH VALUE INPUTS”可改为“ILLUSTRATIVE MONTHLY SCENARIO”。原表四行可填：

| Input | Value / source |
|---|---|
| Comparable cases | 1,000 per month — assumption |
| Model cost | USD 0.017668 per full path — six simulated traces |
| Wage reference | USD 21.53/hour — US BLS, May 2025 |
| Fixed incremental cost | USD 100/month — assumption |

原ROI展示位改为：

> Break-even condition: about 19.7 net human seconds saved per case.

页下注：

> Human time savings are not measured. The wage reference is US data, not Chinese platform costs. Freed capacity is not demonstrated cash savings.

备注说明F=50/月运维＋600实施费按12月摊销50，均为演示假设；净人工节省包含审批、纠错与返工。模型3.254秒不能当人工节省秒数。可用[情景图](../research/cost-scenarios-20261123/scenario.png)替代大段公式，计算记录见[成本方法](cost-value-scenarios-2026-11-23.md)。

中文讲述：我们算得出模型费用，但不知道真实人工能省多少。这里反过来算，在明确假设下，平均每条链至少净省多少人工时间才值得；这比编一个真实ROI更可辩护。

## 第13页：已知局限和下一步

原“守卫待验／录屏待交／对照待跑”改为当前状态：

> Current scope: simulated orders and coupons; real-model trials completed. Human usability and real payment outcomes remain unverified.

三项近期动作：

- Correct explanations, intent-to-action consistency and unsupported promises.
- Resolve the extra goodwill policy and retest affected paths.
- Complete benefit-version evidence and replace scenario inputs when local data is available.

外部基准接入放Later，不把全套新A/B/C写成今天已承诺任务。原电商售后扩展仍是未来可能应用。

## 第14页：定义与版本

Correct handling改为三个维度全满足；pending单列并保留总分母。把Unsafe proposals拆明“明确越权赔付建议”与“误承诺”，不再直接统计unsafe标志。Executed errors区分错误弹卡和工单／模拟发券。Repeat consistency应说明一致的失败也会一致。

Run ID可填：`gpt56-formal-20261123 / 176fbb0 / GPT-5.6 Sol / demo-v1 + human-review-v1`。原始日志、逐次事后复核、源码诊断分别引用；reviewer写当前项目会话Agent，不冒称测试组独立签字。

## 第15页：来源与真实贡献

Jacky：业务与规则材料；林：此前平台观察；李宗谦：实现、部署、开发录屏和基准线索；A＋gaga：既有试用反馈；李宾雄／当前会话：正式120与本轮复核、证据整理、PPT综合。正式英文姓名／学号由本人确认，不能由Agent臆造。

讲者备注链接[本轮统一入口](ppt-evidence-closeout-2026-11-23.md)、[外部资料核验](../research/benchmark-source-review-2026-11-23.md)和[Jacky待补清单](../../notes/team/jacky-ppt-evidence-2026-11-23.md)。保留真实AI辅助制作声明；系统运行模型与制作工具分开写。

第7—8页继续使用开发已交的两段真实模型录屏，标DeepSeek与受测版本；当前文案没有把它们重命名为GPT-5.6演示。最终录制时长、准确提交入口与成员信息仍需最后核实。
