# ORD001 本机网页交付 · 2026-11-10

任务：ORD001 顾客网页、独立审批入口及首轮开发验证。负责人按任务卡为李宗谦；接收人为李宾雄、gaga老师、A。状态：**待复核**，尚未经接收人验收。

## 本轮交付

顾客能输入诉求，LangChain 模拟模型调用查单工具；服务端核验订单归属，将订单事实交给现有资格判定模块。符合条件时先让顾客确认，再用 LangGraph resume 创建待审工单。商家端可批准、驳回或要求补充资料，顾客端约 3 秒同步结果。补资料沿用同一工单：needs_info → 本人补充 → pending → 再审，保留多轮历史；同一订单和规则版本下重复申请复用工单。

使用 demo-v1：已送达、延误严格超过 30 分钟、建议 ¥10 模拟券。ORD001 预计 18:00、实际 18:50，延误 3000 秒。模型为 `ord001-scripted-model`；没有接真实模型、真实订单或实际发券服务。

| 入口 | 地址 | 账号 |
|---|---|---|
| 顾客 | http://127.0.0.1:8024/ | U001；另有 U002 用于归属对照 |
| 审批员 | http://127.0.0.1:8024/review | R001 |
| 健康检查 | http://127.0.0.1:8024/api/health | 无需登录 |

## 启动和复跑

需要 uv；脚本声明 Python 3.12 和固定版本的直接依赖。首次运行由 uv 准备依赖。本机实际验证 Python 3.12.16、LangGraph 1.2.19、LangChain 1.4.9、Starlette 1.10.0、Uvicorn 0.54.0。完整依赖版本见验收 JSON。

在仓库根目录用 Mac / zsh 启动：

```bash
export UV_PYTHON_INSTALL_DIR="$HOME/.uv/python"
export LANGSMITH_TRACING=false
export LANGCHAIN_TRACING_V2=false

env -u ORD001_CHAT_MODEL -u ORD001_POLICY_PATH \
  uv run --no-project --python 3.12 examples/ord001/ord001_web.py \
  --host 127.0.0.1 --port 8024 --db "$PWD/ord001-demo.sqlite3"
```

找不到 uv 时把它替换为 `$HOME/.local/bin/uv`。Windows / PowerShell 的完整命令及逐步点击说明见 [网页运行指南](../../examples/ord001/README.md)。本轮实际运行环境为 Mac；Windows 命令已提供，尚未在 Windows 设备实跑。

本机 8024 服务实际采用 `--db /Users/lizongqian/is5542-dev/ord001-demo.sqlite3`，加载新增补资料功能后已重启并通过健康检查，沿用同一文件。工单、补资料和事件落库；重新启动仍需重新登录，旧聊天及未确认申请不恢复。

在另一个终端独立复跑，不影响当前网页里的模拟数据：

```bash
export UV_PYTHON_INSTALL_DIR="$HOME/.uv/python"
env -u ORD001_CHAT_MODEL -u ORD001_POLICY_PATH LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false \
  uv run --no-project --python 3.12 examples/ord001/ord001_web_check.py \
  --json /tmp/ord001-check.json --markdown /tmp/ord001-check.md
```

若需对已经启动的网页服务逐项验收，在脚本路径后加入 `--base-url http://127.0.0.1:8024`。这个模式会在每项前重置全部模拟数据，请与手动演示分开运行。

## 实际结果和证据

2026-11-10 香港时间，新增补资料后的后端在进程内 HTTP 服务和采用文件库的真实 127.0.0.1:8024 服务分别完成验收，**各通过 12 项、失败 0 项**。补资料专项另有 **6 组通过、0 组失败**，包括输入与权限、多轮恢复、批准／驳回、并发重试及旧库迁移与重启。新版真实浏览器检查 **9 项通过、0 项失败**，覆盖完整补资料交互、跨轮询草稿／焦点／光标保留及 390px 双端完整处理；浏览器异常与服务端 5xx 记录为空。原 12 项中的范围说明不计作补资料通过项。

- [最新版进程内验收](../../examples/ord001/evidence/2026-11-10-product/api-inprocess.md)
- [最新版实际端口验收](../../examples/ord001/evidence/2026-11-10-product/api-live.md)
- [补资料专项原始结果](../../examples/ord001/evidence/2026-11-10-product/followup-results.json)
- [界面升级说明与浏览器证据入口](ord001-ui-upgrade-2026-11-10.md)

初版界面的浏览器曾通过 5 项；下表与旧截图用于追溯首轮主链路。新版界面及其完整交互按升级说明中的最终证据复核。批准与驳回均从重置后的初态独立试跑；批准记录 ¥10 模拟券，批准前及驳回后均无发券记录。

| 范围 | 预期与实际 | 状态 |
|---|---|---|
| P01 批准 | 确认前不建单；确认后待审；批准后顾客看到同一工单 approved 和 ¥10 模拟券 | 通过 |
| P01 驳回 | 从重置后的同一初态试跑；驳回后同一工单 rejected，顾客看到说明且未发券 | 通过 |
| 重试与权限 | 重复申请复用工单；重复确认、重复审批拒绝；未登录或顾客账号不能审批；他人不能读取工单 | 通过 |
| P02 | 10 分钟、29:59、30:00 不符合；30:01 可提交；31 分钟可申请且取消不建单 | 通过 |
| P03 | 缺订单号先追问；U001 查询 ORD101 不返回他人事实、不建单；本人 U002 可正常查询 | 通过 |
| 查无、未送达、时间缺失 | 服务端区分原因，向顾客说明，均不建工单 | 通过 |
| 原 Studio 参考图 | 50 分钟批准／驳回、30 分钟结束、31 分钟待审 | 通过；沿用原参考实现 |
| 初版浏览器 | P01 批准、P01 驳回、P03 缺订单号、P03 订单归属、390px 手机布局；未发现页面异常或 HTTP 5xx | 通过，历史证据保留 |
| P01 扩展：要求补资料 | 要求说明→本人补充→同工单待审，支持多轮及最终批准／驳回；历史保留，订单事实、规则版本及建议券额不被补资料更改 | 新增专项 6 组通过，见最新版证据 |

