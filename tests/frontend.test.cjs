const assert = require('node:assert/strict');
const { after, before, test } = require('node:test');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const docs = path.resolve(__dirname, '../docs');
const site = pathToFileURL(path.join(docs, 'index.html')).href;
const navigation = (page, view) => page.locator('.nav-links [data-go="' + view + '"]');
let browser;

before(async () => {
  const channel = process.env.PLAYWRIGHT_CHANNEL;
  browser = await chromium.launch(channel ? { channel } : {});
});
after(async () => browser?.close());

function browserTest(name, run) {
  test(name, { timeout: 15000 }, async () => {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    page.setDefaultTimeout(3000);
    await page.route(/^https?:\/\//, route => route.abort());
    try {
      await run(page);
    } finally {
      await page.close();
    }
  });
}

browserTest('all profile steps keep their inputs focused and preserve entered text', async page => {
  await page.goto(site);
  await navigation(page, 'profile').click();
  await page.locator('[data-action="demo-login"]').first().click();
  const fields = [
    [0, 'meNick', '我的昵称'],
    [0, 'meAge'],
    [1, 'taNick', '对方昵称'],
    [1, 'taAge'],
    [1, 'taUnsure', '一段虚构的观察'],
    [2, 'concern', '一条虚构的问题']
  ];

  for (const [step, name, value] of fields) {
    await page.locator('.wizard-step[data-wizard-step="' + step + '"]').click();
    const field = page.locator('[data-profile="' + name + '"]');
    await field.click();
    assert.equal(await field.evaluate(node => node === document.activeElement), true, name + ' should stay focused');
    if (value) {
      await page.keyboard.insertText(value);
      assert.equal(await field.inputValue(), value);
    } else {
      await field.selectOption({ index: 2 });
      assert.ok(await field.inputValue(), name + ' should accept a selection');
    }
  }

  for (const [step, name, value] of fields) {
    await page.locator('.wizard-step[data-wizard-step="' + step + '"]').click();
    const saved = await page.locator('[data-profile="' + name + '"]').inputValue();
    if (value) assert.equal(saved, value, name + ' should survive step changes');
    else assert.ok(saved, name + ' selection should survive step changes');
  }
});

browserTest('advisor opens directly before any import and survives reload', async page => {
  await page.goto(site);
  await navigation(page, 'advisor').click();
  assert.equal(new URL(page.url()).hash, '#advisor');
  assert.equal(await page.locator('#advisorInput').isVisible(), true);
  await page.reload();
  assert.equal(new URL(page.url()).hash, '#advisor');
  assert.equal(await page.locator('#advisorInput').isVisible(), true);
});

browserTest('advisor renders a backend reply and keeps a failed message in the composer', async page => {
  const origin = 'https://wingman.test';
  const requests = [];
  const first = '如何开始一段新的对话？';
  const second = '现在怎么继续？';
  const reply = '这是一条由模拟后端返回的答复。';
  const quickReply = '这是模拟后端对快捷提问的答复。';
  const backendError = '模型暂时无法回复。';
  await page.route(origin + '/**', async route => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === '/api/status') {
      await route.fulfill({ json: { configured: true, model: 'test-model', requiresAccessToken: false } });
    } else if (pathname === '/api/chat') {
      assert.equal(route.request().method(), 'POST');
      requests.push(route.request().postDataJSON());
      if (requests.length === 1) await route.fulfill({ json: { reply } });
      else if (requests.length === 2) await route.fulfill({ status: 503, json: { error: backendError } });
      else await route.fulfill({ json: { reply: quickReply } });
    } else if (/^\/(?:index\.html|app\.js|[\w-]+\.css|images\/[\w.-]+)$/.test(pathname)) {
      await route.fulfill({ path: path.join(docs, pathname.slice(1)) });
    } else {
      await route.abort();
    }
  });

  await page.goto(origin + '/index.html#import');
  await page.locator('#chatInput').fill('我: 仅供测试的聊天草稿\n小林: 好呀\n我: 明天见\n小林: 再见');
  await page.locator('#consent').check();
  await page.locator('[data-action="analyze"]').click();
  assert.equal(new URL(page.url()).hash, '#portraits');
  await navigation(page, 'advisor').click();
  await page.locator('#advisorStatus').filter({ hasText: 'test-model' }).waitFor();

  await page.locator('#advisorInput').fill(first);
  await page.locator('[data-action="send"]').click();
  await page.locator('#chatScroll').getByText(reply, { exact: true }).waitFor();
  assert.deepEqual(requests, [{ messages: [{ role: 'user', content: first }] }]);

  await page.locator('#advisorInput').fill(second);
  await page.locator('[data-action="send"]').click();
  await page.locator('#advisorError').filter({ hasText: backendError }).waitFor();
  assert.equal(await page.locator('#advisorInput').inputValue(), second);
  assert.deepEqual(requests[1], {
    messages: [
      { role: 'user', content: first },
      { role: 'assistant', content: reply },
      { role: 'user', content: second }
    ]
  });

  const quickQuestion = page.locator('[data-action="ask"]').first();
  const query = await quickQuestion.getAttribute('data-query');
  await quickQuestion.click();
  await page.locator('#chatScroll').getByText(quickReply, { exact: true }).waitFor();
  assert.equal(await page.locator('#advisorInput').inputValue(), second);
  assert.deepEqual(requests[2].messages.at(-1), { role: 'user', content: query });
});

