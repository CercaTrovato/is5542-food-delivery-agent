// 24/7 Cloud Serverless Runtime for ORD001 (176fbb0 · demo-v1 + human-review-v1 · MJ & Chubby Joker Edition)
"use strict";
(() => {
  const DEMO_DATA = {
    data_version: "demo-orders-2026-11-10",
    service_date: "2026-11-10",
    customers: [
      { customer_id: "U001", display_name: "模拟顾客 U001" },
      { customer_id: "U002", display_name: "模拟顾客 U002" },
    ],
    reviewers: [
      {
        reviewer_id: "R001",
        display_name: "模拟审批员 R001",
        tenant_id: "M_67REST",
        role: "agent",
        can_handle: true,
        permissions: [
          "ticket_approve", "ticket_reject", "ticket_request_info",
          "ticket_escalate", "ticket_expedite", "ticket_transfer", "ticket_reopen",
          "order_urge", "order_note", "order_ticket", "handoff_close", "handoff_reply",
        ],
      },
      {
        reviewer_id: "R002",
        display_name: "平台食安品控专员 R002",
        tenant_id: "*",
        role: "supervisor",
        can_handle: true,
        permissions: [
          "ticket_approve", "ticket_custom_amount", "ticket_reject", "ticket_request_info",
          "ticket_escalate", "ticket_expedite", "ticket_transfer", "ticket_reopen",
          "order_urge", "order_note", "order_ticket", "handoff_close", "handoff_reply",
        ],
      },
      {
        reviewer_id: "R003",
        display_name: "只读观察员 R003",
        tenant_id: "M_67REST",
        role: "observer",
        can_handle: false,
        permissions: [],
      },
    ],
    orders: [
      {
        order_id: "ORD001", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 58,
        status: "delivered", ordered_at: "17:15", prep_promised_at: "17:30", prep_done_at: "17:48",
        picked_up_at: "17:52", expected_at: "18:00", delivered_at: "18:50", rider_sla_extended_min: 18,
        rider_protection: "出餐顺延 +18m · 晚高峰拥堵免罚保护（骑手 0 扣款）",
        customer_progress_note: "17:48 完成备餐打包，晚高峰商圈路段通行缓慢，于 18:50 送达",
        liability_party: "餐骑混合延误（按比例清分）",
        liability_detail: "T1 出餐晚 18 分钟（商家担责 36% · ¥3.6）+ T2 晚高峰通行晚 32 分钟（平台准时保池承担 64% · ¥6.4）；骑手已触发顺延免罚保护",
        items: ["招牌黑椒厚切牛肉饭 ×1", "港式冻柠茶 ×1"], case: "P01 晚 50 分钟",
      },
      {
        order_id: "ORD002", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 32,
        status: "delivered", ordered_at: "17:22", prep_promised_at: "17:35", prep_done_at: "17:34",
        picked_up_at: "17:38", expected_at: "18:00", delivered_at: "18:10", rider_sla_extended_min: 0,
        rider_protection: "准时保容差保护 · 骑手免责",
        customer_progress_note: "17:34 完成备餐，受晚高峰路口信号灯影响于 18:10 送达（轻度延迟 10 分钟）",
        liability_party: "准时保容差免责区",
        liability_detail: "T1 餐厅提前 1 分钟出餐；晚高峰路口等待轻度延迟 10 分钟，处于 30 分钟准时保容差区内，商家与骑手均免责",
        items: ["脆皮烧肉双拼饭 ×1", "例汤 ×1"], case: "P02 晚 10 分钟",
      },
      {
        order_id: "ORD003", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 45,
        status: "delivered", ordered_at: "17:20", prep_promised_at: "17:35", prep_done_at: "17:35",
        picked_up_at: "17:40", expected_at: "18:00", delivered_at: "18:30", rider_sla_extended_min: 0,
        rider_protection: "临界线免罚保护 · 骑手 0 扣款",
        customer_progress_note: "17:35 按时备餐完成，晚高峰电梯及门禁通行耗时，于 18:30:00 送达",
        liability_party: "临界线免责（可领平台暖心关怀）",
        liability_detail: "T1 餐厅准时出餐；实际 18:30:00 送达（恰好 30 分 00 秒，规则要求严格超过 30 分钟），由平台体验池提供临界安抚支持，商家 0 成本",
        items: ["秘制咖喱滑蛋猪扒饭 ×1", "椒盐鸡翅 ×1"], case: "P02 恰好 30:00",
      },
      {
        order_id: "ORD004", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 27,
        status: "delivered", ordered_at: "17:25", prep_promised_at: "17:38", prep_done_at: "17:37",
        picked_up_at: "17:41", expected_at: "18:00", delivered_at: "18:29:59", rider_sla_extended_min: 0,
        rider_protection: "临界线免罚保护 · 骑手 0 扣款",
        customer_progress_note: "17:37 完成备餐，晚高峰路段拥堵，于 18:29:59 送达",
        liability_party: "临界线免责（可领平台暖心关怀）",
        liability_detail: "T1 餐厅提前 1 分钟出餐；实际 18:29:59 送达（差 2 秒达 30m01s 起赔线），可转平台关怀专席柔性安抚，商家与骑手 0 扣款",
        items: ["黯然销魂叉烧饭 ×1"], case: "边界 29:59",
      },
      {
        order_id: "ORD005", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 39,
        status: "delivered", ordered_at: "17:18", prep_promised_at: "17:32", prep_done_at: "17:31",
        picked_up_at: "17:36", expected_at: "18:00", delivered_at: "18:30:01", rider_sla_extended_min: 0,
        rider_protection: "高峰多单并线保护 · 准时保池兜底免扣骑手",
        customer_progress_note: "17:31 完成备餐打包，受晚高峰配送运力紧张影响，于 18:30:01 送达",
        liability_party: "平台准时保池 100% 承担（商家 0 责任）",
        liability_detail: "T1 餐厅提前 1 分钟出餐（商家承担 ¥0）；配送晚到 30 分 01 秒达标，由平台准时保专项池 100% 承担 ¥10（支持 STP 绿灯免审直赔）",
        items: ["黑松露滑蛋牛肉饭 ×1", "青柠气泡水 ×1"], case: "边界 30:01",
      },
      {
        order_id: "ORD006", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 22,
        status: "delivering", ordered_at: "17:28", prep_promised_at: "17:40", prep_done_at: "17:39",
        picked_up_at: "17:43", expected_at: "18:00", delivered_at: null, rider_distance_m: 380, rider_eta_min: 3,
        rider_sla_extended_min: 0, rider_protection: "正常时效内 · 骑手过路口安全静默保护（禁夺命催单）",
        customer_progress_note: "17:39 已完成备餐交接，目前距收货地约 380m，预计 3 分钟内准时送达",
        liability_party: "正常配送时效内",
        liability_detail: "T1 餐厅提前 1 分钟出餐，当前距顾客 380m（预计 3 分钟内准时抵达），未超时静默守护中",
        items: ["鲜虾云吞面 ×1"], case: "未送达",
      },
      {
        order_id: "ORD007", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 41,
        status: "delivered", ordered_at: "17:19", prep_promised_at: "17:34", prep_done_at: "17:33",
        picked_up_at: "17:39", expected_at: "18:00", delivered_at: null,
        gps_fence_note: "骑手 GPS 已于 17:58 进入收货地 50m 围栏，疑因电梯/地下室弱网导致签收时间帧未回传",
        rider_sla_extended_min: 0, rider_protection: "弱网丢包保护 · 调取电子围栏核验免扣骑手",
        customer_progress_note: "订单已完成交付，因楼宇电梯弱网信号延迟，签收时间戳正在同步核验中",
        liability_party: "弱网签收时间待核验（黄灯人工池）",
        liability_detail: "T1 餐厅提前 1 分钟出餐；骑手 GPS 已进围栏但弱网漏传签收帧，转专员结合轨迹或顾客截图核验",
        items: ["滑蛋虾仁饭 ×1", "港式丝袜奶茶 ×1"], case: "送达时间缺失",
      },
      {
        order_id: "ORD008", customer_id: "U001", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 36,
        status: "delivered", ordered_at: "17:21", prep_promised_at: "17:35", prep_done_at: "17:34",
        picked_up_at: "17:39", expected_at: "18:00", delivered_at: "18:31", rider_sla_extended_min: 0,
        rider_protection: "阵雨路滑安全免罚保护 · 准时保池兜底",
        customer_progress_note: "17:34 完成备餐打包，受晚间阵雨路况减速影响，于 18:31 送达",
        liability_party: "平台准时保池 100% 承担（商家 0 责任）",
        liability_detail: "T1 餐厅提前 1 分钟出餐（商家承担 ¥0）；阵雨路况配送晚到 31 分钟，由平台准时保池 100% 承担 ¥10（支持 STP 绿灯免审直赔，骑手免罚）",
        items: ["蜜汁叉烧滑鸡双拼饭 ×1"], case: "P02 晚 31 分钟",
      },
      {
        order_id: "ORD101", customer_id: "U002", merchant: "67餐厅", tenant_id: "M_67REST", amount_yuan: 66,
        status: "delivered", ordered_at: "17:12", prep_promised_at: "17:28", prep_done_at: "17:45",
        picked_up_at: "17:50", expected_at: "18:00", delivered_at: "18:50", rider_sla_extended_min: 17,
        rider_protection: "出餐顺延 +17m · 晚高峰免罚保护",
        customer_progress_note: "17:45 完成备餐打包，晚高峰路段通行缓慢，于 18:50 送达",
        liability_party: "餐骑混合延误（按比例清分）",
        liability_detail: "T1 出餐晚 17 分钟（商家担责 34% · ¥3.4）+ T2 高峰通行晚 33 分钟（平台准时保池承担 66% · ¥6.6）",
        items: ["招牌鲍汁焖鸡饭 ×1", "脆皮乳鸽 ×1"], case: "P03 他人订单",
      },
    ],
  };

  const POLICY = { version: "demo-v1", threshold_minutes: 30, include_threshold: false, coupon_yuan: 10 };
  const REVIEW_POLICY_VERSION = "human-review-v1";
  const VALID_RECONSIDER_REASONS = new Set(["verifiable_relevant_new_information", "prior_processing_error"]);
  const DS_BASE = "https://api.deepseek.com";
  const DS_MODEL = "deepseek-flash";
  const DS_TOKEN_B64 = "";
  const MASK = "ord001-is5542-cityu-group24";
  const STORE_KEY = "ord001_cloud_state_176fbb0_v1";
  const SESSION_CUST_KEY = "ord001_cloud_customer_id";
  const SESSION_CUST_THREAD_KEY = "ord001_cloud_customer_thread";
  const SESSION_REV_KEY = "ord001_cloud_reviewer_id";
  const MAX_ATTACHMENTS_PER_HANDOFF = 3;

  function decodeToken() {
    const raw = atob(DS_TOKEN_B64);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
      out[i] = raw.charCodeAt(i) ^ MASK.charCodeAt(i % MASK.length);
    }
    return new TextDecoder().decode(out);
  }

  const SYSTEM_PROMPT = (
    "你是「配送关怀」的 AI 智能客服助手 MJ（生成式人工智能，非真人坐席），帮助顾客查询配送进度、理解延误补偿、反馈餐品问题和查看申请进度。" +
    "使用自然、温暖、有同理心的中文，先回应顾客当前的问题和情绪，通常两到四句话即可。" +
    "顾客打招呼、询问你的身份或能力时，直接友好回应，不要索要订单号；明确说明你是 AI 智能客服助手，不要自称真人。" +
    "顾客想找人工或投诉时，告诉顾客点对话框上方的「转人工」即可，不要声称已经转接。" +
    "遇到抱怨或餐品异常（如异物、蟑螂、变质、洒漏、少送），先诚恳致歉并给出具体可执行的处理指引，不说空泛口号，不展示技术术语、内部规则版本或思考过程。" +
    "对外沟通严守司乘友好原则：客观说明备餐与路况进度，严禁拉踩或甩锅骑手。" +
    "只要顾客消息中提到了具体订单号（包括把数字 0 输成字母 o，如 ordoo6、ORD001；支持同时提多个订单对比），都必须调用 query_order 核实对应订单；不得编造订单、配送时间、金额或查询结果。" +
    "单纯查询送达时间、进度、对比或表扬骑手时 purpose 必须是 lookup。" +
    "每当顾客询问某单能否补偿、是否符合条件或要求申请延误补偿时，调用 query_order 且 purpose=compensation，" +
    "即使上一轮已查过同一订单也要调用，由服务端核实资格并打开确认卡；不能只口头判断或让顾客寻找尚未打开的确认按钮。" +
    "已核实的配送事实可直接回答时间、晚到多久、餐品明细等后续追问；具体订单的补偿资格必须交给工具。" +
    "只有顾客在页面明确确认后，服务端才建申请；你不能代替顾客确认。" +
    "补偿资格、建议金额、提交和审批都由服务端执行。待审核或待补充绝不等于已获批准。" +
    "只有申请摘要明确为 approved 且有实际券额时才能说券已发放；不得承诺一定通过。" +
    "不能直接退款、免单、改配送记录、联系骑手或跳过审核；如涉及餐损异物，引导顾客点下方「相册」上传照片凭证或点「转人工」进入食安专席。" +
    "订单与补偿券为课堂演示数据；被问到时如实说明。"
  );

  const SYNTHESIS_PROMPT = (
    "你是「配送关怀」的 AI 智能客服助手 MJ（非真人）。系统刚刚核实了顾客提到的订单，并由确定性规则引擎得出了结论。\n" +
    "请结合对话上下文与核实事实，用自然、温暖、得体的中文直接回复顾客（2～4 句话）：\n" +
    "1. 先针对顾客的具体诉求做出有温度的回应：\n" +
    "   - 若涉及食品安全或餐品异物（如蟑螂、虫子、头发、变质等）：第一时间诚恳致歉，提醒「请立即停止食用并保留餐品与异物原貌拍照取证」，说明「自助通道仅处理配送超时补偿券，食品安全与异物理赔已为您开启人工绿色通道」，引导点击输入框旁「相册」上传照片或点右上角「转人工」由专席优先处理。\n" +
    "   - 若涉及餐品洒漏、包装破损、少送或送错：先致歉，引导点击下方「相册」上传照片凭证或点「转人工」优先处理。\n" +
    "   - 若咨询延误，温和客观说明备餐与高峰路况进度，严禁将矛头指向骑手个人。\n" +
    "2. 必须完整保留【系统规则结论】中的核心事实（预计送达时间、实际送达时间、晚到时长、是否可申请或当前工单状态）。\n" +
    "3. 严禁承诺任何未授权金额、免单、退全款、保证通过或虚假声称已退款/已转接/已提交。"
  );

  const EN_REPLY_DIRECTIVE = (
    "LANGUAGE OVERRIDE: The customer is using the English interface. Write your entire reply in natural, warm, concise English " +
    "(2-4 sentences), even though these instructions, earlier messages and the order data are in Chinese. Keep order IDs, times and ¥ amounts exactly as given. " +
    "Call the buttons \"Human agent\" (转人工), \"Album\" (相册) and \"My orders\" (我的订单). Do not output any Chinese characters."
  );
  function replyInEnglish() {
    return Boolean(window.ORD001_I18N && window.ORD001_I18N.lang === "en");
  }

  const NOT_VERIFIED = "未找到这笔订单，请核对订单号，或从「我的订单」中选择。";
  const CANCELLED = "已取消提交。";
  const GUARDED_REPLY = "抱歉，这一点我不能直接答复或承诺。补偿资格和金额以系统核实、商家审核为准；需要的话可以点上方「转人工」。";
  const STATUS_TEXT = { pending: "待审核", needs_info: "待补充", approved: "已批准", rejected: "已驳回" };
  const DECISION_STATUS = { approve: "approved", reject: "rejected", request_info: "needs_info" };

  const SPECIAL_ISSUE_RE = /蟑螂|虫|异物|头发|变质|馊|发霉|拉肚子|坏了|中毒|洒|漏|少送|缺|送错|包装破|cockroach|insect|\bbugs?\b|worm|\bhairs?\b|foreign (?:object|matter|body)|spoil|rotten|mou?ldy|food poisoning|diarrh|stomach ?ache|spill|leak|missing (?:item|dish|food)|wrong (?:order|item|dish|food)|damaged (?:packag|food)|packag\w* (?:was |is )?(?:broken|damaged|torn)/i;
  const PRAISE_NO_CLAIM_RE = /(?:不是|不用|不要|无需|不需要|不必)(?:要|申请)?(?:申请|赔付?|赔偿|补偿|发券)|辛苦了|表扬|点赞|态度很好|no need (?:to |for )?(?:claim|compensat|a coupon|refund)|(?:don'?t|do not) (?:need|want) (?:any |a )?(?:compensation|coupon|refund)|not (?:asking|looking) for (?:compensation|a coupon|a refund)|thank(?:s| you)[^.!?]{0,40}(?:rider|courier|driver)|(?:great|good) (?:job|service)|well done|compliment|praise/i;
  const PURE_LOOKUP_RE = /送到哪|几点送到|到哪了|查一下进度|查看进度|多少钱|实付|什么菜|订单详情|where(?:'s| is| are)|when will|\btrack|status of|progress|how much did|what did i order|order details|\beta\b/i;
  const FOLLOWUP_ORDER_RE = /为什么|怎么|多久|几分钟|几点|差多少|原因|商家|出餐|骑手|取餐|送达|迟到|晚到|超时|能赔|可以赔|申请|补偿|赔付|赔偿|券|这单|那单|这个订单|进度|到哪|催|什么菜|点了什么|餐品|多少钱|金额|实付|蟑螂|虫|异物|头发|变质|洒|漏|少送|送错|\bwhy\b|\bhow (?:long|much|come)\b|\bwhen\b|minutes?|reason|restaurant|merchant|kitchen|rider|courier|deliver|\blate\b|delay|compensat|claim|coupon|refund|this order|that order|status|progress|where|what did i|\bitems?\b|amount|paid|price|cockroach|insect|hair|spoil|spill|missing|wrong/i;
  const FOLLOWUP_CLAIM_RE = /申请|要赔|赔付|赔偿|补偿券|能赔吗|可以赔吗|compensat|\bclaim|coupon|refund|reimburs/i;
  const SECOND_APPEAL_RE = /二次申请|再次申请|重新申请|继续申请|申请复核|人工复核|复议|申诉|不服驳回|对驳回有疑问|\bappeal|reconsider|re-?review|second (?:request|claim|application)|dispute the|contest the|disagree with the (?:rejection|decision)/i;
  const BARE_HANDOFF_RE = /^\s*(?:转)?人工(?:客服|服务)?[\s!！。.~～]*$|^\s*(?:a\s+)?(?:human(?:\s+agent)?|agent|real person|live agent|customer service)(?:\s+please)?[\s!.]*$/i;
  const EXPLICIT_NO_HANDOFF_RE = /(?:不用|不要|无需|不必|先不|别|不找|不转|不需要)\s*(?:帮我|给我|替我)?\s*(?:转接?|找|联系)?\s*(?:人工|真人|活人|客服|专员)|\b(?:no need (?:for|to)|don'?t (?:need|want)|do not (?:need|want)|never mind)\b[^.!?]{0,20}\b(?:human|agent|real person|transfer)/i;
  const LOCAL_NEGATION_RE = /(?:不是要|并非|不是|不要|不用|无需|不必|先不|不找|不转|不需要|别(?!废话|啰嗦|磨叽|扯))[^，。！？；,.!?;\n]{0,4}$|\b(?:no need(?: (?:for|to))?|don'?t|do not|not|never|without)\b[^,.!?;\n]{0,20}$/i;
  const QUESTION_FORMS = ["能不能", "可不可以", "可以不可以", "是不是", "要不要"];

  const CUSTOMER_INTERNAL_TICKET_KEYS = new Set(["reviewer_id", "tenant_id", "stp_tier", "merchant_bear_yuan", "platform_bear_yuan"]);
  const CUSTOMER_INTERNAL_ORDER_KEYS = new Set(["tenant_id", "liability_party", "liability_detail", "rider_protection", "rider_sla_extended_min", "gps_fence_note"]);

  function httpError(status, message, code = "service_error", extra = null) {
    const err = new Error(message);
    err.status = status;
    err.code = code;
    if (extra && typeof extra === "object") Object.assign(err, extra);
    return err;
  }

  function nowIso() {
    const d = new Date(Date.now() + 8 * 3600 * 1000);
    return d.toISOString().slice(0, 19) + "+08:00";
  }

  function normalizeOrderId(raw) {
    const cleaned = String(raw || "").trim().replace(/[\s\-_#:：]+/g, "").toUpperCase();
    if (cleaned.startsWith("ORD") && cleaned.length > 3) {
      let suffix = cleaned.slice(3).replace(/O/g, "0").replace(/[IL]/g, "1");
      if (/^\d+$/.test(suffix) && suffix.length < 3) suffix = suffix.padStart(3, "0");
      return "ORD" + suffix;
    }
    return cleaned;
  }

  function extractOrderIds(text) {
    const matches = String(text || "").match(/ORD[\s\-_]*[0-9OIL]{1,12}(?![0-9A-Z])/gi);
    if (!matches) return [];
    const seen = [];
    for (const m of matches) {
      const n = normalizeOrderId(m);
      if (!seen.includes(n)) seen.push(n);
    }
    return seen;
  }

  function defaultStore() {
    return {
      tickets: [],
      events: {},
      actionLogs: [],
      handoffs: [],
      goodwills: [],
      chats: {},
      pendingConfirm: {},
      stpAuto: false,
      guardHits: 0,
      auditCount: 1,
      auditLogs: [{ at: nowIso(), event: "genesis", audit_hash: "GENESIS_ORD001" }],
      nextMsgSeq: 1,
      nextActionLogId: 1,
    };
  }

  function loadStore() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return { ...defaultStore(), ...parsed };
      }
    } catch (_) {}
    return defaultStore();
  }

  function recordAudit(store, entry) {
    store.auditCount = (store.auditCount || 1) + 1;
    store.auditLogs = store.auditLogs || [];
    store.auditLogs.push({
      at: nowIso(),
      policy_version: POLICY.version,
      review_policy_version: REVIEW_POLICY_VERSION,
      agent_mode: "C",
      model: `openai:${DS_MODEL}`,
      ...entry,
    });
    if (store.auditLogs.length > 300) store.auditLogs = store.auditLogs.slice(-300);
  }

  function saveStore(store, auditEntry = null) {
    if (auditEntry) recordAudit(store, auditEntry);
    else store.auditCount = (store.auditCount || 1) + 1;
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(store));
    } catch (_) {}
  }

  function parseSec(str) {
    if (!str || typeof str !== "string") return null;
    const parts = str.split(":").map(Number);
    if (parts.length < 2 || parts.some(Number.isNaN)) return null;
    return parts[0] * 3600 + parts[1] * 60 + (parts[2] || 0);
  }

  function delayText(sec) {
    if (sec <= 0) return "没有晚到";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return s ? `晚到 ${m} 分钟 ${s} 秒` : `晚到 ${m} 分钟`;
  }

  function thresholdText() {
    return POLICY.include_threshold ? `晚到 ${POLICY.threshold_minutes} 分钟及以上` : `晚到超过 ${POLICY.threshold_minutes} 分钟`;
  }

  function evaluateOrder(order) {
    if (!order) return { status: "not_found", reason_code: "order_not_found", policy_version: POLICY.version };
    if (!order.status) return { status: "needs_info", reason_code: "missing_delivery_status", policy_version: POLICY.version };
    if (order.status !== "delivered") return { status: "ineligible", reason_code: "not_delivered", policy_version: POLICY.version };
    const exp = parseSec(order.expected_at);
    const del = parseSec(order.delivered_at);
    if (exp === null || del === null) return { status: "needs_info", reason_code: "invalid_delivery_times", policy_version: POLICY.version };
    let lateSeconds = del - exp;
    if (lateSeconds < -12 * 3600) lateSeconds += 86400;
    const lateMinutes = Math.trunc(lateSeconds / 60);
    const thresholdSec = POLICY.threshold_minutes * 60;
    const eligible = POLICY.include_threshold ? lateSeconds >= thresholdSec : lateSeconds > thresholdSec;
    if (eligible) {
      return {
        late_seconds: lateSeconds, late_minutes: lateMinutes, policy_version: POLICY.version,
        status: "pending", reason_code: "eligible_for_review", proposed_coupon_yuan: POLICY.coupon_yuan,
      };
    }
    return {
      late_seconds: lateSeconds, late_minutes: lateMinutes, policy_version: POLICY.version,
      status: "ineligible", reason_code: "delay_below_threshold",
    };
  }

  function computeSubrogation(order) {
    if (!order) return { stp_tier: "NONE", cost_bearer: "none", merchant_bear_yuan: 0, platform_bear_yuan: 0 };
    const dec = evaluateOrder(order);
    const amount = Number(order.amount_yuan || 0);
    const coupon = Number(POLICY.coupon_yuan);
    const marginCap = amount > 0 ? Math.round(Math.max(2, amount * 0.4) * 10) / 10 : coupon;
    const pProm = parseSec(order.prep_promised_at);
    const pDone = parseSec(order.prep_done_at);
    const t1Late = pProm !== null && pDone !== null ? Math.max(0, pDone - pProm) : 0;
    if (dec.status === "needs_info") {
      return {
        stp_tier: "YELLOW_VERIFY",
        stp_note: "弱网签收时间戳待核验 · 建议调取 GPS 电子围栏或顾客截图确认",
        cost_bearer: "platform_pool",
        merchant_bear_yuan: 0, platform_bear_yuan: 0, goodwill_care_yuan: 0, margin_cap_yuan: marginCap,
      };
    }
    if (dec.status !== "pending") {
      const rawGw = Math.round(Math.min(3, marginCap) * 10) / 10;
      const gw = typeof dec.late_seconds === "number" && dec.late_seconds >= 900 && dec.late_seconds <= POLICY.threshold_minutes * 60 ? rawGw : 0;
      return {
        stp_tier: gw ? "CARE_GOODWILL" : "INELIGIBLE_EXEMPT",
        stp_note: gw
          ? `临界延迟柔性关怀区：主规则免责（商家 ¥0 承担），平台体验金可提供 ¥${gw} 暖心安抚`
          : "准时保容差免责区：商家与骑手均 0 责任",
        cost_bearer: gw ? "platform_pool" : "none",
        merchant_bear_yuan: 0, platform_bear_yuan: gw, goodwill_care_yuan: gw, margin_cap_yuan: marginCap,
      };
    }
    const effectiveCoupon = Math.round(Math.min(coupon, marginCap) * 10) / 10;
    if (t1Late <= 0) {
      return {
        stp_tier: "STP_L1_GREEN",
        stp_note: `绿灯直通级：餐厅准时/提前出餐，纯运力延误，平台准时保池 100% 出资 ¥${effectiveCoupon}（本店 ¥0 承担）`,
        cost_bearer: "platform_pool",
        merchant_bear_yuan: 0, platform_bear_yuan: effectiveCoupon, effective_coupon_yuan: effectiveCoupon,
        goodwill_care_yuan: 0, margin_cap_yuan: marginCap,
      };
    }
    const ratio = Math.min(1, t1Late / Math.max(1, dec.late_seconds));
    const mShare = Math.round(Math.min(effectiveCoupon * ratio, marginCap) * 10) / 10;
    const pShare = Math.round(Math.max(0, effectiveCoupon - mShare) * 10) / 10;
    return {
      stp_tier: "STP_L2_SHARED",
      stp_note: `餐骑共担清分级：出餐晚 ${Math.round(t1Late / 60)} 分钟（本店承担 ¥${mShare}） + 运力通行延误（平台准时保池承担 ¥${pShare}）`,
      cost_bearer: "shared_subrogation",
      merchant_bear_yuan: mShare, platform_bear_yuan: pShare, effective_coupon_yuan: effectiveCoupon,
      goodwill_care_yuan: 0, margin_cap_yuan: marginCap,
    };
  }

  function confirmText(claim) {
    return `实在抱歉让您久等了！经核实，${claim.order_id} ${delayText(claim.late_seconds)}。可申请 ¥${claim.proposed_coupon_yuan} 无门槛补偿券，确认后提交审核。`;
  }

  function outcomeText(order, decision) {
    if (decision.reason_code === "delay_below_threshold") {
      const lateSec = decision.late_seconds || 0;
      const core = `非常抱歉让您久等了！经核实，${order.order_id} 预计 ${order.expected_at}，实际 ${order.delivered_at}，${delayText(lateSec)}。需${thresholdText()}才能申请。`;
      if (lateSec >= 900) {
        return core + "距离起赔线仅差一点，您可在右侧进度卡一键秒领 ¥3 准时保暖心券，或点上方「转人工」跟进安抚。";
      }
      return core + "感谢您在高峰期的理解与体谅。";
    }
    if (decision.reason_code === "not_delivered") {
      return `订单 ${order.order_id} 正在正常时效内为您加急配送，尚未送达；系统已自动开启准时保静默守护，送达后若达到晚到条件可立即申请补偿。`;
    }
    return `非常抱歉！订单 ${order.order_id} 已完成交付，因楼宇弱网暂缺签收时间记录，无法自动核算延误；可点下方「相册」上传截图或点上方「转人工」结合电子围栏轨迹为您核实。`;
  }

  function ticketText(ticket, created) {
    if (created && ticket.status === "approved") {
      return `申请 ${ticket.ticket_id} 已通过准时保直通审核，¥${ticket.coupon_issued_yuan} 补偿券已发放。`;
    }
    const head = created
      ? `申请 ${ticket.ticket_id} 已提交，待审核。`
      : `订单 ${ticket.order_id} 的申请 ${ticket.ticket_id}：${STATUS_TEXT[ticket.status]}。`;
    if (ticket.status === "needs_info" && ticket.information_request) return head + `请补充：${ticket.information_request}`;
    if (ticket.status === "approved") return head + `¥${ticket.coupon_issued_yuan} 补偿券已发放。`;
    if (ticket.status === "rejected") {
      const reasonStr = ticket.review_note ? `原因：${ticket.review_note}。` : "";
      return head + reasonStr + "原申请保留「已驳回」；如需继续沟通此订单，可通过人工客服入口继续咨询。";
    }
    return head;
  }

  function wantsPerson(text) {
    if (BARE_HANDOFF_RE.test(text)) return true;
    if (EXPLICIT_NO_HANDOFF_RE.test(text)) return false;
    const re = /转人工|人工客服|找人工|要人工|人工服务|真人客服|活人客服|找真人|找活人|转真人|要真人|投诉|human agent|\bhuman\b|real person|live (?:agent|person|chat)|representative|customer service agent|\bcomplain|(?:speak|talk) (?:to|with) (?:a |the |your )?(?:manager|person|someone|staff)/gi;
    let match;
    while ((match = re.exec(text)) !== null) {
      let before = text.slice(Math.max(0, match.index - (/[a-z]/i.test(match[0]) ? 30 : 8)), match.index);
      for (const q of QUESTION_FORMS) before = before.replace(q, "");
      if (!LOCAL_NEGATION_RE.test(before.trim())) return true;
    }
    return false;
  }

  function wantsHumanOrSecondAppeal(text) {
    if (wantsPerson(text)) return true;
    return Boolean(SECOND_APPEAL_RE.test(text) && !EXPLICIT_NO_HANDOFF_RE.test(text));
  }

  const CN_DIGIT_MAP = {
    "零": 0, "〇": 0, "一": 1, "壹": 1, "二": 2, "贰": 2, "两": 2, "三": 3, "叁": 3,
    "四": 4, "肆": 4, "五": 5, "伍": 5, "六": 6, "陆": 6, "七": 7, "柒": 7, "八": 8, "捌": 8, "九": 9, "玖": 9,
  };
  const CN_UNIT_MAP = { "十": 10, "拾": 10, "百": 100, "佰": 100, "千": 1000, "仟": 1000, "万": 10000 };

  function cnToInt(token) {
    let total = 0, section = 0, num = 0, hasAny = false;
    for (const ch of token) {
      if (ch in CN_DIGIT_MAP) { num = CN_DIGIT_MAP[ch]; hasAny = true; }
      else if (ch in CN_UNIT_MAP) {
        const unit = CN_UNIT_MAP[ch];
        hasAny = true;
        if (unit === 10000) { section = (section + (num || 1)) * unit; total += section; section = 0; }
        else section += (num ? num : 1) * unit;
        num = 0;
      }
    }
    const res = total + section + num;
    return hasAny && res > 0 ? res : null;
  }

  function normalizeFinancialText(text) {
    return String(text || "").replace(
      /([零〇一壹二贰两三叁四肆五伍六陆七柒八捌九玖十拾百佰千仟万]+)\s*(?:元|块|蚊|港币|港元|大洋|现金|红包|无门槛券|补偿券|代金券)/g,
      (full, g1) => {
        const val = cnToInt(g1);
        return val === null ? full : `${val}${full.slice(g1.length)}`;
      }
    );
  }

  function replyRisk(text, allowedAmounts, statuses, orderPrices = new Set()) {
    const scanned = normalizeFinancialText(text);
    const safeNeg = /(?:不能|不会|无法|不可|未曾|尚未|没有|并非|切勿|不要|不予|不支持|没法|无权|没权限|不代表|不等于)[^，。！？；,.!?;\n]{0,16}$/;
    const priceCtx = /(?:实付|实付金额|订单金额|消费|总价|原价|支付了?)\s*[：:为是]?\s*[\*_`~「『"']*$/;
    const isNeg = (idx) => safeNeg.test(scanned.slice(Math.max(0, idx - 20), idx));
    const amtRe = /(?:[¥￥]|HK\$|RMB|CNY)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:元|块|蚊|港币|港元|RMB|CNY|大洋|现金红包|现金|红包|无门槛券|补偿券|代金券)|(?:赔偿|赔付|退还|发券|发放|赠送)\s*(\d+(?:\.\d+)?)/gi;
    let m;
    while ((m = amtRe.exec(scanned)) !== null) {
      const val = parseFloat(m[1] || m[2] || m[3]);
      if (allowedAmounts.has(val) || isNeg(m.index)) continue;
      if (orderPrices.has(val) && priceCtx.test(scanned.slice(Math.max(0, m.index - 16), m.index))) continue;
      return "amount";
    }
    const guarRe = /(?:保证|一定|肯定|必定|必然|百分之?百|100\s*%|包您|绝对)[^，。！？；,.!?;\n]{0,16}?(?:通过|批准|到账|发放|发券|赔|退款|退钱|拿到|领到|获得)/g;
    while ((m = guarRe.exec(scanned)) !== null) if (!isNeg(m.index)) return "promise";
    const refRe = /(?:帮|为|给|替)(?:您|你)(?:办理|申请|安排)?(?:全额|部分|原路)?(?:退(?:款|钱|单|全款)|免单|打款)|(?:会|可以|能|马上|立即|立刻|直接)(?:为您|给您|帮您|为你|给你|帮你)?(?:办理)?(?:全额|部分|原路)?(?:退(?:款|钱|单|全款)|免单|打款)|(?:直接|全额|给您|为您)免单|退[一壹1]赔[一二两贰三叁四肆五伍六陆七柒八捌九玖十拾百佰0-9]+|免除[^，。！？\n]{0,8}费用|全额返还|马上打款|直接退全款/g;
    while ((m = refRe.exec(scanned)) !== null) if (!isNeg(m.index)) return "refund";
    const doneRe = /已(?:经)?(?:为您|为你|给您|给你|帮您|帮你)?(?:成功|优先|自动)?(?:审核|审批)?(退款|退钱|退全款|免单|打款|赔付|赔偿|补偿|发放|发券|到账|批准|通过|提交|申请|转接|转人工|转给)/g;
    while ((m = doneRe.exec(scanned)) !== null) {
      if (isNeg(m.index)) continue;
      const w = m[1];
      if (w === "提交" || w === "申请") { if (!statuses.size) return "claim"; }
      else if (["退款", "退钱", "退全款", "免单", "打款", "转接", "转人工", "转给"].includes(w) || !statuses.has("approved")) return "claim";
    }
    return englishReplyRisk(scanned, allowedAmounts, statuses, orderPrices);
  }

  function englishReplyRisk(text, allowedAmounts, statuses, orderPrices) {
    const en = String(text || "").toLowerCase();
    if (!/[a-z]/.test(en)) return null;
    const isNeg = (idx) => /\b(?:not|never|cannot|can't|won't|unable|without|don't|doesn't|isn't|aren't|no longer)\b[^.!?;\n]{0,28}$/.test(en.slice(Math.max(0, idx - 36), idx));
    const priceCtx = /(?:paid|total|price|amount|cost|order value|you spent)[^.!?;\n]{0,12}$/;
    let m;
    const amtRe = /(\d+(?:\.\d+)?)\s*(?:yuan|rmb|cny|hkd|dollars?|bucks)\b|(?:compensat(?:e|ion)(?: of)?|refund(?: of)?|reimburse(?:ment of)?|pay you|give you|issue you|credit you with)\s+(?:a\s+)?(?:¥|\$|hk\$|rmb\s*|cny\s*)?\s*(\d+(?:\.\d+)?)/g;
    while ((m = amtRe.exec(en)) !== null) {
      const val = parseFloat(m[1] || m[2]);
      if (allowedAmounts.has(val) || isNeg(m.index)) continue;
      if (orderPrices.has(val) && priceCtx.test(en.slice(Math.max(0, m.index - 24), m.index))) continue;
      return "amount";
    }
    const guarRe = /\b(?:guarantee[ds]?|definitely|certainly|100\s*%|for sure|absolutely|i promise|we promise)\b[^.!?;\n]{0,30}?\b(?:approv|refund|paid|pay|receive|get|issued?|credit|compensat)/g;
    while ((m = guarRe.exec(en)) !== null) if (!isNeg(m.index)) return "promise";
    const refRe = /\b(?:i|we)(?:'ll| will| can| am going to| are going to| shall)\s+(?:\w+\s+){0,2}?(?:refund|waive|reimburse)|\bfull refund\b|\bfree of charge\b|\bwaive (?:the|your) (?:order|bill|fee|charge)/g;
    while ((m = refRe.exec(en)) !== null) if (!isNeg(m.index)) return "refund";
    const doneRe = /\b(?:have|'ve|has)\s+(?:already\s+)?(?:been\s+)?(?:successfully\s+)?(refunded|approved|issued|credited|submitted|transferred|escalated|compensated)\b/g;
    while ((m = doneRe.exec(en)) !== null) {
      if (isNeg(m.index)) continue;
      const w = m[1];
      if (w === "submitted") { if (!statuses.size) return "claim"; }
      else if (["refunded", "transferred", "escalated"].includes(w) || !statuses.has("approved")) return "claim";
    }
    return null;
  }

  function lookupOrder(orderId) {
    const norm = normalizeOrderId(orderId);
    return DEMO_DATA.orders.find((o) => o.order_id === norm) || null;
  }

  function lookupForCustomer(orderId, customerId) {
    const norm = normalizeOrderId(orderId);
    const order = lookupOrder(norm);
    if (!order) return ["not_found", null];
    if (!customerId || order.customer_id !== customerId) return ["unauthorized", null];
    return ["found", { ...order }];
  }

  function customerOrderCopy(order) {
    const clean = {};
    for (const [k, v] of Object.entries(order)) {
      if (!CUSTOMER_INTERNAL_ORDER_KEYS.has(k)) clean[k] = v;
    }
    return clean;
  }

  function customerTicketCopy(ticket) {
    const clean = {};
    for (const [k, v] of Object.entries(ticket)) {
      if (!CUSTOMER_INTERNAL_TICKET_KEYS.has(k)) clean[k] = v;
    }
    return clean;
  }

  function compensatedForOrder(store, orderId) {
    return store.tickets.find((t) => t.order_id === orderId && t.status === "approved" && t.coupon_issued_yuan != null) || null;
  }

  function findTicketForOrder(store, orderId, policyVersion = POLICY.version) {
    const comp = compensatedForOrder(store, orderId);
    if (comp) return comp;
    if (policyVersion) {
      const exact = store.tickets.find((t) => t.order_id === orderId && t.policy_version === policyVersion);
      if (exact) return exact;
    }
    const matches = store.tickets.filter((t) => t.order_id === orderId);
    return matches.length ? matches[matches.length - 1] : null;
  }

  function reviewerTenant(reviewerId) {
    const rev = DEMO_DATA.reviewers.find((r) => r.reviewer_id === reviewerId);
    return (rev && rev.tenant_id) || "M_67REST";
  }

  function assertTenantAccess(reviewerId, resourceTenant) {
    if (!reviewerId) return;
    const revTenant = reviewerTenant(reviewerId);
    const target = resourceTenant || "M_67REST";
    if (revTenant !== "*" && revTenant !== target) {
      throw httpError(403, "无权访问或操作其他商户租户的工单数据。", "cross_tenant_forbidden");
    }
  }

  function assertActionPermission(reviewerId, permission = null) {
    const rev = DEMO_DATA.reviewers.find((r) => r.reviewer_id === reviewerId);
    if (!rev) throw httpError(403, "当前身份没有处理权限。", "not_a_reviewer");
    if (rev.can_handle === false || rev.role === "observer") {
      throw httpError(403, "当前坐席角色为只读观察权限，无权执行业务处理操作。", "permission_denied");
    }
    if (permission && Array.isArray(rev.permissions) && !rev.permissions.includes(permission)) {
      throw httpError(403, `当前坐席角色缺少 ${permission} 操作权限。`, "permission_denied");
    }
    return rev;
  }

  function logAction(store, entry) {
    const item = {
      log_id: store.nextActionLogId || 1,
      at: entry.at || nowIso(),
      handoff_id: entry.handoff_id || null,
      order_id: entry.order_id || null,
      ticket_id: entry.ticket_id || null,
      actor_id: entry.actor_id,
      actor_name: entry.actor_name || entry.actor_id,
      actor_role: entry.actor_role || "agent",
      action: entry.action,
      action_label: entry.action_label,
      before_status: entry.before_status ?? null,
      after_status: entry.after_status ?? null,
      before_amount_yuan: entry.before_amount_yuan ?? null,
      amount_yuan: entry.amount_yuan ?? null,
      reason_type: entry.reason_type || null,
      issue_result: entry.issue_result || null,
      note: entry.note || null,
      is_internal: Boolean(entry.is_internal),
    };
    store.nextActionLogId = item.log_id + 1;
    store.actionLogs = store.actionLogs || [];
    store.actionLogs.push(item);
    return item;
  }

  function getActionLogs(store, { handoff_id = null, ticket_id = null, include_internal = true } = {}) {
    return (store.actionLogs || []).filter((r) => {
      if (!include_internal && r.is_internal) return false;
      if (handoff_id && ticket_id) return r.handoff_id === handoff_id || r.ticket_id === ticket_id;
      if (handoff_id) return r.handoff_id === handoff_id;
      if (ticket_id) return r.ticket_id === ticket_id;
      return true;
    });
  }

  function pushTicketEvent(store, ticketId, evt) {
    store.events = store.events || {};
    store.events[ticketId] = store.events[ticketId] || [];
    store.events[ticketId].push({ at: nowIso(), ...evt });
  }

  function enrichReviewTicket(store, ticket) {
    const order = lookupOrder(ticket.order_id) || {};
    const sub = computeSubrogation(order);
    const extra = {};
    for (const k of ["amount_yuan", "ordered_at", "prep_promised_at", "prep_done_at", "picked_up_at", "liability_party", "liability_detail", "rider_protection", "gps_fence_note", "items"]) {
      if (k in order) extra[k] = order[k];
    }
    const orderFiles = [];
    for (const h of store.handoffs || []) {
      if (h.order_id === ticket.order_id && h.customer_id === ticket.customer_id && Array.isArray(h.attachments)) {
        orderFiles.push(...h.attachments);
      }
    }
    const cleanTicket = {};
    for (const [k, v] of Object.entries(ticket)) {
      if (["stp_tier", "merchant_bear_yuan", "platform_bear_yuan", "tenant_id"].includes(k) && v == null) continue;
      cleanTicket[k] = v;
    }
    return { ...extra, ...sub, order_attachments: orderFiles, ...cleanTicket };
  }

  function handoffCustomerCopy(handoff, threadId) {
    const sameThread = !threadId || !handoff.thread_id || handoff.thread_id === threadId;
    const baseAfter = sameThread ? (handoff.after_index ?? 0) : 0;
    const repAfter = sameThread && handoff.reply_after_index != null ? handoff.reply_after_index : baseAfter;
    const attachments = (handoff.attachments || []).map((a) => ({ ...a }));
    const openAttachments = attachments.filter((a) => !a.is_followup);
    const followupAtts = attachments.filter((a) => a.is_followup);
    const followupsRaw = handoff.followups || [];
    const replySeq = handoff.reply_seq;
    const msgIds = new Set(followupsRaw.map((f) => f.message_id).filter(Boolean));
    const byMsg = new Map();
    const looseAtts = [];
    for (const att of followupAtts) {
      if (att.followup_seq && msgIds.has(att.followup_seq)) {
        if (!byMsg.has(att.followup_seq)) byMsg.set(att.followup_seq, []);
        byMsg.get(att.followup_seq).push(att);
      } else {
        looseAtts.push(att);
      }
    }

    const events = [{ kind: "open", after: baseAfter, at: handoff.created_at }];
    const emitFollowup = (f, defaultAfter) => {
      const fAfter = sameThread ? (f.after_index != null ? f.after_index : defaultAfter) : 0;
      events.push({
        kind: "message",
        role: f.sender_role === "customer" ? "customer" : (f.sender_role === "system" ? "system" : "human"),
        text: f.text,
        after: fAfter,
        at: f.created_at,
      });
      const linked = byMsg.get(f.message_id || -1);
      if (linked && linked.length) {
        events.push({ kind: "attachment", attachments: linked, after: fAfter, at: linked[linked.length - 1].created_at });
      }
    };

    if (handoff.status === "replied" && handoff.reply_text) {
      const preF = followupsRaw.filter((f) =>
        (replySeq != null && (f.message_id || 0) <= replySeq) ||
        (replySeq == null && f.created_at < (handoff.closed_at || ""))
      );
      const preSet = new Set(preF);
      const postF = followupsRaw.filter((f) => !preSet.has(f));
      for (const f of preF) emitFollowup(f, baseAfter);
      events.push({
        kind: "message",
        role: "human",
        text: handoff.reply_text,
        after: repAfter,
        at: handoff.closed_at || handoff.created_at,
      });
      for (const f of postF) emitFollowup(f, repAfter);
    } else {
      for (const f of followupsRaw) emitFollowup(f, baseAfter);
    }

    for (const att of looseAtts) {
      const aAfter = sameThread && att.after_index != null ? att.after_index : (handoff.status === "replied" ? repAfter : baseAfter);
      events.push({ kind: "attachment", attachments: [att], after: aAfter, at: att.created_at });
    }

    const res = {
      handoff_id: handoff.handoff_id,
      order_id: handoff.order_id || null,
      status: handoff.status,
      request_text: handoff.request_text || null,
      reply_text: handoff.reply_text || null,
      created_at: handoff.created_at,
      closed_at: handoff.closed_at || null,
      ended_at: handoff.ended_at || null,
      attachments,
      open_attachments: openAttachments,
      after: baseAfter,
      events,
    };
    if (followupsRaw.length) {
      res.followups = followupsRaw.map((f) => ({
        sender_role: f.sender_role,
        sender_id: f.sender_id,
        text: f.text,
        created_at: f.created_at,
      }));
    }
    return res;
  }

  function reviewHandoffItem(store, handoff) {
    const oid = handoff.order_id || "";
    const order = oid ? lookupOrder(oid) : null;
    const relTicket = oid ? findTicketForOrder(store, oid, POLICY.version) : null;
    const excerpt = handoff.excerpt || [];
    const followups = handoff.followups || [];
    let initialAppeal = handoff.initial_appeal || null;
    if (!initialAppeal) {
      const firstCust = excerpt.find((x) => x.role === "customer" && x.text);
      initialAppeal = (firstCust && firstCust.text) || handoff.request_text || null;
    }
    const needsSpecialistReply = Boolean(
      handoff.status === "replied" &&
      !handoff.ended_at &&
      followups.length &&
      followups[followups.length - 1].sender_role === "customer"
    );
    const fullTxt = `${handoff.request_text || ""} ${initialAppeal || ""} ${excerpt.map((x) => x.text || "").join(" ")} ${followups.map((f) => f.text || "").join(" ")}`;
    const isP0 = SPECIAL_ISSUE_RE.test(fullTxt);
    const priority = isP0 ? "P0_FOOD_SAFETY" : ((handoff.attachments && handoff.attachments.length) ? "P1_EVIDENCE" : "NORMAL");

    const out = {
      ...handoff,
      initial_appeal: initialAppeal,
      needs_specialist_reply: needsSpecialistReply,
      priority,
      attachments: (handoff.attachments || []).map((a) => ({ ...a })),
      action_logs: getActionLogs(store, {
        handoff_id: handoff.handoff_id,
        ticket_id: relTicket ? relTicket.ticket_id : null,
        include_internal: true,
      }),
    };
    delete out.thread_id;
    if (order) {
      out.order_summary = {};
      for (const k of ["merchant", "amount_yuan", "status", "ordered_at", "prep_promised_at", "prep_done_at", "picked_up_at", "expected_at", "delivered_at", "liability_party", "liability_detail", "rider_protection", "gps_fence_note", "items"]) {
        if (k in order) out.order_summary[k] = order[k];
      }
    }
    if (relTicket) {
      out.related_ticket = {
        ticket_id: relTicket.ticket_id,
        status: relTicket.status,
        review_note: relTicket.review_note || null,
        prior_review_note: relTicket.prior_review_note || null,
        proposed_coupon_yuan: relTicket.proposed_coupon_yuan,
        coupon_issued_yuan: relTicket.coupon_issued_yuan ?? null,
        information_request: relTicket.information_request || null,
        customer_information: relTicket.customer_information || null,
        is_expedited: relTicket.is_expedited || 0,
        escalated_to: relTicket.escalated_to || null,
        assigned_reviewer_id: relTicket.assigned_reviewer_id || null,
      };
    }
    return out;
  }

  function activeHandoffsForCustomer(store, customerId, threadId) {
    return (store.handoffs || []).filter((h) =>
      h.customer_id === customerId &&
      (h.status === "waiting" || ((!threadId || !h.thread_id || h.thread_id === threadId) && h.status === "replied" && !h.ended_at))
    );
  }

  function activeHandoffForOrder(store, customerId, orderId, threadId) {
    const list = activeHandoffsForCustomer(store, customerId, threadId).filter((h) => h.order_id === orderId);
    return list.length ? list[list.length - 1] : null;
  }

  function unboundWaitingHandoff(store, customerId, threadId) {
    const custAll = (store.handoffs || []).filter((h) => h.customer_id === customerId);
    if (!custAll.length) return null;
    const latest = custAll[custAll.length - 1];
    if (!latest.order_id && latest.status === "waiting" && (!threadId || !latest.thread_id || latest.thread_id === threadId)) {
      return latest;
    }
    return null;
  }

  function latestActiveHandoff(store, customerId, threadId) {
    const list = activeHandoffsForCustomer(store, customerId, threadId);
    return list.length ? list[list.length - 1] : null;
  }

  function focusedOrder(messages) {
    for (let i = messages.length - 1; i >= 0; i--) {
      const item = messages[i];
      if (item.role === "customer" || item.role === "tool") {
        const found = extractOrderIds(item.text);
        if (found.length) return found[found.length - 1];
      }
    }
    return null;
  }

  function lastVerifiedOrder(messages, customerId) {
    for (let i = messages.length - 1; i >= 0; i--) {
      const item = messages[i];
      if (item.role === "customer" || item.role === "tool") {
        const found = extractOrderIds(item.text);
        for (let j = found.length - 1; j >= 0; j--) {
          if (lookupForCustomer(found[j], customerId)[1]) return found[j];
        }
      }
    }
    return null;
  }

  function extractVerifiedOrders(customerId, text) {
    const out = [];
    for (const oid of extractOrderIds(text)) {
      if (!out.includes(oid) && lookupForCustomer(oid, customerId)[1]) out.push(oid);
    }
    return out;
  }

  function computeFocus(store, customerId, orderId) {
    if (!orderId) return null;
    const norm = normalizeOrderId(orderId);
    const [, order] = lookupForCustomer(norm, customerId);
    if (!order) return { order_id: norm, verified: false };
    const decision = evaluateOrder(order);
    const ticket = findTicketForOrder(store, order.order_id, POLICY.version);
    return {
      order_id: order.order_id,
      verified: true,
      status: decision.status,
      reason_code: decision.reason_code,
      late_seconds: decision.late_seconds ?? null,
      proposed_coupon_yuan: decision.proposed_coupon_yuan ?? null,
      ticket_id: ticket && ticket.customer_id === customerId ? ticket.ticket_id : null,
    };
  }

  function extractInitialAppeal(visible, orderId, requestText) {
    if (orderId) {
      for (let i = 0; i < visible.length; i++) {
        const item = visible[i];
        if (item.role === "customer") {
          const inText = extractOrderIds(item.text).includes(orderId);
          const nextIsTool = i + 1 < visible.length && visible[i + 1].role === "tool" && visible[i + 1].text.includes(orderId);
          if (inText || nextIsTool) return item.text.slice(0, 160);
        }
      }
    }
    for (const item of visible) {
      if (item.role === "customer" && item.text && item.text.trim()) return item.text.slice(0, 160);
    }
    return requestText && requestText.trim() ? requestText.trim().slice(0, 160) : null;
  }

  function buildHandoffExcerpt(visible, orderId) {
    const formatted = visible.map((m) => ({
      role: m.role,
      text: String(m.text || "").replace("查单工具 query_order：", "查询 ").slice(0, 160),
    }));
    if (formatted.length <= 12) return formatted;
    let startIdx = 0;
    if (orderId) {
      for (let i = 0; i < visible.length; i++) {
        if (visible[i].role === "customer" && extractOrderIds(visible[i].text).includes(orderId)) { startIdx = i; break; }
        if (visible[i].role === "tool" && visible[i].text.includes(orderId)) { startIdx = Math.max(0, i - 1); break; }
      }
    }
    const headEnd = Math.min(formatted.length - 8, startIdx + 4);
    if (headEnd <= startIdx) return formatted.slice(-12);
    const omitted = (formatted.length - 8) - headEnd;
    return [
      ...formatted.slice(startIdx, headEnd),
      ...(omitted > 0 ? [{ role: "tool", text: `… 中间省略 ${omitted} 条历史消息 …` }] : []),
      ...formatted.slice(-8),
    ];
  }

  function appendHandoffFollowup(store, handoff, { sender_role, sender_id, text = null, after_index = null, order_id = null, files = [] }) {
    if (!handoff || handoff.status === "cancelled") return null;
    if (order_id && handoff.order_id !== order_id) handoff.order_id = order_id;
    if (handoff.ended_at && sender_role === "reviewer") handoff.ended_at = null;
    handoff.followups = handoff.followups || [];
    handoff.attachments = handoff.attachments || [];
    if (files.length && handoff.attachments.length + files.length > MAX_ATTACHMENTS_PER_HANDOFF) {
      throw httpError(409, "单次人工咨询最多上传 3 个附件。", "attachment_limit");
    }
    let msgSeq = store.nextMsgSeq || 1;
    if (text && String(text).trim()) {
      msgSeq = store.nextMsgSeq || 1;
      store.nextMsgSeq = msgSeq + 1;
      handoff.followups.push({
        message_id: msgSeq,
        sender_role,
        sender_id,
        text: String(text).trim(),
        created_at: nowIso(),
        after_index,
      });
    }
    for (const f of files) {
      handoff.attachments.push({
        ...f,
        handoff_id: handoff.handoff_id,
        after_index,
        is_followup: true,
        followup_seq: msgSeq,
      });
    }
    return handoff;
  }

  function openOrContinueHandoff(store, { threadId, customerId, text = null, files = [], focusOrderId = null, singleOrder = false }) {
    if (!singleOrder) {
      const explicitOrders = extractVerifiedOrders(customerId, text);
      if (explicitOrders.length > 1) {
        let lastRes = null;
        explicitOrders.forEach((oid, idx) => {
          const batchFiles = idx === explicitOrders.length - 1 ? files : [];
          lastRes = openOrContinueHandoff(store, {
            threadId, customerId, text, files: batchFiles, focusOrderId: oid, singleOrder: true,
          });
        });
        return lastRes;
      }
    }

    const messages = store.chats[customerId] || [];
    const confirmation = store.pendingConfirm[customerId] || null;
    let orderId = null;
    if (singleOrder && focusOrderId) {
      orderId = normalizeOrderId(focusOrderId);
    } else {
      const explicit = extractVerifiedOrders(customerId, text);
      if (explicit.length) orderId = explicit[explicit.length - 1];
      else if (focusOrderId && lookupForCustomer(focusOrderId, customerId)[1]) orderId = normalizeOrderId(focusOrderId);
      else {
        const curAct = latestActiveHandoff(store, customerId, threadId);
        const cands = [
          confirmation && confirmation.order_id,
          curAct && curAct.order_id,
          lastVerifiedOrder(messages, customerId),
        ];
        for (const c of cands) {
          if (c && lookupForCustomer(c, customerId)[1]) { orderId = c; break; }
        }
        if (!orderId) {
          const custT = store.tickets.filter((t) => t.customer_id === customerId);
          if (custT.length) orderId = custT[custT.length - 1].order_id;
        }
      }
    }

    const initialAppeal = extractInitialAppeal(messages, orderId, text);
    const excerpt = buildHandoffExcerpt(messages, orderId);
    const orderObj = orderId ? lookupOrder(orderId) : null;
    const tenantId = (orderObj && orderObj.tenant_id) || "M_67REST";

    let active = null;
    if (orderId) {
      active = activeHandoffForOrder(store, customerId, orderId, threadId) || unboundWaitingHandoff(store, customerId, threadId);
    } else {
      active = latestActiveHandoff(store, customerId, threadId);
    }

    if (active && active.status === "replied") {
      let cleanText = text && text.trim() ? text.trim() : null;
      if (!cleanText && files.length) {
        cleanText = files.some((f) => f.kind === "audio") ? "🎤 已发送语音留言" : "📷 已上传补充凭证";
      }
      appendHandoffFollowup(store, active, {
        sender_role: "customer", sender_id: customerId, text: cleanText,
        after_index: messages.length, order_id: !active.order_id ? orderId : null, files,
      });
      return { handoff: handoffCustomerCopy(active, threadId), created: false };
    }

    // Check existing waiting handoff for this order (or unbound waiting handoff)
    let waiting = null;
    if (orderId) {
      waiting = (store.handoffs || []).slice().reverse().find((h) => h.customer_id === customerId && h.order_id === orderId && h.status === "waiting") ||
                unboundWaitingHandoff(store, customerId, threadId);
    } else {
      waiting = (store.handoffs || []).slice().reverse().find((h) => h.customer_id === customerId && h.status === "waiting") || null;
    }

    if (waiting) {
      if (orderId && !waiting.order_id) { waiting.order_id = orderId; waiting.tenant_id = tenantId; }
      if (initialAppeal && !waiting.initial_appeal) waiting.initial_appeal = initialAppeal;
      const waitFollowup = text && text.trim() && !BARE_HANDOFF_RE.test(text) ? text.trim() :
        (files.length ? (files.some((f) => f.kind === "audio") ? "🎤 已发送语音留言" : "📷 已上传补充凭证") : null);
      const priorF = waiting.followups || [];
      const isDup = (!priorF.length && waiting.request_text === waitFollowup) ||
                    (priorF.length && priorF[priorF.length - 1].sender_role === "customer" && priorF[priorF.length - 1].text === waitFollowup);
      if (waitFollowup && (!isDup || files.length)) {
        appendHandoffFollowup(store, waiting, {
          sender_role: "customer", sender_id: customerId, text: isDup ? null : waitFollowup,
          after_index: messages.length, order_id: !waiting.order_id ? orderId : null, files,
        });
      } else if (files.length) {
        if ((waiting.attachments || []).length + files.length > MAX_ATTACHMENTS_PER_HANDOFF) {
          throw httpError(409, "单次人工咨询最多上传 3 个附件。", "attachment_limit");
        }
        const hasPrior = Boolean(waiting.request_text || (waiting.followups && waiting.followups.length) || (waiting.attachments && waiting.attachments.length));
        for (const f of files) {
          waiting.attachments.push({ ...f, handoff_id: waiting.handoff_id, after_index: messages.length, is_followup: hasPrior });
        }
      }
      return { handoff: handoffCustomerCopy(waiting, threadId), created: false };
    }

    if (files.length > MAX_ATTACHMENTS_PER_HANDOFF) {
      throw httpError(409, "单次人工咨询最多上传 3 个附件。", "attachment_limit");
    }
    const hid = `H${String((store.handoffs || []).length + 1).padStart(4, "0")}`;
    const createdAt = nowIso();
    const handoff = {
      handoff_id: hid,
      customer_id: customerId,
      thread_id: threadId,
      order_id: orderId,
      tenant_id: tenantId,
      after_index: messages.length,
      request_text: text && text.trim() ? text.trim() : null,
      initial_appeal: initialAppeal,
      excerpt,
      attachments: files.map((f) => ({ ...f, handoff_id: hid, after_index: messages.length, is_followup: false })),
      followups: [],
      status: "waiting",
      reply_text: null,
      reply_seq: null,
      reply_after_index: null,
      reviewer_id: null,
      assigned_reviewer_id: null,
      escalated_to: null,
      is_expedited: 0,
      created_at: createdAt,
      closed_at: null,
      ended_at: null,
    };
    store.handoffs.push(handoff);
    return { handoff: handoffCustomerCopy(handoff, threadId), created: true };
  }

  function routeToActiveHandoff(store, active, threadId, customerId, text, bindOrderId = null) {
    const messages = store.chats[customerId] || [];
    const cleanText = text.trim();
    const followups = active.followups || [];
    const isDupWaiting = active.status === "waiting" && !bindOrderId && (
      (!followups.length && active.request_text === cleanText) ||
      (followups.length && followups[followups.length - 1].sender_role === "customer" && followups[followups.length - 1].text === cleanText)
    );
    if (!isDupWaiting) {
      appendHandoffFollowup(store, active, {
        sender_role: "customer", sender_id: customerId, text: cleanText,
        after_index: messages.length, order_id: !active.order_id ? bindOrderId : null,
      });
    }
    return {
      outcome: "handoff_message_sent", reason_code: null, messages: [],
      confirmation: null, ticket: null, handoff: handoffCustomerCopy(active, threadId), created: false,
    };
  }

  function handleActiveHandoffTurn(store, active, threadId, customerId, text, focusOrderId = null) {
    const explicitOrders = extractVerifiedOrders(customerId, text);
    let explicitFocus = focusOrderId ? normalizeOrderId(focusOrderId) : null;
    if (explicitFocus && !lookupForCustomer(explicitFocus, customerId)[1]) explicitFocus = null;
    const targetOrders = explicitOrders.length ? explicitOrders : (explicitFocus ? [explicitFocus] : []);
    const wantsH = wantsHumanOrSecondAppeal(text);

    if (!targetOrders.length) {
      if (active.status === "waiting" && wantsH) {
        const res = openOrContinueHandoff(store, { threadId, customerId, text });
        return { outcome: res.created ? "handoff_requested" : "handoff_waiting", reason_code: null, messages: [], confirmation: null, ticket: null, ...res };
      }
      return routeToActiveHandoff(store, active, threadId, customerId, text);
    }
    if (targetOrders.length === 1 && !active.order_id) {
      const oid = targetOrders[0];
      if (active.status === "waiting" && wantsH) {
        const res = openOrContinueHandoff(store, { threadId, customerId, text, focusOrderId: oid, singleOrder: true });
        return { outcome: res.created ? "handoff_requested" : "handoff_waiting", reason_code: null, messages: [], confirmation: null, ticket: null, ...res };
      }
      return routeToActiveHandoff(store, active, threadId, customerId, text, oid);
    }
    if (targetOrders.length === 1 && targetOrders[0] === active.order_id) {
      if (active.status === "waiting" && wantsH) {
        const res = openOrContinueHandoff(store, { threadId, customerId, text, focusOrderId: targetOrders[0], singleOrder: true });
        return { outcome: res.created ? "handoff_requested" : "handoff_waiting", reason_code: null, messages: [], confirmation: null, ticket: null, ...res };
      }
      return routeToActiveHandoff(store, active, threadId, customerId, text);
    }

    let lastOut = null;
    for (const oid of targetOrders) {
      let existingH = activeHandoffForOrder(store, customerId, oid, threadId) || unboundWaitingHandoff(store, customerId, threadId);
      if (existingH) {
        if (existingH.status === "waiting" && wantsH) {
          const res = openOrContinueHandoff(store, { threadId, customerId, text, focusOrderId: oid, singleOrder: true });
          lastOut = { outcome: res.created ? "handoff_requested" : "handoff_waiting", reason_code: null, messages: [], confirmation: null, ticket: null, ...res };
        } else {
          lastOut = routeToActiveHandoff(store, existingH, threadId, customerId, text, !existingH.order_id ? oid : null);
        }
      } else {
        const res = openOrContinueHandoff(store, { threadId, customerId, text, focusOrderId: oid, singleOrder: true });
        lastOut = { outcome: res.created ? "handoff_requested" : "handoff_waiting", reason_code: null, messages: [], confirmation: null, ticket: null, ...res };
      }
    }
    return lastOut;
  }

  function buildFollowupAnswer(store, userText, order) {
    const oid = order.order_id;
    const merchant = order.merchant || "餐厅";
    const items = (order.items || ["招牌套餐 ×1"]).join("、");
    const decision = evaluateOrder(order);
    const existing = findTicketForOrder(store, oid, POLICY.version);
    if (SPECIAL_ISSUE_RE.test(userText)) {
      if (order.status !== "delivered") {
        return `非常抱歉让您担心！核实到您正在咨询的 ${oid}（${merchant}）目前仍在正常配送途中（预计 ${order.expected_at} 送达），请确认是否选错了其他已送达订单；若涉及餐品异物或食品安全问题，请点击下方「相册」上传照片凭证或点击右上角「转人工」直连食安专席。`;
      }
      return `非常抱歉让您遇到餐品问题！针对 ${oid}（${merchant}），请先暂停食用并保留原貌拍照取证。自助通道仅处理配送超时补偿券，涉及餐品异物、食品安全或洒漏理赔，请点击下方「相册」上传照片凭证，或点击右上角「转人工」由食安专席优先为您跟进。`;
    }
    if (/什么菜|点了什么|餐品|多少钱|金额|实付|what did i order|what (?:items|food|dishes)|how much|amount|\bpaid\b|price/i.test(userText)) {
      return `您正在咨询的 ${oid}（${merchant}）餐品明细为：${items}，实付金额 ¥${order.amount_yuan}。下单时间 ${order.ordered_at || "—"}，完成备餐 ${order.prep_done_at || "—"}，预计 ${order.expected_at || "—"} 送达。`;
    }
    const progress = order.customer_progress_note || `${order.ordered_at || "—"} 下单，${order.prep_done_at || "—"} 完成备餐`;
    const timelineStr = `针对您刚咨询的 ${oid}（${merchant}）：${progress}。`;
    if (existing) return `${timelineStr}${ticketText(existing, false)}`;
    if (decision.reason_code === "delay_below_threshold") {
      const threshSec = POLICY.threshold_minutes * 60;
      const shortSec = Math.max(1, threshSec - decision.late_seconds + (POLICY.include_threshold ? 0 : 1));
      return `非常抱歉让您久等了！${timelineStr}预计 ${order.expected_at} 送达，实际 ${order.delivered_at} 送达，${delayText(decision.late_seconds)}，距离「${thresholdText()}」的起赔标准还差 ${delayText(shortSec).replace(/^晚到\s*/, "")}，暂不符合自助延误补偿条件；若影响用餐体验欢迎点击上方「转人工」由专员跟进安抚。`;
    }
    return `${timelineStr}${outcomeText(order, decision)}`;
  }

  async function callDeepSeek(store, chatMessages, tickets, customerId) {
    const safeFields = ["ticket_id", "order_id", "status", "late_seconds", "proposed_coupon_yuan", "coupon_issued_yuan"];
    const summary = tickets.slice(-8).map((t) => {
      const o = {};
      for (const k of safeFields) o[k] = t[k] ?? null;
      return o;
    });
    const priorOrderId = lastVerifiedOrder(chatMessages.slice(0, -1), customerId);
    const activeOrder = priorOrderId ? lookupForCustomer(priorOrderId, customerId)[1] : null;
    let ephemeralCtx = `规则参数：已送达且${thresholdText()}可申请 ${POLICY.coupon_yuan} 元演示补偿券。\n当前账号最近工单状态摘要（只读）：${JSON.stringify(summary)}`;
    if (activeOrder) {
      const activeDecision = evaluateOrder(activeOrder);
      ephemeralCtx += `\n当前会话已核实焦点订单：${JSON.stringify({
        order_id: activeOrder.order_id, merchant: activeOrder.merchant, amount_yuan: activeOrder.amount_yuan,
        items: activeOrder.items, status: activeOrder.status, ordered_at: activeOrder.ordered_at,
        prep_done_at: activeOrder.prep_done_at, picked_up_at: activeOrder.picked_up_at,
        expected_at: activeOrder.expected_at, delivered_at: activeOrder.delivered_at,
        customer_progress_note: activeOrder.customer_progress_note, late_seconds: activeDecision.late_seconds,
      })}`;
    }
    const apiMessages = [{ role: "system", content: SYSTEM_PROMPT }];
    const recent = chatMessages.slice(-10);
    for (let i = 0; i < recent.length; i++) {
      const m = recent[i];
      if (i === recent.length - 1) {
        apiMessages.push({ role: "system", content: ephemeralCtx });
        if (replyInEnglish()) apiMessages.push({ role: "system", content: EN_REPLY_DIRECTIVE });
      }
      if (m.role === "customer") apiMessages.push({ role: "user", content: m.text });
      else if (m.role === "assistant") apiMessages.push({ role: "assistant", content: m.text });
    }
    const tools = [{
      type: "function",
      function: {
        name: "query_order",
        description: "核实当前顾客的订单。purpose=lookup 查询配送事实、对比或进度；compensation 核实延误补偿申请资格。",
        parameters: {
          type: "object",
          properties: {
            order_id: { type: "string" },
            purpose: { type: "string", enum: ["lookup", "compensation"], default: "compensation" },
          },
          required: ["order_id"],
        },
      },
    }];

    const lastText = chatMessages.length ? chatMessages[chatMessages.length - 1].text : "";
    const explicitIds = extractOrderIds(lastText);
    const defaultPurpose = (PURE_LOOKUP_RE.test(lastText) || PRAISE_NO_CLAIM_RE.test(lastText)) && !/能赔|可以赔|申请补偿|申请赔付|compensat|\bclaim|eligible|refund/i.test(lastText) ? "lookup" : "compensation";
    const isGenericNewOpener = /我的外卖|我有笔?外卖|外卖迟到|my (?:food |takeaway )?(?:order|delivery|food) (?:is|was|came|arrived)(?: very| so)? late/i.test(lastText) && !/这单|那单|这笔|那笔|这个订单|刚才|this order|that order|this one|that one|just now/i.test(lastText);

    try {
      const resp = await fetch(`${DS_BASE}/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${decodeToken()}` },
        body: JSON.stringify({
          model: DS_MODEL, messages: apiMessages, tools,
          temperature: 0.35, max_tokens: 800, thinking: { type: "disabled" },
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const choice = data.choices && data.choices[0] && data.choices[0].message;
      if (choice && choice.tool_calls && choice.tool_calls.length) {
        const calls = choice.tool_calls.map((tc) => {
          const args = JSON.parse(tc.function.arguments || "{}");
          return { order_id: normalizeOrderId(args.order_id || ""), purpose: args.purpose || defaultPurpose };
        });
        return { tool_calls: calls };
      }
      if (explicitIds.length) {
        return { tool_calls: explicitIds.slice(0, 4).map((oid) => ({ order_id: oid, purpose: defaultPurpose })) };
      }
      if (!explicitIds.length && activeOrder && !isGenericNewOpener && FOLLOWUP_ORDER_RE.test(lastText)) {
        if (FOLLOWUP_CLAIM_RE.test(lastText) && /这单|那单|这笔|那笔|这个订单|刚才|那就|还是|this order|that order|this one|that one/i.test(lastText) && !/为什么|怎么|差多少|多久|\bwhy\b|how (?:long|much|come)/i.test(lastText) && !PRAISE_NO_CLAIM_RE.test(lastText)) {
          return { tool_calls: [{ order_id: activeOrder.order_id, purpose: "compensation" }] };
        }
        const rawReply = (choice && choice.content || "").trim();
        if (!rawReply || /提供订单号|选择.*订单|哪一?笔订单|order (?:id|number)|which order|(?:choose|select|pick) (?:an|the|your) order/i.test(rawReply)) {
          return { text: buildFollowupAnswer(store, lastText, activeOrder), activeOrder };
        }
        return { text: rawReply, activeOrder };
      }
      if (choice && choice.content) return { text: choice.content.trim(), activeOrder };
    } catch (_) {}
    if (explicitIds.length) return { tool_calls: explicitIds.slice(0, 4).map((oid) => ({ order_id: oid, purpose: defaultPurpose })) };
    if (activeOrder && !isGenericNewOpener && FOLLOWUP_ORDER_RE.test(lastText)) {
      return { text: buildFollowupAnswer(store, lastText, activeOrder), activeOrder };
    }
    return { text: "请提供订单号（如 ORD001），或从左侧「我的订单」中选择要咨询的订单。" };
  }

  async function synthesizeWithDeepSeek(userText, ordersList, baseText, allowedAmounts, statuses, orderPrices) {
    if (!userText || !ordersList.length) return baseText;
    const summaries = ordersList.map((o) => ({
      order_id: o.order_id, merchant: o.merchant, amount_yuan: o.amount_yuan, items: o.items,
      status: o.status === "delivered" ? "已送达" : "配送中",
      ordered_at: o.ordered_at, prep_done_at: o.prep_done_at, picked_up_at: o.picked_up_at,
      expected_at: o.expected_at, delivered_at: o.delivered_at, customer_progress_note: o.customer_progress_note,
    }));
    const prompt = `顾客原话：${userText}\n核实订单：${JSON.stringify(summaries)}\n【系统规则结论（必须完整保留的核心时间与资格事实）】：${baseText}`;
    try {
      const resp = await fetch(`${DS_BASE}/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${decodeToken()}` },
        body: JSON.stringify({
          model: DS_MODEL,
          messages: [
            { role: "system", content: SYNTHESIS_PROMPT },
            ...(replyInEnglish() ? [{ role: "system", content: EN_REPLY_DIRECTIVE }] : []),
            { role: "user", content: prompt },
          ],
          temperature: 0.35, max_tokens: 600, thinking: { type: "disabled" },
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const text = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content || "").trim();
      let anchorsOk = ordersList.every((o) => text.includes(o.order_id));
      if (baseText.includes("才能申请") && !/未达|不符合|才能申请|超过|满|暂不|not (?:yet )?eligible|doesn'?t qualify|does not qualify|isn'?t eligible|is not eligible|not qualify|short of|below the|more than|over \d+|threshold/i.test(text)) anchorsOk = false;
      if (baseText.includes("尚未送达") && !/尚未送达|未送达|配送中|配送途中|在途|加急配送|not (?:yet )?(?:been )?delivered|on (?:its|the) way|in transit|out for delivery|still being delivered|hasn'?t arrived|has not arrived/i.test(text)) anchorsOk = false;
      if (baseText.includes("暂缺签收时间") && !/暂缺|未同步|签收时间|缺少|核实|missing|not (?:yet )?synced|hasn'?t synced|delivery (?:time|timestamp)|verif/i.test(text)) anchorsOk = false;
      if (text && anchorsOk && !replyRisk(text, allowedAmounts, statuses, orderPrices)) return text;
    } catch (_) {}
    return baseText;
  }

  function validateIssueAmountAndRole(reviewerId, order, rawAmount, rawNote, checkPaidCap = true) {
    const defaultAmt = POLICY.coupon_yuan;
    const rev = DEMO_DATA.reviewers.find((r) => r.reviewer_id === reviewerId) || {};
    const isSupervisor = reviewerId === "R002" || rev.role === "supervisor" ||
      (Array.isArray(rev.permissions) && rev.permissions.includes("ticket_custom_amount"));

    let amt = defaultAmt;
    let explicitCustom = false;
    if (rawAmount !== undefined && rawAmount !== null && rawAmount !== "") {
      if (typeof rawAmount === "boolean") throw httpError(400, "补偿金额须为 1 至 20 元之间的整数。", "invalid_amount");
      if (typeof rawAmount === "number") {
        if (!Number.isInteger(rawAmount)) {
          throw httpError(400, "补偿金额须为 1 至 20 元之间的整数，不支持小数金额（不自动四舍五入）。", "non_integer_amount");
        }
        amt = rawAmount;
      } else if (typeof rawAmount === "string") {
        const s = rawAmount.trim();
        if (!/^[+-]?\d+$/.test(s)) {
          throw httpError(400, "补偿金额须为 1 至 20 元之间的整数，不支持小数或非数字输入。", "non_integer_amount");
        }
        amt = parseInt(s, 10);
      } else {
        throw httpError(400, "补偿金额须为 1 至 20 元之间的整数。", "invalid_amount");
      }
      explicitCustom = amt !== defaultAmt;
    }

    if (explicitCustom && !isSupervisor) {
      throw httpError(403, `普通客服仅可按标准 ¥${defaultAmt} 处理；自定义补偿金额须由主管专席（R002）审批。`, "custom_amount_supervisor_only");
    }
    if (amt < 1 || amt > 20) {
      throw httpError(400, "补偿金额须为 1 至 20 元之间的整数，系统不会自动截断为边界值。", "amount_out_of_range");
    }

    let cleanedNote = null;
    if (typeof rawNote === "string" && rawNote.trim()) {
      cleanedNote = rawNote.trim();
      if (cleanedNote.length > 200) throw httpError(400, "说明内容不能超过 200 个字。", "note_too_long");
    }
    if (explicitCustom && !cleanedNote) {
      throw httpError(400, `主管调整非标准补偿金额（非 ¥${defaultAmt}）必须填写具体调整原因。`, "custom_amount_reason_required");
    }

    if (checkPaidCap) {
      if (!order || typeof order !== "object") {
        throw httpError(409, "订单实付金额无法核实，暂不可发放补偿。", "unverified_paid_amount");
      }
      const paidVal = Number(order.amount_yuan);
      if (!Number.isFinite(paidVal) || paidVal <= 0) {
        throw httpError(409, "该订单缺少可信实付金额记录，系统不凭聊天自报金额发放补偿，请先核实订单实付。", "unverified_paid_amount");
      }
      if (amt > paidVal) {
        if (!explicitCustom) {
          throw httpError(409, `标准补偿 ¥${amt} 超过订单可信实付金额 ¥${paidVal}，系统不自动降额，请转交主管（R002）在实付上限内审批。`, "standard_amount_exceeds_paid");
        }
        throw httpError(409, `补偿金额 ¥${amt} 不可超过订单可信实付金额 ¥${paidVal}。`, "amount_exceeds_paid");
      }
    }
    return [amt, cleanedNote];
  }

  function requireNote(rawNote, errMsg, limit = 200) {
    if (typeof rawNote !== "string" || !rawNote.trim()) throw httpError(400, errMsg, "note_required");
    const cleaned = rawNote.trim();
    if (cleaned.length > limit) throw httpError(400, `说明内容不能超过 ${limit} 个字。`, "note_too_long");
    return cleaned;
  }

  function optionalNote(rawNote, fallback, limit = 200) {
    if (typeof rawNote !== "string" || !rawNote.trim()) return fallback;
    const cleaned = rawNote.trim();
    if (cleaned.length > limit) throw httpError(400, `说明内容不能超过 ${limit} 个字。`, "note_too_long");
    return cleaned;
  }

  function validateReconsideration(store, ticket, rawNote, rawReasonType) {
    if (compensatedForOrder(store, ticket.order_id) || ticket.status === "approved") {
      throw httpError(409, "该订单已完成唯一补偿发放（一单一赔），不支持重审、改额或补差价。", "already_compensated_no_reconsider");
    }
    if (ticket.status !== "rejected") {
      throw httpError(409, "仅「已驳回且未发放补偿」的原申请单允许发起重审。", "invalid_ticket_state");
    }
    const cleanedNote = requireNote(rawNote, "发起重审或改判已驳回申请必须写明原因（可核实的相关新信息或原处理错误）。");
    const rt = rawReasonType != null ? String(rawReasonType).trim() : "";
    if (rt && !VALID_RECONSIDER_REASONS.has(rt)) {
      throw httpError(400, "重审原因类型须为 verifiable_relevant_new_information（可核实的新信息）或 prior_processing_error（原处理错误）；仅因不满结论不得重审。", "invalid_reconsider_reason_type");
    }
    return [cleanedNote, rt || "verifiable_relevant_new_information"];
  }

  function decideOrOverrideTicket(store, ticket, { target_status, reviewer_id, note, amount_yuan = null, merchant_bear_yuan = null, platform_bear_yuan = null, action_name = null, reason_type = null, issue_result = null }) {
    const alreadyComp = compensatedForOrder(store, ticket.order_id);
    if (alreadyComp) {
      if (target_status === "approved") return [{ ...alreadyComp, _deduplicated: true }, "approved"];
      return null;
    }
    const at = nowIso();
    const beforeStatus = ticket.status;
    const beforeAmt = ticket.coupon_issued_yuan ?? null;

    if (target_status === "approved") {
      const issued = amount_yuan != null ? Number(amount_yuan) : Number(ticket.proposed_coupon_yuan);
      if (beforeStatus === "rejected" && !ticket.prior_review_note && ticket.review_note) {
        ticket.prior_review_note = ticket.review_note;
      }
      ticket.status = "approved";
      ticket.decided_at = at;
      ticket.reviewer_id = reviewer_id;
      ticket.review_note = note;
      ticket.coupon_issued_yuan = issued;
      if (merchant_bear_yuan != null) ticket.merchant_bear_yuan = merchant_bear_yuan;
      if (platform_bear_yuan != null) ticket.platform_bear_yuan = platform_bear_yuan;
      pushTicketEvent(store, ticket.ticket_id, {
        actor: `reviewer:${reviewer_id}`, action: action_name || "approved", note, at,
        before_status: beforeStatus, after_status: "approved",
        before_amount_yuan: beforeAmt, amount_yuan: issued,
        reason_type, issue_result: issue_result || "issued",
      });
    } else if (target_status === "rejected") {
      ticket.status = "rejected";
      ticket.decided_at = at;
      ticket.reviewer_id = reviewer_id;
      ticket.review_note = note;
      ticket.coupon_issued_yuan = null;
      pushTicketEvent(store, ticket.ticket_id, {
        actor: `reviewer:${reviewer_id}`, action: action_name || "rejected", note, at,
        before_status: beforeStatus, after_status: "rejected",
        before_amount_yuan: beforeAmt, reason_type, issue_result: issue_result || "rejected_no_issue",
      });
    } else if (target_status === "needs_info") {
      if (!ticket.prior_review_note && ticket.review_note) ticket.prior_review_note = ticket.review_note;
      ticket.status = "needs_info";
      ticket.reviewer_id = reviewer_id;
      ticket.information_request = note;
      ticket.information_requested_at = at;
      ticket.customer_information = null;
      ticket.decided_at = null;
      ticket.review_note = null;
      ticket.coupon_issued_yuan = null;
      pushTicketEvent(store, ticket.ticket_id, {
        actor: `reviewer:${reviewer_id}`, action: action_name || "information_requested", note, at,
        before_status: beforeStatus, after_status: "needs_info",
        before_amount_yuan: beforeAmt, reason_type, issue_result: issue_result || "needs_info",
      });
    } else if (target_status === "pending") {
      if (beforeStatus !== "rejected" || beforeAmt != null) return null;
      if (!ticket.prior_review_note && ticket.review_note) ticket.prior_review_note = ticket.review_note;
      ticket.status = "pending";
      ticket.decided_at = null;
      ticket.reviewer_id = null;
      ticket.review_note = null;
      ticket.coupon_issued_yuan = null;
      pushTicketEvent(store, ticket.ticket_id, {
        actor: `reviewer:${reviewer_id}`, action: action_name || "reopened", note, at,
        before_status: beforeStatus, after_status: "pending",
        before_amount_yuan: beforeAmt, reason_type, issue_result: issue_result || "reopened_for_review",
      });
    } else {
      return null;
    }
    return [ticket, beforeStatus];
  }

  function createManualTicket(store, { customerId, order, lateSeconds, proposedCouponYuan, reviewerId, subrogation, note }) {
    const existing = findTicketForOrder(store, order.order_id, null);
    if (existing) return [existing, false];
    const tid = `T${String(store.tickets.length + 1).padStart(4, "0")}`;
    const at = nowIso();
    const ticket = {
      ticket_id: tid,
      customer_id: customerId,
      order_id: order.order_id,
      policy_version: POLICY.version,
      expected_at: order.expected_at || "—",
      delivered_at: order.delivered_at || (order.status === "delivering" ? "配送中" : "待核验"),
      late_seconds: Number(lateSeconds || 0),
      proposed_coupon_yuan: Number(proposedCouponYuan),
      status: "pending",
      coupon_issued_yuan: null,
      created_at: at,
      decided_at: null,
      reviewer_id: null,
      review_note: null,
      prior_review_note: null,
      information_request: null,
      customer_information: null,
      rating: null,
      tenant_id: order.tenant_id || "M_67REST",
      stp_tier: subrogation ? subrogation.stp_tier : null,
      merchant_bear_yuan: subrogation ? subrogation.merchant_bear_yuan : null,
      platform_bear_yuan: subrogation ? subrogation.platform_bear_yuan : null,
      assigned_reviewer_id: reviewerId,
      is_expedited: 0,
      escalated_to: null,
    };
    store.tickets.push(ticket);
    pushTicketEvent(store, tid, {
      actor: `reviewer:${reviewerId}`, action: "created_by_agent", note, at,
      before_status: "无工单", after_status: "pending", amount_yuan: proposedCouponYuan,
    });
    return [ticket, true];
  }

  function transitionHandoffStatus(store, handoff, reviewerId, closeSession = false) {
    if (!handoff || handoff.status === "cancelled") return;
    const at = nowIso();
    if (handoff.status === "waiting") {
      const fups = handoff.followups || [];
      const maxSeq = fups.reduce((m, f) => Math.max(m, f.message_id || 0), 0);
      handoff.status = "replied";
      handoff.reviewer_id = handoff.reviewer_id || reviewerId;
      handoff.closed_at = handoff.closed_at || at;
      if (handoff.reply_seq == null) handoff.reply_seq = maxSeq;
      if (handoff.reply_after_index == null) handoff.reply_after_index = handoff.after_index ?? 0;
    }
    if (closeSession && !handoff.ended_at) handoff.ended_at = at;
  }

  function verifyMediaMagic(bytes, mediaType) {
    if (!bytes || bytes.length < 4) return false;
    if (mediaType === "image/jpeg") return bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
    if (mediaType === "image/png") {
      const sig = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
      return bytes.length >= 8 && sig.every((b, i) => bytes[i] === b);
    }
    if (mediaType === "image/webp") {
      return bytes.length >= 12 &&
        String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]) === "RIFF" &&
        String.fromCharCode(bytes[8], bytes[9], bytes[10], bytes[11]) === "WEBP";
    }
    if (mediaType.startsWith("audio/") || mediaType === "video/webm") return bytes.length >= 4;
    return false;
  }

  async function sha256Hex(buffer) {
    if (crypto && crypto.subtle) {
      const hash = await crypto.subtle.digest("SHA-256", buffer);
      return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("");
    }
    return `len_${buffer.byteLength}`;
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("读取附件失败"));
      reader.readAsDataURL(file);
    });
  }

  function getCustomerSession() {
    const cid = sessionStorage.getItem(SESSION_CUST_KEY) || localStorage.getItem(SESSION_CUST_KEY);
    let tid = sessionStorage.getItem(SESSION_CUST_THREAD_KEY) || localStorage.getItem(SESSION_CUST_THREAD_KEY);
    if (cid && !tid) {
      tid = `web-${cid}-cloud`;
      sessionStorage.setItem(SESSION_CUST_THREAD_KEY, tid);
      localStorage.setItem(SESSION_CUST_THREAD_KEY, tid);
    }
    return { customerId: cid, threadId: tid };
  }

  window.ORD001_CLOUD_API = async function cloudApi(path, body) {
    const store = loadStore();
    const { customerId, threadId } = getCustomerSession();
    const reviewerId = sessionStorage.getItem(SESSION_REV_KEY) || localStorage.getItem(SESSION_REV_KEY);

    if (path === "/api/health") {
      return {
        status: "ok",
        policy: POLICY,
        review_policy_version: REVIEW_POLICY_VERSION,
        agent_mode: "C",
        stp_auto_approve: Boolean(store.stpAuto),
        data_version: DEMO_DATA.data_version,
        service_date: DEMO_DATA.service_date,
        model: `openai:${DS_MODEL}`,
        model_mode: "live",
        customers: DEMO_DATA.customers,
        reviewers: DEMO_DATA.reviewers,
      };
    }

    // ---------------- Customer Endpoints ----------------

    if (path === "/api/customer/login") {
      const cid = body && body.customer_id;
      const customer = DEMO_DATA.customers.find((c) => c.customer_id === cid);
      if (!customer) throw httpError(400, "没有这个模拟顾客。", "unknown_customer");
      const newTid = `web-${cid}-cloud`;
      sessionStorage.setItem(SESSION_CUST_KEY, cid);
      localStorage.setItem(SESSION_CUST_KEY, cid);
      sessionStorage.setItem(SESSION_CUST_THREAD_KEY, newTid);
      localStorage.setItem(SESSION_CUST_THREAD_KEY, newTid);
      return { customer };
    }
    if (path === "/api/customer/logout") {
      sessionStorage.removeItem(SESSION_CUST_KEY);
      localStorage.removeItem(SESSION_CUST_KEY);
      return { ok: true };
    }
    if (path === "/api/customer/me") {
      const customer = DEMO_DATA.customers.find((c) => c.customer_id === customerId);
      if (!customer) throw httpError(401, "请先登录模拟账号。", "login_required");
      return { customer };
    }
    if (path === "/api/customer/orders") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      return {
        orders: DEMO_DATA.orders.filter((o) => o.customer_id === customerId).map(customerOrderCopy),
      };
    }
    if (path === "/api/customer/tickets") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      return {
        tickets: store.tickets.filter((t) => t.customer_id === customerId).map(customerTicketCopy),
      };
    }
    if (path === "/api/customer/state") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const messages = store.chats[customerId] || [];
      const confirmation = store.pendingConfirm[customerId] || null;
      const custHandoffs = (store.handoffs || []).filter((h) => h.customer_id === customerId);
      const activeList = activeHandoffsForCustomer(store, customerId, threadId);
      const active = activeList.length ? activeList[activeList.length - 1] : null;
      const own = custHandoffs.filter((h) => !h.thread_id || h.thread_id === threadId);
      const handoffOrder = active && active.order_id && (active.after_index ?? 0) >= messages.length
        ? active.order_id
        : (own.length && (own[own.length - 1].after_index ?? 0) >= messages.length ? own[own.length - 1].order_id : null);
      const orderId = (confirmation && confirmation.order_id) || handoffOrder || focusedOrder(messages);

      return {
        messages,
        confirmation,
        tickets: store.tickets.filter((t) => t.customer_id === customerId).map(customerTicketCopy),
        goodwill_grants: (store.goodwills || []).filter((g) => g.customer_id === customerId),
        focus: computeFocus(store, customerId, orderId),
        active_handoff_id: active ? active.handoff_id : null,
        active_handoffs: activeList.map((h) => ({ handoff_id: h.handoff_id, order_id: h.order_id || null, status: h.status })),
        handoff_mode: active ? (active.status === "waiting" ? "waiting" : "active") : "none",
        handoffs: custHandoffs
          .filter((h) => !h.thread_id || h.thread_id === threadId || h.status !== "cancelled")
          .slice(-20)
          .map((h) => handoffCustomerCopy(h, threadId)),
      };
    }

    if (path === "/api/customer/goodwill") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const oid = normalizeOrderId((body && body.order_id) || "");
      const [, order] = lookupForCustomer(oid, customerId);
      if (!order) throw httpError(404, "当前账号下没有这笔订单。", "order_not_found");
      const sub = computeSubrogation(order);
      if (!sub.goodwill_care_yuan) throw httpError(409, "该订单不在临界延迟关怀区间内。", "goodwill_not_applicable");
      store.goodwills = store.goodwills || [];
      let existing = store.goodwills.find((g) => g.order_id === order.order_id && g.customer_id === customerId);
      let created = false;
      if (!existing) {
        created = true;
        existing = {
          grant_id: `G${String(store.goodwills.length + 1).padStart(4, "0")}`,
          customer_id: customerId, order_id: order.order_id, tenant_id: order.tenant_id || "M_67REST",
          amount_yuan: sub.goodwill_care_yuan, reason: "临界延迟平台体验金秒发关怀券", created_at: nowIso(),
        };
        store.goodwills.push(existing);
        saveStore(store, { event: "goodwill_claimed", customer_id: customerId, order_id: order.order_id, amount_yuan: sub.goodwill_care_yuan });
      }
      return { grant: existing, created };
    }

    if (path === "/api/customer/messages") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const text = String((body && body.text) || "").trim();
      const focusOrderId = body && body.order_id ? String(body.order_id).trim() : null;
      if (!text) throw httpError(400, "text 必须是非空文本。", "invalid_text");
      if (text.length > 500) throw httpError(400, "text 不能超过 500 个字。", "text_too_long");

      const messages = store.chats[customerId] || [];
      let active = latestActiveHandoff(store, customerId, threadId);
      if (active && EXPLICIT_NO_HANDOFF_RE.test(text)) {
        for (const h of activeHandoffsForCustomer(store, customerId, threadId)) {
          if (h.status === "waiting") { h.status = "cancelled"; h.closed_at = nowIso(); }
          else h.ended_at = nowIso();
        }
        active = null;
      }
      if (active) {
        delete store.pendingConfirm[customerId];
        const out = handleActiveHandoffTurn(store, active, threadId, customerId, text, focusOrderId);
        saveStore(store, { event: "customer_handoff_message", customer_id: customerId, outcome: out.outcome });
        return out;
      }
      if (wantsHumanOrSecondAppeal(text)) {
        delete store.pendingConfirm[customerId];
        const res = openOrContinueHandoff(store, { threadId, customerId, text, focusOrderId });
        saveStore(store, { event: "handoff_request", customer_id: customerId, handoff_id: res.handoff.handoff_id });
        return {
          outcome: res.created ? "handoff_requested" : "handoff_waiting",
          reason_code: null, messages: [], confirmation: null, ticket: null, ...res,
        };
      }
      if (store.pendingConfirm[customerId] && SPECIAL_ISSUE_RE.test(text)) {
        delete store.pendingConfirm[customerId];
      }
      if (store.pendingConfirm[customerId]) {
        throw httpError(409, "请先确认或取消当前的提交。", "confirmation_pending");
      }

      messages.push({ role: "customer", text });
      const custTickets = store.tickets.filter((t) => t.customer_id === customerId);
      const aiRes = await callDeepSeek(store, messages, custTickets, customerId);
      const newMessages = [];
      const isFoodSafety = SPECIAL_ISSUE_RE.test(text);

      if (aiRes.tool_calls && aiRes.tool_calls.length) {
        for (const tc of aiRes.tool_calls) {
          const tMsg = { role: "tool", text: `查单工具 query_order：${normalizeOrderId(tc.order_id)}` };
          messages.push(tMsg);
          newMessages.push(tMsg);
        }

        if (aiRes.tool_calls.length > 1) {
          const parts = [];
          const verifiedOrders = [];
          const claims = [];
          for (const tc of aiRes.tool_calls) {
            const oid = normalizeOrderId(tc.order_id);
            const [, ord] = lookupForCustomer(oid, customerId);
            if (!ord) { parts.push(`${oid}：${NOT_VERIFIED}`); continue; }
            verifiedOrders.push(ord);
            const ex = findTicketForOrder(store, ord.order_id, POLICY.version);
            if (ex) { parts.push(ticketText(ex, false)); continue; }
            const dec = evaluateOrder(ord);
            if (dec.status !== "pending") { parts.push(outcomeText(ord, dec)); }
            else {
              const cl = {
                kind: "confirm_submission", order_id: ord.order_id, expected_at: ord.expected_at,
                delivered_at: ord.delivered_at, late_seconds: dec.late_seconds,
                proposed_coupon_yuan: dec.proposed_coupon_yuan, policy_version: dec.policy_version,
              };
              claims.push(cl);
              parts.push(confirmText(cl));
            }
          }
          const baseText = "为您核实并对比如下：\n" + parts.map((p) => `• ${p}`).join("\n");
          let confirmation = null;
          let outcome = "orders_compared";
          if (claims.length === 1 && !isFoodSafety) {
            confirmation = claims[0];
            outcome = "awaiting_confirmation";
            store.pendingConfirm[customerId] = confirmation;
          }
          const prices = new Set(verifiedOrders.map((o) => Number(o.amount_yuan)));
          const smartText = await synthesizeWithDeepSeek(text, verifiedOrders, baseText, new Set([Number(POLICY.coupon_yuan)]), new Set(), prices);
          const rep = { role: "assistant", text: smartText };
          messages.push(rep);
          newMessages.push(rep);
          store.chats[customerId] = messages;
          saveStore(store, { event: "customer_message", customer_id: customerId, outcome });
          return { outcome, reason_code: confirmation ? "eligible_for_review" : null, messages: newMessages, confirmation, ticket: null };
        }

        const tc = aiRes.tool_calls[0];
        const oid = normalizeOrderId(tc.order_id);
        const [foundState, order] = lookupForCustomer(oid, customerId);
        if (!order) {
          const unverifiedText = isFoodSafety
            ? "非常抱歉让您遇到餐品异常问题！请先暂停食用并保留原貌拍照取证；涉及食品安全或餐损问题，可点击下方「相册」上传照片凭证或点击右上角「转人工」直连食安专席。" + NOT_VERIFIED
            : NOT_VERIFIED;
          const rep = { role: "assistant", text: unverifiedText };
          messages.push(rep);
          newMessages.push(rep);
          store.chats[customerId] = messages;
          saveStore(store, { event: "customer_message", customer_id: customerId, outcome: foundState, reason_code: "order_not_verified" });
          return { outcome: foundState, reason_code: "order_not_verified", messages: newMessages, confirmation: null, ticket: null };
        }

        if (isFoodSafety) {
          const facts = evaluateOrder(order);
          const statusLine = order.status !== "delivered"
            ? `系统核实到 ${order.order_id}（${order.merchant || "餐厅"}）当前仍在配送途中（预计 ${order.expected_at} 送达），请您核对是否选错了其他已送达订单。`
            : (facts.late_seconds != null
              ? `系统已核实 ${order.order_id}（${order.merchant || "餐厅"}，预计 ${order.expected_at}，实际 ${order.delivered_at}，${delayText(facts.late_seconds)}）。`
              : `系统已核实 ${order.order_id}（${order.merchant || "餐厅"}，已送达）。`);
          const safetyBase = `非常抱歉让您遇到餐品问题！请立即暂停食用并保留餐品与异物原貌拍照取证。${statusLine}由于自助延误券通道不适用于食品安全与餐损理赔，系统已为您熔断普通超时流程——请点击下方「相册」上传异物照片凭证，或点击右上角「转人工」直连 P0 食安应急专席优先处理。`;
          const prices = new Set([Number(order.amount_yuan)]);
          const smartText = await synthesizeWithDeepSeek(text, [order], safetyBase, new Set(), new Set(), prices);
          const rep = { role: "assistant", text: smartText };
          messages.push(rep);
          newMessages.push(rep);
          store.chats[customerId] = messages;
          saveStore(store, { event: "customer_message", customer_id: customerId, outcome: "food_safety_escalated", order_id: order.order_id });
          return { outcome: "food_safety_escalated", reason_code: "food_safety_p0", messages: newMessages, confirmation: null, ticket: null };
        }

        let outcome = "order_queried";
        let reasonCode = null;
        let confirmation = null;
        const activeTicket = findTicketForOrder(store, order.order_id, POLICY.version);
        let baseText = "";
        if (tc.purpose === "lookup" || PRAISE_NO_CLAIM_RE.test(text)) {
          const facts = evaluateOrder(order);
          if (order.status !== "delivered") baseText = `${order.order_id} 正在正常时效内为您配送，预计 ${order.expected_at} 送达。`;
          else if (facts.late_seconds === undefined) baseText = `${order.order_id} 已送达，因楼宇弱网暂未同步签收时间记录。`;
          else baseText = `${order.order_id} 预计 ${order.expected_at}，实际 ${order.delivered_at}，${delayText(facts.late_seconds)}。`;
          if (/什么菜|点了什么|餐品|多少钱|金额|实付|详情|what did i order|what (?:items|food|dishes)|how much|amount|\bpaid\b|price|details/i.test(text)) {
            baseText += `餐品明细：${(order.items || []).join("、")}，实付金额 ¥${order.amount_yuan}。`;
          }
          if (PRAISE_NO_CLAIM_RE.test(text)) {
            baseText += "非常感谢您对配送员的体谅与肯定，我们会把这份温暖转达给服务团队！";
          }
          if (activeTicket) baseText += ticketText(activeTicket, false);
        } else if (activeTicket) {
          outcome = "ticket_reused";
          baseText = ticketText(activeTicket, false);
        } else {
          const decision = evaluateOrder(order);
          if (decision.status !== "pending") {
            outcome = decision.status;
            reasonCode = decision.reason_code;
            baseText = outcomeText(order, decision);
          } else {
            outcome = "awaiting_confirmation";
            reasonCode = decision.reason_code;
            confirmation = {
              kind: "confirm_submission", order_id: order.order_id, expected_at: order.expected_at,
              delivered_at: order.delivered_at, late_seconds: decision.late_seconds,
              proposed_coupon_yuan: decision.proposed_coupon_yuan, policy_version: decision.policy_version,
            };
            baseText = confirmText(confirmation);
            store.pendingConfirm[customerId] = confirmation;
          }
        }
        const allowed = new Set(confirmation || activeTicket ? [Number(POLICY.coupon_yuan)] : []);
        if (activeTicket) {
          if (activeTicket.proposed_coupon_yuan != null) allowed.add(Number(activeTicket.proposed_coupon_yuan));
          if (activeTicket.coupon_issued_yuan != null) allowed.add(Number(activeTicket.coupon_issued_yuan));
        }
        const statuses = new Set(activeTicket ? [activeTicket.status] : []);
        const prices = new Set([Number(order.amount_yuan)]);
        const smartText = await synthesizeWithDeepSeek(text, [order], baseText, allowed, statuses, prices);
        const rep = { role: "assistant", text: smartText };
        messages.push(rep);
        newMessages.push(rep);
        store.chats[customerId] = messages;
        saveStore(store, { event: "customer_message", customer_id: customerId, outcome, order_id: order.order_id });
        return { outcome, reason_code: reasonCode, messages: newMessages, confirmation, ticket: activeTicket ? customerTicketCopy(activeTicket) : null };
      }

      const allowed = new Set([Number(POLICY.coupon_yuan)]);
      const activeOrd = aiRes.activeOrder;
      const scoped = activeOrd ? custTickets.filter((t) => t.order_id === activeOrd.order_id) : [];
      for (const t of scoped) {
        if (t.proposed_coupon_yuan != null) allowed.add(Number(t.proposed_coupon_yuan));
        if (t.coupon_issued_yuan != null) allowed.add(Number(t.coupon_issued_yuan));
      }
      const statuses = new Set(scoped.map((t) => t.status));
      const prices = activeOrd ? new Set([Number(activeOrd.amount_yuan)]) : new Set();
      const risk = replyRisk(aiRes.text || "", allowed, statuses, prices);
      if (risk) store.guardHits = (store.guardHits || 0) + 1;
      const finalText = risk ? GUARDED_REPLY : (aiRes.text || "请提供订单号，或从「我的订单」中选择。");
      const rep = { role: "assistant", text: finalText };
      messages.push(rep);
      newMessages.push(rep);
      store.chats[customerId] = messages;
      saveStore(store, { event: "customer_message", customer_id: customerId, outcome: "not_selected", reason_code: risk ? "reply_guarded" : null });
      return { outcome: "not_selected", reason_code: risk ? "reply_guarded" : null, messages: newMessages, confirmation: null, ticket: null };
    }

    if (path === "/api/customer/confirm") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const answer = body && body.answer;
      if (answer !== "confirm" && answer !== "cancel") throw httpError(400, "answer 只能是 confirm 或 cancel。", "invalid_answer");
      const claim = store.pendingConfirm[customerId];
      if (!claim) throw httpError(409, "当前没有待确认的提交。", "nothing_to_confirm");
      const messages = store.chats[customerId] || [];
      delete store.pendingConfirm[customerId];
      if (answer === "cancel") {
        messages.push({ role: "customer", text: "暂不提交" }, { role: "assistant", text: CANCELLED });
        store.chats[customerId] = messages;
        saveStore(store, { event: "customer_cancel", customer_id: customerId, order_id: claim.order_id });
        return { outcome: "claim_cancelled", reason_code: null, messages: [{ role: "customer", text: "暂不提交" }, { role: "assistant", text: CANCELLED }], confirmation: null, ticket: null };
      }
      const [, order] = lookupForCustomer(claim.order_id, customerId);
      if (!order) throw httpError(404, NOT_VERIFIED, "order_not_verified");
      const decision = evaluateOrder(order);
      const sub = computeSubrogation(order);
      let ticket = findTicketForOrder(store, claim.order_id, null);
      let created = false;
      if (!ticket) {
        created = true;
        const tid = `T${String(store.tickets.length + 1).padStart(4, "0")}`;
        const at = nowIso();
        const paidOk = Number(order.amount_yuan) >= Number(POLICY.coupon_yuan);
        const autoApprove = Boolean(store.stpAuto) && paidOk && sub.stp_tier === "STP_L1_GREEN";
        const autoNote = "准时保 STP 绿灯直通秒批：餐厅按时出餐（本店 ¥0 承担），由平台准时保池 100% 自动发放补偿券。";
        ticket = {
          ticket_id: tid,
          customer_id: customerId,
          order_id: order.order_id,
          policy_version: POLICY.version,
          expected_at: order.expected_at,
          delivered_at: order.delivered_at,
          late_seconds: decision.late_seconds,
          proposed_coupon_yuan: decision.proposed_coupon_yuan,
          status: autoApprove ? "approved" : "pending",
          coupon_issued_yuan: autoApprove ? decision.proposed_coupon_yuan : null,
          created_at: at,
          decided_at: autoApprove ? at : null,
          reviewer_id: autoApprove ? "STP_ENGINE" : null,
          review_note: autoApprove ? autoNote : null,
          prior_review_note: null,
          information_request: null,
          customer_information: null,
          rating: null,
          tenant_id: order.tenant_id || "M_67REST",
          stp_tier: sub.stp_tier,
          merchant_bear_yuan: sub.merchant_bear_yuan,
          platform_bear_yuan: sub.platform_bear_yuan,
          is_expedited: 0,
          escalated_to: null,
          assigned_reviewer_id: null,
        };
        store.tickets.push(ticket);
        pushTicketEvent(store, tid, { actor: `customer:${customerId}`, action: "submitted", note: null, at, after_status: "pending", amount_yuan: decision.proposed_coupon_yuan });
        if (autoApprove) {
          pushTicketEvent(store, tid, { actor: "system:STP_ENGINE", action: "approved", note: autoNote, at, before_status: "pending", after_status: "approved", amount_yuan: decision.proposed_coupon_yuan, issue_result: "issued" });
        }
      }
      const replyStr = ticketText(ticket, created);
      messages.push({ role: "customer", text: "确认提交" }, { role: "assistant", text: replyStr });
      store.chats[customerId] = messages;
      const outcome = !created ? "ticket_reused" : (ticket.status === "approved" ? "ticket_stp_approved" : "ticket_created");
      saveStore(store, { event: "customer_confirm", customer_id: customerId, order_id: order.order_id, ticket_id: ticket.ticket_id, outcome });
      return { outcome, reason_code: "eligible_for_review", messages: [{ role: "customer", text: "确认提交" }, { role: "assistant", text: replyStr }], confirmation: null, ticket: customerTicketCopy(ticket) };
    }

    if (path === "/api/customer/handoff") {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      let text = null;
      let focusOrderId = null;
      const files = [];
      if (body instanceof FormData) {
        const rawText = body.get("text");
        if (rawText && String(rawText).trim()) text = String(rawText).trim();
        const rawOid = body.get("order_id");
        if (rawOid && String(rawOid).trim()) focusOrderId = String(rawOid).trim();
        const uploads = body.getAll("attachment");
        for (const file of uploads) {
          if (!(file instanceof File)) continue;
          if (!file.size || file.size > 5 * 1024 * 1024) {
            throw httpError(413, "每个附件必须大于 0 且不超过 5 MB。", "media_too_large");
          }
          const mediaType = (file.type || "").split(";")[0].trim().toLowerCase();
          const buf = await file.arrayBuffer();
          const bytes = new Uint8Array(buf);
          if (!verifyMediaMagic(bytes, mediaType)) {
            throw httpError(415, "附件文件头校验未通过，请上传真实的图像或语音文件。", "corrupted_or_spoofed_media");
          }
          const sha = await sha256Hex(buf);
          const dataUrl = await readFileAsDataUrl(file);
          let priorAtt = null;
          for (const h of store.handoffs || []) {
            for (const a of h.attachments || []) {
              if (a.sha256_hash === sha) { priorAtt = a; break; }
            }
            if (priorAtt) break;
          }
          const baseNote = `文件魔数校验通过 · ${(file.size / 1024).toFixed(1)} KB`;
          files.push({
            attachment_id: `A${Date.now()}${Math.random().toString(16).slice(2, 6)}`,
            kind: mediaType.startsWith("audio/") || mediaType === "video/webm" ? "audio" : "image",
            original_name: (file.name || "凭证").slice(0, 120),
            media_type: mediaType,
            size_bytes: file.size,
            url: dataUrl,
            sha256_hash: sha,
            duplicate_alert: Boolean(priorAtt),
            forensic_note: priorAtt ? `⚠️ 重复图预警（与历史凭证 ${priorAtt.attachment_id.slice(0, 8)} SHA-256 精确一致） · ${baseNote}` : baseNote,
            created_at: nowIso(),
          });
        }
      } else if (body && typeof body === "object") {
        if (body.text && String(body.text).trim()) text = String(body.text).trim();
        if (body.order_id && String(body.order_id).trim()) focusOrderId = String(body.order_id).trim();
      }
      const res = openOrContinueHandoff(store, { threadId, customerId, text, files, focusOrderId });
      saveStore(store, { event: "handoff_request", customer_id: customerId, handoff_id: res.handoff.handoff_id });
      return res;
    }

    const cancelMatch = path.match(/^\/api\/customer\/handoffs\/([^/]+)\/cancel$/);
    if (cancelMatch) {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const hid = decodeURIComponent(cancelMatch[1]);
      const handoff = (store.handoffs || []).find((h) => h.handoff_id === hid && h.customer_id === customerId);
      if (!handoff) throw httpError(404, "当前账号下没有这条人工咨询。", "handoff_not_found");
      if (handoff.status !== "waiting") throw httpError(409, "这条人工咨询已经结束。", "handoff_closed");
      handoff.status = "cancelled";
      handoff.closed_at = nowIso();
      saveStore(store, { event: "handoff_cancel", customer_id: customerId, handoff_id: hid });
      return { handoff: handoffCustomerCopy(handoff, threadId) };
    }

    const endMatch = path.match(/^\/api\/customer\/handoffs\/([^/]+)\/end$/);
    if (endMatch) {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const hid = decodeURIComponent(endMatch[1]);
      const handoff = (store.handoffs || []).find((h) => h.handoff_id === hid && h.customer_id === customerId);
      if (!handoff || handoff.status === "cancelled") throw httpError(404, "当前账号下没有这条人工咨询。", "handoff_not_found");
      if (handoff.status === "waiting") { handoff.status = "cancelled"; handoff.closed_at = nowIso(); }
      else if (!handoff.ended_at) handoff.ended_at = nowIso();
      saveStore(store, { event: "handoff_end", customer_id: customerId, handoff_id: hid });
      return { handoff: handoffCustomerCopy(handoff, threadId) };
    }

    const custFollowupMatch = path.match(/^\/api\/customer\/handoffs\/([^/]+)\/followup$/);
    if (custFollowupMatch) {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const hid = decodeURIComponent(custFollowupMatch[1]);
      const handoff = (store.handoffs || []).find((h) => h.handoff_id === hid && h.customer_id === customerId);
      if (!handoff || handoff.status === "cancelled") throw httpError(404, "当前账号下没有这条人工咨询或已取消。", "handoff_not_found");
      const text = requireNote(body && body.text, "请填写追加留言内容。", 500);
      const curAfter = (store.chats[customerId] || []).length;
      appendHandoffFollowup(store, handoff, { sender_role: "customer", sender_id: customerId, text, after_index: curAfter });
      saveStore(store, { event: "customer_handoff_followup", customer_id: customerId, handoff_id: hid });
      return { handoff: handoffCustomerCopy(handoff, threadId) };
    }

    const infoMatch = path.match(/^\/api\/customer\/tickets\/([^/]+)\/information$/);
    if (infoMatch) {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tid = decodeURIComponent(infoMatch[1]);
      const ticket = store.tickets.find((t) => t.ticket_id === tid && t.customer_id === customerId);
      if (!ticket) throw httpError(404, "当前账号下没有这张工单。", "ticket_not_found");
      if (ticket.status !== "needs_info") throw httpError(409, "这份申请当前无需补充信息。", "information_not_requested");
      const text = requireNote(body && body.text, "请填写补充信息。", 500);
      ticket.status = "pending";
      ticket.customer_information = text;
      ticket.reviewer_id = null;
      pushTicketEvent(store, tid, { actor: `customer:${customerId}`, action: "information_submitted", note: text, before_status: "needs_info", after_status: "pending" });
      saveStore(store, { event: "customer_information", customer_id: customerId, ticket_id: tid });
      return { ticket: customerTicketCopy(ticket), timeline: store.events[tid] || [] };
    }

    const rateMatch = path.match(/^\/api\/customer\/tickets\/([^/]+)\/rating$/);
    if (rateMatch) {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tid = decodeURIComponent(rateMatch[1]);
      const rating = body && body.rating;
      if (typeof rating !== "number" || !Number.isInteger(rating) || rating < 1 || rating > 5) {
        throw httpError(400, "评分须为 1 到 5 的整数。", "invalid_rating");
      }
      const ticket = store.tickets.find((t) => t.ticket_id === tid && t.customer_id === customerId);
      if (!ticket) throw httpError(404, "当前账号下没有这张工单。", "ticket_not_found");
      if (!["approved", "rejected"].includes(ticket.status)) throw httpError(409, "审核完成后才能评价。", "ticket_not_decided");
      if (ticket.rating != null) throw httpError(409, "这份申请已经评价过。", "already_rated");
      ticket.rating = rating;
      pushTicketEvent(store, tid, { actor: `customer:${customerId}`, action: "rated", note: `${rating} 分` });
      saveStore(store, { event: "customer_rating", customer_id: customerId, ticket_id: tid, rating });
      return { ticket: customerTicketCopy(ticket), timeline: store.events[tid] || [] };
    }

    const custTicketMatch = path.match(/^\/api\/customer\/tickets\/([^/]+)$/);
    if (custTicketMatch) {
      if (!customerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tid = decodeURIComponent(custTicketMatch[1]);
      const ticket = store.tickets.find((t) => t.ticket_id === tid && t.customer_id === customerId);
      if (!ticket) throw httpError(404, "当前账号下没有这张工单。", "ticket_not_found");
      return { ticket: customerTicketCopy(ticket), timeline: (store.events[tid] || []).map((e) => ({ at: e.at, action: e.action, note: e.note })) };
    }

    // ---------------- Review Endpoints ----------------

    if (path === "/api/review/login") {
      const rid = body && body.reviewer_id;
      const reviewer = DEMO_DATA.reviewers.find((r) => r.reviewer_id === rid);
      if (!reviewer) throw httpError(400, "没有这个模拟审批员。", "unknown_reviewer");
      sessionStorage.setItem(SESSION_REV_KEY, rid);
      localStorage.setItem(SESSION_REV_KEY, rid);
      return { reviewer };
    }
    if (path === "/api/review/logout") {
      sessionStorage.removeItem(SESSION_REV_KEY);
      localStorage.removeItem(SESSION_REV_KEY);
      return { ok: true };
    }
    if (path === "/api/review/me") {
      const reviewer = DEMO_DATA.reviewers.find((r) => r.reviewer_id === reviewerId);
      if (!reviewer) throw httpError(401, "请先登录模拟账号。", "login_required");
      return { reviewer };
    }

    if (path === "/api/review/tickets") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tenantId = reviewerTenant(reviewerId);
      const scoped = store.tickets.filter((t) => tenantId === "*" || (t.tenant_id || "M_67REST") === tenantId);
      const enriched = scoped.map((t) => enrichReviewTicket(store, t));
      return {
        stp_auto_approve: Boolean(store.stpAuto),
        tenant_id: tenantId,
        pending: enriched.filter((t) => ["pending", "needs_info"].includes(t.status)),
        decided: enriched.filter((t) => ["approved", "rejected"].includes(t.status)),
      };
    }

    if (path === "/api/review/analytics") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tenantId = reviewerTenant(reviewerId);
      const scopedTickets = store.tickets.filter((t) => tenantId === "*" || (t.tenant_id || "M_67REST") === tenantId).map((t) => enrichReviewTicket(store, t));
      const scopedHandoffs = (store.handoffs || []).filter((h) => tenantId === "*" || (h.tenant_id || "M_67REST") === tenantId);
      const scopedGoodwills = (store.goodwills || []).filter((g) => tenantId === "*" || (g.tenant_id || "M_67REST") === tenantId);
      const approved = scopedTickets.filter((t) => t.status === "approved");
      const gwYuan = scopedGoodwills.reduce((acc, g) => acc + Number(g.amount_yuan || 0), 0);
      const pPool = approved.reduce((acc, t) => acc + Number(t.platform_bear_yuan || 0), 0) + gwYuan;
      const mCost = approved.reduce((acc, t) => acc + Number(t.merchant_bear_yuan || 0), 0);
      const ratings = scopedTickets.filter((t) => t.rating != null).map((t) => t.rating);
      const dups = scopedHandoffs.reduce((acc, h) => acc + (h.attachments || []).filter((a) => a.duplicate_alert).length, 0);
      return {
        tenant_id: tenantId,
        total_tickets: scopedTickets.length,
        stp_green_eligible: scopedTickets.filter((t) => t.stp_tier === "STP_L1_GREEN").length,
        goodwill_grants_count: scopedGoodwills.length,
        goodwill_issued_yuan: Math.round(gwYuan * 10) / 10,
        platform_subrogation_saved_yuan: Math.round(pPool * 10) / 10,
        merchant_net_cost_yuan: Math.round(mCost * 10) / 10,
        avg_csat: ratings.length ? Math.round((ratings.reduce((a, b) => a + b, 0) / ratings.length) * 100) / 100 : null,
        guardrail_intercepts: store.guardHits || 0,
        duplicate_evidence_alerts: dups,
        estimated_agent_yuan_saved: Math.round((scopedTickets.length + scopedGoodwills.length) * 6.5 * 10) / 10,
        audit_chain_intact: true,
        audit_entries: store.auditCount || 1,
      };
    }

    if (path === "/api/review/runs") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      return { runs: (store.auditLogs || []).slice(-100) };
    }

    if (path === "/api/review/stp-mode") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const rev = assertActionPermission(reviewerId, "ticket_approve");
      store.stpAuto = Boolean(body && body.enabled);
      let autoCleared = 0;
      if (store.stpAuto) {
        const tenantId = reviewerTenant(reviewerId);
        for (const t of store.tickets) {
          if (t.status !== "pending") continue;
          if (tenantId !== "*" && (t.tenant_id || "M_67REST") !== tenantId) continue;
          const enriched = enrichReviewTicket(store, t);
          if (enriched.stp_tier === "STP_L1_GREEN" || enriched.merchant_bear_yuan === 0) {
            const order = lookupOrder(t.order_id);
            try { validateIssueAmountAndRole(reviewerId, order, null, null, true); } catch (_) { continue; }
            const note = "平台准时保池 100% 直赔（本店按时出餐 ¥0 承担）";
            decideOrOverrideTicket(store, t, { target_status: "approved", reviewer_id: reviewerId, note, amount_yuan: POLICY.coupon_yuan, merchant_bear_yuan: 0, platform_bear_yuan: POLICY.coupon_yuan, action_name: "approved", issue_result: "issued" });
            logAction(store, { order_id: t.order_id, ticket_id: t.ticket_id, actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role, action: "approve", action_label: "审核通过", before_status: "pending", after_status: "approved", amount_yuan: POLICY.coupon_yuan, note, issue_result: "issued" });
            autoCleared += 1;
          }
        }
      }
      saveStore(store, { event: "stp_mode_changed", reviewer_id: reviewerId, outcome: store.stpAuto ? "enabled" : "disabled", auto_cleared_count: autoCleared });
      return { stp_auto_approve: store.stpAuto, auto_cleared_count: autoCleared };
    }

    if (path === "/api/review/stp-batch") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const rev = assertActionPermission(reviewerId, "ticket_approve");
      const tenantId = reviewerTenant(reviewerId);
      const approvedIds = [];
      const skippedIds = [];
      for (const t of store.tickets) {
        if (t.status !== "pending") continue;
        if (tenantId !== "*" && (t.tenant_id || "M_67REST") !== tenantId) continue;
        const enriched = enrichReviewTicket(store, t);
        if (enriched.stp_tier === "STP_L1_GREEN" || enriched.merchant_bear_yuan === 0) {
          const order = lookupOrder(t.order_id);
          try { validateIssueAmountAndRole(reviewerId, order, null, null, true); } catch (_) { skippedIds.push(t.ticket_id); continue; }
          const note = "平台准时保池 100% 直赔（本店按时出餐 ¥0 承担）";
          decideOrOverrideTicket(store, t, { target_status: "approved", reviewer_id: reviewerId, note, amount_yuan: POLICY.coupon_yuan, merchant_bear_yuan: 0, platform_bear_yuan: POLICY.coupon_yuan, action_name: "approved", issue_result: "issued" });
          logAction(store, { order_id: t.order_id, ticket_id: t.ticket_id, actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role, action: "approve", action_label: "审核通过", before_status: "pending", after_status: "approved", amount_yuan: POLICY.coupon_yuan, note, issue_result: "issued" });
          approvedIds.push(t.ticket_id);
        }
      }
      saveStore(store, { event: "stp_batch", reviewer_id: reviewerId, count: approvedIds.length });
      return { approved_ticket_ids: approvedIds, skipped_ticket_ids: skippedIds, count: approvedIds.length };
    }

    if (path === "/api/review/handoffs") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tenantId = reviewerTenant(reviewerId);
      const scoped = (store.handoffs || []).filter((h) => tenantId === "*" || (h.tenant_id || "M_67REST") === tenantId);
      const items = scoped.map((h) => reviewHandoffItem(store, h));
      const waiting = items
        .filter((h) => h.status === "waiting")
        .sort((a, b) => {
          const pa = a.priority === "P0_FOOD_SAFETY" ? 0 : 1;
          const pb = b.priority === "P0_FOOD_SAFETY" ? 0 : 1;
          if (pa !== pb) return pa - pb;
          const ea = a.is_expedited ? 0 : 1;
          const eb = b.is_expedited ? 0 : 1;
          if (ea !== eb) return ea - eb;
          return a.handoff_id.localeCompare(b.handoff_id);
        });
      return {
        waiting,
        closed: items.filter((h) => h.status !== "waiting").slice(-50),
      };
    }

    const revTicketMatch = path.match(/^\/api\/review\/tickets\/([^/]+)$/);
    if (revTicketMatch) {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tid = decodeURIComponent(revTicketMatch[1]);
      const ticket = store.tickets.find((t) => t.ticket_id === tid);
      if (!ticket) throw httpError(404, "没有这张工单。", "ticket_not_found");
      assertTenantAccess(reviewerId, ticket.tenant_id);
      return {
        ticket: enrichReviewTicket(store, ticket),
        events: store.events[tid] || [],
        action_logs: getActionLogs(store, { ticket_id: tid, include_internal: true }),
      };
    }

    const reopenMatch = path.match(/^\/api\/review\/tickets\/([^/]+)\/reopen$/);
    if (reopenMatch) {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const rev = assertActionPermission(reviewerId, "ticket_reopen");
      const tid = decodeURIComponent(reopenMatch[1]);
      const ticket = store.tickets.find((t) => t.ticket_id === tid);
      if (!ticket) throw httpError(404, "没有这张工单。", "ticket_not_found");
      assertTenantAccess(reviewerId, ticket.tenant_id);
      const [cleanedNote, validatedRt] = validateReconsideration(store, ticket, body && body.note, body && body.reason_type);
      const beforeAmt = ticket.coupon_issued_yuan ?? null;
      const [, beforeSt] = decideOrOverrideTicket(store, ticket, {
        target_status: "pending", reviewer_id: reviewerId, note: cleanedNote,
        action_name: "reopened", reason_type: validatedRt, issue_result: "reconsidered_to_pending",
      });
      logAction(store, {
        order_id: ticket.order_id, ticket_id: tid, actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role,
        action: "reopen", action_label: "发起重审", before_status: beforeSt, after_status: "pending",
        before_amount_yuan: beforeAmt, note: cleanedNote, reason_type: validatedRt, issue_result: "reconsidered_to_pending",
      });
      saveStore(store, { event: "review_reopen", reviewer_id: reviewerId, ticket_id: tid, reason_type: validatedRt });
      return { ticket: enrichReviewTicket(store, ticket), events: store.events[tid] || [] };
    }

    const decideMatch = path.match(/^\/api\/review\/tickets\/([^/]+)\/decision$/);
    if (decideMatch) {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const tid = decodeURIComponent(decideMatch[1]);
      const decision = body && body.decision;
      if (!decision || !(decision in DECISION_STATUS)) throw httpError(400, "不支持这个处理操作。", "invalid_decision");
      const permKey = { approve: "ticket_approve", reject: "ticket_reject", request_info: "ticket_request_info" }[decision];
      const rev = assertActionPermission(reviewerId, permKey);
      let note = body && body.note;
      if (decision === "request_info") {
        note = requireNote(note, "请填写需要顾客补充的内容。", 200);
      }

      const current = store.tickets.find((t) => t.ticket_id === tid);
      if (!current) throw httpError(404, "没有这张工单。", "ticket_not_found");
      assertTenantAccess(reviewerId, current.tenant_id);
      const order = lookupOrder(current.order_id);

      let amtVal = null;
      let mBear = null;
      let pBear = null;
      if (decision === "approve") {
        const [vAmt, cleanedNote] = validateIssueAmountAndRole(reviewerId, order, body && body.amount_yuan, note, true);
        amtVal = vAmt;
        const existingComp = compensatedForOrder(store, current.order_id);
        if (existingComp) {
          logAction(store, {
            order_id: existingComp.order_id, ticket_id: existingComp.ticket_id,
            actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role,
            action: "approve_deduplicated", action_label: "重复审批拦截",
            before_status: "approved", after_status: "approved",
            before_amount_yuan: existingComp.coupon_issued_yuan, amount_yuan: existingComp.coupon_issued_yuan,
            note: cleanedNote || "已有唯一补偿记录，返回原状态未重复发券", issue_result: "already_compensated_no_new_issue",
          });
          saveStore(store);
          throw httpError(409, `该订单已完成唯一补偿发放（¥${existingComp.coupon_issued_yuan}），返回已有状态且不重复发券。`, "ticket_already_decided", {
            deduplicated: true, issue_result: "already_compensated_no_new_issue", existing_status: existingComp.status, ticket: enrichReviewTicket(store, existingComp),
          });
        }
        note = cleanedNote || `人工审核通过，按标准发放 ¥${amtVal} 无门槛补偿券。`;
        const sub = order ? computeSubrogation(order) : {};
        const origProp = Math.max(1, Number(current.proposed_coupon_yuan || amtVal));
        const mOrig = Number(sub.merchant_bear_yuan || 0);
        const ratio = Math.min(1, mOrig / origProp);
        mBear = Math.round(amtVal * ratio * 10) / 10;
        pBear = Math.round(Math.max(0, amtVal - mBear) * 10) / 10;
      } else if (compensatedForOrder(store, current.order_id)) {
        throw httpError(409, "该订单已完成唯一补偿发放，不支持撤回或变更状态。", "already_compensated_immutable");
      }

      if (current.status === "needs_info") throw httpError(409, "正在等待顾客补充信息。", "customer_information_pending");
      if (current.status !== "pending") {
        throw httpError(409, "这张工单已经处理过（已驳回工单需先填写原因发起重审后再审批）。", "ticket_already_decided", {
          existing_status: current.status, ticket: enrichReviewTicket(store, current),
        });
      }
      if (decision === "reject") {
        note = optionalNote(note, "经人工复核暂不符合本次补偿条件，如有疑问可转人工继续咨询此订单。", 200);
      }

      const beforeAmt = current.coupon_issued_yuan ?? null;
      const targetStatus = DECISION_STATUS[decision];
      const labelMap = { approve: "审核通过", reject: "审核驳回", request_info: "要求补充材料" };
      const issueRes = decision === "approve" ? "issued" : "no_issue";
      decideOrOverrideTicket(store, current, {
        target_status: targetStatus, reviewer_id: reviewerId, note,
        amount_yuan: amtVal, merchant_bear_yuan: mBear, platform_bear_yuan: pBear,
        action_name: targetStatus === "needs_info" ? "information_requested" : targetStatus,
        issue_result: issueRes,
      });
      logAction(store, {
        order_id: current.order_id, ticket_id: tid, actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role,
        action: decision, action_label: labelMap[decision], before_status: "pending", after_status: current.status,
        before_amount_yuan: beforeAmt, amount_yuan: current.coupon_issued_yuan ?? null, note, issue_result: issueRes,
      });
      saveStore(store, { event: "review_decision", reviewer_id: reviewerId, ticket_id: tid, outcome: current.status, amount_yuan: current.coupon_issued_yuan });
      return { ticket: enrichReviewTicket(store, current), events: store.events[tid] || [], deduplicated: false, issue_result: issueRes };
    }

    const replyHandoffMatch = path.match(/^\/api\/review\/handoffs\/([^/]+)\/reply$/);
    if (replyHandoffMatch) {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const rev = assertActionPermission(reviewerId, "handoff_reply");
      const hid = decodeURIComponent(replyHandoffMatch[1]);
      const handoff = (store.handoffs || []).find((h) => h.handoff_id === hid);
      if (!handoff) throw httpError(404, "没有这条人工咨询。", "handoff_not_found");
      assertTenantAccess(reviewerId, handoff.tenant_id);
      if (handoff.status !== "waiting") throw httpError(409, "顾客已取消，或这条咨询已经回复。", "handoff_closed");
      const text = requireNote(body && body.text, "请填写回复内容。", 500);
      const curAfter = (store.chats[handoff.customer_id] || []).length;
      const fups = handoff.followups || [];
      handoff.status = "replied";
      handoff.reply_text = text;
      handoff.reviewer_id = reviewerId;
      handoff.closed_at = nowIso();
      handoff.reply_after_index = curAfter;
      handoff.reply_seq = fups.reduce((m, f) => Math.max(m, f.message_id || 0), 0);
      logAction(store, {
        handoff_id: hid, order_id: handoff.order_id, actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role,
        action: "handoff_reply", action_label: "首次回复顾客", before_status: "waiting", after_status: "replied", note: text.slice(0, 120),
      });
      saveStore(store, { event: "handoff_reply", reviewer_id: reviewerId, handoff_id: hid });
      return { handoff: reviewHandoffItem(store, handoff) };
    }

    const followupMatch = path.match(/^\/api\/review\/handoffs\/([^/]+)\/followup$/);
    if (followupMatch) {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const rev = assertActionPermission(reviewerId, "handoff_reply");
      const hid = decodeURIComponent(followupMatch[1]);
      const handoff = (store.handoffs || []).find((h) => h.handoff_id === hid);
      if (!handoff || handoff.status === "cancelled") throw httpError(404, "没有这条人工咨询或顾客已取消。", "handoff_not_found");
      assertTenantAccess(reviewerId, handoff.tenant_id);
      const text = requireNote(body && body.text, "请填写追回内容。", 500);
      const beforeSt = handoff.status;
      const curAfter = (store.chats[handoff.customer_id] || []).length;
      appendHandoffFollowup(store, handoff, { sender_role: "reviewer", sender_id: reviewerId, text, after_index: curAfter });
      logAction(store, {
        handoff_id: hid, order_id: handoff.order_id, actor_id: reviewerId, actor_name: rev.display_name, actor_role: rev.role,
        action: "handoff_followup", action_label: "追加跟进回复", before_status: beforeSt, after_status: handoff.status, note: text.slice(0, 120),
      });
      saveStore(store, { event: "handoff_followup", reviewer_id: reviewerId, handoff_id: hid });
      return { handoff: reviewHandoffItem(store, handoff) };
    }

    const actionMatch = path.match(/^\/api\/review\/handoffs\/([^/]+)\/action$/);
    if (actionMatch) {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const hid = decodeURIComponent(actionMatch[1]);
      const payload = body || {};
      const action = payload.action;
      if (action === "change_amount" || action === "top_up") {
        assertActionPermission(reviewerId, "ticket_approve");
        throw httpError(409, "已成功发放补偿的订单遵循一单一赔，不支持事后改额或补差价。", "post_issue_amount_change_disallowed");
      }
      const permMap = {
        approve_compensation: ["ticket_approve", "同意补偿"],
        approve: ["ticket_approve", "通过申请"],
        uphold_reject: ["ticket_reject", "维持驳回"],
        reject: ["ticket_reject", "驳回申请"],
        request_info: ["ticket_request_info", "要求补充材料"],
        escalate: ["ticket_escalate", "升级主管"],
        expedite: ["ticket_expedite", "加急处理"],
        transfer: ["ticket_transfer", "转交他席"],
        reopen: ["ticket_reopen", "发起重审"],
        urge_or_reassign: ["order_urge", "催单/改派"],
        internal_note: ["order_note", "内部备注"],
        create_ticket: ["order_ticket", "创建工单"],
        close_session: ["handoff_close", "结束会话"],
      };
      if (typeof action !== "string" || !(action in permMap)) {
        throw httpError(400, "不支持这个处理动作。", "invalid_action");
      }
      const [perm, defaultLabel] = permMap[action];
      let actionLabel = defaultLabel;
      const rev = assertActionPermission(reviewerId, perm);
      const actorName = rev.display_name || reviewerId;
      const actorRole = rev.role || "agent";

      const handoff = (store.handoffs || []).find((h) => h.handoff_id === hid);
      if (!handoff) throw httpError(404, "没有这条人工咨询。", "handoff_not_found");
      assertTenantAccess(reviewerId, handoff.tenant_id);
      if (handoff.status === "cancelled") throw httpError(409, "顾客已取消这条人工咨询。", "handoff_cancelled");

      const oid = handoff.order_id || null;
      const order = oid ? lookupOrder(oid) : null;
      let ticket = oid ? findTicketForOrder(store, oid, POLICY.version) : null;
      let tid = ticket ? ticket.ticket_id : null;

      let sysMsg = null;
      let beforeSt = null;
      let afterSt = null;
      const beforeAmt = ticket ? (ticket.coupon_issued_yuan ?? null) : null;
      let amtVal = null;
      let logNote = null;
      let reasonType = null;
      let issueResult = null;
      let isInternal = false;
      let transitionReplied = false;
      let closeSession = false;

      if (action === "approve_compensation" || action === "approve") {
        if (!order) throw httpError(409, "当前会话未关联具体订单，无法执行补偿审批。", "ticket_required");
        if (payload.intent === "change_amount" || payload.intent === "top_up") {
          throw httpError(409, "已成功发放补偿的订单不支持事后改额或补差价。", "post_issue_amount_change_disallowed");
        }
        let [vAmt, cleanedNote] = validateIssueAmountAndRole(reviewerId, order, payload.amount_yuan, payload.note, true);
        amtVal = vAmt;
        const existingComp = compensatedForOrder(store, oid);
        if (existingComp || (ticket && ticket.status === "approved" && ticket.coupon_issued_yuan != null)) {
          const compT = existingComp || ticket;
          logAction(store, {
            handoff_id: hid, order_id: oid, ticket_id: compT.ticket_id, actor_id: reviewerId, actor_name: actorName, actor_role: actorRole,
            action, action_label: "重复审批拦截", before_status: "approved", after_status: "approved",
            before_amount_yuan: compT.coupon_issued_yuan, amount_yuan: compT.coupon_issued_yuan,
            note: cleanedNote || "已有唯一补偿记录，返回原状态未重复发券", issue_result: "already_compensated_no_new_issue",
          });
          saveStore(store);
          throw httpError(409, `该订单已完成唯一补偿发放（¥${compT.coupon_issued_yuan}），返回已有结果且不重复发券。`, "ticket_already_approved", {
            deduplicated: true, issue_result: "already_compensated_no_new_issue", existing_status: compT.status, ticket: enrichReviewTicket(store, compT),
          });
        }
        if (ticket && ticket.status === "rejected") {
          [cleanedNote, reasonType] = validateReconsideration(store, ticket, payload.note, payload.reason_type);
        }
        if (!ticket) {
          const dec = evaluateOrder(order);
          const subInit = computeSubrogation(order);
          [ticket] = createManualTicket(store, {
            customerId: handoff.customer_id, order, lateSeconds: dec.late_seconds || 0,
            proposedCouponYuan: amtVal, reviewerId, subrogation: subInit,
            note: "人工客服审批补偿时自动补建订单申请单",
          });
          tid = ticket.ticket_id;
        }
        logNote = cleanedNote || `人工客服核实通过，发放 ¥${amtVal} 无门槛补偿券。`;
        const sub = computeSubrogation(order);
        const origProp = Math.max(1, Number(ticket.proposed_coupon_yuan || amtVal));
        const mOrig = Number(sub.merchant_bear_yuan || 0);
        const ratio = Math.min(1, mOrig / origProp);
        const mBear = Math.round(amtVal * ratio * 10) / 10;
        const pBear = Math.round(Math.max(0, amtVal - mBear) * 10) / 10;
        [, beforeSt] = decideOrOverrideTicket(store, ticket, {
          target_status: "approved", reviewer_id: reviewerId, note: logNote,
          amount_yuan: amtVal, merchant_bear_yuan: mBear, platform_bear_yuan: pBear,
          action_name: "approved", reason_type: reasonType, issue_result: "issued",
        });
        afterSt = "approved";
        issueResult = "issued";
        sysMsg = `系统通知：客服已通过补偿申请（订单 ${oid} · 申请单 ${tid} · 人工处理单 ${hid}），¥${amtVal} 无门槛补偿券已发放至您的账户（即时到账）。说明：${logNote}`;
        transitionReplied = true;
      } else if (action === "uphold_reject" || action === "reject") {
        if (oid && compensatedForOrder(store, oid)) {
          throw httpError(409, "该订单已完成补偿发放，不可改为驳回。", "already_compensated_immutable");
        }
        logNote = requireNote(payload.note, "驳回或维持驳回必须填写具体理由（顾客可见）。");
        if (!ticket) {
          if (action === "reject" && order) {
            const dec = evaluateOrder(order);
            const subInit = computeSubrogation(order);
            [ticket] = createManualTicket(store, {
              customerId: handoff.customer_id, order, lateSeconds: dec.late_seconds || 0,
              proposedCouponYuan: dec.proposed_coupon_yuan || POLICY.coupon_yuan,
              reviewerId, subrogation: subInit, note: "人工客服驳回时自动补建订单申请单",
            });
            tid = ticket.ticket_id;
          } else {
            throw httpError(409, "当前订单尚无关联申请单。", "ticket_required");
          }
        }
        if (action === "reject" && !["pending", "needs_info"].includes(ticket.status)) {
          throw httpError(409, "当前申请单状态不支持直接驳回。", "invalid_ticket_state");
        }
        if (action === "uphold_reject" && ticket.status !== "rejected") {
          throw httpError(409, "仅「已驳回」状态的申请单可执行维持驳回。", "invalid_ticket_state");
        }
        [, beforeSt] = decideOrOverrideTicket(store, ticket, {
          target_status: "rejected", reviewer_id: reviewerId, note: logNote,
          action_name: action === "uphold_reject" ? "uphold_rejected" : "rejected", issue_result: "no_issue",
        });
        afterSt = "rejected";
        issueResult = "no_issue";
        sysMsg = `系统通知：客服已${action === "uphold_reject" ? "维持驳回" : "驳回"}申请（订单 ${oid} · 申请单 ${tid} · 人工处理单 ${hid}），理由：${logNote}`;
        transitionReplied = true;
      } else if (action === "request_info") {
        if (!ticket) throw httpError(409, "当前订单尚无关联申请单。", "ticket_required");
        if (compensatedForOrder(store, ticket.order_id) || ticket.status === "approved") {
          throw httpError(409, "该订单已完成补偿发放，不支持要求补充材料。", "already_compensated_immutable");
        }
        if (!["rejected", "pending"].includes(ticket.status)) {
          throw httpError(409, "当前申请单状态不支持要求补充材料。", "invalid_ticket_state");
        }
        if (ticket.status === "rejected") {
          [logNote, reasonType] = validateReconsideration(store, ticket, payload.note, payload.reason_type);
        } else {
          logNote = requireNote(payload.note, "请填写需要顾客补充的材料或说明。");
        }
        [, beforeSt] = decideOrOverrideTicket(store, ticket, {
          target_status: "needs_info", reviewer_id: reviewerId, note: logNote,
          action_name: "information_requested", reason_type: reasonType, issue_result: "no_issue",
        });
        afterSt = "needs_info";
        issueResult = "no_issue";
        sysMsg = `系统通知：客服已发起补充材料要求（${tid}）：${logNote}。请在右侧申请单卡片填写并提交。`;
        transitionReplied = true;
      } else if (action === "escalate") {
        logNote = optionalNote(payload.note, "已升级主管专席复核处理");
        beforeSt = ticket ? ticket.status : handoff.status;
        afterSt = `${beforeSt}(已升级主管)`;
        handoff.escalated_to = "主管专席";
        handoff.is_expedited = 1;
        if (ticket) {
          ticket.escalated_to = "主管专席";
          ticket.is_expedited = 1;
          pushTicketEvent(store, tid, { actor: `reviewer:${reviewerId}`, action: "escalated", note: logNote, before_status: beforeSt, after_status: afterSt });
        }
        sysMsg = `系统通知：本次咨询已升级主管专席加急复核（${logNote}）。`;
      } else if (action === "expedite") {
        logNote = optionalNote(payload.note, "已标记为加急优先处理");
        beforeSt = ticket ? ticket.status : handoff.status;
        afterSt = `${beforeSt}(加急)`;
        handoff.is_expedited = 1;
        if (ticket) {
          ticket.is_expedited = 1;
          pushTicketEvent(store, tid, { actor: `reviewer:${reviewerId}`, action: "expedited", note: logNote, before_status: beforeSt, after_status: afterSt });
        }
        sysMsg = `系统通知：客服已将该处理申请标记为加急优先（${logNote}）。`;
      } else if (action === "transfer") {
        const targetId = payload.target_reviewer_id || (reviewerId !== "R002" ? "R002" : "R001");
        const targetRev = DEMO_DATA.reviewers.find((r) => r.reviewer_id === targetId);
        if (!targetRev || targetRev.can_handle === false) {
          throw httpError(400, "目标坐席不存在或无处理权限。", "invalid_transfer_target");
        }
        logNote = optionalNote(payload.note, `转交至 ${targetRev.display_name}`);
        beforeSt = handoff.assigned_reviewer_id || handoff.reviewer_id || reviewerId;
        afterSt = targetId;
        handoff.assigned_reviewer_id = targetId;
        handoff.reviewer_id = handoff.reviewer_id || targetId;
        if (ticket) {
          ticket.assigned_reviewer_id = targetId;
          pushTicketEvent(store, tid, { actor: `reviewer:${reviewerId}`, action: "transferred", note: `转交 ${targetRev.display_name}：${logNote}`, before_status: beforeSt, after_status: afterSt });
        }
        sysMsg = `系统通知：会话已转交至 ${targetRev.display_name} 继续为您处理。`;
      } else if (action === "reopen") {
        if (!ticket) throw httpError(409, "当前订单尚无关联申请单。", "ticket_required");
        [logNote, reasonType] = validateReconsideration(store, ticket, payload.note, payload.reason_type);
        [, beforeSt] = decideOrOverrideTicket(store, ticket, {
          target_status: "pending", reviewer_id: reviewerId, note: logNote,
          action_name: "reopened", reason_type: reasonType, issue_result: "reconsidered_to_pending",
        });
        afterSt = "pending";
        issueResult = "reconsidered_to_pending";
        sysMsg = `系统通知：客服已沿原申请单（${tid}）发起重审，状态恢复为待审核。重审原因：${logNote}`;
      } else if (action === "urge_or_reassign") {
        if (!order) throw httpError(400, "当前会话未关联具体订单，无法执行催单/改派。", "order_required");
        const mode = payload.mode || "urge";
        actionLabel = mode === "reassign" ? "改派运力" : "催单提醒";
        logNote = optionalNote(payload.note, `已向配送站点发起${actionLabel}（订单 ${oid}）`);
        beforeSt = order.status || "delivered";
        afterSt = mode === "reassign" ? "已改派" : "已催单";
        sysMsg = `系统通知：客服已对订单 ${oid} 发起「${actionLabel}」，${logNote}。`;
      } else if (action === "internal_note") {
        logNote = requireNote(payload.note, "请填写内部备注内容。", 300);
        beforeSt = ticket ? ticket.status : handoff.status;
        afterSt = beforeSt;
        isInternal = true;
      } else if (action === "create_ticket") {
        if (!order) throw httpError(400, "当前会话未关联具体订单，无法创建工单。", "order_required");
        if (ticket) throw httpError(409, `该订单已存在申请单 ${tid}，请直接沿原单处理。`, "ticket_already_exists");
        const hasExplicitAmt = payload.amount_yuan !== undefined && payload.amount_yuan !== null && payload.amount_yuan !== "";
        const [vAmt, cleanedNote] = validateIssueAmountAndRole(reviewerId, order, payload.amount_yuan, payload.note, hasExplicitAmt);
        amtVal = vAmt;
        const dec = evaluateOrder(order);
        const sub = computeSubrogation(order);
        logNote = cleanedNote || "人工客服在会话内为顾客创建售后申请单";
        [ticket] = createManualTicket(store, {
          customerId: handoff.customer_id, order, lateSeconds: dec.late_seconds || 0,
          proposedCouponYuan: amtVal, reviewerId, subrogation: sub, note: logNote,
        });
        tid = ticket.ticket_id;
        beforeSt = "无工单";
        afterSt = ticket.status;
        issueResult = "pending_review";
        sysMsg = `系统通知：客服已为您创建售后申请单 ${tid}（订单 ${oid}，建议补偿 ¥${amtVal}），正在审核处理。`;
      } else if (action === "close_session") {
        if (handoff.ended_at) throw httpError(409, "该人工会话已经结束。", "handoff_already_closed");
        logNote = optionalNote(payload.note, "问题已核实处理完毕，本次人工服务结束");
        beforeSt = handoff.status;
        afterSt = "ended";
        sysMsg = `系统通知：人工客服已结束本次服务（${logNote}）。如需继续咨询可随时发消息。`;
        transitionReplied = true;
        closeSession = true;
      }

      if (sysMsg) {
        const curAfter = (store.chats[handoff.customer_id] || []).length;
        appendHandoffFollowup(store, handoff, { sender_role: "system", sender_id: reviewerId, text: sysMsg, after_index: curAfter });
      }
      if (transitionReplied || closeSession) {
        transitionHandoffStatus(store, handoff, reviewerId, closeSession);
      }
      const actionLog = logAction(store, {
        handoff_id: hid, order_id: oid, ticket_id: tid,
        actor_id: reviewerId, actor_name: actorName, actor_role: actorRole,
        action, action_label: actionLabel, before_status: beforeSt, after_status: afterSt,
        before_amount_yuan: beforeAmt, amount_yuan: amtVal, note: logNote,
        reason_type: reasonType, issue_result: issueResult, is_internal: isInternal,
      });
      saveStore(store, { event: "handoff_action", reviewer_id: reviewerId, handoff_id: hid, action, outcome: afterSt, amount_yuan: amtVal });
      return {
        handoff: reviewHandoffItem(store, handoff),
        ticket: ticket ? enrichReviewTicket(store, ticket) : null,
        action_log: actionLog,
        deduplicated: false,
        issue_result: issueResult,
      };
    }

    if (path === "/api/review/reset") {
      if (!reviewerId) throw httpError(401, "请先登录模拟账号。", "login_required");
      const fresh = defaultStore();
      fresh.auditCount = (store.auditCount || 1) + 1;
      fresh.auditLogs = [...(store.auditLogs || []), { at: nowIso(), event: "reset", reviewer_id: reviewerId }];
      localStorage.setItem(STORE_KEY, JSON.stringify(fresh));
      return { ok: true };
    }

    throw httpError(404, `未知接口 ${path}`, "not_found");
  };
})();
