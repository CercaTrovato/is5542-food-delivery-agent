# GPT-5.6正式试跑：PPT补料（成品尚未修改）

## 11月23日PPT证据与完整复核已补齐

本人已确认完整处理标准：B通过37／未过23；C通过45／未过6／待核9，每边60。市场12格已用旧材料整理；成本已做有条件情景估算。[最新材料入口](ppt-evidence-closeout-2026-11-23.md)。原始120不重跑，未新增API调用；PPT成品尚未自动填入，3元范围与外部补件仍明确保留。

[完整分析](../eval/gpt56-results-2026-11-23.md) · [指标图PNG](../../examples/ord001/evidence/gpt56-formal-20261123/ppt-metrics.png) · [指标图SVG](../../examples/ord001/evidence/gpt56-formal-20261123/ppt-metrics.svg)

## 第6页：真实模型配置

可写：Formal evaluation: GPT-5.6 Sol, reasoning=none, temperature=0.35, max output=800 tokens, timeout=30s, no retries. Model ID verified in every response.

演示录屏继续标DeepSeek Flash；正式评测另标GPT-5.6。不能把两份记录写成同一配置。Key不放PPT。

## 第9页：方法

可写：20 synthetic cases × 2 configured systems × 3 repeats = 120 system trials. Same model, data and execution protections; isolated order store per trial. All attempts retained.

页下注：B and C also differ in intent handling, fallback and food-safety preprocessing. This is a configured-system comparison, not a single-factor ablation. Executed by the project owner's assistant, not human usability testing.

## 第10页：实测指标与问题

可写：Expected ticket-state agreement: B 60/60; C 60/60. Mean processing time: B 3.605s; C 3.254s. Estimated model cost/trial: B $0.007317; C $0.008740.

页下注：Ticket-state agreement is not complete response correctness. Timing excludes human waiting and fixture setup. Price-based USD estimates, not invoiced charges. The sample does not establish production or market superiority.

建议另用一个例子框：Customer: “Just check the dishes and payment; do not apply.” B says it will not apply, yet opens a confirmation card (3/3); C remains in lookup mode (3/3). No ticket is created without confirmation.

若增加失败分析页：14 B amount-guard false positives; 4 ambiguous eligibility flags; C surfaced an unapproved 3-yuan goodwill extension in 9 replies. Automated 65% vs 100% is not a valid overall correctness claim.

## 第12—13页：成本及局限

本批总用量估算约US$1.058140，含234正式模型请求、24预置、1预检；不是120次各一次模型请求。可填运行成本，ROI仍不填，尚无同条件真人处理成本或节省时间证据。

优先收尾：澄清eligible与next_action含义、修误拦与回退日志、本人决定3元扩展范围后定向复核。市场比较页继续保留真实来源限制，不写胜过平台。

本批只准备数据、图与文字；可编辑PPT文件、录屏与其他会话均未自动修改／发送。
