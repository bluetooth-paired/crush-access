"""P0 regression: all user data is synthetic; API responses are test substitutes, not model output."""
from pathlib import Path
import json, os, base64
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def build_html():
    styles='\n'.join((ROOT/f).read_text(encoding='utf-8') for f in ['styles.css','refinement.css','wizard.css','phase1.css','report.css'])
    scripts=[]
    for f in ['api/config.js','api/client.js','api/adapter.js','dashboard.js','mocks/mock-data.js','app.js']:
        s=(ROOT/f).read_text(encoding='utf-8')
        if f=='app.js':
            # Use only checked-in V6 images; no external network needed for screenshot tests.
            for img in (ROOT/'images').iterdir():
                if img.suffix.lower() in ('.jpg','.jpeg','.png'):
                    mimetype='image/png' if img.suffix.lower()=='.png' else 'image/jpeg'
                    uri=f'data:{mimetype};base64,'+base64.b64encode(img.read_bytes()).decode('ascii')
                    s=s.replace(f'images/{img.name}',uri)
        scripts.append('<script>'+s+'</script>')
    return '<html lang="zh-CN"><head><meta charset="UTF-8"><style>'+styles+'</style></head><body><div class="background-blobs"></div><div id="app"></div><div id="toast" class="toast"></div>'+''.join(scripts)+'</body></html>'

