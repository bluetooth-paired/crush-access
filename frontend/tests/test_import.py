"""V6 JSON Schema 1.0 browser tests using wholly fictional messages.

Run from any directory with: python tests/test_import.py
Requires: pip install playwright and an installed Chromium executable.
The test uses page.set_content() so it does not need network access.
"""
from __future__ import annotations

from pathlib import Path
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / 'tests' / 'fixtures'


def build_inline_html() -> str:
    styles = '\n'.join((ROOT / f).read_text('utf-8') for f in ('styles.css', 'refinement.css', 'wizard.css', 'phase1.css'))
    scripts = '\n'.join('<script>' + (ROOT / f).read_text('utf-8') + '</script>' for f in ('api/config.js','api/client.js','api/adapter.js','dashboard.js','mocks/mock-data.js','app.js'))
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8">'
        f'<style>{styles}</style></head><body>'
        '<div class="background-blobs"></div><div id="app"></div>'
        '<div id="toast" class="toast" role="status"></div>'
        f'{scripts}</body></html>'
    )


def run() -> None:
    results: list[str] = []
    errors: list[str] = []
    with sync_playwright() as p:
        chromium_path = os.environ.get('CHROMIUM_PATH')
        browser = p.chromium.launch(
            headless=True, executable_path=chromium_path,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.set_content(build_inline_html(), wait_until='load', timeout=30000)
        assert page.locator('.v4-home').count() == 1, 'Original V6 home must still render'
        page.locator('nav.nav-links [data-go="import"]').first.click()
        assert page.locator('#chatInput').count() == 1
        results.append('首页及原聊天导入模块保留')

        # JSON paste: two messages must be enough for a JSON exploration report.
        standard = (FX/'chat-schema1-standard.json').read_text('utf-8')
        page.locator('#chatInput').fill(standard)
        assert '解析成功：共 2 条' in page.locator('#parseStatus').inner_text()
        assert '2 条消息' in page.locator('#previewCount').inner_text()
        bubbles = page.locator('#previewMessages .preview-chat')
        assert bubbles.count() == 2
        assert 'self' in bubbles.nth(0).get_attribute('class')
        assert 'other' in bubbles.nth(1).get_attribute('class')
        assert '周末有空吗？' in bubbles.nth(0).inner_text()
        assert '2026-11-07 10:30 +08:00' in bubbles.nth(0).inner_text()
        assert 'ID: m001' in bubbles.nth(0).inner_text()
        results.append('Schema 1.0 JSON 粘贴：身份、原始时间偏移、ID、顺序及条数')

        # Changing visible nicknames must never relabel sender keys.
        page.locator('#ownName').fill('小舟')
        page.locator('#otherName').fill('阿宁')
        assert '小舟' in bubbles.nth(0).inner_text()
        assert '阿宁' in bubbles.nth(1).inner_text()
        assert 'self' in bubbles.nth(0).get_attribute('class')
        assert 'other' in bubbles.nth(1).get_attribute('class')
        results.append('更改昵称仅影响显示，不会反向推断 JSON sender')
        page.locator('#consent').check()
        page.locator('[data-action="analyze"]').click()
        assert page.locator('.portrait-grid').count() == 1
        assert '2 条消息' in page.locator('.result-banner').inner_text()
        page.locator('nav.nav-links [data-go="import"]').first.click()
        results.append('只有两条标准 JSON（self/other 各一条）仍能传入画像页面')

        # JSON file upload after navigating home and back.
        page.locator('#fileInput').set_input_files(str(FX/'chat-schema1-emoji-unknown.json'))
        page.wait_for_function("() => document.querySelector('#parseStatus')?.textContent.includes('解析成功：共 5 条')")
        assert '解析成功：共 5 条' in page.locator('#parseStatus').inner_text()
        assert '未知 1' in page.locator('#parseStatus').inner_text()
        assert '5 条消息' in page.locator('#previewCount').inner_text()
        bubbles = page.locator('#previewMessages .preview-chat')
        assert bubbles.count() == 5
        assert 'other' in bubbles.nth(0).get_attribute('class')
        assert 'self' in bubbles.nth(1).get_attribute('class')
        assert 'unknown' in bubbles.nth(2).get_attribute('class')
        assert '未知发送者' in bubbles.nth(2).inner_text()
        assert '第一条是 TA 发的 🌸\n这是同一条消息的第二行！' in bubbles.nth(0).inner_text()
        assert 'ID: original-05' in bubbles.nth(4).inner_text()
        assert '2026-11-07 09:05 +08:00' in bubbles.nth(4).inner_text()
        results.append('JSON 文件上传：中文/Emoji/换行/unknown/ID/时间/顺序/计数')

        # All downstream pages consume exactly those five normalized messages.
        page.locator('#consent').check()
        page.locator('[data-action="analyze"]').click()
        assert page.locator('.portrait-grid').count() == 1, 'should navigate to portraits'
        port_text = page.locator('.result-banner').inner_text()
        assert '5 条消息' in port_text and '双方 4 条' in port_text and '未知发送者 1 条' in port_text
        page.locator('nav.nav-links [data-go="signals"]').first.click()
        assert '5' in page.locator('.tiny-metrics').inner_text()
        page.locator('nav.nav-links [data-go="advisor"]').first.click()
        assert page.locator('#advisorInput').count() == 1
        page.locator('#advisorInput').fill('这周可以一起看展吗？')
        page.locator('[data-action="send"]').click()
        assert page.locator('.chat-msg.me').count() >= 1
        assert page.locator('.chat-msg.bot').count() >= 1
        results.append('双向画像/互动信号/军师对话：共用标准化数据并保持正常运行')

        # Go back to input for invalid/malformed tests.
        page.locator('nav.nav-links [data-go="import"]').first.click()
        page.locator('#fileInput').set_input_files(str(FX/'chat-schema1-metadata-mismatch.json'))
        page.wait_for_function("() => document.querySelector('#parseStatus')?.textContent.includes('metadata.total_messages 为 999')")
        assert '共 5 条' in page.locator('#parseStatus').inner_text()
        assert 'metadata.total_messages 为 999' in page.locator('#parseStatus').inner_text()
        assert 'metadata.unknown_senders 为 0' in page.locator('#parseStatus').inner_text()
        results.append('metadata 计数不一致：显示警告，以实际消息数组为准')

        for name, expected_error in (
            ('invalid-json-syntax.json', 'JSON 语法错误'),
            ('invalid-duplicate-id.json', 'id 重复'),
            ('invalid-sender.json', 'sender 必须是 self'),
        ):
            page.locator('#fileInput').set_input_files(str(FX/name))
            page.wait_for_function("([expected]) => document.querySelector('#parseStatus')?.textContent.includes(expected)", arg=[expected_error], timeout=10000)
            assert expected_error in page.locator('#parseStatus').inner_text(), name
            assert page.locator('#previewMessages .preview-chat').count() == 0, name
            assert '0 条消息' in page.locator('#previewCount').inner_text(), name
            page.locator('#consent').check()
            page.locator('[data-action="analyze"]').click()
            assert page.locator('#chatInput').count() == 1, name
        results.append('非法 JSON：语法/重复 ID/错误 sender 均阻断分析且不回退成文本')

        # Malformed pasted JSON must also block analysis.
        page.locator('#chatInput').fill('{"schema_version":"1.0", bad')
        assert 'JSON 语法错误' in page.locator('#parseStatus').inner_text()
        assert '0 条消息' in page.locator('#previewCount').inner_text()
        results.append('非法 JSON 粘贴：即时错误提示、清空预览和消息计数')

        # Existing pure text file import retained, Markdown excluded.
        page.locator('#fileInput').set_input_files(str(FX/'plain-text-sample.txt'))
        page.wait_for_function("() => document.querySelector('#parseStatus')?.textContent.includes('已识别 4 条纯文本消息')")
        assert '已识别 4 条纯文本消息' in page.locator('#parseStatus').inner_text()
        assert '4 条消息' in page.locator('#previewCount').inner_text()
        page.locator('#consent').check()
        page.locator('[data-action="analyze"]').click()
        assert page.locator('.portrait-grid').count() == 1
        page.locator('nav.nav-links [data-go="import"]').first.click()
        accept = page.locator('#fileInput').get_attribute('accept') or ''
        assert '.json' in accept and '.txt' in accept and '.csv' in accept and '.md' not in accept
        results.append('纯文本粘贴/文本文件原有分析闭环保留；.md 不列入上传格式')
        page.locator('#chatInput').fill('[10:30] 我: 哈喽！\n[10:32] 小林: 你好！\n我: 在吗？\n小林: 在呢')
        assert '已识别 4 条纯文本消息' in page.locator('#parseStatus').inner_text()
        assert '4 条消息' in page.locator('#previewCount').inner_text()
        results.append('原 V6 带方括号时间 [HH:MM] 的纯文本格式仍可正常解析')

        assert not errors, f'Uncaught browser errors: {errors}'
        results.append('无未捕获 JavaScript 浏览器异常')
        browser.close()

    for i, res in enumerate(results, 1):
        print(f'PASS {i:02d}: {res}')
    print(f'ALL PASS: {len(results)} groups')

if __name__ == '__main__':
    run()
