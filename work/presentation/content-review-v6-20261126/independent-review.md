# IS5542 Group 24 v6 四页独立风险抽检

日期：2026-11-26。审查者未参与候选撰写；本次仅做指定四项修改的定向抽检，不是全篇独审、真人学习验收或提交批准。

结论：本次样本未发现阻塞问题，可交本人审阅修改点。没有执行应用、联网、模型调用、上传、提交或 Git 写入。正式发布仍须遵从本人决定。

## 冻结对象与实际范围

- 候选：`candidate/IS5542-Group24-Slides-v6.pptx`，SHA-256 `030c150ed98def01e296a728b1857f60779de6435ef06ec57b27db148029f7a3`。
- 源 v5：`source-v5.pptx`，SHA-256 `8aace90a5b4e3870bb000d76474ed80e5af1715d8788ca82c37719de5d2b45d4`。
- 先读 `candidate/slide-text-v6.json` 第 2、6、13、15 页的全部文字及备注，再对照源 v5 `shape-inventory.json`、`candidate/edits.json` 和下列来源。
- 实际查看四张 1600×900 渲染：`render/slide-02.png`、`slide-06.png`、`slide-13.png`、`slide-15.png`。新增文字可读，未见截断、越界、遮挡或错列。
- 独立包级字节比较：仅 `ppt/slides/slide{2,6,13,15}.xml` 及对应四个 notes XML 改变，共 8 个部件；其余部件相同。因此封面成员信息、未改页的核心结果与视频均未被本次编辑改写。此项不等于重新认证封面身份。
- 两个 MP4 的 SHA-256 分别为 `6ed8e2e321b2363e59d5cc69020a4543d074f85cd4c6c7f18393497e76464dda`、`2bcca47c8d72af26e15c858cf79f67eb134760ac8d573d64d0022365defb29f3`，与源包一致；未重新播放视频。

## 四项发现

| 页 | 实际核对与结论 | 问题等级 |
|---|---|---|
| 2 | 本课 `work/data/meituan_lateness_stats.json` 的 `non_prebook.orders=546364`、`share_late_any=0.1478`、`share_late_over_10min=0.0141`，对应 14.78%→14.8%、1.41%→1.4%，舍入正确。日期 17–24 Oct 2022 与数据日期数组一致。页面写 historical sample、delivery-delay shares, not complaint rates；备注进一步排除当前平台整体表现，未写成 2026 年投诉率。致谢逐字保留 `This research was supported by data provided by Meituan.`，与本课 `work/data/README.md` 要求一致。 | 无阻塞 |
| 6 | 正式 `profile.json` 明确 user-selected GPT-5.6、请求 `gpt-5.6-sol`、reasoning none、T=0.35、800 tokens、30 s、0 retries、固定 `176fbb0`、自动批准关闭；与页文及备注一致。`gpt56-results-2026-11-23.md` 记录本人选模、两边统一及配置系统比较边界。开发者脱敏运行说明及其接收记录支持已有 DeepSeek 实现与开发／演示约 CNY 1–5 的自报估算。候选备注明确 reported/developer estimate，未编造选型竞赛、稳定性优胜或跨模型因果结论。 | 无阻塞 |
| 13 | 标题与横幅明确 proposed rollout / future stages；三阶段依次为只读影子建议、保留人工批准的小规模试点、带监控回滚的渐进扩量。各阶段 gate 均写出，备注额外要求验证并获授权的生产接口。没有把 gate 写成已达到或把真订单试点写成已执行。B 的 14+6+3、C 的 6 和 9 pending 与完整处理复核来源一致；9 次额外暖心券仍是政策待决定，没有自行纳入 demo-v1。人工批准没有被取消。 | 无阻塞 |
| 15 | 六实名与本次用户直接确认的映射吻合：PAN Pan=Jacky、Ko Anderson=gaga、WU Yang=A。LI Binxiong／LI Zongqian／LIN Jingkai 分工与指定承接记录一致。源 v5 的 A+gaga 既有反馈拆为两人实名，不声称两人各自独立验收全部结果；没有分数、贡献百分比或互评结论。最新 `notes/recording-intake-20261126.md` 已记录整段录像实际收到，故 recorded presentation 不再是仅将计划写成完成；身份依据仍为用户映射和单人录制安排，审查者未从声音或画面识别人。 | 无阻塞 |

## 第 6、13 页来源核对的具体深度

只读协作副本：`E:/app-data/codex/scratchpad/is5542-recording-intake-20261126/publish-repo/`。

