const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const base = (process.argv[2] || 'http://127.0.0.1:8027').replace(/\/$/, '');
const evidence = process.argv[3];
if (!evidence) throw new Error('Usage: node live.cjs LOCAL_URL EVIDENCE_DIRECTORY');
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw new Error('Use a local demo service.');

(async () => {
  await fs.mkdir(evidence, { recursive: true });
  const browser = await chromium.launch(process.env.PLAYWRIGHT_CHROME ? { executablePath: process.env.PLAYWRIGHT_CHROME, headless: true } : { channel: 'chrome', headless: true });
  const errors = [];
  const results = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, colorScheme: 'light' });
    const customer = await context.newPage();
    const merchant = await context.newPage();
    for (const page of [customer, merchant]) {
      page.on('pageerror', error => errors.push(error.message));
      page.on('response', response => { if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`); });
      page.on('request', request => { if (request.url().startsWith('https://')) errors.push('Unexpected external browser request'); });
    }
    const health = await (await context.request.get(`${base}/api/health`)).json();
    assert.equal(health.model_mode, 'live');
    const state = async () => (await context.request.get(`${base}/api/customer/state`)).json();
    const send = async text => {
      await customer.locator('#input').fill(text);
      const received = customer.waitForResponse(response => response.url() === `${base}/api/customer/messages` && response.request().method() === 'POST', { timeout: 45000 });
      await customer.locator('#send').click();
      const response = await received;
      assert.equal(response.status(), 200);
      const body = await response.json();
      await customer.waitForFunction(() => !document.body.classList.contains('is-working'));
      return body;
    };
    const shot = async name => {
      await customer.evaluate(() => window.scrollTo(0, 0));
      await customer.screenshot({ path: path.join(evidence, name), fullPage: true });
    };
    await customer.goto(base);
    await customer.getByRole('button', { name: '模拟顾客 U001', exact: true }).click();
    await customer.locator('#app').waitFor();
    let response = await send('你好，请问您是？');
    let answer = response.messages.filter(item => item.role === 'assistant').map(item => item.text).join('\n');
    assert.match(answer, /客服|助手|AI/);
    assert(!answer.includes('请提供订单号'));
    assert.equal((await state()).confirmation, null);
    await shot('live-greeting.png');
    results.push({ case: '真实网页直接回应身份问候', status: 'passed', answer });

    response = await send('只查 ORD008 的送达情况，不要申请补偿。');
    assert.equal(response.outcome, 'order_queried');
    assert.equal((await state()).confirmation, null);
    assert.equal(await customer.locator('#confirm').isVisible(), false);
    results.push({ case: '只查订单不出现申请确认卡', status: 'passed' });

    response = await send('那帮我申请这笔订单的延误补偿。');
    assert.equal(response.outcome, 'awaiting_confirmation');
    await customer.locator('#confirm').waitFor();
    assert.equal(response.confirmation.order_id, 'ORD008');
    assert(!(await state()).tickets.some(ticket => ticket.order_id === 'ORD008'));
    await shot('live-confirmation.png');
    await customer.locator('#confirm-yes').click();
    await customer.locator('#tickets .badge-pending').waitFor();
    const ticket = (await state()).tickets.find(item => item.order_id === 'ORD008');
    assert(ticket && ticket.status === 'pending' && ticket.coupon_issued_yuan === null);
    results.push({ case: '模型承接上文并打开确认卡，顾客确认才建单', status: 'passed', ticket_id: ticket.ticket_id });

    await merchant.goto(`${base}/review`);
    await merchant.getByRole('button', { name: '模拟审批员 R001', exact: true }).click();
    await merchant.locator('#pending textarea').waitFor();
    await merchant.locator('#pending textarea').fill('已核对配送记录，本次未通过补偿申请。');
    await merchant.getByRole('button', { name: '拒绝', exact: true }).click();
    await customer.locator('#tickets .badge-rejected').waitFor();
    response = await send('商家处理完了吗？这笔申请结果是什么？');
    answer = response.messages.filter(item => item.role === 'assistant').map(item => item.text).join('\n');
    assert.match(answer, /未通过|拒绝|驳回/);
    const final = (await state()).tickets.find(item => item.ticket_id === ticket.ticket_id);
    assert.equal(final.status, 'rejected');
    assert.equal(final.coupon_issued_yuan, null);
    await shot('live-result.png');
    results.push({ case: '商家拒绝后，模型读取最新同票结果', status: 'passed', answer });

    await customer.setViewportSize({ width: 390, height: 844 });
    assert(await customer.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await shot('live-mobile.png');
    await customer.locator('#meta').click();
    assert((await customer.locator('#policy-details').innerText()).includes('在线模型'));
    assert((await customer.locator('#policy-details').innerText()).includes('deepseek-flash'));
    await customer.keyboard.press('Escape');
    results.push({ case: '手机无横向溢出，按需说明显示在线模型', status: 'passed' });
    assert.deepEqual(errors, []);
    const report = { checked_at: new Date().toISOString(), base, model: health.model, results, errors, summary: { passed: results.length, failed: 0 } };
    await fs.writeFile(path.join(evidence, 'live-browser.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    await fs.writeFile(path.join(evidence, 'live-browser-failure.json'), JSON.stringify({ results, errors, failure: error.stack }, null, 2));
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
