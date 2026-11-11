const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const [entry, passwordFile, evidence, liveOrigin] = process.argv.slice(2);
if (!entry || !passwordFile || !evidence || !liveOrigin) throw new Error('Usage: share.cjs HTTPS_ENTRY PASSWORD_FILE_OR_DASH EVIDENCE_DIRECTORY HTTPS_LIVE_ORIGIN');
if (new URL(entry).protocol !== 'https:' || new URL(liveOrigin).protocol !== 'https:') throw new Error('Use HTTPS sharing addresses.');
const open = passwordFile === '-';

(async () => {
  const password = open ? null : (await fs.readFile(passwordFile, 'utf8')).trim();
  await fs.mkdir(evidence, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const results = [], errors = [];
  const allowed = new Set([new URL(entry).hostname, new URL(liveOrigin).hostname]);
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, colorScheme: 'light' });
    const customer = await context.newPage();
    const watch = page => {
      page.on('pageerror', error => errors.push(error.message));
      page.on('response', response => { if (response.status() >= 500) errors.push(`${response.status()} ${new URL(response.url()).pathname}`); });
      page.on('request', request => { if (!allowed.has(new URL(request.url()).hostname)) errors.push('Unexpected browser destination'); });
    };
    watch(customer);
    context.on('requestfailed', request => errors.push(`requestfailed: ${new URL(request.url()).pathname} ${request.failure()?.errorText}`));
    await customer.goto(entry, { waitUntil: 'domcontentloaded' });
    await customer.waitForSelector('#password, #login-choices', { timeout: 20000 });
    const gated = await customer.locator('#password').isVisible();
    const probe = await context.request.get(`${liveOrigin}/api/health`);
    assert.equal(probe.status(), gated ? 401 : 200);
    await customer.setViewportSize({ width: 390, height: 844 });
    assert(await customer.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    if (gated) {
      assert(password, 'Live page asks for a password; pass a private password file.');
      await customer.screenshot({ path: path.join(evidence, 'share-access.png'), fullPage: true });
      await customer.getByLabel('小组访问口令').fill(password);
      await customer.getByRole('button', { name: '进入', exact: true }).click();
      results.push({ case: 'Surge 固定入口打开带口令页面，未授权接口 401，手机无横向溢出', status: 'passed' });
    } else {
      results.push({ case: 'Surge 固定入口直接进入顾客页（未设口令），手机无横向溢出', status: 'passed' });
    }
    await customer.getByRole('button', { name: '模拟顾客 U001', exact: true }).click();
    await customer.locator('#app').waitFor();
    assert.equal(await customer.locator('.chat-caption').innerText(), 'AI 客服 · 非真人');
    assert(await customer.locator('#handoff').isVisible(), 'The public page is not the version with the handoff button');
    const health = await (await context.request.get(`${liveOrigin}/api/health`)).json();
    assert.equal(health.model_mode, 'live');
    const input = '你好，请问您是？';
    await customer.locator('#input').fill(input);
    const received = customer.waitForResponse(response => response.url() === `${liveOrigin}/api/customer/messages` && response.request().method() === 'POST', { timeout: 45000 });
    await customer.locator('#send').click();
    const response = await received;
    assert.equal(response.status(), 200);
    const body = await response.json();
    await customer.waitForFunction(() => !document.body.classList.contains('is-working'));
    const answer = body.messages.filter(message => message.role === 'assistant').map(message => message.text).join('\n');
    assert.match(answer, /客服|助手|AI/);
    assert(!answer.includes('请提供订单号'));
    assert.equal(body.confirmation, null);
    await customer.screenshot({ path: path.join(evidence, 'share-live-mobile.png'), fullPage: true });
    results.push({ case: '公网真实 DeepSeek 问候成功，浏览器不请求模型供应商', status: 'passed', model: health.model, answer });
    await customer.setViewportSize({ width: 1440, height: 1050 });
    await customer.screenshot({ path: path.join(evidence, 'share-customer.png'), fullPage: true });
    const merchant = await context.newPage();
    watch(merchant);
    await merchant.goto(`${entry}/review`, { waitUntil: 'domcontentloaded' });
    await merchant.getByRole('button', { name: '模拟审批员 R001', exact: true }).click();
    await merchant.locator('#app').waitFor();
    const tickets = await (await context.request.get(`${liveOrigin}/api/review/tickets`)).json();
    assert(Array.isArray(tickets.pending) && Array.isArray(tickets.decided));
    await merchant.screenshot({ path: path.join(evidence, 'share-merchant.png'), fullPage: true });
    results.push({ case: 'Surge 商家入口可登录并读取当前工单，未改动任何审批结果', status: 'passed', tickets_visible: tickets.pending.length + tickets.decided.length });
    const reset = await context.request.post(`${liveOrigin}/api/review/reset`, { data: {}, headers: { Origin: liveOrigin } });
    assert.equal(reset.status(), 403);
    results.push({ case: '公网商家端不能清空演示数据', status: 'passed' });
    assert.deepEqual(errors, []);
    const report = { checked_at: new Date().toISOString(), entry, live_origin: liveOrigin, mode: gated ? 'password' : 'open', results, errors, summary: { passed: results.length, failed: 0 } };
    await fs.writeFile(path.join(evidence, 'public-browser.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify(report, null, 2));
  } catch (error) {
    const failure = password ? String(error.stack).split(password).join('[REDACTED]') : String(error.stack);
    const pages = browser.contexts().flatMap(context => context.pages());
    const visiblePages = [];
    for (const [index, page] of pages.entries()) {
      await page.screenshot({ path: path.join(evidence, `public-browser-failure-${index}.png`), fullPage: true }).catch(() => {});
      visiblePages.push({ url: page.url(), text: (await page.locator('body').innerText().catch(() => '')).split(password || '\u0000').join('[REDACTED]') });
    }
    await fs.writeFile(path.join(evidence, 'public-browser-failure.json'), JSON.stringify({ results, errors, failure, pages: visiblePages }, null, 2));
    throw new Error(failure);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
