# IS5542 · 外卖客服 Agent

Group 24 的私有协作仓库。项目做已送达订单的延误补偿咨询。Agent 核验模拟订单、解释补偿规则、生成草稿，再由人工审批并反馈结果。

## 首轮实名分工

以下姓名或组内称呼及角色来自 11 月 9 日小组提供的现行分工。点自己的名字打开任务卡。表里的细任务、交件和日期为首轮建议，日期按香港时间。

| 成员 | 已确认角色 | 首轮具体任务 | 交件与接收人 | 建议期限 |
|---|---|---|---|---|
| [李宗谦](notes/team/li-zongqian.md) | 开发侧 | 交可重跑的 LangChain／LangGraph 首版分支和启动说明。 | 首版代码分支与启动说明 → 李宾雄、gaga老师、A | 11 月 12 日 |
| [李宾雄](notes/team/li-binxiong.md) | 工程／baseline 侧 | 对齐订单、工单和审批字段，给出可复现的基线 B。 | `work/eval/baseline-b.md` 或基线分支 → 李宗谦、gaga老师、A | 11 月 11 日 |
| [Jacky](notes/team/jacky-research.md) | 业务调研侧 | 把业务报告整理成首版补偿政策草案和需求说明。 | `work/spec/compensation-policy.md` → 李宗谦、李宾雄、gaga老师、A | 11 月 11 日 |
| [林](notes/team/lin-research.md) | 业务调研 | 整理竞品证据和用户场景，给政策与用例提供可追溯输入。 | `work/spec/competitor-evidence.md` → Jacky、gaga老师、A | 11 月 11 日 |
| [gaga老师](notes/team/gaga-test.md) | 测试侧 | 验收 P01 主链路，记录待审、批准和驳回是否正确。 | `work/eval/p01-functional.md` → 李宗谦、李宾雄、A | 11 月 13 日 |
| [A](notes/team/a-test.md) | 测试侧 | 验收 P02／P03 的阈值边界、缺单和订单归属失败。 | `work/eval/p02-p03-edge-cases.md` → 李宗谦、李宾雄、gaga老师 | 11 月 13 日 |

首版采用 **LangChain／LangGraph**。补偿政策待确认，开发先用可替换的演示参数跑通流程。首轮日期用于排协作，课程交付日期见下方。

## 当前进度 · 2026-11-09

- 已确定外卖方向，沿用原调研、开发、测试分工。组员已交商业调研和 Demo 设计，三组开发验收用例已拟定。
- 主要实现与部署拟交给有免费 Token 的技术成员。LangChain／LangGraph 的 ORD001 参考原型已跑通，可用于交接和验收对照。团队首版采用 LangChain／LangGraph，补偿规则和部署方案待对齐。
- 课程记录的交付日期为 **11 月 28 日**，交录像与 slides。具体时刻和入口待查。

## 文件入口

| 内容 | 入口 |
|---|---|
| 课程要求、方案、当前分工 | [任务说明](notes/任务说明.md) |
| 运行 ORD001 参考原型 | [Studio 启动与测试说明](examples/ord001/README.md) |
| 实现顺序、补偿规则草案、P01–P03 验收 | [开发交接](notes/supervision-report.md) |
| 会议信息与方向沿革 | [团队会议与决策](notes/团队会议与决策.md) |
| 商业调研 Word（含 9 张截图）、启动会摘要、早期方向稿 | [组内原件](work/team-private/README.md) |
| Python 依赖与本机运行说明 | [工程环境](work/app/README.md) |
| 配送延误汇总统计和脚本 | [数据说明](work/data/README.md) |
| 结构化进度、决策与历史 | [进度快照](progress/README.md) |

第一版优先跑通 ORD001 和审批状态。开发与测试使用模拟订单。组员可以从 main 拉取，开各自分支，提交 PR 时写清完成范围、运行方式和验收记录。

组内原件仅供私有协作。美团逐单数据、模型凭据、群聊截图和个人运行环境均留在各自本机。
