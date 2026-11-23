# 给李宗谦的回复草稿（未代发，未记为已派任务）

这轮资料很有用，先把SOP-Maze、VitaBench和WOWService的链接、版本、能用于哪页PPT整理入库。我们已经用GPT-5.6跑完20题×B/C×3轮，先不再开整套A/B/C，避免增加两天收尾范围。

有几点先对齐：正式BC18里B和C都3次查单且保持10元确认，之前冒烟要单列模型版本；SOP-Maze是整理后的SOP任务，不是原始线上聊天；VitaBench是另一套模拟工具环境；WOWService已经是LLM＋多Agent，不能把自建关键词菜单叫美团／淘宝真实工作流。若以后加A，请叫“菜单／规则型参考客服”，不写平台复刻。

目前更有价值的是根据这轮原始记录修具体问题：B解释拒赔原因时误拦、缺资料／驳回后人工下一步、只查单仍弹申请卡；C称已开启静默提醒但当前只是toast、口头承诺转达服务团队却无动作，以及3元暖心券超出已确认范围。3元功能先等李宾雄决定，不自行扩大补偿政策。修完固定新提交，原120保留，只对受影响问题定向复测，先不用重复跑整套。

如果你愿意继续补外部题，先交4—6条SOP-Maze相关原题的文件名／索引、它测哪项能力、怎样映射到我们订单和规则、哪些规则改了。确认后再决定小规模扩展，不直接出“战胜大厂”的成绩图。

显式链接：

- 本轮完整复核：https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/main/work/eval/gpt56-complete-review-2026-11-23.md
- 四份资料核验：https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/main/work/research/benchmark-source-review-2026-11-23.md
- 原120证据：https://github.com/CercaTrovato/is5542-food-delivery-agent/tree/main/examples/ord001/evidence/gpt56-formal-20261123
- 当前人工边界：https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/main/work/spec/human-review-boundaries.md

## 给组员Agent的边界

输入固定176fbb0与本批复核，先区分原始模型建议、最终回复、确认卡、工单与发放。修改后交分支／新提交、受影响路径、定向复测JSON及残余问题；不能覆盖原120、改失败标签或混入旧DeepSeek样本。外部原题、改编题与自建A单独命名。以上是待本人转发的建议，不代表组员已承诺或接受。