def run():
    outputs=[];errors=[];calls=[];advisor_count=0
    report={
      'status':'completed','analysis_id':'11111111-1111-4111-8111-111111111111','client_id':'placeholder',
      'metrics':{'interaction_index':67,'participation_balance':1.0,'other_question_ratio':0.5,'shared_activity_ratio':0.25,'positive_tone_ratio':0.5,'message_counts':{'total':2,'self':1,'other':1,'unknown':0},'disclaimer':'仅为模拟评估数据。'},
      'daily_distribution':[{'date':'2026-11-07','total':2,'self':1,'other':1,'unknown':0}],
      'portraits':{'self_portrait':[{'label':'发问方式','level':'直接','detail':'来自虚构聊天片段。'}],'other_portrait':[{'label':'回应方式','level':'开放','detail':'仅描述示例回复。'}]},
      'signals':[{'category':'positive','name':'回应对话','description':'虚构 TA 有继续回答','evidence_ids':['m002'],'positive_interpretation':'正常参与聊天','alternative_interpretation':'一般礼貌回应'}],
      'evidence':{'m002':{'id':'m002','content':'有呀，怎么啦？','sender':'other'}},
      'relationship_assessment':{'stage':'信息有限','summary':'这两条虚构对话不足以判定真实感受。','neutral_alternatives':['日常礼貌交流']},'limitations':['仅有两条消息'],'data_quality':{'total_messages':2}
    }
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        html=build_html()
        page.set_content(html,wait_until='load',timeout=50000)
        assert page.locator('.v4-home').count()==1
        assert page.locator('.v5-home-login').count()==1
        assert page.locator('nav.nav-links [data-go="report"]').count()==1
        outputs.append('原首页、登录及第 5 个关系报告导航保留')

        page.locator('nav.nav-links [data-go="advisor"]').click()
        assert page.locator('.v4-chat-panel').count()==1
        assert '演示模式' in page.locator('.chat-composer .disclaimer').inner_text()
        page.locator('#advisorInput').fill('TA 忙时我应该怎么办？')
        page.locator('[data-action="send"]').click()
        page.locator('#advisorInput').fill('我能否尊重 TA 的边界？')
        page.locator('[data-action="send"]').click()
        assert page.locator('.chat-msg.me').count()==2
        assert page.locator('.chat-msg.bot').count()==3
        outputs.append('P0-3 无分析仍可打开完整聊天室，预设多轮回复且明确为演示')

        page.locator('nav.nav-links [data-go="report"]').click()
        assert page.locator('.report-section').count()==0
        page.locator('[data-action="sample-report"]').click()
        assert page.locator('.report-section').count()==4
        assert 'Agent 3' in page.locator('.report-footer-note').inner_text()
        assert page.locator('.report-metrics').count()==1
        page.evaluate('window.__printTriggered=false;window.print=()=>{window.__printTriggered=true}')
        page.locator('[data-action="print-report"]').click()
        assert page.evaluate('window.__printTriggered') is True
        outputs.append('P0-4 无分析时不伪造报告；虚构样例可生成四章报告并打印')

        page.locator('[data-action="mode-real"]').click()
        page.locator('nav.nav-links [data-go="advisor"]').click()
        assert page.locator('.v4-chat-panel').count()==1
        assert page.locator('.send-btn').is_disabled()
        assert 'analysis_id' in page.locator('.v4-workspace').inner_text()
        outputs.append('P0-3 真实模式未获 analysis_id 前禁止发送，但保留聊天室')

        page.route('https://api.test/**',lambda route:handle_api(route,report,calls))
        page.evaluate("window.HeartSignalAPIConfig={baseUrl:'https://api.test',enabled:true,timeoutMs:8000}")
        page.locator('nav.nav-links [data-go="import"]').click()
        page.locator('#fileInput').set_input_files(str(ROOT/'tests/fixtures/chat-schema1-standard.json'))
        page.locator('#parseStatus').get_by_text('解析成功',exact=False).wait_for(timeout=10000)
        assert '2 条消息' in page.locator('#previewCount').inner_text()
        assert page.locator('.preview-chat').count()==2
        page.locator('#consent').check();page.locator('#identityConfirmed').check();page.locator('#sendConsent').check()
        page.locator('[data-action="analyze"]').click()
        page.locator('.score-center b').get_by_text('67').wait_for(timeout=10000)
        assert len([x for x in calls if x[0]=='/api/v1/analyze'])==1
        assert '后端' in page.locator('.mode-strip').inner_text()
        outputs.append('P0-2 JSON 上传、身份授权、模拟 HTTP 接口、动态 67 指数与消息统计')
        page.locator('nav.nav-links [data-go="portraits"]').click()
        assert '虚构聊天片段' in page.locator('.portrait-grid').inner_text()
        page.locator('nav.nav-links [data-go="advisor"]').click()
        page.locator('#advisorInput').fill('第一轮要怎么做？')
        page.locator('[data-action="send"]').click()
        page.locator('.chat-msg.bot').last.get_by_text('模拟服务第 1 轮',exact=False).wait_for(timeout=10000)
        page.locator('#advisorInput').fill('第二轮呢？')
        page.locator('[data-action="send"]').click()
        page.locator('.chat-msg.bot').last.get_by_text('模拟服务第 2 轮',exact=False).wait_for(timeout=10000)
        advisor_requests=[req for path,req in calls if path=='/api/v1/advisor/chat']
        assert len(advisor_requests)==2
        assert advisor_requests[0]['session_id'] is None
        assert advisor_requests[1]['session_id']=='22222222-2222-4222-8222-222222222222'
        outputs.append('P0-3 后端协议桩 2 轮上下文使用同一 session_id')
        page.locator('nav.nav-links [data-go="report"]').click()
        assert page.locator('.report-section').count()==4
        assert '这两条虚构对话不足' in page.locator('.report-section').last.inner_text()
        assert '模拟服务第 2 轮' in page.locator('.report-section').last.inner_text()
        assert '有呀，怎么啦？' in page.locator('.report-section').nth(2).inner_text()
        assert '没有调用 Agent 3' in page.locator('.report-footer-note').inner_text()
        outputs.append('P0-4 后端结构化报告 + 证据 + 同会话军师回复正确汇总，未冒充 Agent 3')

        # A reply started under the previous analysis must stay out of a new report.
        pending = []
        advisor_url = 'https://api.test/api/v1/advisor/chat'
        page.route(advisor_url, lambda route: pending.append(route))
        page.locator('nav.nav-links [data-go="advisor"]').click()
        page.locator('#advisorInput').fill('来自旧分析的问题')
        with page.expect_request(advisor_url):
            page.locator('[data-action="send"]').click()
        page.locator('nav.nav-links [data-go="import"]').click()
        page.locator('[data-action="analyze"]').click()
        page.locator('.score-center b').get_by_text('67').wait_for(timeout=10000)
        with page.expect_response(advisor_url):
            handle_api(pending[0], report, calls)
        page.locator('nav.nav-links [data-go="advisor"]').click()
        assert page.locator('.chat-msg.bot').count() == 1
        assert page.locator('.send-btn').is_enabled()
        page.unroute(advisor_url)
        outputs.append('重新分析后忽略上一次分析的延迟军师回复')

        # Disconnect backend and verify that user still has to manually opt in to demo.
        page.locator('nav.nav-links [data-go="import"]').click()
        page.route('https://api.test/api/v1/analyze',lambda route:route.fulfill(status=503,headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},body=json.dumps({'error':{'code':'MODEL_NOT_CONFIGURED','message':'模拟断网'}})))
        page.locator('[data-action="analyze"]').click()
        page.locator('.mode-error').get_by_text('模拟断网',exact=False).wait_for(timeout=10000)
        assert '真实 API' in page.locator('.mode-strip').inner_text()
        page.locator('.mode-error [data-action="mode-demo"]').first.click()
        assert '演示模式' in page.locator('.mode-strip').inner_text()
        page.locator('nav.nav-links [data-go="advisor"]').click()
        assert page.locator('.v4-chat-panel').count()==1
        outputs.append('P0-7 后端故障不静默切 Mock，手动切演示后仍可聊天')
        assert not errors,errors
        mobile=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        mobile.on('pageerror',lambda e:errors.append(str(e)))
        mobile.set_content(html,wait_until='load',timeout=50000)
        assert mobile.locator('.mobile-shortcuts').is_visible()
        mobile.locator('.mobile-shortcuts [data-go="advisor"]').click()
        assert mobile.locator('.v4-chat-panel').count()==1
        assert mobile.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
        mobile.locator('.mobile-shortcuts [data-go="report"]').click()
        assert mobile.locator('.empty-state').count()==1
        mobile.locator('[data-action="sample-report"]').click()
        assert mobile.locator('.report-section').count()==4
        assert mobile.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1')
        assert not errors,errors
        outputs.append('移动端军师与关系报告导航可达；无横向溢出与 JS 异常')
        mobile.context.close()
        browser.close()
    log='\n'.join('PASS '+x for x in outputs)+'\n'
    print(log)

