# IS5542 Group 24 视觉改版说明

2026-11-23 · DRAFT v2。按本人“初稿观感差，需要美化、视觉检查和更多流程结构／真实图标／专业图片”的反馈重做。同一份 15 页在线演示稿继续编辑，页 ID 保留；不改变业务方向，不补造测试、比较或 ROI 数字。

## 视觉系统

- 深蓝 `#132432`、暖黄 `#FFBD45` 与浅灰白 `#F7F9FA`；深浅页面交替，图中颜色对应重点与工作环节。
- 标题 Bahnschrift，正文 Calibri。大标题 54 px（约 40.5 pt），正文一般 25–31 px；页码和来源／版本条单独缩小。
- 封面使用一张生成的无商标外卖场景图。真实业务流程、模型架构和数据规则仍用原生对象绘制，图片不冒充应用截图或团队实拍。
- 图标来自 Lucide 官方 SVG；保留原 SVG 与 ISC 许可，并导出同源透明 PNG 嵌入幻灯片。流程节点、连线、文字和结果表可继续编辑。

## 页面设计

| 页 | 新版视觉组织 |
|---|---|
| 01 | 深蓝文字区与外卖场景主视觉，强化项目识别和标题层次。 |
| 02 | 顾客问题、订单事实、人工决策组成一条关系链；标明何处需要信息衔接。 |
| 03 | 三平台按行分开，保障版本用成组节点呈现，适用条件放在同一条阅读线上。 |
| 04 | 模型／可信工具、程序／顾客、人工／真实状态三个职责区，六步原生流程连线。 |
| 05 | 左侧可信字段与用途，右侧强调严格 `> 30 min` 与 `10 yuan` 的课程规则。 |
| 06 | 深色架构图，图标区分模型、工具、规则、状态和人工；框架职责与模型待核项另列。 |
| 07 | 大幅真实录屏位置与右侧五步状态链，避免拿静态界面替代运行证据。 |
| 08 | 左侧重审条件链，右侧录屏位置，下方列主管权限、整数金额与同单一次补偿。 |
| 09 | B／C 分叉和共同执行边界，突出公平控制；计划运行次数仍标为计划。 |
| 10 | 保留两张原生空表：主要指标与定向复测。减少装饰，不画假图表。 |
| 11 | 空比较矩阵与证据条件说明并列，保留四对象和三主题。 |
| 12 | 价值假设链、成本输入空表、可编辑 ROI 分式，明确还没有收益结论。 |
| 13 | 深色路线图，把固定版本、证据制作、价值核验和后续应用分开。 |
| 14 | 原生指标定义表，分开危险建议与实际错误动作，保留证据字段。 |
| 15 | 图标化来源入口与真实交件贡献表；正式姓名／学号仍待确认。 |

中文逐页讲述目的继续参见初稿的 `slide-guide-zh.md`；本页说明本次视觉变化。录屏、正式 B/C、市场比较、成本、官方出处定位及实名的缺口继续保留。

## 图片与图标来源

官方图标：https://lucide.dev/icons/ 。许可：https://github.com/lucide-icons/lucide/blob/main/LICENSE 。取得日期 2026-11-23，原件哈希见 `assets/asset-sources.json`。

主视觉保存为 `assets/delivery-hero.png`，使用内置 ImageGen 生成；没有运行项目的业务模型或评测实验。生成图属于演示的情境素材，不是项目运行或实测证据。最终提示词如下：

> Create a premium editorial photograph for the cover of a university business presentation about an AI assistant handling food-delivery complaints. Wide landscape 3:2 composition. Close view of a neatly folded unbranded kraft paper takeaway bag with sturdy handles, a charcoal insulated courier bag, and a modern smartphone lying face-up but with a completely dark screen, arranged on a clean dark midnight-blue counter in a contemporary restaurant. The objects occupy the right two-thirds, with moody dark negative space on the left. Refined studio-quality side lighting with a warm amber highlight, realistic paper and woven fabric textures, restrained navy, warm white and golden amber palette. Quiet credible business atmosphere, sharply composed photographic detail, no people, no text, no logos, no symbols, no floating UI, no futuristic holograms. This is an illustrative scene, not a screenshot or operational evidence.

## 使用方式

继续使用原 Page `page_f38c3a93a3c88191b00a5db63884cb6d`，在本次交付的演示卡片中编辑或导出 `.pptx`。源码 `redesign.mjs` 用于现有 Artifact Session 的指定页重排，运行时传本目录 `assets` 的实际绝对路径。不要对已经手工修改的稿直接整批重放。

本批不发送群消息或跨会话消息，不更新共享 management 和线上看板，不改工程或运行真实模型。当前仍为 DRAFT，不能把视觉改版记成业务验收、录像完成或正式提交。
