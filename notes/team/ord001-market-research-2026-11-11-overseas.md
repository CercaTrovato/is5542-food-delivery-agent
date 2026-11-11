# 外卖客服调研：海外平台与法规（2026-11-11）

调研时间 2026-11-11，用于 ORD001 补功能。未经组员复核；标「摘要」「第三方」的条目演示前需再核对原页。

标注说明：「摘要」表示页面本身抓不到，事实只来自搜索引擎摘要；「第三方」表示非官方网站。这两类都应视为待核实。Grab、Just Eat 帮助中心和 LegiScan 页面都无法直接抓取，建议演示前在浏览器里打开核对一次。

## 1. 平台对比

**表 1a**

| 维度 | DoorDash | Uber Eats | Grubhub | Deliveroo |
|---|---|---|---|---|
| 入口 | 订单 → Help → 先选大类（Delivery Issues / Order Issues），再选具体问题 [1][2] | 从订单进入对应问题的表单，如 Wrong or missing items [9] | 官方说明未查到 | Order History → 选订单 → Order Help（摘要）[14] |
| 延误处理 | 普通订单：未查到公开的延误补偿规则。Catering 订单：比送达窗口晚 ≥20 分钟可退款，形式和金额由平台决定，须 14 天内联系客服，不自动发放 [3][4] | 比预计时间晚 20 分钟以上，联系客服后"可能"退款或给 Uber credits，须在 48 小时内联系 [6]。Uber One 会员：超过"最晚送达"时间即自动发 Uber Cash（台湾 NT$30，30 天过期）[7]；北美金额不确定（摘要称 $2.50，约 2 小时到账）[8] | Grubhub Guarantee：迟到给 ≥$5 Perks，用于下次订单（2021 年报道）[12]；现行条款页读不到，目前是否仍有效不确定 | 英国条款：比告知的最晚时间晚 15 分钟以上，平台会调查，若属平台原因"可能"补偿，由平台裁量；Priority Delivery 迟到可申领 credit [13]。Diamond 会员规则不确定 |
| 其它售后 | 缺送/错送：请附清晰照片，结果可能是 credit、退款或重送 [2]。未送达：每单都调查 [1] | 缺送/错送须 48 小时内报，照片可选（0–1 张）[9]；默认给 Uber Cash（第三方）[10] | 默认给 credit，可要求原路退（第三方，不确定）[10] | 订单被取消时原路退款，可另加 credit；Freshness Promise 可选原路退款或 credit（3 个月过期）[13] |
| AI 与转人工 | 按屏幕提示"选一个解决方案，或与客服聊天"，聊天和电话 24 小时在线 [1]；客服机器人用 RAG，同时服务顾客和骑手 [5]；AI 身份如何披露未查到 | 页面写明 GenAI 客服助手面向司机；"功能由 GenAI 驱动时会告诉你" [11]；顾客侧的 AI 客服和转人工未查到 | 未查到 | 顾客侧 AI 客服未查到 |
| 进度通知 | 未查到 | Uber One 补偿约 2 小时自动进钱包（摘要，不确定）[8] | 未查到 | 未查到 |
| 评价 | 未查到 | 未查到 | 未查到 | 未查到 |

**表 1b**

