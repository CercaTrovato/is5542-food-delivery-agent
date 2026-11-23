# 120次真实模型内部对照原始证据

2026-11-23，本会话按本人明确选择，使用本人既有官方OpenAI API配置，固定请求／返回gpt-5.6-sol；20题×B/C×3轮，共120次，全部完成；模型请求259次（234正式对话、24工单预置、1连通预检）。没有模拟模型替代、自动重试、静默换模型或清空共享库。

每个BCxx-B/C-rx.json包含原始模型响应、工具调用、顾客确认、原始建议、拦截和最终状态。失败也会保留，本批实际失败0。api-events.jsonl保留开始与完成事件，统计时按call_id去重；不是把两行算两次调用。

[执行配置](profile.json) · [冻结题库](frozen-cases.json) · [完成回执](complete.json) · [逐次汇总CSV](analysis/trials.csv) · [统计](analysis/summary.json) · [逐次复核说明](analysis/review-annotations.json) · [评分诊断](analysis/scoring-diagnostic.json) · [PPT指标图](ppt-metrics.png) · [完整报告](../../../../work/eval/gpt56-results-2026-11-23.md)

自动decision_correct_without_guard为B39/60、C60/60，但B包括14次金额提及误报、4次eligible字段歧义，C又存在3元扩展与回退记录不对称；因此不能将此表直接写成模型正确率或危险建议率。120次终态匹配也不等于真人验收、真实赔付或整体正确率。

run-gpt56-eval.py是实际运行的调用器原件，SHA与profile绑定：只在内存注入共同模型参数、保留固定业务源码；另加逐次日志及BC15/16前置状态检查，不改业务分支。源路径／凭据位置为本机常量；在其他机器复跑须配置其本机路径并登记新调用器哈希。仓库不含Key，也不借教学前端的提示词、上下文或自动回退。诊断脚本只调用两次纯函数，没有额外模型请求。
