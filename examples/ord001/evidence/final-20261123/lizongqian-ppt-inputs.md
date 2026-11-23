> 开发侧原始资料的目录副本，非测试组正式验收。相对链接已按本资料目录修正；原文同名 `.source.txt` 保留原始字节。正式题量现已由本人确认20题×2模式×3轮=120次系统试跑。方法／成本／PPT采用限制见[接收评阅](../../../../work/eval/developer-delivery-2026-11-23.md)。

# IS5542 Group 24 PPT 开发侧补齐材料清单（李宗谦 / LI Zongqian · 60582017）

> 对应组长草稿：`IS5542-Group24-DRAFT-v2.pptx`（共 15 页）与 `work/presentation/material-checklist.md`（M01–M14）。
> 范围声明：本文件**仅提供李宗谦（开发）负责提交的真实受测数据、架构图、录屏与技术口径**；不代填测试组（A + gaga）的正式 60 次同题对照成绩或视觉问卷结果，也不改动组长李宾雄已定的 PPT 叙事结构。

---

## 1. 逐页填空对照表（直接供组长填入 `IS5542-Group24-DRAFT-v2.pptx`）

### Slide 1 — 封面成员信息（对应 `M02` 本人项）
- **英文姓名（按 CityU 教务规范）**：`LI Zongqian`（中文：李宗谦）
- **学号（SID）**：`60582017`
- **本组角色**：`Prototype & Baseline Developer (Explicit-Rule Agent C, Basic Tool Baseline B & Human-Review Workbench)`

---

### Slide 4 & Slide 5 — 业务规则与系统架构（对应 `M05`、`M06`）
- **受测冻结代码提交（Code Commit SHA）**：`176fbb0`（完整哈希：`176fbb0264203b53e7ed8c68760a75243e5b113b`，前端静态资源版本 `?v=20261123-v18` 与后端完全同提交对齐）
- **生效规则组合**：`demo-v1` + `human-review-v1`
  - **基础资格（`demo-v1`）**：订单状态须为已送达（`status == "delivered"`），且实际延误严格超过 30 分钟（`late_seconds > 1800`；恰好 `30:00` 即 `1800s`、未送达、缺签收时间均不符合自助确认）。
  - **人工审批主链路开关**：`stp_auto_approve = false`（默认关闭自动直通秒批，所有通过顾客确认的申请均进入 `pending` 待人工审批）。
  - **人工重审与改额四项边界（`human-review-v1`，D18–D21）**：
    1. **有理由重审**：仅限 `status == "rejected"` 且该订单尚未成功发放过补偿的原工单；须勾选重审依据（`verifiable_relevant_new_information` 可核实新信息 / `prior_processing_error` 原处理错误）并填写非空书面原因，沿原工单恢复 `pending` 重新核验并完整保留 `prior_review_note` 与历史事件；仅反复表达不满不自动重开。
    2. **改额角色权限**：普通客服 `R001` 仅可按标准 `¥10` 审批；仅主管角色 `R002` 可自定义金额；`R003` 为只读观察席（全部写操作 `403`）；顾客与 AI 均无权直接改额。
    3. **金额范围与实付上限**：标准 `¥10` 模拟无门槛券；`R002` 自定义金额须为 `1–20` 元正整数、必填改额理由，且所有实际发放金额（含标准 `¥10`）均不得超过服务端可信订单实付 `amount_yuan`（例如 `¥8` 实付订单尝试发 `¥10` 或 `¥9` 均拒绝 `409` 且不静默降额，`R002` 填理由批 `¥8` 可通过；实付缺失不可核时拒绝发放；`0 / 21 / 1.5` 等非法输入直接报 `400` 拒绝，绝不四舍五入或截断）。
    4. **一单一赔防重**：SQLite 部分唯一索引（`idx_one_compensated_per_order`）+ 服务端原子事务锁保证同一 `order_id` 最多成功发放一次补偿；发券后禁止重审、改额或补差价；连点、刷新、换坐席、换会话、并发审批或切换 `policy_version` 均返回原补偿记录而不重复发券；同顾客名下不同订单（如 `ORD001` 与 `ORD005`）以及人工处理单（`H0001` / `H0002` 一单一编号）彼此完全独立。
- **架构图文件（可直接拖入 Slide 5 或 Slide 9）**：
  - 矢量原图：`examples/ord001/evidence/final-20261123/architecture-bc-flow.svg`
  - 高清 2x 位图（2400×1360）：`examples/ord001/evidence/final-20261123/architecture-bc-flow.png`

---

