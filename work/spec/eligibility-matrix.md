# 资格判定与分流 · 首轮工程核对

日期为 2026 年 11 月 10 日。当前使用演示规则 demo-v1，订单已送达且延误超过 30 分钟时拟 ¥10 券，由人工决定。团队正式阈值、券额和例外条件等调研回件后确认。

## 节点的输入和输出

节点接收查单工具返回的订单事实和一份规则配置。演示订单使用同日的预计送达时间和实际送达时间。订单归属在查单工具层核实。节点用实际时间减预计时间得到延误秒数，再判断该订单能否进入审批。

输出保留状态、判定理由、政策版本，以及可计算时的延误秒数。符合条件时记录建议券额。进入人工审批后，审批结果继续使用原工单保存的规则版本和建议金额。

| 当前输入 | 演示状态 | 处理方向 |
|---|---|---|
| 已送达，延误 1800 秒 | ineligible / delay_below_threshold | 解释未达门槛并结束 |
| 已送达，延误 1801 秒 | pending / eligible_for_review | 符合申请资格。首版在顾客确认提交后建待审工单 |
| 实际送达时间缺失 | needs_info / invalid_delivery_times | 提示资料不足，结束本次运行，等待补充 |
| 查不到订单或查单失败 | not_found 或 query_failed | 说明无法核实订单，当前运行结束 |

## 开发接入

服务端可从 [ord001_policy](../../examples/ord001/ord001_policy.py) 导入 evaluate_order。它只用 Python 标准库。调用前先核验订单归属。接口返回资格状态、理由和规则版本。pending 表示可以申请，用户确认后才建立待审工单。网页的待审、批准和驳回以服务端工单状态为准。

~~~python
from ord001_policy import evaluate_order

verified_order = {"status": "delivered", "expected_at": "18:00", "delivered_at": "18:50"}
decision = evaluate_order(verified_order)
~~~

verified_order 包含 status、expected_at、delivered_at。示例时间使用同日 HH:MM 或 HH:MM:SS。真实订单的时间格式和时区由集成侧另行对齐。

## 首轮复跑证据

用 ORD001、预计 18:00、demo-v1 和模拟模型在本机运行 C 图。此次覆盖判定节点及其后续路由。

| 编号 | 实际送达 | 观察到的结果 |
|---|---|---|
| ENG-C01 | 18:30:00 | 1800 秒，ineligible，流程结束 |
| ENG-C02 | 18:30:01 | 1801 秒，pending，暂停等待审批。输入 reject 后回到同一工单，状态为 rejected，延误仍为 1801 秒 |
| ENG-C03 | 缺失 | needs_info，流程结束 |

上表记录本地资格判定图的开发验证。团队首版需接订单归属、顾客确认、工单状态和网页，见 [前端与工程交接](../../notes/team/frontend-handoff.md)。正式 B/C 对照须等比较范围与规则确认。

## 一起检查代码

打开 [evaluate_order](../../examples/ord001/ord001_policy.py)，找到 include_threshold。值为 false 时用严格大于，值为 true 时包含恰好达到门槛的情形。小组确认正式规则后，更新规则配置版本，并和测试组一起更新边界预期。

- [演示规则配置](../../examples/ord001/demo-policy.json)
- [已发布的 Studio 参考流程](../../examples/ord001/README.md)
- [当前方案与进度](../../notes/current-plan.md)
