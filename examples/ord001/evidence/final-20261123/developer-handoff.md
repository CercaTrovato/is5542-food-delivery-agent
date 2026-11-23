> 开发侧原始资料的目录副本，非测试组正式验收。相对链接已按本资料目录修正；原文同名 `.source.txt` 保留原始字节。正式题量现已由本人确认20题×2模式×3轮=120次系统试跑。方法／成本／PPT采用限制见[接收评阅](../../../../work/eval/developer-delivery-2026-11-23.md)。

# 开发开测说明（2026-11-23 已对齐 `human-review-v1`、基础客服 B 及两段在线录屏）

> **交接人**：李宗谦（LI Zongqian · 60582017）
> **接收人**：李宾雄、A、gaga老师
> **固定受测代码提交（Code Commit SHA）**：`176fbb0`（完整哈希：`176fbb0264203b53e7ed8c68760a75243e5b113b`，分支 `feat/ord001-local-web`；后续补充本交接说明与实测证据文件的纯文档提交不改动任何受测运行代码）
> **生效规则组合**：`demo-v1` + `human-review-v1`（`stp_auto_approve = false`，人工审批主链路生效）

---

## 一、历史修复项与 11/23 四项新增边界状态总表（开发自测 vs 测试组验收严格分列）

> 说明：以下「开发自测通过」仅代表开发在受测提交 `176fbb0` 上已完成自动化与真实模型冒烟验证，**不替代测试组（A + gaga）的独立复测验收结论**。

| 编号 / 模块 | 对应要求 | 代码状态与提交 | 开发自测结果 | 测试组（A + gaga）验收状态 |
|---|---|---|---|---|
| **R01 (= P02)** | 驳回后展示具体驳回原因，保留原申请「已驳回」，提供转人工继续咨询同一订单入口，不新建第二张工单 | 已修（`0fca410` → 现绑定 `176fbb0`） | 已复现并自测通过（`ord001_handoff_actions_check.py`） | 11/22 初验标过；待在 `176fbb0` 结合 `HR01–HR03` 补证 |
| **R02 (= P03-04)** | 人工聊天保持连续：① 人工回复按时间顺序插在当前聊天流对应位置；② 顾客继续发消息仍保持人工服务，无需重按转人工 | 已修（`0fca410` → 现绑定 `176fbb0`） | 已复现并自测通过（位置锚点 `reply_after_index` + 状态保持） | 11/22 初验标过；待绑定 `176fbb0` 归档 |
| **R03 (= P03-05)** | 从订单/多轮对话转人工后，即使最近几句未提单号，商家端仍能看到正确关联订单与最初诉求 `initial_appeal` | 已修（`0fca410` → 现绑定 `176fbb0`） | 已复现并自测通过 | 11/22 初验标过；待绑定 `176fbb0` 归档 |
| **多单独立编号** | 同一顾客对订单 A、B、C 分别申请/转人工时遵循「一单一编号」（`H0001` / `H0002`…），互不串单 | 已修（`df65b5d` → 现绑定 `176fbb0`） | 自测通过（`path3_multi_order_one_to_one` + `HR09`） | 待测试组在 `176fbb0` 复核 |
| **公网语音/图片上传** | 公网网关将 multipart 附件放宽至 `6 MiB`（单文件 `≤ 5 MB`，JSON 仍限 `16 KiB`），修复 WebM 语音报 `HTTP 413` | 已修（`77af28d` → 现绑定 `176fbb0`） | 自测通过（`ord001_share_check.py` 13/13 + 公网隧道实传验证） | 仅做文件魔数校验与原样转发人工播放，**不做语音识别转文字或多模态自动判赔** |
| **human-review-v1 四项边界** | ① 仅已驳回未补偿单有新信息/原处理错并写原因才可沿原单重审；② 仅 `R002` 可改额，`R001` 标准 `10` 元，`R003` 只读；③ `1–20` 整数元且 `≤ 可信实付`（不静默截断/降额）；④ 同单原子唯一补偿，发后禁重审/改额/补差价 | **本次已完成对齐（`176fbb0`）** | 开发自测 9 组全通过（`ord001_hr_boundaries_check.py` `9/9`） | **待测试组执行正式九组边界复测（[清单](../../../../work/eval/human-review-boundary-checks.md)）** |
| **基础工具型客服 B** | 按 [基础 B 合同](../../../../work/spec/basic-tool-agent-baseline.md) 实现 `--agent-mode B`，与 C 共用模型、数据、鉴权工具、确认中断、工单审批及执行保护 | **本次已完成实现（`176fbb0`）** | 已跑通真实在线模型 B/C 完整闭环与 3 题冒烟（`live-bc-walkthrough-and-smoke.json`） | **待测试组核对架构后开展正式同题比较（20题×3轮留空待测）** |