### Slide 6 — 模拟数据集与在线模型真实配置（对应 `M06`、`M07`）
- **订单数据版本**：`demo-orders-2026-11-10`（模拟服务日期 `2026-11-10`；另有 `HR06` 专用隔离数据 `fixtures/hr06-isolated-data.json` 含 `ORD009` 实付 `¥8` 与 `ORD010` 实付缺失样本，不污染主库）
- **模拟账号与租户隔离**：
  - `U001`：含 `ORD001`（50m，`¥58`）、`ORD002`（10m，`¥32`）、`ORD003`（恰好 30:00，`¥45`）、`ORD004`（29:59，`¥27`）、`ORD005`（边界 30:01，`¥39`）、`ORD006`（配送中，`¥22`）、`ORD007`（缺送达时间，`¥41`）、`ORD008`（31m，`¥36`）
  - `U002`：含 `ORD101`（50m，`¥66`，验证跨顾客盲化防越权：对 `U001` 查 `ORD101` 与查不存在的 `ORD999` 返回完全一致的未核实提示）
  - 坐席账号：`R001`（门店普通客服，标准 `¥10`）、`R002`（平台主管，支持 `1–20` 整数元改额）、`R003`（只读观察席）
- **在线大模型真实配置（脱敏，不含任何密钥）**：
  - **接入协议与网关**：OpenAI-Compatible HTTPS (`https://api.deepseek.com`)
  - **配置请求模型标识**：`openai:deepseek-flash`（请求字段 `model: "deepseek-flash"`）
  - **服务端响应实测返回模型标识（`response_metadata.model_name`）**：`deepseek-flash`
  - **固定推理参数**：`temperature = 0.35`, `max_tokens = 800`, `timeout = 30s`, `max_retries = 0`, `thinking = disabled`（关闭深度思考链以稳定客服首字响应）

---

### Slide 7 — 正常全链路真实演示录屏（对应 `M08` 正常录屏 + 3 张状态截图）
- **视频文件（可直接插入 PPT 播放，H.264 MP4 + VP9 WebM 双格式）**：
  - `examples/ord001/evidence/final-20261123/demo-normal-ord001-approve.mp4`
  - `examples/ord001/evidence/final-20261123/demo-normal-ord001-approve.webm`
- **Slide 7 底部元数据标注建议文本**：
  - `Commit: 176fbb0 (v18) | Live Model: deepseek-flash (T=0.35, thinking=disabled) | Policy: demo-v1 + human-review-v1 | Captured: 2026-11-23`
- **五步画面精确对应**：
  1. `01 Query order`：`U001` 登录顾客端，输入 `ORD001` 延误补偿诉求，在线模型调用 `query_order("ORD001")` 核实预计 `18:00`、实际 `18:50`（晚到 50 分钟）。
  2. `02 Confirm request`：弹出确认卡片（`¥10`、`demo-v1`），确认前数据库 0 工单、0 发券。
  3. `03 Pending review`：点击「确认提交」生成 `T0001`（状态 `待审核`，`coupon_issued_yuan = null`）。
  4. `04 Human approval`：切换 `/review` 登录 `R001`（界面显示普通客服金额锁定标准 `¥10`），填写说明并点击「通过」。
  5. `05 Actual status`：切回顾客端，`T0001` 实时更新为 `已通过`（已发放 `¥10` 模拟券），并显示一单一赔防重说明。
- **供轻量视觉检查的 3 张独立状态截图**：
  - 待审核：`examples/ord001/evidence/final-20261123/state-pending.png`
  - 已通过：`examples/ord001/evidence/final-20261123/state-approved.png`
  - 已驳回（含具体原因与人工复核入口）：`examples/ord001/evidence/final-20261123/state-rejected.png`

---

### Slide 8 — 驳回、连续人工咨询与主管有理由重审改额录屏（对应 `M08` 异常/边界录屏）
- **视频文件（H.264 MP4 + VP9 WebM 双格式）**：
  - `examples/ord001/evidence/final-20261123/demo-exception-reject-reconsider.mp4`
  - `examples/ord001/evidence/final-20261123/demo-exception-reject-reconsider.webm`
- **Slide 8 底部元数据标注建议文本**：
  - `Commit: 176fbb0 (v18) | Live Model: deepseek-flash | Scenario: ORD008 Rejected → H0001 Human Appeal → R001 Escalate → R002 Reconsider ¥15 on T0001 | Captured: 2026-11-23`
- **演示链路**：
  1. `U001` 提交 `ORD008`（实付 `¥36`，晚 31 分钟）→ `R001` 首次以临时管制为由驳回 `T0001`（未发券）。
  2. 顾客端清晰展示具体驳回原因，保留原单 `T0001 · 已驳回`（不新建 `T0002`），点击「二次申请 · 转人工处理」生成独立处理单 `H0001` 并连续发送可核实门禁签收记录与汤洒说明。
  3. `/review` 中 `R001` 查看 `H0001`（金额框锁定标准 `¥10` 灰置不可改），点击「升级主管」。
  4. 切换主管 `R002` 登录，选择重审依据 `可核实的相关新信息`，输入合法整数金额 `15`（`1–20` 整数且 `≤ 实付 ¥36`）与书面复核理由，沿**原工单 `T0001`** 改判通过并发放唯一 `¥15` 补偿券，界面随即锁定为「已完成唯一补偿 ¥15（一单一赔）」。
  5. 切回顾客端，原聊天流内按时间顺序出现系统通知，右侧原工单 `T0001` 同步更新为 `已通过 · ¥15`。

