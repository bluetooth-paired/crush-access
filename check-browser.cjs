const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.setDefaultTimeout(10000);
    const backendCalls = [];
    page.on('request', req => {
      if (req.method() === 'POST' && new URL(req.url()).pathname.startsWith('/api/v1/')) {
        backendCalls.push(req.postDataJSON());
      }
    });
    const nav = view => page.locator('header .nav-links [data-go="' + view + '"]');
    assert.equal((await page.goto('http://127.0.0.1:8789/')).status(), 200);
    await nav('import').click();
    await page.locator('[data-action="mode-real"]').first().click();
    await page.getByText('已连接本地模拟后端', { exact: false }).first().waitFor();
    await page.locator('#fileInput').setInputFiles(path.join(__dirname, 'backend/tests/fixtures/fictional_chat.json'));
    await page.locator('#previewCount').filter({ hasText: '12 条消息' }).waitFor();
    for (const id of ['consent', 'identityConfirmed', 'sendConsent']) await page.locator('#' + id).check();
    const analyze = page.waitForResponse(r => r.url().endsWith('/api/v1/analyze') && r.request().method() === 'POST');
    await page.locator('[data-action="analyze"]').click();
    const reportResponse = await analyze;
    assert.equal(reportResponse.status(), 200);
    const report = await reportResponse.json();
    assert.ok(report.analysis_id);
    assert.ok(report.client_id);
    await page.waitForURL('**/#signals');
    await nav('advisor').click();
    let sessionId;
    for (const question of ['怎么开始聊天？', '可以举一个例子吗？']) {
      await page.locator('#advisorInput').fill(question);
      const replyPromise = page.waitForResponse(r => r.url().endsWith('/api/v1/advisor/chat') && r.request().method() === 'POST');
      await page.locator('[data-action="send"]').click();
      const response = await replyPromise;
      assert.equal(response.status(), 200);
      const reply = await response.json();
      assert.ok(reply.reply);
      assert.ok(reply.session_id);
      if (sessionId) assert.equal(reply.session_id, sessionId);
      sessionId = reply.session_id;
      await page.locator('#chatScroll .bot').filter({ hasText: reply.reply }).last().waitFor();
    }
    assert.equal(backendCalls.length, 3);
    assert.equal(backendCalls[1].analysis_id, report.analysis_id);
    assert.equal(backendCalls[2].analysis_id, report.analysis_id);
    assert.equal(backendCalls[1].session_id, null);
    assert.equal(backendCalls[2].session_id, sessionId);
    console.log('PASS: actual backend HTTP, rendered report, two rendered replies and reused session');
    await nav('home').click();
    await page.locator('[data-action="sample"]').first().click();
    await nav('advisor').click();
    const before = await page.locator('#chatScroll .bot').count();
    await page.locator('[data-action="ask"]').first().click();
    await page.waitForFunction(n => document.querySelectorAll('#chatScroll .bot').length > n, before);
    assert.equal(backendCalls.length, 3);
    console.log('PASS: demo reply without backend POST');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