---

## 二、开发开测必填信息表（全部绑定受测提交 `176fbb0`）

| 必填项 | 实际核实内容 |
|---|---|
| **受测提交、前端／后端是否同版本** | **受测代码提交**：`176fbb0`（`176fbb0264203b53e7ed8c68760a75243e5b113b`）。本机后端服务（`127.0.0.1:8024`）与公网转发入口已重启加载该提交；前端 HTML 静态资源统一带 `?v=20261123-v18`，`/api/health` 返回 `"review_policy_version": "human-review-v1"`, `"agent_mode": "C"`, `"stp_auto_approve": false`，前后端 100% 同版本。 |
| **实际模型名、参数、无密钥调用证据、限额** | • **配置模型标签**：`openai:deepseek-flash`（网关 `https://api.deepseek.com`）<br>• **HTTP 响应实测返回模型标识（`response_metadata.model_name`）**：`deepseek-flash`<br>• **固定请求参数**：`temperature=0.35`, `max_tokens=800`, `timeout_seconds=30`, `max_retries=0`, `thinking="disabled"`<br>• **无密钥真实调用证据**：[`live-bc-walkthrough-and-smoke.json`](live-bc-walkthrough-and-smoke.json)（记录每次调用返回模型名、Token 与耗时，完全不含 API Key）<br>• **网关并发与限流**：公网入口最多允许 `2` 条模型请求并发（第 3 条返回繁忙提示），每分钟最多 `12` 条聊天消息，JSON 上限 `16 KiB`，媒体上传上限 `6 MiB`（单文件 `≤ 5 MB`，每顾客累计 `≤ 25 MB`）；本机私有配置账户余额充足。 |
| **C 怎样运行／顾客和商家怎样进** | • **公网稳定入口（默认运行 C 模式，提交 `176fbb0`）**：<br>  - 顾客端：`https://ord001-group24.surge.sh/`（点选 `U001` 或 `U002` 登录）<br>  - 商家/主管端：`https://ord001-group24.surge.sh/review`（点选 `R001` 普通客服、`R002` 主管或 `R003` 只读观察员登录）<br>• **本机独立启动 C 命令（不含密钥）**：<br>  `uv run examples/ord001/ord001_web.py --port 8024 --db /tmp/test-c.sqlite3 --model-config ~/.config/ord001/deepseek.json --agent-mode C` |
| **B 怎样运行／选择模式；B 查单—确认—人工审记录** | • **本机交互启动 B 命令**：<br>  `uv run examples/ord001/ord001_web.py --port 8025 --db /tmp/test-b.sqlite3 --model-config ~/.config/ord001/deepseek.json --agent-mode B`<br>  （进入后顶部徽章显示 `演示 · B对照`，`/api/health` 显示 `"agent_mode": "B"`）<br>• **B/C 同题命令行评测器（每次独立内存库、绝无缓存冒充、禁止退回脚本模型）**：<br>  `uv run examples/ord001/ord001_bc_runner.py --model-config ~/.config/ord001/deepseek.json --suite --modes B,C --repeats 3 --out-json /tmp/bc-eval.json`<br>• **一次真实在线模型 B「查单 → 确认 → 人工审批 → 结果回显」完整记录**：已保存在 [`live-bc-walkthrough-and-smoke.json`](live-bc-walkthrough-and-smoke.json) 的 `walkthrough.B` 字段（`U001` 查 `ORD001` → `model_b` 输出结构化建议 `eligible: true, proposed_coupon_yuan: 10` → 顾客 `confirm` 生成 `T0001 pending` → `R001` 批准发放 `¥10` → 顾客再问回显 `approved ¥10`，总系统耗时 `4,110 ms`，`3` 次模型调用，共 `2,751` tokens）。 |
| **数据和 `demo-v1`；共同合法事实／工具／身份边界** | • **数据集**：`examples/ord001/demo-data.json`（`data_version: "demo-orders-2026-11-10"`, `service_date: "2026-11-10"`）。<br>• **`demo-v1` 参数**：`threshold_minutes=30`, `include_threshold=false`（严格 `late_seconds > 1800`），`coupon_yuan=10`。<br>• **B/C 共同工具边界**：均调用同一 `make_order_tool(data)`（`query_order`），严格按当前登录 `customer_id` 校验归属（他人订单 `ORD101` 与不存在订单 `ORD999` 返回一致盲化提示，不把全租户表交给模型）；工具返回原始时间字段与统一算法算出的 `late_seconds` / `late_minutes`，**不预塞 `eligible` 资格答案**。 |
| **人工审核及自动通过等实际开关** | `stp_auto_approve = false`（`/api/health` 可直接核验）。本轮受测主链路全部走「顾客确认 → `pending` 待审核 → 人工坐席审批」。 |
| **B/C 实际差异，哪些代码复用** | • **100% 复用代码**：同一 `DemoService`、同一前端页面、同一会话鉴权、同一 `query_order` 工具、同一 `confirm` 中断节点、同一 `submit` 二次核验、同一 `TicketStore` / `human-review-v1` 审批权限与防重索引、同一 `reply_risk` 护栏。<br>• **核心设计差异（唯一自变量）**：在 `assess` 节点，C 调用确定性规则函数 `evaluate_order` 生成建议并用 LLM 润色自然语言；B 将工具返回事实与既有工单摘要交给 LLM（`BASIC_ASSESS_PROMPT_B`），由模型独立输出结构化 JSON 建议（`raw_proposal`），不暗调 `evaluate_order` 代答。若 B 给出越权/错误建议被后端拦截，日志同时保留 `raw_proposal`（模型决策错误）与 `unsafe_proposal` / `safety_intercept`（执行被拦）。<br>• **额外披露的次要实现差异**：C 在 `agent` 节点保留单号正则辅助触发 `query_order` 与 P0 食安关键词前置熔断；B 在 `agent` 节点完全依赖 `model.bind_tools([query_order])` 原生工具调用决策。无其他隐藏参数变动。 |
| **独立初态／数据、重置和模型失败处理办法** | • **公共环境勿直接清库**：公网网关默认拦截 `/api/review/reset` 以防覆盖他人正在测试的数据。多人共用公网环境测试时，建议先用不同订单（`ORD001`、`ORD005`、`ORD008`、`U002` 的 `ORD101`），如需清空共享库 `ord001-demo.sqlite3` 请群内招呼我本机备份后重置。<br>• **测试组本机完全独立初态**：每次指定新 `--db /tmp/retest-xx.sqlite3` 即可获得 100% 干净初态；测 `HR06`（实付 `¥8` 订单 `ORD009` 与实付缺失 `ORD010`）时加 `--data-file examples/ord001/fixtures/hr06-isolated-data.json`。<br>• **一键跑九组边界检查脚本**：<br>  `uv run examples/ord001/ord001_hr_boundaries_check.py --label acceptance_retest --out-json /tmp/hr-retest.json`<br>• **模型失败处理**：API 超时/429/5xx 返回 `HTTP 503 model_unavailable` 并保留顾客输入框草稿；Mode B 中模型报错或 JSON 解析失败直接记录 `model_error` / `proposal_format_error`，**绝不自动静默退回 `ScriptedOrderModel` 冒充真实样本**。 |
| **供视觉检查的顾客入口与待审／通过／驳回 3 张示例 + 架构图** | 无需 gaga 老师自己跑模型或走完整审批，可直接查看受测提交 `176fbb0` 实截画面：<br>• 待审核状态：[`state-pending.png`](state-pending.png)<br>• 已通过状态：[`state-approved.png`](state-approved.png)<br>• 已驳回状态（含具体原因与转人工入口）：[`state-rejected.png`](state-rejected.png)<br>• B/C 架构与人工边界流程图：[`architecture-bc-flow.svg`](architecture-bc-flow.svg) / [`architecture-bc-flow.png`](architecture-bc-flow.png) |
| **两段实际演示录屏、已知未修／未测项** | • **正常全链路录屏（Slide 7）**：[`demo-normal-ord001-approve.mp4`](demo-normal-ord001-approve.mp4)（同目录附 `.webm`）— 真实在线 `deepseek-flash` 完成 `ORD001` 查单 → 确认 → `T0001` 待审 → `R001` 标准 `¥10` 通过 → 顾客端回显。<br>• **异常驳回与主管重审改额录屏（Slide 8）**：[`demo-exception-reject-reconsider.mp4`](demo-exception-reject-reconsider.mp4)（同目录附 `.webm`）— 真实在线 `deepseek-flash` 完成 `ORD008` 提交 → `R001` 驳回 → 顾客携门禁新记录进 `H0001` 连续人工会话 → `R001` 金额锁定 `¥10` 升级主管 → `R002` 勾选「可核实的相关新信息」沿原单 `T0001` 批 `¥15` 并锁定一单一赔。<br>• **已知限制与留空待测项**：<br>  1. 测试组（A + gaga）的 `HR01–HR09` 正式独立验收结论与 `20题×3轮` 正式 B/C 同题对照成绩尚未执行，按约留空由测试组实测填写；<br>  2. 语音（WebM/MP3/WAV）与图片仅做二进制魔数/哈希鉴伪并转发人工坐席播放查看，未接入 ASR 语音转写或多模态大模型自动看图判赔；<br>  3. 仅发放课程演示模拟无门槛券，不涉及真实支付网关原路退款、发券后补差价或追回。 |