---

### Slide 9 — 基础工具型客服 B vs 显式业务规则型 C 架构对照表（对应 `M09` 开发架构输入）
- **两方案 100% 共用层**：同一在线模型 `deepseek-flash` 与相同推理参数、同一 `demo-v1 + human-review-v1` 规则文本、同一会话登录身份隔离、同一 `query_order` 查单工具（统一计算 `late_seconds` 但**不预塞 `eligible` 答案**）、同一多轮 SQLite 检查点、同一 `confirm_submission` 顾客确认中断、同一 `TicketStore` / 人工审批 / 一单一赔防重与 `reply_risk` 输出护栏。
- **唯一核心自变量**：
  - **方案 B（`--agent-mode B`）**：工具返回订单原始事实后，由大模型阅读 `demo-v1` 规则直接输出结构化建议（`eligible`, `next_action`, `order_id`, `proposed_coupon_yuan`, `reason`, `reply`），不调用程序规则节点代答；服务端分别记录 `raw_proposal`（模型原始决策）与 `safety_intercept` / `final_outcome`（共享安全层拦截与终态）。
  - **方案 C（`--agent-mode C`）**：工具返回事实后，由确定性程序规则节点 `evaluate_order` 判定资格与下一步动作，大模型仅在锁定核心时间与资格结论的前提下生成自然语言回复。
- **附带已披露实现细节差异**：方案 C 在 `agent` 节点含单号正则兜底强制调工具逻辑以防漏查，而方案 B 完全依赖 `model.bind_tools([query_order])` 原生工具调用决策（实测在对抗注入题 `BC18` 中即体现出这一真实差异：B 受覆盖指令干扰漏调工具，C 稳定查单并给出合法 `¥10` 确认）。
- **单次完整 B 链路实测记录（开发冒烟留证，非正式 60 次评测）**：
  - 详见 `examples/ord001/evidence/final-20261123/live-bc-walkthrough-and-smoke.json`：Mode B 完成 `ORD001 查单 → 顾客确认 → R001 人工审批 → 顾客追问回显已通过 ¥10` 全流程，总系统耗时 `4,110 ms`（模型调用 `3` 次，输入 `2,454` tokens，输出 `297` tokens，总计 `2,751` tokens）；同题 Mode C 完整链路总系统耗时 `4,840 ms`（模型调用 `4` 次，输入 `3,880` tokens，输出 `235` tokens，总计 `4,115` tokens）。

---

### Slide 12 & Slide 14 — 耗时、Token 用量与单位成本口径（对应 `M13` 开发技术输入）
- **计时分离口径（避免把人工等待算进 AI 延迟）**：
  1. **系统响应耗时 `system_latency_ms`**：仅统计顾客发起请求或点击确认后，服务端执行 LangGraph 节点 + 在线 LLM API 往返直至返回响应/弹出确认框的毫秒数（单轮查单实测约 `2.1s – 3.2s`；确认建单纯本地事务约 `50 ms`）。
  2. **人工审批动作耗时 `review_action_latency_ms`**：坐席点击审批按钮后服务端原子落库耗时（实测 `< 10 ms`）；现实业务中的**人工排队等待时长（Human Queue Wait Time）**单列说明，不混入模型系统延迟。
- **Token 用量与单次对话API成本估算口径**：
  - 单次完整自助申诉闭环（含查单核验 + 确认建单 + 审批后查结果）：
    - **方案 B**：约 `2,751` tokens / 闭环（`2,454` input + `297` output，`3` 次 API 调用）
    - **方案 C**：约 `4,115` tokens / 闭环（`3,880` input + `235` output，`4` 次 API 调用，多 1 次受控事实润色调用以换取确定性边界准确度）
  - 按 DeepSeek 在线 API 标准单价折算，两种方案单次客诉全流程的模型 Token 直接边际成本均在 **人民币 `¥0.005 – ¥0.015` / 单（约合 `< HK$0.02` / 单）** 数量级，远低于纯人工客服单均接待成本，同时保留高风险/争议环节的人工最终裁决权。

---

### Slide 15 — 个人分工与 AI 工具辅助声明（对应 `M02`、`M14` 本人项）
- **LI Zongqian (`60582017`) 贡献摘要**：
  - Implemented the LangGraph + Starlette + SQLite customer & merchant/supervisor review web prototype (`examples/ord001`), Explicit-Rule Agent C & Basic Tool Agent B controlled comparison runner (`ord001_bc_runner.py`), `human-review-v1` role/amount/reconsideration/idempotency guards (`ord001_hr_boundaries_check.py`), public gateway media support (`ord001_share.py`), and live-model screen recordings.
- **AI 工具辅助声明（开发部分）**：
  - Used AI coding & image generation assistants during development for code refactoring, edge-case test scaffolding, and non-commercial course demo mascot illustrations; all business boundary rules (`demo-v1 + human-review-v1`), live `deepseek-flash` API executions, and SQLite state assertions were verified against real runtime logs.
