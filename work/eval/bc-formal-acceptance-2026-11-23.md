# 正式内部对照结果表（20题×两模式×3轮，待执行）

本人已于11/23确认20题，两模式各3轮；主计划120次系统试跑。状态：未执行，本表没有成绩。版本176fbb0，规则demo-v1＋human-review-v1，实际环境／模型返回标识／开关由执行者回填，开发自测不复制为本表结果。

| BC编号 | 题型／条件 | B第1／2／3轮与证据 | C第1／2／3轮与证据 | 完整回复／工具／原始建议／拦截／终态复核 |
|---|---|---|---|---|
| BC01 | eligible_50m | 未测 | 未测 | 待核 |
| BC02 | boundary_30m01s | 未测 | 未测 | 待核 |
| BC03 | eligible_31m | 未测 | 未测 | 待核 |
| BC04 | eligible_cancel_confirm | 未测 | 未测 | 待核 |
| BC05 | boundary_exact_30m00s | 未测 | 未测 | 待核 |
| BC06 | boundary_29m59s | 未测 | 未测 | 待核 |
| BC07 | ineligible_10m | 未测 | 未测 | 待核 |
| BC08 | undelivered_order | 未测 | 未测 | 待核 |
| BC09 | missing_delivered_at | 未测 | 未测 | 待核 |
| BC10 | other_customer_order | 未测 | 未测 | 待核 |
| BC11 | nonexistent_order | 未测 | 未测 | 待核 |
| BC12 | missing_order_id_clarify | 未测 | 未测 | 待核 |
| BC13 | multiturn_supply_order_id | 未测 | 未测 | 待核 |
| BC14 | tenant_u002_own_order | 未测 | 未测 | 待核 |
| BC15 | already_compensated_reuse | 未测 | 未测 | 待核 |
| BC16 | rejected_ticket_no_duplicate | 未测 | 未测 | 待核 |
| BC17 | food_safety_anomaly | 未测 | 未测 | 待核 |
| BC18 | adversarial_custom_amount_injection | 未测 | 未测 | 待核 |
| BC19 | adversarial_ineligible_refund_promise | 未测 | 未测 | 待核 |
| BC20 | lookup_praise_no_claim | 未测 | 未测 | 待核 |

每轮保存完整输入、消息／工具、原始建议、格式／模型失败、安全拦截、最终状态与实际发放、模型调用数、Token、系统耗时。逐次给判断，汇总明确分母；错误／超时保留，剔除须说明。HR九组和补充问法／开发冒烟另列，不混进主120。

主要差异与附带的单号兜底／食安前置差异必须披露；结果不能独立归因唯一节点。runner自动字段只是预标注，特别看错误承诺与最终执行分开。正式正确率、通过率、耗时／成本比较、优势结论均留空。

[冻结题库](bc-formal-plan-2026-11-23.json) · [接收与方法评阅](developer-delivery-2026-11-23.md) · [统一验收报告](team-acceptance.md)
