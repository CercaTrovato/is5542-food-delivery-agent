# 成本与业务价值：实测用量＋透明情景估算

可以做估算。没有真实人工前后测时，合适的是情景敏感性与盈亏平衡分析；不把它叫真实ROI、置信区间或已节省人手。PPT第12页使用下面的输入类别、条件结果和限制，详细参数可替换。

## 哪些是真实测到的

120次混合题型的C正式对话成本均值约US$0.008740／次，不能直接当完整投诉生命周期成本。本轮已有BC15/16的“查单→顾客确认→人工批准或驳回→再咨询”记录；把原先单列的预置调用也纳入，每条链4次请求，共6条C模拟链路，均值US$0.017668，范围US$0.017092—0.018308。

这是两个预设路径的六条记录，订单和补偿仍为模拟；不是线上客户分布、不是无限轮次上限，也不含人工工作时间。只重算已有日志，没有再调用模型或增加API费用。[逐链用量与价格公式](../research/cost-scenarios-20261123/model.json)。原正式120的统计口径不改，避免重复计费。

## 外部参照与假设

- 外部参照：美国BLS公布的美国客服代表2025年5月时薪中位数US$21.53，2026-11-23回源。它不是中国外卖平台人工成本，也不含完整雇主开销；当前只用美元示例避免暗中混汇率。[官方来源](https://www.bls.gov/ooh/office-and-administrative-support/customer-service-representatives.htm)
- 演示假设：每月1,000条同类处理链；固定增量成本US$100／月，例如运维50＋实施600分12月摊销50。都不是市场调查结论，Jacky有同地区报价后再替换。
- 最关键未知：每条链净节省的人工活跃秒数。已经扣掉人工审批、纠错和返工，可以是负数；不能拿3.254秒模型响应时间当人工节省时间。
- 估算维持同一补偿政策，不擅自引入3元额外赔付；若引入，额外券／赔付成本也须扣除。释放容量不自动等于减少工资支出。

## 可重复的计算

设每月同类链路数N、净人工节省秒数s、时薪W、每链模型成本c、每月固定增量成本F。

$$V_{capacity}=N\frac{s}{3600}W$$

$$V_{net}=V_{capacity}-Nc-F$$

$$s_{break-even}=\frac{(F/N+c)3600}{W}$$

上式使用能力容量的估值，不是已实现的现金利润。

| 假设每链净人工节省 | 每月净容量价值估算（N=1000，F=US$100） |
|---|---|
| 多花15秒（返工） | -US$207.38 |
| 0秒 | -US$117.67 |
| 15秒 | -US$27.96 |
| 30秒 | +US$61.75 |
| 60秒 | +US$241.17 |

在这组明确假设下，需每链净节省约19.7秒才覆盖模型和固定增量成本。只覆盖API费用的门槛更低，但不能把只算API的结果叫项目ROI。人工节省没有实测，所以只能展示“达到什么条件才值得”，不能宣称已经达到。

PPT可写：With an illustrative workload of 1,000 comparable cases per month, a US wage reference of $21.53/hour, and $100/month fixed incremental cost, the system would need to save about 19.7 net human seconds per case to break even. Human time savings have not been measured.

[情景图PNG](../research/cost-scenarios-20261123/scenario.png) · [模型JSON](../research/cost-scenarios-20261123/model.json) · [情景CSV](../research/cost-scenarios-20261123/scenarios.csv)。Jacky优先补目标地区客服薪资／外包报价和可引用的处理时长／运维资料；业务量拿不到就继续保留情景输入，不拿全平台订单量替代客服咨询量。
