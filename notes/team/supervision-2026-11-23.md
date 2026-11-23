# IS5542 A01 总监督进度核对 · 2026-11-23

## 当前进度

- **演示稿**。15 页可编辑视觉稿 v2 已有，11 月 23 日另导出桌面 PPTX。制作会话报告已用 PowerPoint 实开并逐页检查，总监督复核了本地 PPTX 的 15 页结构、归档完整性和哈希。 本地文件名为 **IS5542-Group24-DRAFT-v2.pptx**，SHA-256 为 **a74e365ef9807008277e10ae249f9947a47482f609329ba9bd794a309c00f6c3**。小组仓库的 [Spaces 视觉稿与取材说明](https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/eb26b4595f01a542dc8e8ea2cd80718d5e370c57/work/presentation/redesign-20261123/README.md) 保留现有入口。
- **开发与测试**。[开发 PR #2](https://github.com/CercaTrovato/is5542-food-delivery-agent/pull/2) 当前候选为 29171c8；11 月 22 日新增四笔迭代。11 月 22 日原表有 8 行标为通过或已解决，缺受测提交及完整配置；末次图片提交晚于测试反馈。四项新边界的代码对齐和 9 组定向复测待核。 开发 PR 仍为开放，运行环境与真实模型对照待验。
- **规则**。已确认四项规则：未补偿的已驳回订单，有可核实的新信息或原处理错误才沿原工单人工重审；仅主管 R002 可改额；默认 ¥10 模拟券，改额限 1–20 元整数、不超实付且记录原因；同一订单最多成功补偿一次。 [规则规范与九组定向复测](https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/c666f1d/work/spec/human-review-boundaries.md)。
- **业务素材**。已核 [新规则调研稿与同一版本说明](https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/main/work/research/jacky-business-rules-2026-11-22.md)。五项保障待补官方 URL 或可追溯原文位置；三平台首轮流程材料此前已收，本轮市场流程比较表在已读范围内待收。

## 本周交付顺序

1. 开发交固定提交、可复跑配置、基础工具型客服 B 与两段正常／异常录屏。录屏采用同一规则版本。
2. 测试组用同一候选和配置交 [九组边界复测](https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/c666f1d/work/eval/human-review-boundary-checks.md)，再用相同订单、规则、输入和评分方法对比 B 与规则版 C。附原始结果、耗时和模型用量。
3. 规则调研补五项出处；流程调研交三平台与本系统的比较表、证据与不可比项。总负责人据实补 PPTX、成本／ROI 和最终录像。
4. 录屏、正式 B/C 对照、市场流程比较、成本／ROI、最终 Slides 与正式提交仍待补。已登记 11 月 28 日交录像和 Slides，Canvas 入口、时长及准确时刻待核。 内部两天收尾窗口沿用原安排。

[11 月 22 日试用表核查](https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/main/work/eval/team-retest-2026-11-22.md) · [小组任务与验收](https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/main/notes/team/final-week-tasks-2026-11-21.md)

本次核对课程主会话、PPT 制作会话、已归档主分支与开发分支及本地 PPTX。测试运行、模型结果、线上部署和 Canvas 提交分别等待对应产物或回执。
