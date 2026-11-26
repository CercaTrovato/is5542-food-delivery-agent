# Group 24 v6 · 四项内容补充，待本人审核

先读 [逐页修改点](CHANGE-REVIEW.md)，再看 [四页修改预览](IS5542-Group24-v6-Changes.pdf)。

- [可编辑PPTX](IS5542-Group24-Slides-v6.pptx)
- [完整PDF](IS5542-Group24-Slides-v6.pdf)
- [独立定向抽检](independent-review.md)
- [版本与检查](manifest.json)

仅第2、6、13、15页及其备注改动。旧v5、两段嵌入演示和完整录像保留。本人审核前没有Canvas上传或提交。

复现编辑：用带lxml的Python执行 `python edit-v6.py --source <保留的v5.pptx> --outdir <库外scratch目录>`；再以PowerPoint导出PDF。内部QA位图保存在本任务scratch；正式预览为矢量PDF，不用上采样冒称新增细节。
