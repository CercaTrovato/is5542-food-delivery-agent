# ORD001 网页开发验收记录

运行时间：2026-11-10T16:21:17+08:00。状态：待组员复核。
模式：每项独立的进程内 HTTP 服务。通过 12 项，失败 0 项，范围说明 1 项。

本次使用模拟模型、模拟订单和 demo-v1；不代表正式模型评测或正式政策验收。

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 配置 | demo-v1：已送达且 >30 分钟，¥10 券 | {"version": "demo-v1", "threshold_minutes": 30, "include_threshold": false, "coupon_yuan": 10}；订单数据 demo-orders-2026-11-10；模型 ord001-scripted-model | 通过 |
| P01 批准 | 顾客确认前无工单；确认后待审；人工处理后同一工单回显；重试复用 | 工单 T0001：确认前无工单；确认后 pending、券 None；重复确认 HTTP 409，重试为 ticket_reused；越权与无效请求 [401, 401, 403, 400, 404]；approve 后顾客端同一工单为 approved、券 10、记录 submitted→approved；再问回复「订单 ORD001 的申请 T0001：已批准。¥10 补偿券已发放。」；共 1 张工单 | 通过 |
| P01 驳回 | 顾客确认前无工单；确认后待审；人工处理后同一工单回显；重试复用 | 工单 T0001：确认前无工单；确认后 pending、券 None；重复确认 HTTP 409，重试为 ticket_reused；越权与无效请求 [401, 401, 403, 400, 404]；reject 后顾客端同一工单为 rejected、券 None、记录 submitted→rejected；再问回复「订单 ORD001 的申请 T0001：已驳回。原因：演示：审批员驳回」；共 1 张工单 | 通过 |
| P02 晚 10／30 分钟 | 两笔均不符合，无确认框、无工单 | ORD002 ineligible / delay_below_threshold，回复「ORD002 晚到 10 分钟。需晚到超过 30 分钟才能申请。」；ORD003 ineligible / delay_below_threshold，回复「ORD003 晚到 30 分钟。需晚到超过 30 分钟才能申请。」；无确认框、无工单 | 通过 |
| P02 边界 29:59 | 1799 秒不符合，无工单 | ORD004 ineligible / delay_below_threshold，回复「ORD004 晚到 29 分钟 59 秒。需晚到超过 30 分钟才能申请。」；无确认框、无工单 | 通过 |
| P02 边界 30:01 | 1801 秒可提交，驳回后同一工单仍保留原始秒数 | 1801 秒，awaiting_confirmation / eligible_for_review；确认后工单 T0001 待审；reject 后同一工单为 rejected，仍为 1801 秒 | 通过 |
| P02 晚 31 分钟并取消 | 可申请；取消不建单；可重新咨询 | 1860 秒，awaiting_confirmation；确认框未处理时再发消息 HTTP 409；暂不提交 → claim_cancelled，无工单；再问为 awaiting_confirmation | 通过 |
| P03 缺订单号后提供他人订单 | 先追问，再拒绝核验；不泄露订单事实、不建单；本人可正常查询 | 先追问「请提供订单号，或从「我的订单」中选择。」；ORD101 → unauthorized / order_not_verified，回复「未找到这笔订单，请核对订单号，或从「我的订单」中选择。」；未出现他人订单信息；无工单；日志 ['not_selected', 'unauthorized']；对照组 U002 本人为 awaiting_confirmation | 通过 |
| P03 查无订单 | 与未授权使用相同的顾客回复；服务端日志区分 not_found | not_found / order_not_verified，回复「未找到这笔订单，请核对订单号，或从「我的订单」中选择。」，与未授权是同一句；无工单；日志 ['not_found'] | 通过 |
| 未送达 | 解释仅处理已送达订单，不建单 | ORD006 ineligible / not_delivered，回复「订单 ORD006 尚未送达，请在送达后申请。」；无确认框、无工单 | 通过 |
| 送达时间缺失 | 提示资料不足，不建单 | ORD007 needs_info / invalid_delivery_times，回复「订单 ORD007 暂缺送达记录，无法提交申请。」；无确认框、无工单 | 通过 |
| Studio 参考图 | 独立验证 50 分钟批准／驳回与 30／31 分钟分流 | 18:50 pending → approved；18:50 pending → rejected；18:30 ineligible → ineligible；18:31 pending → rejected | 通过 |
| 补资料扩展的独立验收 | 补资料专项与新版浏览器检查分别验证恢复链路，不并入本脚本的12项 | request_info 需填写补资料说明；工单进入 needs_info，由本人补充后同一工单回到 pending 再审。该链路的权限、多轮历史、数据库迁移与浏览器交互另由补资料专项检查和 UI 检查验证；实际结果见 evidence/2026-11-10-product/。本行仅说明验收范围，不计为本脚本通过项。 | 仅记录 |

## 运行环境

Python 3.12.16；macOS-26.6.2-arm64-arm-64bit。

- langgraph: 1.2.19
- langchain: 1.4.9
- langchain-core: 1.7.7
- langchain-openai: 1.7.4
- starlette: 1.10.0
- uvicorn: 0.54.0
- httpx: 0.28.1

完整请求、工单与运行记录保存在同次运行的 JSON 文件中。