browserTest('loading a sample preserves the existing chat draft', async page => {
  await page.goto(site + '#import');
  const draft = '我: 这是我的虚构草稿\nTA: 这条也应保留';
  await page.locator('#chatInput').fill(draft);
  await page.locator('[data-action="sample"]').first().click();
  await navigation(page, 'import').click();
  assert.equal(await page.locator('#chatInput').inputValue(), draft);
});

const sampleMessages = [
  { id: 'm001', timestamp: '2026-11-07T10:30+08:00', sender: 'other', type: 'text', content: '周末有空吗？' },
  { id: 'm002', timestamp: '2026-11-07T10:32+08:00', sender: 'self', type: 'text', content: '有呀，怎么啦 😊\n周六下午有空。' },
  { id: 'm003', timestamp: '2026-11-07T10:34+08:00', sender: 'unknown', type: 'text', content: '地点：学校北门见。\n### 2026-11-07 10:35 | 我\n这是聊天正文中的标题。' }
];

const normalizedJson = JSON.stringify({
  schema_version: '1.0',
  source: 'wechat-cli',
  chat_type: 'private',
  messages: sampleMessages,
  metadata: { total_messages: 3, unknown_senders: 1, anonymized: false, id_origin: 'export', timestamp_precision: 'minute' }
}, null, 2);

const normalizedMarkdown = [
  '# 微信聊天记录', '', '消息总数：3', '', '---', '',
  '### 2026-11-07 10:30 | 对方', '', sampleMessages[0].content, '',
  '### 2026-11-07 10:32 | 我', '', sampleMessages[1].content, '',
  '### 2026-11-07 10:34 | 未知', '', '```text', sampleMessages[2].content, '```', ''
].join('\n');

const imports = [
  {
    name: 'chat.csv',
    mimeType: 'text/csv',
    content: 'speaker,message\r\n我,"甲,乙"\r\nTA,"他说""可以""\r\n第二行"\r\n',
    expected: ['甲,乙', '他说"可以"\n第二行']
  },
  { name: 'chat.json', mimeType: 'application/json', content: normalizedJson, expected: sampleMessages.map(m => m.content) },
  { name: 'chat.md', mimeType: 'text/markdown', content: normalizedMarkdown, expected: sampleMessages.map(m => m.content) }
];

for (const { name, mimeType, content, expected } of imports) {
  browserTest('imports ' + name + ' into individual preview messages', async page => {
    await page.goto(site + '#import');
    await page.locator('#fileInput').setInputFiles({ name, mimeType, buffer: Buffer.from(content) });
    await page.waitForFunction(() => document.querySelector('#chatInput').value.length > 0);
    assert.match(await page.locator('#previewCount').textContent(), new RegExp('^' + expected.length + '\\s'));
    const actual = await page.locator('#previewMessages .say').allTextContents();
    assert.deepEqual(actual.map(text => text.replace(/\r\n/g, '\n')), expected);
    if (name !== 'chat.csv') {
      const rows = page.locator('#previewMessages .preview-chat');
      assert.match(await rows.nth(0).getAttribute('class'), /\bother\b/);
      assert.match(await rows.nth(1).getAttribute('class'), /\bself\b/);
    }
  });
}