开发任务卡的三项核对均有本机开发证据，当前统一标为待复核：

| 任务卡核对项 | 本轮对应证据 | 交接状态 |
|---|---|---|
| 双入口可操作 | 浏览器的顾客确认、审批批准／驳回及双端截图 | 已具备开发证据，待复核 |
| 服务端归属与审批权限 | P03 他人订单不泄露；顾客／未登录审批请求拒绝；他人读工单拒绝 | 已具备开发证据，待复核 |
| 同工单状态与重复申请 | P01 同一工单待审→批准或驳回；重试 ticket_reused，仅保留一张工单 | 已具备开发证据，待复核 |

开发分支使用 `feat/ord001-local-web`，GitHub 交件方式见下方“版本与合入”。上表不表示测试组已验收，也不直接更改进度看板的通过计数。

原始证据：

- [进程内验收摘要](../../examples/ord001/evidence/2026-11-10/api-inprocess.md) / [完整 JSON](../../examples/ord001/evidence/2026-11-10/api-inprocess.json)
- [实际端口验收摘要](../../examples/ord001/evidence/2026-11-10/api-live.md) / [完整 JSON](../../examples/ord001/evidence/2026-11-10/api-live.json)
- [浏览器验收 JSON](../../examples/ord001/evidence/2026-11-10/browser-results.json)
- [顾客确认前](../../examples/ord001/evidence/2026-11-10/p01-before-confirm.png)、[审批待审](../../examples/ord001/evidence/2026-11-10/p01-review-pending.png)
- [顾客批准结果](../../examples/ord001/evidence/2026-11-10/p01-customer-approved.png)、[审批批准结果](../../examples/ord001/evidence/2026-11-10/p01-review-approved.png)
- [顾客驳回结果](../../examples/ord001/evidence/2026-11-10/p01-customer-rejected.png)、[审批驳回结果](../../examples/ord001/evidence/2026-11-10/p01-review-rejected.png)
- [订单归属处理](../../examples/ord001/evidence/2026-11-10/p03-order-ownership.png)、[手机布局](../../examples/ord001/evidence/2026-11-10/customer-mobile.png)

## 版本与合入

原始 GitHub ZIP 注释记录的基线提交：`2d7951b1cab009e54447ef357db709ca941d3f28`。源 ZIP 的 SHA-256 为 `bcd9f9e2c38587b2bc2f135d92a916cff69df4ec7bf205e094c18486625ae28b`。

开发最初在 ZIP 工作副本进行，现已建立保留原仓库历史的真实 Git 工作副本。GitHub 本人授权已完成，原私库写入权限已核实；本轮使用开发分支 [`feat/ord001-local-web`](https://github.com/CercaTrovato/is5542-food-delivery-agent/tree/feat/ord001-local-web) 交付。实际提交号见该分支的提交记录和关联 PR。**上述基线号仅用于追溯来源，不代表本次开发提交号。**

持有原私库访问权限的组员，可以在新目录拉取交付分支：

```bash
git clone --branch feat/ord001-local-web --single-branch https://github.com/CercaTrovato/is5542-food-delivery-agent.git ord001-local-web
cd ord001-local-web
git log -1 --format='%H %s'
```

再按上面的启动命令复跑。PR 用于交接和复核，开发分支不自动合入 main；任务 Issue 保持“待复核”，由接收人填写验收结果。如何在网页查看自己的任务、提交证据和记录复核，见 [GitHub 组内协作方式](github-collaboration.md)。

## 待核和下一步

1. **组员复核**：按开发分支和关联 PR 检查本轮代码与证据，在任务 Issue 记录实际复跑结果；三项任务卡核对保持待复核，直到接收人确认。
2. **补资料复核**：同工单补充与再审已接入，本轮支持文本说明，不支持图片或附件上传。接收人按专项与新版浏览器证据复跑；补充内容不能用于直接改写订单事实和规则。
3. **团队模型与正式政策**：目前验证的是固定模拟模型下的工程链路，正式模型、提示词泛化、补偿例外与 B/C 对照均待团队输入后验证。
4. **部署**：当前仅本机运行，模拟账号无密码。线上身份认证与部署地址尚未接入。
5. **重启行为**：当前文件库保留工单、补资料记录与事件，重启后可重新登录并继续处理已建工单；旧聊天、登录会话、未确认申请及图检查点不恢复。省略 `--db` 时使用内存，工单也会在重启后清空。

原 Studio 参考图仍调用 ord001_graph.py 的旧判断：只接收 HH:MM，阈值 >30 分钟和 ¥10 为硬编码。本轮 Studio 对照仅验证 50 分钟批准／驳回及 30／31 分钟分流；30:01 的秒级边界由新网页和共享 ord001_policy.py 验证。两套图尚未统一规则模块，不能把 Studio 对照当成秒级边界验证。

接收人复核优先按网页指南分别跑一遍批准和驳回，再用验收脚本核对 P02／P03。开发证据保留为待复核，不能替代测试组验收。
