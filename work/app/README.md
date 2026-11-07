# IS5542 外卖客服 Agent（开发准备）

本项目做已送达外卖订单的延误补偿咨询。在模拟环境内查询订单、解释课程自定义政策、生成补偿草稿，由人工审批，再反馈处理状态。τ-bench 零售领域仅作为历史方案和可选外部参照。

截至 2026-11-07，本目录提供 Python 依赖、锁文件与配置样例。已核实 τ-bench 数据目录可用。外卖领域代码、Agent 调用与评测结果待补。业务报告、验收用例和分工见 [开发交接](../../notes/supervision-report.md)。

## 本地环境（Windows PowerShell）

先克隆 τ-bench 并检出下方锁定提交。回到本项目的 work/app 目录运行依赖安装和数据检查。将 `$tauRepo` 改为实际克隆路径。

```powershell
$tauRepo = 'C:/path/to/tau2-bench'
git -C $tauRepo rev-parse HEAD
$env:TAU2_DATA_DIR = Join-Path $tauRepo 'data'
uv sync --locked --python 3.12
uv run --no-sync tau2 check-data
```

锁定提交是 `da0835f6c67baef58bdda18f2a3b037dfb3a1754`。可从 [τ-bench 源仓库](https://github.com/sierra-research/tau2-bench) 获取。现有环境 10 月 31 日记录为 tau2 2.0.0、langgraph 1.2.19、litellm 1.82.6，以 `uv.lock` 为准。

环境和数据目录检查无需模型密钥。实际模型试跑时从 `.env.example` 创建本地 `.env` 并按接入方式配置，凭据保留在本机。首轮验收使用模拟订单，先做订单归属校验、政策判断、草稿、审批与状态回显，再接 B/C 做同案评测。
