# 三平台＋本系统：12格市场比较（证据版）

已用现有材料填齐12格，不再把全部写成待交。平台材料由林自述于2026-11-11在佛山采集，本轮承接11/12已有核验，不伪称11/23新实测。各样本订单条件不同，比较前台可见功能和解释方式，不比较赔付成功率／客户满意度。

证据类型：O＝既有组员页面观察；P＝官方公开条款；R＝本系统真实模型服务层运行；D＝开发截图／录屏。O与P不证明平台内部模型、检查先后或系统成本；R不等于真人网页验收。

| 对象／主题 | 条件与可见结果 | 类型／日期与精确证据 | 可以说明什么；不能说明什么 |
|---|---|---|---|
| 美团：选订单 | 旧已完成单；商家会话发送咨询卡，平台会话带订单，询问延误后返回该单送达时间。 | O，11/11报告；FLOW-MT-R01-01—08，[截图页1—8](../team-private/2026-11-12-customer-service-flows/meituan-screenshots-redacted.pdf#page=1)。 | 支持订单上下文可用；不证明任意模糊表述或多订单时自动选对。 |
| 美团：解释补偿 | 所见旧单保障结束，客服说完成超过48小时暂无法处理；没有有效期内延误赔付链路。 | O，FLOW-MT-R02-01，[图10＝PDF页9](../team-private/2026-11-12-customer-service-flows/meituan-screenshots-redacted.pdf#page=9)；P：[保障总则§3](https://rules-center.meituan.com/m/detail/guize/374012?activeRule=1)，11/23回源。 | 支持此单回复和保障存在；48小时不是已核的全平台时限，不能由此算拒赔率。 |
| 美团：人工／进度 | 顶部有人工／进度；点击人工出现在线服务、网络电话、热线选项。 | O，FLOW-MT-R03-01，[图9＝PDF页10](../team-private/2026-11-12-customer-service-flows/meituan-screenshots-redacted.pdf#page=10)。 | 人工入口已见；没有真人接通、排队或正式工单进度闭环。 |
| 淘宝闪购：选订单 | 本单提前6分钟送达；在线小蜜会话带订单卡，有“咨询其他订单”、预设问题和自由输入。 | O，FLOW-TB-R01-01—05，[PDF页1—5](../team-private/2026-11-12-customer-service-flows/taobao-screenshots-redacted.pdf#page=1)。 | 支持订单卡与选其他订单入口；未验证任意路由、多订单切换或后台共用记忆。 |
| 淘宝闪购：解释补偿 | 回复取餐、实际、预计最晚时间并算出提前6分钟；后续出现找餐、退款审核指引。 | O，FLOW-TB-R02-01—03，[PDF页6—8](../team-private/2026-11-12-customer-service-flows/taobao-screenshots-redacted.pdf#page=6)；P：[慢必赔§3—4](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_other/suit_bu1_other202108021609_91951.html)。 | 时间依据展示已见；退款指引不是延误赔付到账。未取得符合保障的真实超时订单。 |
| 淘宝闪购：人工／进度 | 顶部工具／进度可见，报告没有进入工具内真人入口。 | O，FLOW-TB-R03-01，[PDF页5](../team-private/2026-11-12-customer-service-flows/taobao-screenshots-redacted.pdf#page=5)。 | 入口部分可见；未进入不等于平台没有真人客服或工单。 |
| 京东秒送：选订单 | 旧已完成单，卡片01-14，年份未明；商家会话有选单卡、AI角标和门店联系按钮。 | O，FLOW-JD-R01-01—05，[PDF页1—5](../team-private/2026-11-12-customer-service-flows/jd-screenshots-redacted.pdf#page=1)。 | 支持所见会话带单；不推断商家与平台共享后台状态。 |
| 京东秒送：解释补偿 | 自助页说明某准时保10分钟以上有券；旧单会话又说超过24小时不支持售后。 | O，FLOW-JD-R02-01—02，[PDF页6—7](../team-private/2026-11-12-customer-service-flows/jd-screenshots-redacted.pdf#page=6)；P：[指定20分钟免单旧规则](https://help.jd.com/user/issue/37-4558.html)，11/23仍可访问。 | 保留10分钟券／20分钟免单两个产品版本；当前适用性待核，不把网页可访问当作本日所有订单在售。24小时仅属样本话术。 |
| 京东秒送：人工／进度 | 客服首页有热线、在线客服、服务进度；没有真人接通或已有工单页面闭环。 | O，FLOW-JD-R03-01，[图6＝PDF页8](../team-private/2026-11-12-customer-service-flows/jd-screenshots-redacted.pdf#page=8)。 | 支持入口存在；不把在线机器人入口直接当真人接通。 |
| 本系统：选订单 | 缺单号先追问，补ORD001后查单；U001查他人ORD101不返回事实，U002可查自身ORD101。 | R，11/23 GPT-5.6：[BC12](../../examples/ord001/evidence/gpt56-formal-20261123/BC12-C-r1.json)、[BC13](../../examples/ord001/evidence/gpt56-formal-20261123/BC13-C-r1.json)、[BC10](../../examples/ord001/evidence/gpt56-formal-20261123/BC10-C-r1.json)、[BC14](../../examples/ord001/evidence/gpt56-formal-20261123/BC14-C-r1.json)。 | 证实这些服务层输入的身份／查单；没有据此宣称网页选单操作由本人验收。 |
| 本系统：解释补偿 | 50分钟与30分01秒进入标准券确认；恰好30分钟不符主规则；顾客确认后才建待审工单。 | R：[BC01](../../examples/ord001/evidence/gpt56-formal-20261123/BC01-C-r1.json)、[BC02](../../examples/ord001/evidence/gpt56-formal-20261123/BC02-C-r1.json)、[BC05](../../examples/ord001/evidence/gpt56-formal-20261123/BC05-C-r1.json)；[完整复核](../eval/gpt56-complete-review-2026-11-23.md)。 | 时间／确认／工单可追溯；当前还有3元扩展待决和答复缺陷，不能写成100%正确或比平台赔得更多。 |
| 本系统：人工／进度 | 驳回后回复保留T0001、原因与人工入口；已批准的工单回显10元、不新建。开发另交前后端录屏。 | R：[BC16](../../examples/ord001/evidence/gpt56-formal-20261123/BC16-C-r1.json)、[BC15](../../examples/ord001/evidence/gpt56-formal-20261123/BC15-C-r1.json)；D：[开发两段录屏](../../examples/ord001/evidence/final-20261123/)。 | 证实模拟状态回显，入口／录屏是另一种证据；不声称真人接通或真实到账。 |

## 放第11页的简版

| 对象 | 订单关联 | 补偿解释 | 人工／进度 |
|---|---|---|---|
| 美团 | 所见旧单有订单上下文 | 所见旧单受时效回复限制；保障版本须核 | 人工选择浮层已见，闭环未观察 |
| 淘宝闪购 | 订单卡及切换入口已见 | 提前送达样本展示完整时间链；未测延误赔付 | 工具／进度可见，真人未进入 |
| 京东秒送 | 选单卡已见 | 所见券保障与旧免单规则需分版本 | 热线／在线／进度已见，闭环未观察 |
| 本系统 | 已验证追问、补单号及归属检查 | 显式规则／顾客确认可追溯，完整复核仍有缺陷 | 模拟工单状态和人工入口说明已验证 |

可讲的定位是本原型聚焦可解释、可追溯的补偿申请流程；三平台也已具备订单上下文、时间解释和人工入口的证据。当前不能据不同订单条件认定本组在准确率、赔付率或效率上领先。

公开架构还可对照[WOWService报告](https://arxiv.org/html/2510.13291v2)：平台已有LLM、多Agent及规则信号。本组是范围较小的LangChain／LangGraph课堂实现，未复刻其训练、线上协同或规模。这比把大厂一律描绘成关键词菜单更准确。

[原九行观察核验](../spec/competitor-evidence.md) · [参考工作流设计](market-reference-workflow.md) · [外部基准核验](benchmark-source-review-2026-11-23.md)。所有图片使用既有脱敏版本；本轮没有新拿到真实赔付订单。
