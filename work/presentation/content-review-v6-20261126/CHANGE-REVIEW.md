# v6 修改点｜请本人审核后再上传

基于本人已确认的 v5，保持原 15 页顺序与视觉设计。封面六人姓名／学号、核心评测结果与两段嵌入演示均保留。

| 页码 | 已落实修改 | 依据与边界 |
|---|---|---|
| 2 · Business problem | 增加历史样本：546,364 个非预订单，14.8% 迟到、1.4% 超过10分钟；写明2022-10-17至24、Meituan INFORMS TSL及致谢。 | 原汇总0.1478／0.0141，分别为14.78%／1.41%，按一位百分数舍入。是历史配送延误占比，不是投诉率、2026现状或货币损失。未重新分发原始逐单数据。 |
| 6 · Model selection | 演示选DeepSeek Flash：已有工具接入、较低演示成本；正式比较选GPT-5.6：可用API、原生工具调用和逐请求用量日志，便于可审计的同配置B/C比较。 | 依据既有实现、开发者成本自报及正式请求／返回记录；不添加未做的跨模型优胜、时延或稳定性排名。 |
| 13 · Rollout plan | 保留B14／6／3、C6及9待核的改进事项，增加“影子运行→小范围试点→逐步扩大”及每阶段放量条件。 | 明确是未来建议：政策决定与受影响路径通过后进入只读影子；有限真实订单试点保留人工批准，要求无错赔／重复及人工检查通过；扩大须本地成本价值成立、扣审核返工后仍省时，并有监控／回滚。不是已上线或已承诺的新开发任务。 |
| 15 · Real-name contributions | 用与封面一致的六个实名，LI Binxiong单列baseline规范、评测与PPT整合；其余实现、调研、观察、反馈、录制分别对应真实成员。 | 本人本轮确认：Jacky＝PAN Pan；gaga＝Ko Anderson；A＝WU Yang（本人纠正中文笔误）。没有写互评分数、贡献百分比或虚构全员独立验收。 |

实名表：LI Binxiong—baseline specification/evaluation/slides；LI Zongqian—prototype/B implementation/deployment/demo recordings；PAN Pan—business/guarantees/cost research；LIN Jingkai—earlier observations；WU Yang—trial/QA feedback；Ko Anderson—trial feedback/presentation recording。

## 请查看

- [只看四张修改页（4页PDF）](IS5542-Group24-v6-Changes.pdf)
- [完整15页PDF](IS5542-Group24-Slides-v6.pdf)
- [可编辑PPTX](IS5542-Group24-Slides-v6.pptx)

提交用PPT已另存为 `submission/IS5542-Group24-Slides-v6.pptx`，旧v5未覆盖。请先看这四页，确认修改点后再继续Canvas上传；当前没有上传或正式提交。

现有录像仍是 `IS5542-Group24-Presentation-20261126.mp4`，15:37.583、149.37MB、HEVC/AAC，未剪辑、加速或转换。它展示修改前的v5，新增量化／模型理由／上线计划／实名表不会自动进入已录画面。此前约38秒时长差异和H.264兼容性建议保留，不能因PPT完成就称录像已全部符合。

Canvas登录已恢复。本轮实际打开当前Group Project及空白File Upload表单：视频和slides两个文件、每组一次；表单未显示额外MB或扩展名要求，file input的accept/max/data-max-file-size均为空。只查看后取消空表单，未选文件／填评论／上传／提交。最终提交仍由本人执行，互评保持后置且未写。
