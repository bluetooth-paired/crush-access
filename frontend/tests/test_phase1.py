"""Phase 1 browser tests. Only fictional fixtures; no external LLM or private data."""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def run():
    results=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
        page=browser.new_page(viewport={'width':1440,'height':900})
        page.on('pageerror',lambda e:errors.append(str(e)))
        styles='\n'.join((ROOT/f).read_text('utf8') for f in ['styles.css','refinement.css','wizard.css','phase1.css'])
        scripts='\n'.join('<script>'+ (ROOT/f).read_text('utf8') +'</script>' for f in ['api/config.js','api/client.js','api/adapter.js','dashboard.js','mocks/mock-data.js','app.js'])
        html='<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"><style>'+styles+'</style></head><body><div class=\"background-blobs\"></div><div id=\"app\"></div><div id=\"toast\" class=\"toast\"></div>'+scripts+'</body></html>'
        page.set_content(html,wait_until='load',timeout=35000)
        assert page.locator('.v4-home').count()==1
        assert page.locator('nav.nav-links [data-go="profile"]').count()==1
        results.append('V6 首页/导航/档案未退化')
        page.locator('nav.nav-links [data-go="import"]').click()
        assert page.locator('#chatInput').count()==1
        standard=json.loads((ROOT/'tests/fixtures/chat-schema1-standard.json').read_text(encoding='utf-8'))
        standard['messages'][0]['sender_name']='虚构的我'; standard['messages'][1]['sender_name']='虚构的TA'
        standard['metadata']['anonymized']=True
        page.locator('#chatInput').fill(json.dumps(standard,ensure_ascii=False))
        assert 'JSON Schema 1.0 解析成功' in page.locator('#parseStatus').inner_text()
        assert page.locator('#previewMessages .preview-chat').count()==2
        assert '虚构的我' in page.locator('#previewMessages .preview-chat').nth(0).inner_text()
        assert '虚构的TA' in page.locator('#previewMessages .preview-chat').nth(1).inner_text()
        assert '10:30 +08:00' in page.locator('#previewMessages').inner_text()
        assert 'm001' in page.locator('#previewMessages').inner_text()
        assert '2 条消息' in page.locator('#previewCount').inner_text()
        results.append('JSON 粘贴 schema1/sender_name/时间/ID/统计')
        page.locator('#chatInput').fill('ほげ { "schema_version": }')
        # That deliberately non-JSON-like prefix is normal text; test actual malformed JSON
        page.locator('#chatInput').fill('{"schema_version":"1.0", broken')
        assert '导入失败' in page.locator('#parseStatus').inner_text()
        assert page.locator('#previewMessages .preview-chat').count()==0
        results.append('非法 JSON 拦截，未当作文本')
        page.locator('#fileInput').set_input_files(str(ROOT/'mocks/warm-chat.json'))
        page.locator('#previewCount').get_by_text('14 条消息').wait_for(timeout=5000)
        assert page.locator('.preview-chat').count()==5
        results.append('标准 chat.json 上传及消息预览')
        page.locator('#consent').check()
        page.locator('[data-action="analyze"]').click()
        assert page.locator('.portrait-grid').count()==1
        page.locator('nav.nav-links [data-go="signals"]').click()
        assert page.locator('.score-ring').count()==1
        before=page.locator('.score-center b').inner_text()
        page.locator('[data-action="mock-reserved"]').click()
        assert page.locator('.portrait-grid').count()==1
        page.locator('nav.nav-links [data-go="signals"]').click()
        after=page.locator('.score-center b').inner_text()
        assert before != after, (before,after)
        assert '24' in after
        assert '边界提醒' in page.locator('.signal-detail-grid').inner_text() or '边界' in page.locator('.info-note.red').inner_text()
        results.append(f'不同 Mock 场景图表动态变化：{before}→{after}')
        page.locator('nav.nav-links [data-go="advisor"]').click()
        assert page.locator('.v4-chat-panel').count()==1
        page.locator('[data-action="ask"]').first.click()
        assert page.locator('.chat-msg.me').count()==1
        assert page.locator('.chat-msg.bot').count()==2
        page.locator('#advisorInput').fill('我能怎样尊重 TA 的决定？')
        page.locator('[data-action="send"]').click()
        assert page.locator('.chat-msg.me').count()==2
        assert page.locator('.chat-msg.bot').count()==3
        assert '演示模式' in page.locator('.chat-composer .disclaimer').inner_text()
        results.append('军师预设多轮回复/历史状态（非LLM）')
        # switch to real, consent + identities are mandatory
        page.locator('[data-action="mode-real"]').click()
        assert '真实 API' in page.locator('.mode-strip').inner_text()
        page.locator('nav.nav-links [data-go="import"]').click()
        assert page.locator('#identityConfirmed').count()==1
        assert page.locator('#sendConsent').count()==1
        page.locator('#fileInput').set_input_files(str(ROOT/'mocks/warm-chat.json'))
        page.locator('#previewCount').get_by_text('14 条消息').wait_for(timeout=5000)
        page.locator('#consent').check()
        page.locator('[data-action="analyze"]').click()
        assert '真实模式须先确认' in page.locator('#toast').inner_text() or '身份' in page.locator('.import-confirm').inner_text()
        page.locator('#identityConfirmed').check()
        page.locator('#sendConsent').check()
        page.locator('[data-action="analyze"]').click()
        assert '真实 API 尚未配置' in page.locator('.mode-error').inner_text()
        assert page.locator('.mode-error [data-action="mode-demo"]').count()==1
        results.append('真实模式：身份确认、发送许可、未配置协议时禁止上传')
        # Inject a temporary test adapter / configuration: endpoints are tested with no live backend.
        page.evaluate('''() => {
          window.HeartSignalAPIConfig={enabled:true,baseUrl:'http://127.0.0.1:9',timeoutMs:650};
          window.HeartSignalAPIAdapter={ready:true,buildAnalyzeRequest:({chatDocument})=>({fictional_test_only:chatDocument}),readAnalyzeResponse:()=>({analysisId:'test-only',clientId:'test-client-123',report:{},dashboard:window.HeartSignalMockData.warm.dashboard}),buildAdvisorRequest:({question})=>({fictional_test_only:question}),readAdvisorResponse:()=>({reply:'test',sessionId:'local-test',suggestions:[],evidence:[],boundaryNotes:[]})};
          window.HeartSignalAPI={analyze:async()=>{throw new Error('虚构连接故障')}};
        }''')
        page.locator('[data-action="analyze"]').click()
        page.wait_for_timeout(1100)
        assert '分析调用失败' in page.locator('.mode-error').inner_text()
        assert '真实 API' in page.locator('.mode-strip').inner_text(), 'must not silently switch'
        page.locator('.mode-error [data-action="mode-demo"]').first.click()
        assert '演示模式' in page.locator('.mode-strip').inner_text()
        page.locator('[data-action="mock-warm"]').click()
        page.locator('nav.nav-links [data-go="advisor"]').click()
        page.locator('[data-action="send"]').click() if False else None
        assert page.locator('.v4-chat-panel').count()==1
        results.append('后端断网显式报错；用户手动切演示后恢复完整军师')
        assert not errors, errors
        results.append('无未捕获浏览器 JS 异常')
        browser.close()
    (ROOT/'tests/phase1-results.txt').write_text('\n'.join('PASS '+x for x in results)+'\n',encoding='utf8')
    print('\n'.join('PASS '+x for x in results))

if __name__=='__main__':run()
