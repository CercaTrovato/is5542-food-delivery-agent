# IS5542 · 外卖延误补偿 Agent

Group 24 的课程项目。我们用模拟外卖订单验证一件事：面对缺信息、说法不一致或涉及审批的延误投诉，系统能否给出**正确、安全的处理结果**。效率和成本作为辅助结果。课程交付包括可运行的演示、录制视频和 slides。

## 从这里开始

1. 看[当前方案与进度](notes/current-plan.md)，了解完整流程、已确认的决定和下一步。
2. 在下表点自己的名字，看这轮要读什么、交什么、交给谁。
3. 要复跑，打开 [ORD001 网页与 Studio 运行指南](examples/ord001/README.md)。顾客页、审批页、P01–P03 开发验证和待接项见 [11 月 10 日本机交付](notes/team/ord001-web-delivery-2026-11-10.md)；新版页面、交互与浏览器证据见 [界面升级说明](notes/team/ord001-ui-upgrade-2026-11-10.md)；图片、语音和移动端界面见 ORD001 指南中的 [2026-11-13 媒体交付](examples/ord001/README.md#2026-11-13-媒体交付与界面证据)。
4. 要在 GitHub 查看每位成员的任务、交件与复核状态，打开 [GitHub 组内协作方式](notes/team/github-collaboration.md)。交接格式按[组内协作规范](notes/team/collaboration.md)填写。

截至 **11 月 13 日**，首版框架已选 **LangChain／LangGraph**，ORD001 顾客网页、审批网页、人工咨询和媒体附件流程已具备，使用 `feat/ord001-local-web` 分支交接，**待组员复核**。本轮 GitHub 证据包含订单详情、图片附件、商家附件和 390px 移动端界面；三平台调研任务已写明，正式补偿参数、团队模型和 B/C 评测细节待对齐。

## 首轮实名分工

角色按 11 月 9 日小组名单记录，李宾雄的具体职责已于 11 月 10 日确认。其他首轮交件和下表日期用于对齐安排，日期按香港时间。

| 成员 | 角色 | 首轮交件 | 接收人 | 建议日期 |
|---|---|---|---|---|
| [Jacky](notes/team/jacky-research.md) | 业务调研 | 三平台公开补偿规则表及待核项 | 林、开发与测试 | 11 月 11 日 |
| [林](notes/team/lin-research.md) | 业务调研 | R01–R03 实际客服流程与证据 | Jacky、开发与测试 | 11 月 11 日 |
| [李宾雄](notes/team/li-binxiong.md) | 工程／baseline | 规则判定表、资格判定与分流节点、baseline B 和评分口径 | 李宗谦、gaga老师、A | 随首轮交期对齐 |
| [李宗谦](notes/team/li-zongqian.md) | 开发（含前端与部署） | 可点的 ORD001 网页、可重跑分支与试跑记录 | 李宾雄、gaga老师、A | 11 月 10 日开发交件，待复核 |
| [gaga老师](notes/team/gaga-test.md) | 测试 | P01 的待审、批准与驳回验收记录 | 李宗谦、李宾雄、A | 11 月 13 日 |
| [A](notes/team/a-test.md) | 测试 | P02／P03 的阈值、缺单和订单归属验收记录 | 李宗谦、李宾雄、gaga老师 | 11 月 13 日 |

## 查找具体材料

| 我想找 | 从这里读 |
|---|---|
| 课程交什么、怎么评分 | [课程任务说明](notes/任务说明.md) |
| 三家平台查什么、交件怎么填 | [调研交接与模板](notes/team/research-handoff.md) |
| 李宗谦与开发 Agent 今天怎么开工 | [ORD001 前端与工程交接](notes/team/frontend-handoff.md) |
| 开发首轮怎么验、P01–P03 是什么 | [开发交接](notes/supervision-report.md#首轮开发交接) |
| 界面概念、截图和交互验证 | [静态概念图](examples/ord001/design/concept.png) / [界面升级说明](notes/team/ord001-ui-upgrade-2026-11-10.md) |
| 组内调研报告、附录截图、启动会记录 | [组内原件](work/team-private/README.md) |
| 过去为什么这样选、建库时是什么状态 | [历史决策与进度快照](progress/README.md) |

课程公告记录 **11 月 28 日交录像与 slides**。具体时刻和提交入口以 Canvas 后续通知为准。
