# IS5542 · 外卖延误补偿 Agent

## 2026-11-20 · 最新进度复核

三平台首轮观察已收核，15 张表、26 张截图的有限比较成立；真实超时赔付、真人接通与工单闭环仍待补。远端 feat/ord001-local-web 已有开发代码及 11 月 10–11 日历史自检／共享入口记录，最新已见提交 9c8fdbc（11 月 18 日）；本次只核分支与报告，未重跑当前服务、真实模型或接收验收，不将历史自检升级为当前团队 P01 通过。

接收方从已见开发分支核版本、启动说明及 P01/P02/P03；研究成员补可得的日期、点击路径、转接／工单证据。正式政策与 B/C 口径仍待确认，11 月 28 日准确交付条件待核。

[全思路解析与历史](THINKING.md) · [项目时间线](TIMELINE.md) · [结构化当前进度](progress/assignment.json)。后面的既有内容保留为来源和历史；以本节及复核后的时间线判断当前行动。材料版本、提交事实、个人准备与最终报告分别记账。


## 进度与每日事项入口

- [项目时间线：已完成、当前与未来](TIMELINE.md)
- [个人助手读取说明](ASSISTANT-README.md) · [结构化时间线](progress/timeline.json) · [总监督每日事项候选](progress/daily-plan.json)

时间线按可核事实维护，建议日期需确认，等待回件与已验收分开。线上只读看板：https://cityu-board-online.vercel.app/


Group 24 的课程项目。我们用模拟外卖订单验证一件事：面对缺信息、说法不一致或涉及审批的延误投诉，系统能否给出**正确、安全的处理结果**。效率和成本作为辅助结果。课程交付包括可运行的演示、录制视频和 slides。

## 从这里开始

1. 看[当前方案与进度](notes/current-plan.md)，了解完整流程、已确认的决定和下一步。
2. 在下表点自己的名字，看这轮要读什么、交什么、交给谁。
3. 要复跑，打开 [ORD001 Studio 运行指南](examples/ord001/README.md)。要交接给队友或其 Agent，按[组内协作规范](notes/team/collaboration.md)填写交接记录。

截至 **11 月 12 日**，首版仍用 **LangChain／LangGraph**。Jacky 的规则 v1.3 已收；林的三平台 R01–R03 报告及 **26 张截图已核读**：[规则研究](work/spec/market-compensation-rules.md) · [客服流程核验](work/spec/competitor-evidence.md)。已补上首轮市面产品流程观察，真实超时赔付、真人接通和工单进度仍待核。正式政策和 B/C 范围继续对齐；远端开发分支有新提交，网页及 P01 结果留待另批验收，不能仅据分支存在标完成。

## 首轮实名分工

角色按 11 月 9 日小组名单记录，李宾雄的具体职责已于 11 月 10 日确认。其他首轮交件和下表日期用于对齐安排，日期按香港时间。

| 成员 | 角色 | 首轮交件 | 接收人 | 建议日期 |
|---|---|---|---|---|
| [Jacky](notes/team/jacky-research.md) | 业务调研 | 三平台公开补偿规则表及待核项 | 林、开发与测试 | 11 月 11 日 |
| [林](notes/team/lin-research.md) | 业务调研 | R01–R03 实际客服流程与证据 | Jacky、开发与测试 | 11 月 11 日 |
| [李宾雄](notes/team/li-binxiong.md) | 工程／baseline | 规则判定表、资格判定与分流节点、baseline B 和评分口径 | 李宗谦、gaga老师、A | 随首轮交期对齐 |
| [李宗谦](notes/team/li-zongqian.md) | 开发（含前端与部署） | 可点的 ORD001 网页、可重跑分支与试跑记录 | 李宾雄、gaga老师、A | 建议 11 月 12 日，待确认 |
| [gaga老师](notes/team/gaga-test.md) | 测试 | P01 的待审、批准与驳回验收记录 | 李宗谦、李宾雄、A | 11 月 13 日 |
| [A](notes/team/a-test.md) | 测试 | P02／P03 的阈值、缺单和订单归属验收记录 | 李宗谦、李宾雄、gaga老师 | 11 月 13 日 |

## 查找具体材料

| 我想找 | 从这里读 |
|---|---|
| 课程交什么、怎么评分 | [课程任务说明](notes/任务说明.md) |
| 已收补偿规则、核验边界和截图 | [规则核验入口](work/spec/market-compensation-rules.md) |
| 已收三平台客服流程、证据及待核 | [R01–R03 核验入口](work/spec/competitor-evidence.md) |
| 三家平台查什么、交件怎么填 | [调研交接与模板](notes/team/research-handoff.md) |
| 李宗谦与开发 Agent 今天怎么开工 | [ORD001 前端与工程交接](notes/team/frontend-handoff.md) |
| 开发首轮怎么验、P01–P03 是什么 | [开发交接](notes/supervision-report.md#首轮开发交接) |
| 组内调研报告、附录截图、启动会记录 | [组内原件](work/team-private/README.md) |
| 过去为什么这样选、建库时是什么状态 | [历史决策与进度快照](progress/README.md) |

课程公告记录 **11 月 28 日交录像与 slides**。具体时刻和提交入口以 Canvas 后续通知为准。
