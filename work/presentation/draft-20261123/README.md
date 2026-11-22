# IS5542 Group 24 可编辑演示初稿

2026-11-23 · DRAFT · 13 页正文＋2 页附录。

成品保存在 Spaces，打开本次交付聊天中的演示文稿卡片即可编辑，并可从查看器导出 PowerPoint `.pptx`。Page 为 `page_f38c3a93a3c88191b00a5db63884cb6d`，原生引用为 `artifact_external_2d3d9a3f-796e-4766-9241-deca7a6a8029`。这是已保存的演示稿，下面的代码与说明是配套源文件。本批没有另外生成本地 `.pptx` 副本。

- [中文逐页说明](slide-guide-zh.md)
- [缺素材清单](missing-materials.md)
- [制作、来源与检查记录](production-notes.md)
- [原生文稿标识与版本](artifact-manifest.json)
- [封面源代码](build-cover.mjs)与[其余页源代码](build-deck.mjs)

业务背景、职责、流程、demo 规则和架构已填。真实录屏、正式 B/C、市场比较、成本／ROI、正式成员信息仍留空或待核。最终 Canvas 条件未新核，不标可提交。

后续编辑优先继续同一个 artifactRef，先回读现有内容。重建时需在新建并连接的 Artifact Session 中调用 buildCover，再以 buildBatch 按 2–4、5–8、9–12、13–15 的小批调用，首批加 removeEmpty:true 以补封面备注。不要把重建流程误用到已有完整稿而重复追加页面。
