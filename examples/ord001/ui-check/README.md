# 网页交互复跑

这是开发验证脚本，连接已经运行的本机网页服务，使用 Playwright 操作安装在电脑上的 Google Chrome。它会通过审批入口**多次清空全部模拟工单和对话**，请与手动演示分开运行。无需模型密钥。

先按 [网页运行指南](../README.md) 启动服务。再在另一个终端运行。需要 Node.js、npm 和已安装的 Google Chrome；浏览器检查工具不会随网页服务自动安装。

## Mac / zsh

从仓库根目录执行：

```bash
cd examples/ord001/ui-check
npm install
npm run check -- http://127.0.0.1:8024 /tmp/ord001-ui-check
```

## Windows / PowerShell

从仓库根目录执行：

```powershell
Set-Location .\examples\ord001\ui-check
npm install
npm run check -- http://127.0.0.1:8024 "$env:TEMP\ord001-ui-check"
```

实际运行环境为 Mac + Chrome；Windows 命令尚未实跑。脚本使用 Playwright 的 `chrome` 渠道查找已安装浏览器。如果 Chrome 在非标准位置，在运行前设置 `PLAYWRIGHT_CHROME` 为浏览器可执行文件的完整路径。

脚本保存每项结果、浏览器异常、服务端 5xx 和截图。成功退出码为 0；失败退出码为 1，并保存 `browser-failure.json`。检查包含通过和拒绝、取消不建单、订单归属、申请步骤回显、订单搜索、说明对话框、主题保留，以及客服对话不出现模型名称或规则版本。

补资料检查会从商家要求补充开始，在顾客输入后跨过一次轮询，检查草稿、焦点和光标没有丢失；再由顾客提交、商家查看补充并通过。过程中核对同一申请、原始延误与规则不变，审核通过前没有券。

390px 检查会实际完成一次申请：顾客确认 ORD005、商家拒绝、顾客在同一申请看到说明；核对 30 分 1 秒的原始延误值与无券结果，并保存确认页、商家待处理页和顾客结果页截图。

[本轮开发结果](../evidence/2026-11-10-product/browser-results.json)；[界面升级说明](../../../notes/team/ord001-ui-upgrade-2026-11-10.md)。开发验证不代替组员验收。
