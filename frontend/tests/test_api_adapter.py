"""In-browser fake OpenAPI adapter tests. This never sends private data or calls any provider."""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def make_page(page):
    css='\n'.join((ROOT/f).read_text('utf8') for f in ['styles.css','refinement.css','wizard.css','phase1.css'])
    scripts='\n'.join('<script>'+ (ROOT/f).read_text('utf8') +'</script>' for f in ['api/config.js','api/client.js','api/adapter.js','dashboard.js','mocks/mock-data.js','app.js'])
    html='<html><head><meta charset="UTF-8"><style>'+css+'</style></head><body><div class="background-blobs"></div><div id="app"></div><div id="toast" class="toast"></div>'+scripts+'</body></html>'
    page.set_content(html,wait_until='load',timeout=35000)

def test():
    errors=[];out=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
        page=b.new_page(viewport={'width':1440,'height':900})
        page.on('pageerror',lambda e:errors.append(str(e)))
        make_page(page)
        page.locator('nav [data-go="import"]').click()
        page.locator('[data-action="mode-real"]').click()
        page.locator('#fileInput').set_input_files(str(ROOT/'mocks/warm-chat.json'))
        page.locator('#previewCount').get_by_text('14 条消息').wait_for(timeout=5000)
        page.locator('#consent').check()
        page.locator('#identityConfirmed').check()
        page.locator('#sendConsent').check()
        page.evaluate("""() => {
          window.__calls=[];window.__failNext=false;
          window.HeartSignalAPI={
            health:async()=>({status:'ok',model:{provider:'mock'},features:{thinking_supported:true,thinking_note:'mock',web_search:{supported:true}}}),
            analyze:async body=>{window.__calls.push({kind:'analyze',body});return {fictional:'analysis'}},
            advisorChat:async body=>{window.__calls.push({kind:'advisor',body});if(window.__failNext){window.__failNext=false;throw new Error('虚构连接故障')}return {fictional:'advisor'}}
          };
          window.HeartSignalAPIAdapter={
            ready:true,
            buildAnalyzeRequest:({chatDocument,identities,clientId,thinkingLevel})=>({conversation:chatDocument,profile:{self:identities.self,other:identities.other},client_id:clientId,options:{thinking_level:thinkingLevel}}),
            readAnalyzeResponse:()=>({analysisId:'fake-analysis-001',clientId:'fake-client-123',status:'completed',report:{},dashboard:window.HeartSignalMockData.warm.dashboard,suggestions:['先自然地确认时间地点。']}),
            buildAdvisorRequest:({question,analysisId,sessionId,clientId,thinkingLevel,webSearch})=>({message:question,analysis_id:analysisId,session_id:sessionId,client_id:clientId,thinking_level:thinkingLevel,web_search:webSearch}),
            readAdvisorResponse:()=>({reply:'虚构服务回复：真诚并尊重边界。',sessionId:'fake-session-002',suggestions:['尊重双方意愿。'],evidence:[],boundaryNotes:[]})
          };
        }""")
        page.locator('[data-action="analyze"]').click()
        page.locator('.score-center b').get_by_text('74').wait_for(timeout=5000)
        assert page.locator('.score-ring').count()==1
        out.append('模拟适配器成功处理分析响应，动态指数 74')
        page.locator('nav [data-go="advisor"]').click()
        page.locator('#advisorInput').fill('第一轮：如何邀约')
        page.locator('[data-action="send"]').click()
        page.locator('.chat-msg.bot').last.get_by_text('虚构服务回复', exact=False).wait_for(timeout=5000)
        page.locator('#advisorInput').fill('第二轮：怎样维持边界')
        page.locator('[data-action="send"]').click()
        assert page.locator('.chat-msg.bot').count()>=3
        calls=page.evaluate('window.__calls')
        assert calls[0]['kind']=='analyze'
        assert calls[1]['body']['analysis_id']=='fake-analysis-001'
        assert calls[1]['body']['client_id']=='fake-client-123'
        assert calls[2]['body']['session_id']=='fake-session-002'
        assert calls[2]['body']['thinking_level']=='auto' and calls[2]['body']['web_search'] is False
        out.append('analysis_id、client_id、session_id 与配置参数按后端契约透传；上下文由后端会话管理')
        page.evaluate('window.__failNext=true')
        page.locator('#advisorInput').fill('第三轮：模拟失败')
        page.locator('[data-action="send"]').click()
        page.locator('.retry-chat').wait_for(timeout=5000)
        assert '虚构连接故障' in page.locator('.chat-scroll').inner_text()
        page.locator('.retry-chat').click()
        assert page.locator('.retry-chat').count()==0
        assert page.locator('.chat-msg.bot').count()>=4
        out.append('军师请求失败可见，点击重发可恢复')
        assert page.evaluate("HeartSignalDashboard.asPercent(.2,'fraction')") == 20
        assert page.evaluate("HeartSignalDashboard.asPercent(20,'percent')") == 20
        assert page.evaluate("() => {try{HeartSignalDashboard.asPercent(20,'fraction');return false}catch{return true}}")
        out.append('fraction 与 percent 单位明确校验')
        assert not errors,errors
        b.close()
    (ROOT/'tests/api-results.txt').write_text('\n'.join('PASS '+x for x in out)+'\n',encoding='utf8')
    for o in out: print('PASS',o)
if __name__=='__main__':test()
