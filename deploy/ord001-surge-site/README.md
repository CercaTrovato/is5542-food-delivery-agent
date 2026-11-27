# ORD001 · Surge 线上版网页源码 / Live web build

线上地址 / Live demo:
- 顾客端 Customer: https://ord001-group24.surge.sh/
- 商家与专员端 Merchant & specialist console: https://ord001-group24.surge.sh/review

这是部署在 Surge 上的纯静态版本，业务代码基于 `feat/ord001-local-web` 分支的 `176fbb0`（demo-v1 + human-review-v1）。原来由 Python 服务端完成的订单核实、补偿规则、人工审核和审计逻辑，在 `static/cloud-runtime.js` 里以浏览器端运行时实现，数据保存在浏览器 `localStorage`，模型调用直连 DeepSeek（`deepseek-flash`，T=0.35，800 tokens）。

This is the static build deployed on Surge. Business logic follows commit `176fbb0` on `feat/ord001-local-web` (demo-v1 + human-review-v1). Order verification, compensation rules, human review and audit run in the browser via `static/cloud-runtime.js`; state lives in `localStorage`; the model is DeepSeek `deepseek-flash` (T=0.35, 800 tokens).

## 中英双语 / Bilingual UI (2026-11-27)

页面右上角的 **EN / 中文** 按钮可一键切换语言，选择会被记住；也可以直接用 `?lang=en` 或 `?lang=zh` 打开。

The **EN / 中文** button in the top bar switches language with one click (remembered per browser); `?lang=en` / `?lang=zh` also work.

| 文件 File | 作用 Purpose |
|---|---|
| `static/i18n-dict.js` | 中英词典：约 680 条界面原文 + 170 条带变量的模板 / dictionary of ~680 strings + ~170 templates |
| `static/i18n.js` | 切换按钮与实时翻译层：翻译文字和无障碍属性，切回中文时还原原文；对话气泡只做整句精确翻译 / toggle + live translation layer; chat bubbles use whole-sentence matches only |
| `static/cloud-runtime.js` | 英文界面下让模型用英文回复；意图识别（查单、补偿、餐品异物、转人工、复议）和回复安全校验（金额、承诺、退款、虚假完成）新增英文规则 / English replies, English intent detection and English reply guardrails |

业务规则、金额边界和审批流程没有改动 / Business rules, amount limits and approval flow are unchanged.

## 本地运行 / Run locally

```bash
python3 -m http.server 8642
# 打开 http://127.0.0.1:8642/?lang=en
```

## 部署 / Deploy

```bash
surge . ord001-group24.surge.sh
```

## 模型凭证 / Model credentials

公开源码不含内置 API 密钥。未配置密钥时，网页使用已有规则与固定回复，不向模型服务发送请求；演示说明中的对话模式显示为“固定脚本”。如需在自己的本地浏览器会话测试真实模型，可设置 `globalThis.ORD001_DEEPSEEK_API_KEY` 后再发起对话。该值只在当前页面会话中使用，不能写入或提交源码，也不要部署含密钥的静态配置文件。

No API credential is bundled. Without a locally configured session key, existing deterministic replies and rules remain available and no model request is made. For local development, provide your own key through `globalThis.ORD001_DEEPSEEK_API_KEY` in your browser session. Never commit or deploy that value. A browser client cannot keep a shared provider key secret; a shared live-model deployment requires a server-side credential boundary.

原演示凭证应由持有人撤销或轮换；删除源码中的值不能使旧副本失效。线上现有部署与本次无内置凭证源码的发布状态分别核验。

The holder should revoke or rotate the previous demo credential. Removing a value from source does not invalidate old copies. Verify the live deployment separately from the credential-free source release.
