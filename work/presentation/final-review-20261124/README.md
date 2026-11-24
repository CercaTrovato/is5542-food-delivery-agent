# Group 24 最终审稿候选 v3

2026-11-24。当前交付为本地15页REVIEW v3，保留原v2设计与页序。原在线Page仍为v2，请以此处文件审稿。

- [可编辑PPTX（含两段嵌入视频）](IS5542-Group24-REVIEW-v3.pptx)
- [PDF静态预览](IS5542-Group24-REVIEW-v3.pdf)
- [中文逐页完整讲稿](IS5542-Group24-Speaker-Script-ZH-v3.md)
- [来源增量、规则取舍、播放与视觉核验](source-reconciliation.md)
- [版本、哈希与检查记录](manifest.json)

第7页视频21.1秒，第8页30.3秒，均无音轨；PowerPoint放映时点击视频区域播放，录制时须配旁白。PDF仅显示静态画面。正式120次比较使用GPT-5.6，两段开发录屏使用DeepSeek，主稿已分开标识；未采用另一套90次结论。

还需本人核：额外3元政策（C9次继续待核）、正式姓名／学号与贡献措辞、稿件和录制。未提交作业，不声明全部业务或生产能力已验收。Canvas显示11/28 11:59pm，每组一次上传录像＋slides；时区标签、硬性视频上限和互评表见来源记录中的实际范围。

源文件 `build-final.py` 从只读v2改写候选，`add-media.json` 通过OfficeCLI嵌入媒体，`render-final.py` 使用本机PowerPoint渲染。重放需要更新其中本机路径；不要覆盖本人后续编辑的成品。正式PPT、讲稿和证据内容以当前版本为准。

`patch-notes.py`／`patch-notes.json` 为第3页最终来源备注的补丁，实际成品备注同时保存在 `content-and-notes.json`。
