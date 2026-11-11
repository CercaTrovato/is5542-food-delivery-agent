# ORD001 真实模型接入记录

本次在既有顾客与商家流程上追加真实模型接入。用户已指定 DeepSeek 官方，并授权使用其自行提供的 API 密钥。调用 `https://api.deepseek.com/models` 验证成功后，选择可用的 `deepseek-flash`。实际密钥仅保存于本机仓库外的私有文件，文件权限为 0600，不进入源码、浏览器、Git 或交付包。

此前冻结提交 `d7ba6084934f095ce2c9cb6d1dc03a431091e456` 及 UI 升级 ZIP 仍是固定脚本版本；本记录描述其后的真实模型增量，不能把旧版本当成已经接入真实 API。

## 已实现行为

| 范围 | 当前行为 |
|---|---|
| 问候与身份 | 正常回应“你好，请问您是”，不再对所有输入索要订单号。 |
| 多轮对话 | 使用同一会话的前文；能记住虚构称呼、承接“那这笔订单”等指代。 |
| 工具调用 | 模型选择只读查单或补偿资格核实；只查送达情况不打开申请确认卡。 |
| 资格与建单 | 补偿请求必须调用服务端工具。只有页面明确确认才建单；规则与订单事实不由模型改写。 |
| 最新结果 | 每次模型调用注入当前账号的最新申请摘要，审批状态优先于旧聊天；补充与批准、拒绝均可继续追问。 |
| 权限 | 模型只有查单工具；无法通过聊天批准、改券额、发券或查看他人订单。 |
| 故障 | 凭据错误、余额不足、限流、连接失败返回脱敏错误；保留输入，不自动降级成固定脚本。 |
| 配置 | `--model-config` 或 `ORD001_MODEL_CONFIG` 指定仓库外的 JSON；DeepSeek 使用非思考模式，30 秒超时。 |

模型负责对话和调用工具。资格结果、申请确认、状态更新及券额仍由服务端生成；真实对话中出现确定的规则结果文本属于正常设计。当前模型并不具备退款、联系骑手、实际发券或修改配送记录的权限。

## 实际验证

| 验证 | 结果 | 记录 |
|---|---|---|
| 真实 DeepSeek，经独立 HTTP 服务 | 8 项通过、0 失败 | [live-api.json](../../examples/ord001/evidence/2026-11-10-live-model/live-api.json) |
| 真实 Chrome 交互 | 5 项通过、0 失败，errors=[] | [live-browser.json](../../examples/ord001/evidence/2026-11-10-live-model/live-browser.json) |
| 合成服务故障与配置保密，不发外部请求 | 5 项通过、0 失败 | [model-errors.json](../../examples/ord001/evidence/2026-11-10-live-model/model-errors.json) |
| 原流程回归，固定脚本隔离验证 | 12 项通过、0 失败 | [api-regression.json](../../examples/ord001/evidence/2026-11-10-live-model/api-regression.json) |
| 补资料回归，固定脚本隔离验证 | 6 组通过、0 失败 | [followup-regression.json](../../examples/ord001/evidence/2026-11-10-live-model/followup-regression.json) |
| 实际 8024 切换 | 实际调用 DeepSeek；原有 1 张工单、1 条事件逐字段一致 | [main-service.json](../../examples/ord001/evidence/2026-11-10-live-model/main-service.json) |

接口场景覆盖身份问候、上下文、只查不申请、1801 秒资格、确认后建单、越权指令不改变状态、最新补充及批准结果、他人订单不可见、恰好 1800 秒不符合。

浏览器通过真实输入与点击，完成问候、只查订单、承接前文打开确认卡、确认建单、商家拒绝、顾客继续追问同票结果，以及 390px 页面与按需模型说明。没有浏览器异常或页面直接请求外部模型服务。

截图：[问候](../../examples/ord001/evidence/2026-11-10-live-model/live-greeting.png) · [申请确认](../../examples/ord001/evidence/2026-11-10-live-model/live-confirmation.png) · [最终结果](../../examples/ord001/evidence/2026-11-10-live-model/live-result.png) · [手机](../../examples/ord001/evidence/2026-11-10-live-model/live-mobile.png)。

第一轮真实接口实测发现“口头提示确认但未打开确认卡”，修正工具调用约束后完整 8 项通过；原记录保留为 [live-api-attempt1.json](../../examples/ord001/evidence/2026-11-10-live-model/live-api-attempt1.json)。首次浏览器脚本错误地等待“发送按钮恢复可用”，而确认卡打开时发送按钮本应锁定；改为等待处理中状态结束后，5 项通过。原脚本失败记录保留为 [live-browser-attempt1.json](../../examples/ord001/evidence/2026-11-10-live-model/live-browser-attempt1.json)。

## 复跑与运行

完整配置和启动命令见 [运行指南](../../examples/ord001/README.md#接入真实模型)。实际配置必须由运行者提供自己的密钥，仓库仅有 [无密钥模板](../../examples/ord001/model-config.example.json)。

真实接口复跑使用 [ord001_live_check.py](../../examples/ord001/ord001_live_check.py)，要求独立服务及空模拟库，不会重置已有数据。会真实调用提供商、创建和审批模拟申请，运行会产生 API 费用。浏览器专项在接口专项完成后的同一独立库运行；它使用尚未申请的 ORD008，不重置数据：

```bash
npm --prefix examples/ord001/ui-check install
node examples/ord001/ui-check/live.cjs http://127.0.0.1:8027 /tmp/ord001-live-browser
```

错误与保密检查使用 [ord001_model_check.py](../../examples/ord001/ord001_model_check.py)，不发外部请求。

## 边界与待复核项

- 这是单一 DeepSeek 模型的开发验证，不是正式 B/C 模型对照、负载测试或测试组验收。
- 订单、账号、规则和券继续使用课程模拟数据，不能当成真实平台补偿服务。
- 当前登录和聊天检查点在内存；重启须重新选择演示身份。工单与补充记录保存到独立 SQLite。
- 真实模型仍可能误解自然语言。订单权限、资格、确认、审批和券额由服务端强制执行；尚未对所有对话文本进行系统性质量评测。
- 密钥和个人模型账户不能随仓库共享，其他组员需自行配置；Windows 尚未实跑。
- 原任务保持待复核，不替测试组勾选验收项。