| 维度 | Just Eat Takeaway（英国站） | Swiggy | Zomato | Grab（GrabFood） |
|---|---|---|---|---|
| 入口 | 订单 → I'm unhappy with my order → 选原因（摘要）[16] | 官方说明未查到 | App 内 Help → 选原因（第三方）[22] | 订单记录 → 选问题 → 上传照片 → 提交（摘要）[26] |
| 延误处理 | "订单迟到"帮助页只让用户去订单记录里写评价，未提补偿（摘要）[15] | One BLCK（邀请制，2025-01 推出）含 On-Time Guarantee，金额和形式未公开 [17] | Gold 会员的准时保障，对 2023-11-25 起购买或续费的会员取消（摘要）[19] | On-Time Promise 自动发券。新加坡：Priority 订单晚 >30 分钟；马来西亚：Priority 订单晚 >15 分钟给 RM2.5；24 小时内进 Offers（摘要）[23][24]。泰国：晚 16–30 分钟给 15 泰铢，31 分钟以上给 25 泰铢 [25] |
| 其它售后 | 错送须附照片（摘要）[16] | 官方说明未查到。有报道称 Instamart 用户用 AI 改图拿到全额退款，平台未回应 [18] | 常要求照片，退款常进 App 余额（第三方）[22] | 缺送/错送须 24 小时内报并附照片；给券或退款；GrabPay 24 小时内到账，银行卡 2–3 个工作日，最长 30 天（摘要）[26] |
| AI 与转人工 | 未查到 | One BLCK 会员可优先接通资深客服 [17]；AI 客服未查到 | 自研 Nugget：每月 1500 万次对话，平均解决率 85%（2026-01，自报），转人工规则未公开 [20]；2026-08 有报道称关闭海得拉巴客服中心，约 250 人受影响 [21] | LLM 按菜单估算少送部分的退款额；食品安全和质量投诉直接转人工；每月少 3.2 万张人工工单（自报）[27]。AI 身份披露方式未查到 |
| 进度通知 | 未查到 | 未查到 | 未查到 | 补偿券 24 小时内到账（摘要）[23]；退款到账时限见上一行 [26] |
| 评价 | 迟到时引导用户写订单评价 [15] | 未查到 | 未查到 | 可评价餐厅和骑手（摘要）[28]；客服满意度评价未查到 |

## 2. AI 客服实践要点

1. **随时能找到真人。** Klarna 2024 年 2 月称，AI 助手上线首月处理 230 万次对话，占客服聊天的三分之二，满意度与人工持平，解决时间从 11 分钟降到 2 分钟以内 [29]。2025 年 5 月，CEO 承认过于看重成本导致质量下降，开始重新招人工，并说要让客户清楚"想找人时总有人" [30]。
2. **各家"解决率"的算法差别很大。** Intercom Fin 把"用户确认满意"和"用户没再求助就离开"都算作解决。用户要求找人或表现出不满时，Fin 转人工。用户之后回到同一对话继续问，这次解决就作废 [31]。Zendesk 只评估没转人工的对话，并让 LLM 读对话核实是否真的解决。聊天默认在首条消息 2 小时后判定，最长可调到 72 小时（该文适用于 2026-05-18 之前的规则）[32]。Fin 自称平均解决率 76% [33]，Nugget 自称 85% [20]，两者算法不同，不能直接比较。
3. **满意度在关键时刻问。** Fin 在三种时刻发满意度问卷：用户给出正面反馈时、转人工时、用户一段时间没回复时。问卷分 5 档，报表能区分评的是 AI 还是人工 [34]。
4. **企业要为 AI 说错的话负责。** Air Canada 的聊天机器人告诉乘客丧亲优惠票价可以事后申请，实际政策不允许。2024 年 2 月，加拿大不列颠哥伦比亚省的民事仲裁庭判航空公司赔偿，并驳回了"机器人是独立主体"的抗辩 [35]。2026 年 10 月有用户称 DoorDash 机器人先承诺退款、后又说不符合条件，此事未经核实 [36]。DoorDash 给骑手用的语音客服加了防幻觉、防提示注入的护栏，并且不把个人信息交给生成式 AI [37]。
5. **用转人工记录补知识，敏感问题直接交给人。** DoorDash 分析转到人工的对话，用 LLM 起草知识库文章再由人审核，高频问题的转人工率从 78% 降到 43% [5]。Grab 让 LLM 估算退款额，但食品安全投诉立即转人工 [27]。
6. **照片证据可能是 AI 改过的。** 有报道称 Instamart 用户把 1 个裂开的蛋改成二十多个，拿到了全额退款 [18]。

## 3. 法规要点