- 读 `examples/ord001/evidence/gpt56-formal-20261123/profile.json` 的配置字段；核 `complete.json` 为 planned/attempts/completed=120、failed=0；目录实有 120 个 trial JSON。
- 轻量核日志结构：`api-events.jsonl` 有 259 个 started、259 个 response 事件，259 个 response 均有嵌套 usage；抽读 `BC01-B-r1.json` 的记录结构含 steps/api_calls。它支持“有可审计日志”，本次未重新逐条评分全部回复。
- 对照 `work/eval/gpt56-results-2026-11-23.md`、`work/eval/gpt56-complete-review-2026-11-23.md` 的既有配置、结果及缺陷分类；未重跑评测。
- 开发成本依据：`E:/app-data/codex/scratchpad/is5542-dev-delivery-20261123/review-repo/work/team-private/final-replies-20261123/developer-runtime-redacted.txt` 及同副本 `work/research/final-replies-intake-2026-11-23.md`。这是开发者估算及既有接收核对，不是独立项目账单认证；候选没有越过该边界。

## 非阻塞观察与未抽范围

- 第 2 页出处／致谢为较小页脚，当前渲染能读；实际播放若缩成小窗口，仍宜口述历史样本边界。无需为此改写核心数字。
- 第 6 页屏幕正文的 low demo cost 在备注中有 developer estimate 限定；讲述时应沿用该限定，不把它说成生产成本或已核账单。
- 三阶段 gate 是项目建议，尚不是经真实业务验证的发布规程；本次候选已明确其未来地位。
- 未抽查其余 11 页的全部文字、来源或视觉；未重算全量模型成本、重评分 120 次、重算美团原始逐单数据；未核外部链接可达性、当前公网应用、Canvas、录像内容质量／时长或正式提交条件。
- 未添加制作／AI 使用声明；本次四页及其备注未见新增该类声明。没有生成互评。

写入范围：仅本报告；未改正式文件、候选、课程元数据或共享看板。

## 第 6 页拟改措辞的定向意见

作者在本次审查中另提出、尚未实施的两行：

> Demo: DeepSeek Flash — low-cost model already integrated with order tools.
>
> Formal: GPT-5.6 Sol — available API with native tool calls and per-request usage logs.

结论：措辞有本地证据支持，可以采用。针对 native tool calls 追加核对同一 `api-events.jsonl`：138 个 started 请求声明 `query_order` 工具；126 个返回原生 `tool_calls` 均为 `query_order`；259 个 response 均有 usage。实际成功运行记录支持 available API，未外推为现时可用性或所有环境可用。开发者运行说明及既有演示支持 DeepSeek 已接入订单工具，low-cost 仅沿用开发／演示估算，notes 应继续保留 reported/developer estimate 和 CNY 1–5 的边界。该句不暗示与其他模型竞赛胜出，较 owner-selected 单独作理由更能解释功能适配。

此项是对拟改文案的证据意见，尚未查看改后新渲染，不把以上冻结哈希冒用为改后版本。改后只需作者核两行最终 fit、备注限定与参数保留；不需因此重开全篇审查或模型试跑。

## 第 6 页定向关闭记录

作者实施上述两行后，本次仅重新核对 S6，并追加记录，未重审其他页。

- 实际对候选 PPTX 计算 SHA-256 为 `837aaae14cb9cc0cfa8a0dc834ac700b045a0a1c3a07a3388d6429b61238ca19`，与作者提交的最终候选哈希一致。此前 `030c150e…` 为旧候选的历史审查绑定，不是最终版。
- 直接读取包内 `ppt/slides/slide6.xml`、`ppt/notesSlides/notesSlide6.xml`，与刷新后的 `candidate/slide-text-v6.json` 一致；两行已准确采用前节认可措辞。
- 备注继续明确 low reported development/demo cost、developer estimate CNY 1–5，以及 owner-selected、B/C identical settings、完整 usage 日志、固定代码、自动批准关闭和 configured-system comparison；仍写明未进行跨模型选型基准。未新增稳定性／竞赛优势或生产低成本断言。
- 参数行未改，仍为 T=0.35、800 output tokens、30 s timeout、no retries、code 176fbb0。
- 实际查看更新后的 `render/slide-06.png`：两行均完整显示，未见截断、遮挡或越界。

关闭结论：S6 定向修改已核清，无剩余阻塞。原报告其余抽检范围与未抽范围保持；本记录不扩大为全篇重新验收或正式提交批准。仍仅写本报告。
