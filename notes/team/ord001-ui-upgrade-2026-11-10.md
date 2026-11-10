# ORD001 客服界面与补充资料

本轮交付包含顾客端、商家工作台、补充资料闭环及开发证据。继续使用模拟订单和 demo-v1；组员复核完成前，任务状态保持**待复核**。

## 网页入口

| 入口 | 本机地址 | 演示身份 |
|---|---|---|
| 顾客 | http://127.0.0.1:8024/ | U001／U002 |
| 商家 | http://127.0.0.1:8024/review | R001 |

安装与启动见 [运行指南](../../examples/ord001/README.md)。两个入口连接同一服务端工单，顾客确认后才建单，商家通过后才记录模拟券。

## 视觉与交互

先完成 [高保真概念图](../../examples/ord001/design/concept.png) 与 [概念源文件](../../examples/ord001/design/concept.html)，再参照概念实现网页。根据使用反馈增加原创、有表情的软玻璃配送袋，保留多彩、通透的界面结构。

| 范围 | 实际用途 |
|---|---|
| 公共界面 | 原创彩色图标与配送袋、浅色和深色主题、响应式布局；字体、图标与插画均不依赖外部服务。 |
| 顾客 | 订单搜索与展开、订单咨询、提交前确认、申请进度、补充说明与结果；通过和拒绝均展示处理说明。 |
| 商家 | 待处理与已处理切换、订单事实、补偿金额、要求补充、通过和拒绝；等待补充期间不能直接审批。 |
| 文案 | 主界面只保留角色任务、订单事实、状态和操作；模型与规则版本收进按需说明，客服回复去掉开发信息和重复解释。 |
| 操作反馈 | 冲突操作锁定、失败保留输入、轮询保留补充草稿与焦点；重置收进演示说明，并使用页面内确认。 |

## 补充资料闭环

1. 商家在待处理申请填写问题，选择要求补充。同一申请进入「待补充」，没有券。
2. 顾客在申请卡看到问题，提交补充说明。原申请回到待审核，订单号、原始延误、规则版本和金额不变。
3. 商家阅读补充后可再次询问、通过或拒绝。多轮问题和回复保存在处理记录中。
4. 同一订单和规则版本仍只有一张申请；重复提交、回复或审批不会重复生效。

后端接口：原审批接口支持 `request_info`；顾客补充为 `POST /api/customer/tickets/{ticket_id}/information`，正文 `{ "text": "补充说明" }`。商家问题限 200 字、顾客补充限 500 字，由服务端核验身份、归属、内容和当前状态。

## 开发验证

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 原 P01–P03、边界与 Studio 参考图，进程内 | 12 项通过、0 项失败 | [JSON](../../examples/ord001/evidence/2026-11-10-product/api-inprocess.json)／[记录](../../examples/ord001/evidence/2026-11-10-product/api-inprocess.md) |
| 补资料专项 | 6 组通过、0 组失败 | [JSON](../../examples/ord001/evidence/2026-11-10-product/followup-results.json) |
| 原 P01–P03、边界与 Studio 参考图，真实 8024 服务 | 12 项通过、0 项失败 | [JSON](../../examples/ord001/evidence/2026-11-10-product/api-live.json)／[记录](../../examples/ord001/evidence/2026-11-10-product/api-live.md) |
| 最终真实浏览器 Chrome | 9 项通过、0 项失败；无浏览器异常或服务端 5xx | [JSON](../../examples/ord001/evidence/2026-11-10-product/browser-results.json) |

专项覆盖问题必填、归属与文本边界、同一申请两轮补充、批准才发券、拒绝无券、并发重试、旧 SQLite 无损迁移，以及待补充／待审核两种状态下重启后继续处理。顾客对不存在与非本人申请得到相同的 404 回复。

浏览器实际操作包含批准与拒绝、取消不建单、订单归属、搜索与展开、说明弹窗、主题保留、补资料草稿／焦点／光标保留及双端完整历史。390px 场景实际完成确认、商家拒绝、顾客同一申请看到结果，保留 1801 秒事实且无券。

截图：[登录](../../examples/ord001/evidence/2026-11-10-product/customer-entry.png) · [确认](../../examples/ord001/evidence/2026-11-10-product/p01-before-confirm.png) · [顾客补充](../../examples/ord001/evidence/2026-11-10-product/customer-information-request.png) · [商家阅读补充](../../examples/ord001/evidence/2026-11-10-product/merchant-information-received.png) · [批准与处理记录](../../examples/ord001/evidence/2026-11-10-product/customer-information-approved.png) · [深色](../../examples/ord001/evidence/2026-11-10-product/customer-dark.png) · [手机确认](../../examples/ord001/evidence/2026-11-10-product/customer-mobile.png) · [手机商家](../../examples/ord001/evidence/2026-11-10-product/review-mobile.png) · [手机结果](../../examples/ord001/evidence/2026-11-10-product/customer-mobile-result.png)。

补资料专项可从仓库根目录复跑：

```bash
export UV_PYTHON_INSTALL_DIR="$HOME/.uv/python"
uv run --no-project --python 3.12 examples/ord001/ord001_followup_check.py --json /tmp/ord001-followup-results.json
```

Windows／PowerShell：

```powershell
uv run --no-project --python 3.12 .\examples\ord001\ord001_followup_check.py --json "$env:TEMP\ord001-followup-results.json"
```

浏览器复跑见 [UI 检查说明](../../examples/ord001/ui-check/README.md)。命令需在独立演示时运行，会清空当前模拟工单与对话。

## 运行与验收边界

工单和补充历史可保存到文件 SQLite；本机运行服务已配置独立模拟库。登录与图检查点仍在内存，重启后需要重新选择演示身份。源码默认不指定 `--db` 时使用内存库。

本轮使用脚本模型、模拟账号、模拟订单和模拟券；真实模型、正式平台政策、生产身份认证及线上部署仍待团队接入。Windows 命令已提供，尚未在 Windows 电脑实跑。原 Studio 参考图仍使用旧判定模块，秒级边界以新网页接入的共享资格判定模块为准。

此前版本的 API 与截图见 [初版交付](ord001-web-delivery-2026-11-10.md)。以上均为开发验证，不代替测试组验收，也不会自动把外部管理检查表改成已通过。