1. **欧盟 AI 法案第 50 条**：直接与人交互的 AI 系统必须让用户知道对方是 AI，一眼就能看出的情况除外。告知要清楚、易于辨认，最晚在第一次交互时完成。该条自 2026-08-02 起适用（第 113 条）[38]。欧盟委员会称当天开始执法；AI Omnibus 推迟的是高风险规则（推到 2027-12-02），不涉及第 50 条（摘要）[39]。
2. **加州 BOT Act（商业与职业法典 §17941，2019-07-01 起施行）**：在网上用机器人与加州居民交流，故意隐瞒机器人身份来促成交易，属于违法。只要清楚、显眼地披露"这是机器人"，就不承担责任 [40][41]。
3. **加州 AB 578（2026-01-01 起施行）**：外卖平台必须提供清楚显眼、能联系到真人的客服功能。可以先用自动系统，但它解决不了时，用户必须能及时转到真人。订单未送达或送错，平台要全额退款（含税费和小费），除非是顾客自身原因或疑似欺诈。平台还必须提供"退回原支付方式"的选项 [42][43]。
4. **西班牙 Ley 10/2025（2025-12-28 生效，过渡期 12 个月）**：适用于基础公共服务，以及满足任一条件的大企业：员工 ≥250 人、年营业额 >5000 万欧元，或资产负债表总额 >4300 万欧元。规定包括：
   - 自动应答不能是唯一的客服渠道，用户从交互一开始就可随时要求真人；
   - 95% 的转人工请求平均在 3 分钟内接通；
   - 投诉须在 15 个工作日内答复；
   - 每个投诉给一个编号，用户凭编号查进度 [44]。

## 4. 原型差距清单

| 档位 | 缺口 | 依据 | 最小实现建议 |
|---|---|---|---|
| 课程演示必须补 | 转人工 | AB 578 [42][43]；西班牙法 [44]；Klarna [30]；Fin 的转人工触发条件 [31] | 聊天框常驻「转人工」按钮。用户说"人工""投诉"，或同一问题两轮没解决时，AI 主动提示可以转人工。后端建一张 type=handoff 工单，附订单号和 AI 写的 3 行摘要，进审核端现有队列。用户侧显示"已转人工，排队中"。审核员的回复就算人工回复，不接真实坐席 |
| 必须补 | 第一次交互就披露 AI 身份 | AI 法案第 50 条 [38]；BOT Act [40] | 如果目前只在用户问起时才说明，改为：进入咨询页的第一条固定消息写"我是 AI 助手，不是真人，可随时转人工"；每条 AI 消息气泡加「AI」角标，审核员消息标「人工」 |
| 必须补 | 防止 AI 乱承诺 | Air Canada 判例 [35]；DoorDash [36][37] | 用 Python 写 check_eligibility(order)，返回是否符合、金额 10、原因，LLM 只转述这个结果。回复发出前，用正则检查"退款""已到账""保证""赔偿 X 元"等词，金额与工具结果不符就拦下，换成模板话术并记日志。演示时展示一次拦截 |
| 必须补 | 申请编号和站内通知 | 西班牙法要求编号可查进度 [44]；Grab 补偿 24 小时内到账 [23] | 提交时生成编号（如 DC-20261111-001），显示在卡片上，并写明"预计 24 小时内处理"。前端每 10 秒查一次状态，有变化就弹提示，并在「我的订单」上加红点。不发短信或邮件 |
| 必须补 | 结束时的满意度评价 | Fin 的问卷时机与 5 档评分 [34]；Just Eat 引导写评价 [15] | 状态变为已通过或未通过后，卡片底部出现 5 档评分和一句可选留言，同时记录本单由 AI 还是人工处理，存进 SQLite 或 JSON |
| 值得补 | 先选问题类型 | DoorDash、Uber、Grab 都是先选问题再处理 [1][2][9][26] | 点「咨询」后先选：晚到 / 少送错送 / 餐品损坏 / 没收到 / 其他。只有"晚到"走现有流程，其余直接转人工，并说明"演示版只自动处理晚到" |
| 值得补 | 自动发券、主动告知 | Grab、Uber One 达标即自动发券 [7][23] | 加一个开关：已送达、晚 ≥30 分钟且首次申请的订单，用户登录后直接提示"已为你发放 ¥10 券"，不经人工审核；重复申请或数据异常的仍进人工。演示时对比两种模式 |
| 值得补 | 分档金额、申请时限、券有效期 | Grab 泰国按迟到时长分档 [25]；Uber 48 小时时限 [6]，Uber Cash 30 天过期 [7]；DoorDash 14 天 [3] | 规则写成配置：晚 30–44 分钟给 ¥10，45 分钟以上给 ¥15；送达后 48 小时内可申请；券上显示 30 天有效期。全部放进 check_eligibility |
| 值得补 | 申诉和补充照片 | 多数平台处理缺送错送时要照片 [2][16][26]；AI 改图风险 [18] | "未通过"卡片加「申诉」按钮，限 1 次，必须填理由。"待补充"时允许上传 1 张图（≤2MB，存本地），只给审核员看，AI 不判断图片真假 |
| 值得补 | 指标面板 | Fin 把"用户离开"也算解决 [31]；Zendesk 只算未转人工、且经 LLM 核实的对话 [32] | 审核端加一页，显示申请数、通过率、转人工率、平均审核时长、满意度均分。"已解决"只算用户点了"已解决"或评分 ≥4 的；用户直接离开的单独列为"未确认" |
| 超出范围 | 原路退款、真实资金 | AB 578 [42][43] | 不做。说明页写一句"真实平台需支持原路退款"，原型只发模拟券 |
| 超出范围 | 短信、邮件、App 推送 | 无 | 用上面的站内通知代替 |
| 超出范围 | 少送错送的部分退款估价 | Grab 用 LLM 估价 [27] | 不做，这类问题一律转人工 |
| 超出范围 | 图片真伪识别 | AI 改图案例 [18] | 不做，由审核员人工判断 |
| 超出范围 | 联系骑手、实时追踪、语音客服 | DoorDash 语音客服 [37] | 不做，订单页用假数据显示配送时间线 |

