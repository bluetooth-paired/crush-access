const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { test } = require('node:test');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

test('profile editing and local advisor example keep the original chat draft', async () => {
  const channel = process.env.PLAYWRIGHT_CHANNEL;
  const browser = await chromium.launch(channel ? { channel } : {});
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const api = [];
    page.on('request', request => {
      if (/\/api\/v1\/|\/health(?:\?|$)/.test(request.url())) api.push(request.url());
    });
    const site = pathToFileURL(path.resolve(__dirname, '../index.html')).href;
    await page.goto(site);
    await page.locator('nav.nav-links [data-go="profile"]').click();
    await page.locator('[data-action="demo-login"]').first().click();
    const name = page.locator('[data-profile="meNick"]');
    await name.click();
    assert.equal(await name.evaluate(node => node === document.activeElement), true);
    await page.keyboard.insertText('虚构昵称');
    assert.equal(await name.inputValue(), '虚构昵称');

    await page.locator('nav.nav-links [data-go="import"]').click();
    await page.locator('#chatInput').fill('我: 虚构草稿');
    await page.locator('[data-action="sample"]').first().click();
    await page.locator('nav.nav-links [data-go="advisor"]').click();
    await page.locator('[data-action="ask"]').first().click();
    assert.equal(await page.locator('.chat-msg.bot').count(), 2);
    assert.match(await page.locator('.chat-composer .disclaimer').innerText(), /演示模式/);
    assert.deepEqual(api, []);

    await page.locator('nav.nav-links [data-go="import"]').click();
    assert.equal(await page.locator('#chatInput').inputValue(), '我: 虚构草稿');
    await page.goto(site + '#advisor');
    await page.reload();
    assert.equal(new URL(page.url()).hash, '#advisor');
    await page.locator('[data-action="ask"]').first().click();
    assert.equal(await page.locator('.chat-msg.bot').count(), 2);
  } finally {
    await browser.close();
  }
});
