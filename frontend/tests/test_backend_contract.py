"""Browser-level contract test against a mocked copy of Wenqing's documented API.
No real provider, private chat record, or live backend is used.
"""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
FX=ROOT/'tests'/'fixtures'

def build_html():
    css='\n'.join((ROOT/f).read_text('utf8') for f in ['styles.css','refinement.css','wizard.css','phase1.css'])
    scripts='\n'.join('<script>'+ (ROOT/f).read_text('utf8') +'</script>' for f in ['api/config.js','api/client.js','api/adapter.js','dashboard.js','mocks/mock-data.js','app.js'])
    return '<html><head><meta charset="UTF-8"><style>'+css+'</style></head><body><div class="background-blobs"></div><div id="app"></div><div id="toast" class="toast"></div>'+scripts+'</body></html>'

def run():
    calls=[]; errors=[]
    analysis={
      'analysis_id':'11111111-1111-4111-8111-111111111111',
      'client_id':'frontend-test-1234',
      'created_at':'2026-11-07T12:00:00+00:00','expires_at':'2026-11-14T12:00:00+00:00',
      'status':'completed',
      'metrics':{
        'message_counts':{'self':1,'other':1,'unknown':0,'total':2},
        'participation_balance':1.0,'other_question_ratio':0.25,
        'shared_activity_ratio':0.5,'positive_tone_ratio':None,
        'interaction_index':68.5,
        'semantic_detection':{'method':'llm','text_message_count':2,'flagged_message_count':2,'note':'由 LLM 标记'},
        'disclaimer':'互动参考指数是启发式参考值，不代表真实好感概率。'
      },
      'daily_distribution':[{'date':'2026-11-06','self':1,'other':1,'unknown':0,'total':2}],
      'portraits':{
        'self_portrait':[{'key':'topic_initiative','label':'话题主动性','level':'中','score':55,'detail':'本人发起一条问题。','evidence_ids':['m001'],'confidence':'medium'}],
        'other_portrait':[{'key':'response_engagement','label':'关心与回应程度','level':'数据不足','score':None,'detail':'样本较短。','evidence_ids':['m002'],'confidence':'low'}]
      },
      'signals':[{'category':'positive','name':'积极回应','description':'对方回应了周末安排。','evidence_ids':['m002'],'positive_interpretation':'愿意继续交流。','alternative_interpretation':'也可能只是礼貌回应。','evidence_strength':'medium','impact':'仅作参考','scope':'仅限当前样本'}],
      'relationship_assessment':{'stage':'信息不足','summary':'当前只有两条消息，不能判断关系发展。','supporting_facts':['对方作出回应。'],'contradicting_facts':[],'neutral_alternatives':['可能是普通礼貌回应。'],'confidence':'low'},
      'advisor':{'suggestions':['先自然确认周末安排。']},
      'evidence':{'m002':{'id':'m002','sender':'other','sender_label':'对方(TA)','timestamp':'2026-11-06T22:41','type':'text','content':'有呀！','sender_name':'测试联系人'}},
      'data_quality':{'total_messages':2,'confirmed_sender_ratio':1.0,'unknown_sender_ratio':0.0,'analyzable_text_ratio':1.0,'time_order_anomalies':0,'duplicate_message_risk':'low','partial_export_possible':False,'coverage':'2 条消息'},
      'limitations':['样本只有两条消息。'],'errors':[]
    }
    advisor_turn=0
    with sync_playwright() as p:
      browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
      page=browser.new_page(viewport={'width':1440,'height':1000})
      page.on('pageerror',lambda e:errors.append(str(e)))
      def route_handler(route):
        nonlocal advisor_turn
        req=route.request
        path=req.url.split('api.test',1)[-1]
        headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type,X-Client-Id','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Content-Type':'application/json'}
        if req.method=='OPTIONS':
          route.fulfill(status=204,headers=headers,body='');return
        if path=='/health':
          route.fulfill(status=200,headers=headers,body=json.dumps({'status':'ok','version':'test','time':'2026-11-07T12:00:00Z','store_backend':'memory','model':{'provider':'mock','model':'mock-model'},'features':{'thinking_levels':['auto','low','medium','high'],'thinking_supported':True,'thinking_note':'测试端点支持思考参数。','web_search':{'supported':True,'default_enabled':False}}}));return
        body=json.loads(req.post_data or '{}')
        calls.append({'path':path,'body':body,'headers':dict(req.headers)})
        if path=='/api/v1/analyze':
          response=dict(analysis);response['client_id']=body.get('client_id')
          route.fulfill(status=200,headers=headers,body=json.dumps(response,ensure_ascii=False));return
        if path=='/api/v1/advisor/chat':
          advisor_turn+=1
          route.fulfill(status=200,headers=headers,body=json.dumps({'analysis_id':body['analysis_id'],'session_id':'22222222-2222-4222-8222-222222222222','turn':advisor_turn,'reply':f'测试军师第 {advisor_turn} 轮：先尊重对方的节奏。','evidence_ids':['m002'],'evidence':[{'id':'m002','sender':'other','sender_label':'对方(TA)','timestamp':'2026-11-06T22:41','type':'text','content':'有呀！'}],'suggestions':['先自然确认具体时间。'],'boundary_notes':[],'ai_config':{'thinking':{'requested':body.get('thinking_level'),'applied':body.get('thinking_level'),'supported':True},'web_search':{'requested':body.get('web_search',False),'performed':False,'results_count':0,'query_used':None,'note':'mock test'}}},ensure_ascii=False));return
        route.fulfill(status=404,headers=headers,body='{}')
      page.route('https://api.test/**',route_handler)
      page.set_content(build_html(),wait_until='load',timeout=30000)
      page.evaluate("window.HeartSignalAPIConfig={baseUrl:'https://api.test',enabled:true,timeoutMs:5000}")
      page.locator('nav [data-go="import"]').first.click()
      page.locator('[data-action="mode-real"]').click()
      page.locator('.mode-strip').get_by_text('后端健康检查通过',exact=False).wait_for(timeout=5000)
      page.locator('#fileInput').set_input_files(str(FX/'chat-schema1-naive-time.json'))
      page.locator('#parseStatus').get_by_text('解析成功：共 2 条',exact=False).wait_for(timeout=5000)
      assert '2026-11-06 22:39' in page.locator('#previewMessages').inner_text()
      assert '没有时区偏移' in page.locator('#parseStatus').inner_text()
      page.locator('#consent').check();page.locator('#identityConfirmed').check();page.locator('#sendConsent').check()
      page.locator('[data-action="analyze"]').click()
      page.locator('.score-center b').get_by_text('69').wait_for(timeout=5000)
      assert len(calls)==1 and calls[0]['path']=='/api/v1/analyze'
      req=calls[0]['body']
      assert req['conversation']['messages'][0]['timestamp']=='2026-11-06T22:39'
      assert req['conversation']['messages'][0]['sender_name']=='me'
      assert isinstance(req['client_id'],str) and len(req['client_id'])>=8
      assert calls[0]['headers'].get('x-client-id')==req['client_id']
      assert req['options']['include_evidence'] is True
      assert req['options']['thinking_level']=='auto'
      assert '双方共同活动表达占比' in page.locator('.signal-detail-grid').inner_text()
      assert '数据不足' in page.locator('.signal-detail-grid').inner_text()
      assert '25%' in page.locator('.tiny-metrics').inner_text()
      page.locator('nav [data-go="portraits"]').first.click()
      assert 'Agent 交流画像' in page.locator('.portrait-grid').inner_text()
      assert '样本较短' in page.locator('.portrait-grid').inner_text()
      page.locator('nav [data-go="advisor"]').first.click()
      page.locator('#thinkingLevel').select_option('high')
      page.locator('#webSearch').check()
      page.locator('#advisorInput').fill('第一轮：下一步怎么做？')
      page.locator('[data-action="send"]').click()
      page.locator('.chat-msg.bot').last.get_by_text('测试军师第 1 轮',exact=False).wait_for(timeout=5000)
      page.locator('#advisorInput').fill('第二轮：怎么确认时间？')
      page.locator('[data-action="send"]').click()
      page.locator('.chat-msg.bot').last.get_by_text('测试军师第 2 轮',exact=False).wait_for(timeout=5000)
      advisor_calls=[x for x in calls if x['path']=='/api/v1/advisor/chat']
      assert len(advisor_calls)==2
      assert advisor_calls[0]['body']['analysis_id']==analysis['analysis_id']
      assert advisor_calls[0]['body']['session_id'] is None
      assert advisor_calls[0]['body']['thinking_level']=='high'
      assert advisor_calls[0]['body']['web_search'] is True
      assert advisor_calls[1]['body']['session_id']=='22222222-2222-4222-8222-222222222222'
      assert advisor_calls[1]['body']['client_id']==calls[0]['body']['client_id']
      assert '有呀！' in page.locator('.chat-scroll').inner_text()
      assert '先自然确认具体时间' in page.locator('.v4-advisor-aside').inner_text()
      assert not errors,errors
      browser.close()
    print('PASS: 无时区 Schema 1.0 导入与原文保留')
    print('PASS: analyze 请求体、client_id、请求头及真实 metrics 映射')
    print('PASS: null 指标显示数据不足，画像使用后端响应')
    print('PASS: advisor 首轮与后续 session_id、多轮及配置参数契约')
    print('PASS: 证据、建议和后端回复渲染；无浏览器异常')
if __name__=='__main__':run()