def handle_api(route,report,calls):
    req=route.request
    path=req.url.split('api.test',1)[-1]
    head={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type,X-Client-Id','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Content-Type':'application/json'}
    if req.method=='OPTIONS':route.fulfill(status=204,headers=head,body='');return
    if path=='/health':
        route.fulfill(status=200,headers=head,body=json.dumps({'status':'ok','model':{'configured':True,'provider':'local-preview','model':'simulated-fixture'},'features':{'thinking_supported':False,'web_search':{'supported':False}}}));return
    req_body=json.loads(req.post_data or '{}')
    calls.append((path,req_body))
    if path=='/api/v1/analyze':
        resp=dict(report);resp['client_id']=req_body['client_id'];route.fulfill(status=200,headers=head,body=json.dumps(resp,ensure_ascii=False));return
    if path=='/api/v1/advisor/chat':
        turn=len([x for x in calls if x[0]=='/api/v1/advisor/chat'])
        route.fulfill(status=200,headers=head,body=json.dumps({'reply':f'模拟服务第 {turn} 轮：尊重双方边界。','session_id':'22222222-2222-4222-8222-222222222222','turn':turn,'suggestions':['仅限模拟建议'],'evidence':[],'boundary_notes':[]},ensure_ascii=False));return
    route.fulfill(status=404,headers=head,body='{}')

if __name__=='__main__':run()