## 5. 来源

1. DoorDash Help, I never received my order：https://help.doordash.com/en-us/consumers/article/i-never-received-my-doordash-order
2. DoorDash Help, Missing or incorrect items：https://help.doordash.com/en-us/consumers/article/my-order-was-missing-an-item-incorrect-order
3. DoorDash, Catering On-Time Delivery Terms：https://help.doordash.com/en-us/legal/article/cx-ddfb-terms-and-conditions-catering-on-time-delivery
4. DoorDash 新闻，2026-11-02：https://about.doordash.com/en-us/news/meal-boxes-and-catering
5. DoorDash 工程博客，2025-08-18：https://careersatdoordash.com/blog/doordash-llm-chatbot-knowledge-with-ugc/
6. Uber Help, We want to make it right：https://help.uber.com/ubereats/restaurants/article/we-want-to-make-it-right?nodeId=cf5251d1-1972-4293-af82-553e8ff23b19
7. Uber Help, What is "We'll make it right"（台湾内容）：https://help.uber.com/en-GB/ubereats/restaurants/article/what-is-%E2%80%9Cwe%E2%80%99ll-make-it-right%E2%80%9D?nodeId=816a9d8a-1350-412c-a464-ca0dad48430a
8. Uber Help, Promise in delivery times（fr-CA，摘要，页面返回 404）：https://help.uber.com/fr-CA/ubereats/restaurants/article/what-is-promise-in-delivery-times-in-uber-eats?nodeId=260a3730-057a-4e17-8b88-2990e194897f
9. Uber Help, Wrong or missing items：https://help.uber.com/en/ubereats/stores/article/%E6%84%9F%E8%B0%A2%E6%82%A8%E7%9A%84%E5%8F%8D%E9%A6%88?nodeId=beb06041-6d9c-44de-9ecf-2a9fa80c3bc9
10. canireturn（第三方），2026-03-27：https://canireturn.com/blog/food-delivery-refund-comparison
11. Uber, Generative AI Features at Uber（2025 年更新）：https://www.uber.com/au/en/legal/generative-ai-features-at-uber/
12. Restaurant Dive，2021-07-12（ProQuest 收录）：https://www.proquest.com/docview/2558699184
13. Deliveroo 英国条款（2026-10-06 更新）：https://deliveroo.co.uk/legal
14. Deliveroo FAQ（摘要）：https://deliveroo.co.uk/faq
15. Just Eat, My order was late（摘要）：https://www.just-eat.co.uk/help/article/203133651/my-order-was-late-what-should-i-do
16. Just Eat, There's something wrong with my order（摘要）：https://www.just-eat.co.uk/help/article/203065192/theres-something-wrong-with-my-order-what-should-i-do
17. Swiggy 新闻稿，2025-01-06：https://www.swiggy.com/corporate/press-release/swiggy-launches-one-blck-an-invite-only-premium-membership/
18. Business Today，2025-11-26：https://www.businesstoday.in/latest/trends/story/apply-more-cracks-swiggy-instamart-customer-allegedly-uses-ai-to-secure-refund-for-broken-eggs-503803-2025-11-26
19. Economic Times，2024-01-29（摘要）：https://m.economictimes.com/tech/startups/zomato-tweaks-gold-loyalty-programme/articleshow/107232139.cms
20. MongoDB 博客，2026-03-24：https://www.mongodb.com/company/blog/innovation/zomato-ai-solution-nugget-reduces-support-costs
21. OfficeChai，2026-08-31：https://officechai.com/stories/zomato-to-shut-hyderabad-customer-support-center-with-250-employees-18-months-after-launching-ai-support-agent-nugget/
22. News Karnataka（第三方），2025-12-17：https://newskarnataka.com/business/who-really-pays-when-zomato-or-swiggy-refunds-your-ruined-meal/17122025
23. Grab SG, About On-Time Promise（摘要）：https://help.grab.com/passenger/en-sg/40001229
24. Grab MY, About On-Time Promise（摘要）：https://help.grab.com/passenger/en-my/40001229
25. Grab TH, GrabFood On-Time Promise，2025-10-28：https://www.grab.com/th/blog/grabfood-on-time-promise/
26. Grab SG, Missing or wrong items（摘要）：https://help.grab.com/passenger/en-sg/360002059867-I-have-a-missing-or-incorrect-order
27. Grab 博客，2026-08-14：https://www.grab.com/inside-grab/stories/how-we-taught-llms-to-solve-the-missing-muffins-mystery/
28. Grab SG, Rate your GrabFood experience（摘要）：https://help.grab.com/passenger/en-sg/360026391211
29. Klarna 新闻稿，2024-02-27：https://www.klarna.com/international/press/klarna-ai-assistant-handles-two-thirds-of-customer-service-chats-in-its-first-month/
30. CX Dive，2025-05-09：https://www.customerexperiencedive.com/news/klarna-reinvests-human-talent-customer-service-AI-chatbot/747586/
31. Intercom, Fin AI Agent outcomes（2026-09-23）：https://www.intercom.com/help/en/articles/8205718-fin-ai-agent-outcomes
32. Zendesk, About automated resolutions for AI agents：https://support.zendesk.com/hc/en-us/articles/5352026794010-About-automated-resolutions-for-AI-agents
33. Fin 官网：https://fin.ai/
34. Intercom, Fin AI Agent CSAT（2026-07-21）：https://intercom.help/intercom/en/articles/8368157-analyze-and-report-on-fin-ai-agent-csat
35. CTV News，2024-02-15（Air Canada 案）：https://www.ctvnews.ca/business/article/air-canada-chatbot-decision-a-reminder-of-company-liability-experts/
36. The Cool Down，2026-10-16（未经核实）：https://www.thecooldown.com/green-tech/doordash-chatbot-refund-dispute-customer-support/
37. AWS 案例, DoorDash：https://aws.amazon.com/solutions/case-studies/doordash-bedrock-case-study/
38. EU AI Act 第 50 条：https://artificialintelligenceact.eu/article/50/
39. 欧盟委员会新闻，2026-07-31（加泰罗尼亚语版，摘要）：http://ec.europa.eu/newsroom/comm_rep_es/items/950837/ca
40. 加州 B&P §17941：https://california.public.law/codes/business_and_professions_code_section_17941
41. SB 1001 定稿文本（摘要）：https://legiscan.com/CA/text/SB1001/id/1821729
42. AB 578 定稿文本（摘要）：https://legiscan.com/CA/text/AB578/2025
43. Tasting Table，2026-01-06：https://www.tastingtable.com/2069543/new-california-law-food-delivery-app-refunds-2026/
44. BOE, Ley 10/2025：https://www.boe.es/buscar/act.php?id=BOE-A-2025-26698

