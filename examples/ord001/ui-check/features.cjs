const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

// Browser check for the 2026-11-11 additions. It resets the demo data several times: run it against a
// separate scripted server, never against the one used for a live demo.
const base = process.argv[2] || 'http://127.0.0.1:8031';
const evidence = process.argv[3];
if (!evidence) throw new Error('Usage: node features.cjs URL EVIDENCE_DIRECTORY');
const results = [];
const errors = [];

(async () => {
  await fs.mkdir(evidence, { recursive: true });
  const browser = await chromium.launch(process.env.PLAYWRIGHT_CHROME ? { executablePath: process.env.PLAYWRIGHT_CHROME, headless: true } : { channel: 'chrome', headless: true });
  const watch = page => {
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error' && !message.text().includes('401')) errors.push(message.text()); });
    page.on('response', response => { if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`); });
  };
  const shot = async (page, name) => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300); // let tab and toast transitions finish so the picture matches the state
    return page.screenshot({ path: path.join(evidence, name), fullPage: true });
  };
  const noOverflow = async (page, label) => assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${label} overflows`);
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, colorScheme: 'light' });
    const customer = await context.newPage();
    const reviewer = await context.newPage();
    watch(customer); watch(reviewer);
    const state = async () => (await context.request.get(`${base}/api/customer/state`)).json();
    const idle = page => page.waitForFunction(() => !document.body.classList.contains('is-working'));
    const posting = (page, suffix) => page.waitForResponse(response => response.url() === `${base}${suffix}` && response.request().method() === 'POST');
    const journey = async () => customer.locator('#journey .current strong').innerText();
    const tickets = async () => customer.locator('#tickets').innerText();
    const consult = async orderId => {
      await customer.locator('#order-search').fill(orderId);
      const sent = posting(customer, '/api/customer/messages');
      await customer.locator(`#orders .order[data-order-id="${orderId}"]`).getByRole('button', { name: '咨询', exact: true }).click();
      await sent;
      await idle(customer);
      await customer.locator('#order-search').fill('');
    };
    const send = async text => {
      await customer.locator('#input').fill(text);
      const sent = posting(customer, '/api/customer/messages');
      await customer.locator('#send').click();
      await sent;
      await idle(customer);
    };
    const decide = async (name, note) => {
      await reviewer.locator('#tab-pending').click();
      await reviewer.locator('#pending textarea').waitFor();
      await reviewer.locator('#pending textarea').fill(note);
      await reviewer.getByRole('button', { name, exact: true }).click();
      await reviewer.locator('#decided-panel').waitFor();
    };
    const toast = expected => customer.waitForFunction(text => {
      const node = document.getElementById('toast');
      return node.classList.contains('show') && node.textContent.includes(text);
    }, expected, { timeout: 10000 });
    const login = async () => {
      await customer.getByRole('button', { name: '模拟顾客 U001', exact: true }).click();
      await customer.locator('#app').waitFor();
    };
    // The line under the chat box only ever shows a sentence or nothing.
    const cleanStatus = async () => {
      const text = await customer.locator('#status').textContent();
      assert(!/object|undefined|null/i.test(text), `Status line shows "${text}"`);
    };

    await customer.goto(base);
    await login();
    await reviewer.goto(`${base}/review`);
    await reviewer.getByRole('button', { name: '模拟审批员 R001', exact: true }).click();
    await reviewer.locator('#app').waitFor();
    if (!await reviewer.locator('#reset').isVisible()) await reviewer.locator('#meta').click();
    await reviewer.locator('#reset').click();
    await reviewer.locator('#reset-confirm').click();
    await reviewer.waitForFunction(() => !document.getElementById('reset-dialog').open);
    await customer.locator('#tickets .empty').waitFor();
    assert((await customer.locator('#messages .welcome-note').innerText()).includes('不是真人'));
    assert.equal(await customer.locator('.chat-caption').innerText(), 'AI 客服 · 非真人');
    assert.equal(await customer.locator('#handoff-label').innerText(), '转人工');
    results.push({ case: 'AI identity shown before the first message, handoff button always visible', status: 'passed' });

    await consult('ORD001');
    await customer.locator('#confirm').waitFor();
    assert.equal(await customer.locator('#tickets [data-focus-order="ORD001"]').count(), 1);
    assert((await tickets()).includes('待你确认'));
    assert.match(await journey(), /确认/);
    assert.equal(await customer.locator('#messages .bubble-row.assistant .bubble-tag').first().innerText(), 'AI');
    await customer.locator('#confirm-yes').click();
    await customer.locator('#tickets .badge-pending').waitFor();
    await idle(customer);
    await cleanStatus();
    assert((await tickets()).includes('预计 24 小时内处理'));
    await decide('通过', '已核实晚到 50 分钟。');
    await customer.locator('#tickets .badge-approved').waitFor();
    await toast('ORD001 审核通过，¥10 补偿券已发放');
    results.push({ case: 'Status change shows a toast; pending card states the 24-hour target', status: 'passed' });

    // The reported bug: after ORD001 was approved, asking about another order still showed ORD001.
    await consult('ORD002');
    const ord002 = customer.locator('#tickets [data-focus-order="ORD002"]');
    await ord002.waitFor();
    const panel = await tickets();
    assert(panel.includes('未达到申请条件') && panel.includes('晚到 10 分钟'), panel);
    assert(!panel.includes('ORD001') && !panel.includes('T0001'), `ORD002 panel still shows ORD001: ${panel}`);
    assert.equal(await customer.locator('#tickets .badge-approved').count(), 0);
    assert.match(await journey(), /核实/);
    assert((await customer.locator('#ticket-others').innerText()).includes('其他申请 · 1'));
    await customer.locator('#ticket-others summary').click();
    assert((await customer.locator('#ticket-others').innerText()).includes('已通过'));
    assert.equal(await customer.locator('#orders .order.is-focus').getAttribute('data-order-id'), 'ORD002');
    await shot(customer, 'focus-ord002-after-ord001.png');
    await customer.locator('#ticket-others .other-ticket').first().click();
    await customer.locator('#tickets .badge-approved').waitFor();
    assert.match(await journey(), /结果/);
    await customer.locator('#ticket-others .back-focus').click();
    await ord002.waitFor();
    await send('ORD101');
    await customer.locator('#tickets [data-focus-order="ORD101"]').waitFor();
    const foreign = await tickets();
    assert(foreign.includes('无法核实这笔订单') && !foreign.includes('18:') && !foreign.includes('模拟餐厅') && !foreign.includes('67餐厅'), foreign);
    assert(await customer.locator('#order-picks').isVisible(), 'Order choices missing after an unverified order');
    results.push({ case: 'After ORD001 is approved, asking about ORD002 / ORD101 moves the panel and steps to that order; ORD001 stays one tap away', status: 'passed' });

    await customer.locator('#logout').click();
    await customer.locator('#login-choices button').first().waitFor();
    await login();
    await customer.locator('#tickets .focus-hint').waitFor();
    assert.match(await journey(), /核实/);
    await send('我的外卖迟到了，可以申请补偿吗？');
    await customer.locator('#tickets .focus-hint').waitFor();
    assert(!(await tickets()).includes('ORD001'));
    assert((await customer.locator('#ticket-others').innerText()).includes('我的申请 · 1'));
    assert.equal(await customer.locator('#order-picks .pick[data-pick-order]').count(), 3);
    await shot(customer, 'focus-no-order.png');
    const picked = posting(customer, '/api/customer/messages');
    await customer.locator('#order-picks [data-pick-order="ORD002"]').click();
    await picked;
    await idle(customer);
    await customer.locator('#tickets [data-focus-order="ORD002"]').waitFor();
    assert.equal(await customer.locator('#order-picks').isVisible(), false);
    assert((await customer.locator('#messages').innerText()).includes('预计 18:00，实际 18:10'));
    results.push({ case: 'A question without an order number no longer shows the old ORD001 result; one-tap order choices; reply lists expected and actual time', status: 'passed' });

    await consult('ORD005');
    await customer.locator('#confirm').waitFor();
    assert((await customer.locator('#tickets [data-focus-order="ORD005"]').innerText()).includes('¥10'));
    await customer.locator('#confirm-yes').click();
    await customer.locator('#tickets .badge-pending').waitFor();
    assert.equal(await customer.locator('#tickets [data-ticket-id]').getAttribute('data-ticket-id'), 'T0002');
    assert.match(await journey(), /审核/);
    assert((await customer.locator('#ticket-others summary').innerText()).includes('其他申请 · 1'));
    assert((await customer.locator('#ticket-others').textContent()).includes('ORD001'));
    await decide('通过', '已核实晚到 30 分 1 秒。');
    await toast('ORD005 审核通过');
    await customer.locator('#tickets .badge-approved').waitFor();
    await customer.getByRole('button', { name: '4 分', exact: true }).click();
    await customer.locator('#tickets .rating.rated').waitFor();
    await idle(customer);
    await cleanStatus();
    assert((await customer.locator('#tickets .rating').innerText()).includes('4 分'));
    await reviewer.waitForFunction(() => document.getElementById('decided').textContent.includes('顾客评价 4 / 5'));
    await shot(customer, 'rating-done.png');
    results.push({ case: 'New ORD005 ticket becomes the panel; approval toast; one 1–5 rating shown to the merchant', status: 'passed' });

    const asked = posting(customer, '/api/customer/handoff');
    await customer.locator('#handoff').click();
    await asked;
    await idle(customer);
    await customer.locator('#messages .handoff-note.note-waiting').waitFor();
    await cleanStatus();
    assert.equal(await customer.locator('#handoff-label').innerText(), '人工排队中');
    assert(await customer.locator('#handoff').isDisabled());
    await reviewer.waitForFunction(() => document.getElementById('handoffs-count').textContent === '1');
    await reviewer.locator('#tab-handoffs').click();
    await reviewer.locator('#handoffs .handoff-waiting').waitFor();
    assert((await reviewer.locator('#handoffs .handoff-transcript').innerText()).includes('ORD005'));
    await shot(reviewer, 'handoff-review-waiting.png');
    const answer = '你好，我是人工客服，已看到你的 ORD005 申请。还有问题可以直接在这里留言。';
    await reviewer.locator('#handoffs textarea').fill(answer);
    await reviewer.getByRole('button', { name: '发送回复', exact: true }).click();
    await reviewer.locator('#handoffs .handoff-replied').waitFor();
    await customer.locator('#messages .bubble-row.human').waitFor({ timeout: 10000 });
    assert.equal(await customer.locator('#messages .bubble-row.human .bubble').innerText(), answer);
    assert.equal(await customer.locator('#messages .bubble-row.human .bubble-tag').innerText(), '人工客服');
    await toast('人工客服已回复');
    assert.equal(await customer.locator('#handoff-label').innerText(), '转人工');
    await shot(customer, 'handoff-customer-replied.png');
    results.push({ case: 'Handoff button: queue with transcript, merchant reply appears in the chat tagged 人工客服', status: 'passed' });

    await send('我要投诉');
    await customer.locator('#messages .handoff-note.note-waiting').waitFor();
    assert.equal(await customer.locator('#messages .bubble-row.customer .bubble').last().innerText(), '我要投诉');
    await customer.locator('#messages .handoff-cancel').click();
    await customer.locator('#messages .handoff-note.note-cancelled').waitFor();
    await idle(customer);
    await cleanStatus();
    await reviewer.waitForFunction(() => document.getElementById('handoffs').textContent.includes('顾客已于'));
    results.push({ case: 'Typed 我要投诉 goes straight to the queue; customer can cancel', status: 'passed' });

    await customer.setViewportSize({ width: 390, height: 844 });
    await noOverflow(customer, 'Customer page at 390px');
    await shot(customer, 'mobile-customer.png');
    await reviewer.setViewportSize({ width: 390, height: 844 });
    await noOverflow(reviewer, 'Merchant page at 390px');
    await shot(reviewer, 'mobile-review-handoffs.png');
    await customer.setViewportSize({ width: 1440, height: 1050 });
    await customer.locator('#theme-toggle').click();
    await shot(customer, 'dark-customer.png');
    await noOverflow(customer, 'Customer page desktop dark');
    results.push({ case: '390px layout without horizontal scroll; dark theme', status: 'passed' });
    await context.close();
    assert.deepEqual(errors, []);
    const report = { base, checked_at: new Date().toISOString(), results, errors, summary: { passed: results.length, failed: 0 } };
    await fs.writeFile(path.join(evidence, 'features-results.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report.summary));
  } catch (error) {
    await fs.writeFile(path.join(evidence, 'features-failure.json'), JSON.stringify({ results, errors, failure: error.stack }, null, 2));
    for (const [index, page] of browser.contexts().flatMap(item => item.pages()).entries()) {
      await page.screenshot({ path: path.join(evidence, `features-failure-${index}.png`), fullPage: true }).catch(() => {});
    }
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