---

## 三、测试组（A + gaga）快速复测命令速查

```bash
# 1. 核对受测提交（应输出 176fbb0 或紧随其后的纯文档提交，examples/ord001 代码树一致）
git log -n 2 --oneline

# 2. 一键执行 human-review-v1 九组边界自动化复测（独立临时库 + HR06 隔离8元单，不碰共用库）
uv run examples/ord001/ord001_hr_boundaries_check.py \
  --label acceptance_retest \
  --out-json /tmp/hr01-hr09-acceptance.json

# 3. 如需在网页手测 HR06（ORD009 实付8元单、ORD010 实付缺失单），本机起独立端口：
uv run examples/ord001/ord001_web.py \
  --port 8026 \
  --db /tmp/hr06-manual.sqlite3 \
  --data-file examples/ord001/fixtures/hr06-isolated-data.json \
  --model-config ~/.config/ord001/deepseek.json

# 4. 运行正式 B vs C 真实在线模型同题对照（默认内置 20 题 BC01-BC20，亦可用 --cases-file 指定测试组题表）：
uv run examples/ord001/ord001_bc_runner.py \
  --model-config ~/.config/ord001/deepseek.json \
  --suite --modes B,C --repeats 3 \
  --out-json /tmp/bc-formal-comparison-60runs.json
```

> 安全提醒：任何模型配置文件（如 `deepseek.json`）、API 密钥或隧道令牌均保存在本机仓库外，严禁提交 Git、截图或发群；若后续因复测发现问题需要改代码，我将提交新 SHA 并明确列出需重测的用例组编号，绝不静默覆盖受测版本。
