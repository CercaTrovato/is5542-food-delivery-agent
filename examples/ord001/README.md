# ORD001 参考原型

这个原型给 IS5542 Group 24 提供一份可重跑的流程。团队首版框架和补偿政策待定。示例中的规则仅用于对照验收。已送达且超过 30 分钟时，程序拟 ¥10 券，交人工审批。

## 启动 Studio

在仓库根目录打开 PowerShell。需要 Git、uv 和 Python 3.12，首次运行时 uv 会准备依赖。

~~~powershell
Set-Location .\examples\ord001
$env:ORD001_CHAT_MODEL = $null
$env:ORD001_DELIVERED_AT = '18:50'
$env:LANGSMITH_TRACING = 'false'
$env:LANGCHAIN_TRACING_V2 = 'false'
uv run --no-project --python 3.12 --with 'langgraph-cli[inmem]' --with 'langgraph==1.2.19' --with 'langchain==1.4.9' --with 'langchain-openai==1.7.4' langgraph dev --host 127.0.0.1 --port 2024 --no-browser
~~~

启动后打开 [本地 Studio](https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024)，在顶部选 **ord001_compensation**。这条命令用模拟模型走真实的 LangChain 工具分发、Python 计算和 LangGraph 暂停流程。运行样例无需模型 Key。

## 跑一笔 ORD001

在 **Graph → Input** 选择 **View Raw**。替换输入框里的内容，再点 **Submit**。

~~~json
{"messages":[{"role":"user","content":"我的外卖 ORD001 迟到了，可以申请补偿吗？"}]}
~~~

右侧依次显示 model、tools、calculate_delay、review。工具返回预计 18:00、实际 18:50。calculate_delay 得到 50 分钟，review 暂停在待审批。把 **Resume** 上方输入换成 "approve" 或 "reject"，再点 **Resume**。重新点 **New Thread** 可以走另一种审批结果。

测试阈值边界时，先在终端按 **Ctrl+C** 停止服务，把 ORD001_DELIVERED_AT 改为 18:30 或 18:31，再用同一条启动命令重开服务，并在 Studio 新建线程。恰好 30 分钟预期得到 ineligible，31 分钟预期进入 pending。环境变量为空时，示例保留原先的 18:30 边界记录。

如需使用自己的 OpenAI API，在启动服务前把 ORD001_CHAT_MODEL 设为 openai:你有权限的模型 ID，并在当前终端设置 OPENAI_API_KEY。该配置用组员自己的模型凭据，ORD001 的订单数据仍来自本地模拟记录。

## 文件入口

- [完整补偿图](ord001_compensation.py) 将模型、查单、延误判断和人工审批接起来。
- [独立查单图](ord001_langchain.py) 展示模型发起工具调用、工具返回数据、模型生成回复。
- [独立审批图](ord001_graph.py) 保存 ORD001 模拟订单和演示规则。
- [开发交接](../../notes/supervision-report.md) 记录本地验证结果和团队首版验收范围。
