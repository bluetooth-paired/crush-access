/*
 * 申请查看你的好感度 · 申请查看你的好感度
 * Standalone interactive design prototype. No remote requests, no persistence.
 * Deterministic, rule-based demo analysis: NOT an AI, psychological assessment,
 * scientific relationship score, or a prediction of anyone's feelings.
 */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp = (n, a, b) => Math.min(b, Math.max(a, n));
  const icons = {
    heart:'<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
    arrow:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
    spark:'<path d="m12 3 1.8 6.2L20 11l-6.2 1.8L12 19l-1.8-6.2L4 11l6.2-1.8L12 3Z"/><path d="m19 17 .7 2.3L22 20l-2.3.7L19 23l-.7-2.3L16 20l2.3-.7L19 17Z"/>',
    upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 16v4h16v-4"/>',
    shield:'<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    chat:'<path d="M20 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.6 0-3-.4-4.2-1.1L3 20l1.2-4.1a8.5 8.5 0 1 1 15.8-4.4Z"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    users:'<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 5a3 3 0 0 1 0 6m1 9v-2a6 6 0 0 0-3-5.2"/>',
    chart:'<path d="M4 19V5m0 14h16M7 14l4-4 3 2 5-6"/>',
    magic:'<path d="m4 20 13-13 3 3L7 23 4 20ZM15 3v4m-2-2h4M20 14v4m-2-2h4"/>',
    chevron:'<path d="m9 18 6-6-6-6"/>',
    copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    send:'<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    lock:'<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
    alert:'<path d="M12 3 2 21h20L12 3ZM12 9v5m0 4h.01"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>',
    question:'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5m0 4h.01"/>',
    file:'<path d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2ZM14 3v5h5"/><path d="M9 13h6m-6 4h6"/>',
    rotate:'<path d="M20 11a8 8 0 1 0-2.5 6M20 4v7h-7"/>',
    smile:'<circle cx="12" cy="12" r="9"/><path d="M8 14c2 3 6 3 8 0M8 9h.01M16 9h.01"/>',
    book:'<path d="M3 5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2V5Zm10 0a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v16a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2V5Z"/>',
    star:'<path d="m12 2 3.1 6.6 7.3 1-5.3 5.2 1.3 7.2-6.4-3.4-6.4 3.4 1.3-7.2-5.3-5.2 7.3-1L12 2Z"/>',
    close:'<path d="M5 5 19 19M19 5 5 19"/>',
    trash:'<path d="M4 7h16M10 11v7m4-7v7M6 7l1 14h10l1-14M9 7V4h6v3"/>'
  };
  const ic = (name, size=18) => `<svg aria-hidden="true" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${icons[name] || icons.heart}</svg>`;
  const mascot = (className='mascot-svg') => `<svg class="${className}" viewBox="0 0 240 240" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="粉色爱心军师子乔的原创卡通形象">
    <ellipse cx="117" cy="216" rx="70" ry="13" fill="#b595b6" opacity=".19" />
    <path d="M121 56C86 24 33 39 32 88c-1 50 53 83 88 118 38-35 88-68 87-118-2-47-53-65-86-32Z" fill="#FA7F9C" stroke="#D94D7B" stroke-width="3"/>
    <path d="M121 65C92 38 49 48 47 85" stroke="#FFC3D0" stroke-width="12" stroke-linecap="round" opacity=".85"/>
    <circle cx="83" cy="114" r="13" fill="#F65B83" opacity=".7"/><circle cx="164" cy="114" r="13" fill="#F65B83" opacity=".7"/>
    <path d="M71 102c7-9 18-9 25 0m42 0c7-9 18-9 25 0" stroke="#493041" stroke-width="6" stroke-linecap="round"/>
    <path d="M110 127c7 8 18 8 25 0" stroke="#493041" stroke-width="5" stroke-linecap="round"/>
    <path d="M28 147c-15-8-18-22-12-27M208 145c15-10 19-20 18-30" stroke="#D94D7B" stroke-width="9" stroke-linecap="round"/>
    <path d="M79 187c-10 18-14 30-14 34m109-34c10 18 13 30 13 34" stroke="#D94D7B" stroke-width="9" stroke-linecap="round"/>
    <path d="M102 147h40l-7 36h-26l-7-36Z" fill="#FFF3EE" stroke="#DE6286" stroke-width="3"/>
    <path d="m122 157-7 9 7 10 7-10-7-9Z" fill="#745CBB"/>
    <path d="M97 40c-4-14 8-23 19-22m18 17c10-21 27-13 28-3" stroke="#9E81CC" stroke-width="7" stroke-linecap="round"/>
    <path d="M112 16 118 4l7 13" fill="#FED78E"/>
    <path d="m191 43 4 10 11 2-11 3-4 11-3-11-11-3 11-2 3-10Z" fill="#FFD166"/>
    <path d="m37 51 3 7 8 2-8 2-3 8-2-8-8-2 8-2 2-7Z" fill="#FFC66E"/>
  </svg>`;

  const sampleText = `2026-11-02 19:12 我: 你上次说的艺术展终于开了诶！\n2026-11-02 19:14 小林: 哈哈真的吗！我刷到过那个展\n2026-11-02 19:15 我: 听说互动装置特别有意思\n2026-11-02 19:17 小林: 你最近是不是也在准备期中呀？\n2026-11-02 19:18 我: 对！一边复习一边想出去玩😂\n2026-11-02 19:20 小林: 哈哈哈谁不是呢，最近感觉每天都好累\n2026-11-03 21:03 小林: 对了你上次推荐的歌我听啦，很好听！\n2026-11-03 21:04 我: 真的嘛！哪首最好听\n2026-11-03 21:05 小林: 第二首！前奏一出来我就喜欢了\n2026-11-03 21:06 小林: 你还有类似的歌单吗？\n2026-11-03 21:08 我: 有的，我晚点整理给你\n2026-11-03 21:09 小林: 好呀！期待你的分享\n2026-11-04 18:22 我: 那个展我看了下周末还有票\n2026-11-04 18:23 小林: 诶好耶，你打算什么时候去呀？\n2026-11-04 18:25 我: 可能周六下午\n2026-11-04 18:27 小林: 下次可以一起去呀，我正好也想看！\n2026-11-04 18:29 我: 可以！我查下具体时间\n2026-11-04 18:31 小林: 好～你到时候跟我说就行 🌷`;

  const state = {
    view:'home', tab:'text', raw:'', mode:'demo', mockKey:null, dashboard:null, report:null, analysisId:null, sessionId:null, clientId:null, analysisRunToken:0, chatRunToken:0, apiBusy:false, apiError:'', identityConfirmed:false, sendConsent:false, advisorBusy:false, advisorError:'', failedAdvisorQuestion:'', ownName:'我', otherName:'小林', ownMBTI:'', otherMBTI:'', demo:false, consent:false, apiHealth:null, apiHealthError:'', apiHealthLoading:false, thinkingLevel:'auto', webSearch:false, advisorSuggestions:[], advisorBoundaryNotes:[],
    analysis:null, messages:[], parseResult:{format:'empty',messages:[],error:null,warnings:[]}, fileFormatHint:null, advisorMessages:[], advisorInput:'', privacyOpen:false, loggedIn:false, authTab:'login', loginMethod:'phone', authName:'', profileSaved:false, profileStep:0, profileDirection:'forward', profile:{meNick:'',meGender:'',meAge:'',meMBTI:'',meTraits:[],meStatus:'',meStyle:'',meNeed:'',taNick:'',taGender:'',taAge:'',taMBTI:'',taTraits:[],taStyle:'',taEmotional:'',taUnsure:'',relation:'',stage:'',frequency:'',events:'',eventItems:[],touch:'',boundaries:'',goal:'signals',concern:''}
  };
  function getClientId() {
    const key='heart_signal_client_id';
    try {
      const existing=localStorage.getItem(key);
      if(existing && /^[A-Za-z0-9_-]{8,64}$/.test(existing))return existing;
      const generated=(window.crypto?.randomUUID?.()||`hs_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,12)}`).replace(/[^A-Za-z0-9_-]/g,'');
      const safe=generated.length>=8?generated:`hs_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,8)}`;
      localStorage.setItem(key,safe);return safe;
    } catch {return `hs_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,10)}`;}
  }
  state.clientId=getClientId();
  let toastTimer;
  function toast(msg) {
    const el = $('toast'); el.textContent = msg; el.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3100);
  }
  const parts=[
    {id:'import',name:'聊天导入',icon:'upload'},
    {id:'portraits',name:'双向画像',icon:'users'},
    {id:'signals',name:'互动信号',icon:'chart'},
    {id:'advisor',name:'军师交流',icon:'chat'}
  ];
  function topbar(){
    const links=[['home','首页'],['import','聊天导入'],['profile','人物档案'],['portraits','双向画像'],['signals','互动信号'],['advisor','军师交流']];
    return `<header class="site-header v4-header"><a class="brand" href="#home" data-go="home"><span class="brand-icon">${ic('heart',23)}</span><span>申请查看你的好感度<small>HEART SIGNAL LAB</small></span></a><nav class="nav-links">${links.map(([id,name])=>`<button data-go="${id}" class="${state.view===id?'current':''}">${name}</button>`).join('')}</nav><div class="v5-nav-right"><button class="v5-profile-link ${state.view==='auth'?'selected':''}" data-go="${state.loggedIn?'profile':'auth'}">${state.loggedIn?'♡ 档案设置':'登录 / 注册'}</button><button class="nav-action" data-go="import">开始分析 ${ic('arrow',15)}</button></div></header>`;
  }
    function home(){
    return `${topbar()}<main class="v4-home">
      <section class="v4-hero max">
        <div class="v4-copy"><span class="eyebrow"><span class="tiny-dot"></span> 你的专属 AI 恋爱军师已上线</span><h1>申请查看<br/>你的<span class="special">好感度。</span></h1><p>聊天记录里藏着什么小秘密？<br/>导入你和 TA 的对话，让子乔军师帮你看清互动节奏，找到更自然的下一步。</p>
          <div class="hero-ctas"><button class="btn btn-primary" data-go="import">开始聊天分析 ${ic('arrow',18)}</button><button class="btn btn-white" data-action="sample">${ic('spark',15)} 查看示例报告</button></div>
          <div class="v4-trust">${ic('lock',15)} 本地隐私演示 <span></span> ${ic('check',15)} 不猜测 TA 的真实心理</div>
        </div>
        <div class="v4-collage" aria-label="吕子乔恋爱军师人物主视觉"><div class="v4-soft-glow"></div><div class="v4-photo v4-photo-left"><img src="images/ziqiao-photo.jpeg" alt="子乔侧面剧照"/></div><div class="v4-photo v4-photo-right"><img src="images/ziqiao-black.jpg" alt="子乔黑西装剧照"/></div><img class="v4-hero-actor" src="images/ziqiao-cutout.png" alt="吕子乔西装造型主视觉"/><div class="v4-hand-heart" aria-hidden="true">♡</div><div class="v4-note"><span>人生没有彩排，<br/>每一天都是现场直播。</span><small>—— 子乔语录 · 资料节选</small></div></div>
        <div class="v5-home-login">
          <div class="v5-login-tabs"><button class="${state.loginMethod==='phone'?'active':''}" data-action="method-phone">${ic('user',16)} 手机号登录</button><button class="${state.loginMethod==='wechat'?'active':''}" data-action="method-wechat">${ic('chat',16)} 微信登录</button></div>
          ${loginForm(true)}
        </div>
      </section>
      <section class="max v4-feature-block"><div class="v4-section-intro"><span>FOUR SIMPLE STEPS</span><h2>从一段聊天，到更清楚的下一步</h2><p>没有复杂操作，只保留你真正需要的功能。</p></div><div class="v4-features">
        <button data-go="import"><div class="v4-feature-icon">${ic('upload',23)}</div><span>01 / CHAT</span><h3>聊天导入</h3><p>粘贴文字或选择文本文件，快速整理聊天内容。</p><b>立即导入 ${ic('arrow',15)}</b></button>
        <button data-go="portraits"><div class="v4-feature-icon">${ic('users',23)}</div><span>02 / PEOPLE</span><h3>双向画像</h3><p>了解双方表达习惯与互动模式。</p><b>生成画像 ${ic('arrow',15)}</b></button>
        <button data-go="signals"><div class="v4-feature-icon">${ic('chart',23)}</div><span>03 / SIGNALS</span><h3>互动信号</h3><p>观察主动提问、话题延续与边界信号。</p><b>查看信号 ${ic('arrow',15)}</b></button>
        <button data-go="advisor"><div class="v4-feature-icon">${ic('chat',23)}</div><span>04 / WINGMAN</span><h3>军师交流</h3><p>让子乔给你自然、不越界的回复灵感。</p><b>找子乔聊 ${ic('arrow',15)}</b></button>
      </div></section><section class="max v4-bottom-line"><div>♡ &nbsp;心动需要勇气，也需要一点清醒。</div><button data-go="import" class="btn btn-white">从聊天开始 ${ic('arrow',15)}</button></section></main>${footer()}`;
  }
  function footer(){return `<footer class="footer"><div class="max"><span>♡ 申请查看你的好感度 · 学生项目交互演示</span><span>真诚沟通，尊重彼此意愿。</span></div></footer>`;}
  function sidebar() {return `<aside class="sidebar"><div class="sidebar-title">YOUR HEART JOURNEY</div><div class="step-list">${parts.map((p,i)=>`<button class="step-link ${state.view===p.id?'active':''}" data-go="${p.id}" aria-current="${state.view===p.id?'step':'false'}"><span class="step-icon">${ic(p.icon,17)}</span><span>${p.name}</span>${state.analysis&&i<parts.findIndex(x=>x.id===state.view)?`<span style="margin-left:auto;color:#55ab8f">${ic('check',14)}</span>`:''}</button>`).join('')}</div><div class="sidebar-sep"></div><div class="sidebar-mascot"><img src="images/ziqiao-portrait.jpeg" alt="子乔军师"/><strong>子乔军师 · 演示版</strong><p>恋爱可以心动，判断要留理性。</p></div></aside>`;}

  const ageOptions=['','18岁以下','18–20岁','21–23岁','24–26岁','27岁及以上','不方便透露'];
  const traitList=['外向开朗','内向安静','理性冷静','感性细腻','慢热','主动','幽默','重视边界','热爱分享','喜欢计划'];
  function profileField(id,label,placeholder='',type='text',max=100){const value=state.profile[id]||'';return `<label class="v5-field"><span>${esc(label)}</span><input type="${type}" data-profile="${id}" maxlength="${max}" placeholder="${esc(placeholder)}" value="${esc(value)}"/></label>`;}
  function profileSelect(id,label,options){const val=state.profile[id]||'';return `<label class="v5-field"><span>${esc(label)}</span><select data-profile="${id}">${options.map(o=>{const v=Array.isArray(o)?o[0]:o;const t=Array.isArray(o)?o[1]:o;return `<option value="${esc(v)}" ${v===val?'selected':''}>${esc(t)}</option>`}).join('')}</select></label>`;}
  function chips(id){return `<div class="v5-chips">${traitList.map(t=>`<button type="button" class="v5-chip ${(state.profile[id]||[]).includes(t)?'active':''}" data-trait="${id}" data-value="${t}">${t}</button>`).join('')}</div>`;}
  function loginForm(compact=false){return `${state.loginMethod==='wechat' ? `<div class="v5-wechat-placeholder">${ic('chat',30)}<strong>微信扫码登录</strong><span>这是视觉演示，尚未接入微信开放平台。</span><button data-action="method-phone" class="v5-text-button">改用手机号演示登录</button></div>` : `<div class="v5-auth-fields"><label><span class="sr-only">手机号</span><input id="demoPhone" inputmode="tel" placeholder="请输入手机号（演示可留空）" maxlength="20" autocomplete="off"/></label><div class="v5-code-line"><label><span class="sr-only">验证码</span><input id="demoCode" inputmode="numeric" placeholder="请输入验证码（演示）" maxlength="8" autocomplete="off"/></label><button data-action="demo-code" type="button">获取验证码</button></div><label><span class="sr-only">密码</span><input id="demoPassword" type="password" placeholder="请输入密码（演示，无需填写）" maxlength="30" autocomplete="off"/></label></div>`}
      <button class="v5-login-submit" data-action="demo-login">${state.authTab==='register'?'创建演示账户':'演示登录并开始'} ${ic('arrow',16)}</button><div class="v5-signup-line">${state.authTab==='register'?'已经有账号？':'还没有账号？'} <button data-action="toggle-auth">${state.authTab==='register'?'返回登录':'立即注册'} →</button></div><div class="v5-login-disclaimer">${ic('lock',14)} 仅限离线原型演示 · 不发送短信 · 不保存密码</div>`;}
  function authPage(){return `${topbar()}<main class="v5-auth-page max"><section class="v5-auth-left"><span class="eyebrow">${ic('heart',14)} &nbsp; 子乔军师 · 专属档案</span><h1>先认识你，<br/>再陪你把<span>心事</span>说清楚。</h1><p>从一个真实的故事开始，保存你的沟通偏好与关系背景，让每次分析更有上下文。</p><div class="v5-auth-actor"><img src="images/ziqiao-cutout.png" alt="吕子乔角色主题形象"/><div class="v5-actor-note">“人生没有彩排，每一天都是现场直播。”</div></div></section><section class="v5-auth-form"><div class="v5-form-top"><span>WELCOME TO HEART SIGNAL</span><h2>${state.authTab==='register'?'创建你的演示档案':'欢迎回来，心动观察员'}</h2><p>登录后即可填写人物背景，并进入聊天分析。</p></div><div class="v5-auth-switch"><button class="${state.authTab==='login'?'active':''}" data-action="auth-login">登录</button><button class="${state.authTab==='register'?'active':''}" data-action="auth-register">注册</button></div><div class="v5-login-tabs"><button class="${state.loginMethod==='phone'?'active':''}" data-action="method-phone">${ic('user',16)} 手机号登录</button><button class="${state.loginMethod==='wechat'?'active':''}" data-action="method-wechat">${ic('chat',16)} 微信登录</button></div>${loginForm()}</section></main>${footer()}`;}
  const wizardSteps=[
    {name:'关于你',en:'ABOUT YOU',title:'先从你开始，',highlight:'让分析更懂你。',desc:'告诉我们你平时如何表达、对关系有哪些期待。先理解自己，才更容易看清互动。',quote:'先把你自己说清楚，我才能帮你看清对方的反应。'},
    {name:'关于 TA',en:'ABOUT THEM',title:'再聊聊 TA，',highlight:'走近真实的对方。',desc:'只填写你亲自观察到、或 TA 明确告诉过你的事情；不确定的内容可以留空。',quote:'别靠脑补认识 TA，了解越具体，建议才能越贴近现实。'},
    {name:'关系背景',en:'YOUR STORY',title:'最后说说你们的故事，',highlight:'让建议更有上下文。',desc:'认识经过、相处细节和最近的关键事件，比一句“哈哈”更能解释聊天的语境。',quote:'关系的前因后果，往往比一句话更值得琢磨。'}
  ];
  function profilePills(id,vals,desc=''){
    const value=state.profile[id]||'';
    return `<div class="wizard-pills" role="group" aria-label="${esc(desc||id)}">${vals.map(v=>`<button type="button" data-profile-choice="${id}" data-value="${esc(v)}" class="wizard-pill ${value===v?'is-selected':''}" aria-pressed="${value===v}">${value===v?ic('check',14):''}${esc(v)}</button>`).join('')}</div>`;
  }
  function wizardQuestion(num,label,inner,opts=''){
    return `<div class="wizard-question"><div class="wizard-question-head"><span class="wizard-q-index">${String(num).padStart(2,'0')}</span><strong>${label}</strong>${opts?`<small>${opts}</small>`:''}</div><div class="wizard-answer">${inner}</div></div>`;
  }
  function wizardText(id,label,placeholder,max=240,rows=3){return `<label class="v5-field wizard-text"><span>${esc(label)}</span><textarea data-profile="${id}" maxlength="${max}" rows="${rows}" placeholder="${esc(placeholder)}">${esc(state.profile[id]||'')}</textarea></label>`;}
  function wizardStepContent(){const p=state.profile;
    if(state.profileStep===0)return `<div class="wizard-section-kicker">01 / SELF PORTRAIT <span>你的答案不会被用来判断 TA 的心理</span></div>
      <div class="wizard-form-grid">
        ${wizardQuestion(1,'你的昵称是什么？',profileField('meNick','你希望我们怎么称呼你？','例如：小夏 / 阿眠'))}
        ${wizardQuestion(2,'你的性别是？',profilePills('meGender',['女','男','非二元 / 其他','不方便透露'],'性别'),'选填')}
        ${wizardQuestion(3,'你的年龄段？',profileSelect('meAge','年龄段（选填）',ageOptions))}
        ${wizardQuestion(4,'你的 MBTI 类型？',profileSelect('meMBTI','自述类型（选填）',[['','不知道 / 不填写'],...mbtiOptions.filter(Boolean)]),'选填 · 不用于预测好感')}
      </div>
      <div class="wizard-divider"></div>
      ${wizardQuestion(5,'你目前的感情状态？',profilePills('meStatus',['单身，正在观察','有好感对象','暧昧了解中','恋爱中','还不确定'],'感情状态'),'选填')}
      ${wizardQuestion(6,'你在聊天中通常是什么风格？',profilePills('meStyle',['主动直接','温柔体贴','理性冷静','慢热谨慎','随性自然'],'沟通方式'),'选填')}
      ${wizardQuestion(7,'你最看重一段关系中的什么？',profilePills('meNeed',['被理解','真诚表达','稳定回应','个人空间','互相尊重'],'关系期待'),'选填')}
      <div class="wizard-small-note">${ic('heart',16)} 只需要填写愿意分享的部分，答案可以随时返回修改。</div>`;
    if(state.profileStep===1)return `<div class="wizard-section-kicker">02 / ABOUT THEM <span>不确定就留空，不替 TA 作人格判断</span></div>
      <div class="wizard-form-grid">
        ${wizardQuestion(1,'TA 的昵称是什么？',profileField('taNick','你平时怎么称呼 TA？','例如：小林 / 阿 K'))}
        ${wizardQuestion(2,'TA 的性别是？',profilePills('taGender',['男','女','非二元 / 其他','不确定'],'TA 性别'),'选填')}
        ${wizardQuestion(3,'TA 的年龄段？',profileSelect('taAge','已知年龄段（选填）',ageOptions))}
        ${wizardQuestion(4,'TA 自述过 MBTI 吗？',profileSelect('taMBTI','如果知道请选择',[['','不知道 / 不填写'],...mbtiOptions.filter(Boolean)]),'选填')}
      </div>
      <div class="wizard-divider"></div>
      ${wizardQuestion(5,'你观察到 TA 有哪些特点？',chips('taTraits'),'选填 · 可多选')}
      ${wizardQuestion(6,'TA 平时怎么和你聊天？',profilePills('taStyle',['经常主动找话题','会认真回应、偶尔主动','大多等我开启话题','回复比较简短','不好判断'],'TA 的沟通表现'),'选填')}
      ${wizardQuestion(7,'TA 在情感表达上更接近哪种情况？',profilePills('taEmotional',['表达比较直接','会用行动表达','慢热、比较克制','目前还看不出'],'TA 的情感表达'),'选填')}
      ${wizardQuestion(8,'你最拿不准 TA 的哪一点？',wizardText('taUnsure','可以写一句具体困惑','例如：他会主动分享歌单，但不太发起线下邀约……',260,3),'选填')}
      <div class="wizard-small-note">${ic('shield',16)} 对 TA 的描述都只是你的视角，最终以 TA 明确表达的意愿为准。</div>`;
    return `<div class="wizard-section-kicker">03 / YOUR RELATIONSHIP <span>发生过什么，比单句聊天更重要</span></div>
      <div class="wizard-form-grid">
        ${wizardQuestion(1,'你们是怎么认识的？',profileSelect('relation','认识渠道',[['','请选择（可跳过）'],'同学 / 同校','朋友介绍','社团 / 活动','线上认识','工作 / 实习','其他']))}
        ${wizardQuestion(2,'现在处于什么关系阶段？',profileSelect('stage','当前阶段',[['','请选择（可跳过）'],'刚认识','普通朋友','暧昧了解中','正在约会','稳定交往','关系冷淡 / 停止联系']))}
        ${wizardQuestion(3,'平时联系频率如何？',profileSelect('frequency','联系频率',[['','请选择（可跳过）'],'几乎每天','每周多次','每周一次左右','偶尔聊天','很少联系']))}
        ${wizardQuestion(4,'你们在线下见过面吗？',profilePills('touch',['见过','还没见过','不确定'],'线下相处'),'选填')}
      </div>
      <div class="wizard-divider"></div>
      ${wizardQuestion(5,'最近发生过哪些关键事情？',`<div class="wizard-event-list">${(p.eventItems||[]).map((e,i)=>`<div class="wizard-event-row"><input type="date" data-event-field="date" data-event-index="${i}" value="${esc(e.date||'')}" aria-label="事件 ${i+1} 日期"/><input type="text" data-event-field="text" data-event-index="${i}" maxlength="180" value="${esc(e.text||'')}" placeholder="例如：一起去看展 / TA 主动分享歌单" aria-label="事件 ${i+1} 内容"/><button data-action="remove-event" data-index="${i}" type="button" aria-label="移除事件">${ic('close',16)}</button></div>`).join('')}</div><button class="wizard-add-event" type="button" data-action="add-event">${ic('spark',16)} 添加一件小事</button><div class="wizard-memo">${wizardText('events','或者直接用一段话概括','比如：一起参加过活动；TA 曾主动邀请我；最近因为考试联系减少……',700,3)}</div>`,'可以写下 1–3 件')}
      ${wizardQuestion(6,'有没有需要特别尊重的边界？',profilePills('boundaries',['目前没有明确拒绝','TA 表达过不愿继续','尚不确定'],'边界情况'),'可跳过')}
      ${wizardQuestion(7,'这次最希望得到什么帮助？',`<div class="wizard-goals">${[['signals','看清互动信号'],['reply','学习如何回复'],['date','是否适合邀约'],['boundaries','尊重边界和情绪']].map(([v,label])=>`<button type="button" data-goal="${v}" class="${p.goal===v?'active':''}">${ic(p.goal===v?'check':'heart',16)} ${label}</button>`).join('')}</div>`)}
      ${wizardQuestion(8,'有什么问题想直接问子乔？',wizardText('concern','写下你最真实的困惑','例如：TA 回复慢，但见面时很热情，我应该怎么理解？',400,3),'选填')}
      <div class="wizard-small-note">${ic('shield',16)} 以上信息仅在当前网页中使用。分析报告会区分“你提供的背景”和“聊天里的实际证据”。</div>`;
  }
  function profilePage(){
    if(!state.loggedIn)return authPage();
    const i=state.profileStep,meta=wizardSteps[i];
    return `${topbar()}<main class="wizard-page" data-wizard-step="${i}">
      <div class="wizard-top max">
        <div class="wizard-top-title"><span class="wizard-top-spark">✦</span> PERSONA BUILDER · 人物档案</div>
        <div class="wizard-stepper" aria-label="人物档案三个步骤">${wizardSteps.map((t,n)=>`<button type="button" class="wizard-step ${n===i?'active':''} ${n<i?'complete':''}" data-wizard-step="${n}" aria-current="${n===i?'step':'false'}"><span class="wizard-step-number">${n<i?ic('check',14):n+1}</span><span>${t.name}</span></button>${n<2?'<span class="wizard-connector"></span>':''}`).join('')}</div>
        <div class="wizard-progress"><strong>0${i+1} / 03</strong><span class="wizard-progress-track"><i style="width:${(i+1)/3*100}%"></i></span></div>
      </div>
      <div class="wizard-layout max">
        <aside class="wizard-intro"><div class="wizard-intro-eyebrow">${ic('spark',14)} 人物档案 · 第 ${i+1} 阶段</div><h1>${meta.title}<br/><span>${meta.highlight}</span></h1><p>${meta.desc}</p>
          <div class="wizard-actor" aria-hidden="true"><div class="wizard-actor-halo"></div><img src="images/ziqiao-cutout.png" alt=""/><span class="wizard-heart-one">♡</span></div>
          <div class="wizard-quote"><span>“${meta.quote}”</span><small>— 子乔军师 · 风格化提示</small></div>
        </aside>
        <section class="wizard-card" aria-label="${meta.name}的资料问答"><div class="wizard-card-top"><div><span class="wizard-card-en">${meta.en}</span><h2>${meta.name}<small>第 ${i+1} / 3 阶段</small></h2></div><span class="wizard-card-count">${i===0?'从认识自己开始':i===1?'只填写已知信息':'把故事讲完整'}</span></div>
          <div class="wizard-stage wizard-motion-${state.profileDirection}" id="wizardStage">${wizardStepContent()}</div>
          <div class="wizard-bottom"><span>${ic('shield',15)} 所有问题可选填 · 当前浏览器内处理</span><div class="wizard-inline-tools"><button data-action="fill-demo-profile" type="button">试填虚构示例</button><button data-action="clear-profile" type="button">清空资料</button></div></div>
        </section>
      </div>
      <div class="wizard-footer max"><button class="btn btn-white" data-action="wizard-back">${ic('chevron',17)} ${i===0?'返回首页':'上一步：'+wizardSteps[i-1].name}</button><span class="wizard-swipe-hint">${ic('arrow',16)} 点击下一步，也可左右滑动切换</span><button class="btn btn-primary" data-action="wizard-next">${i===2?'完成档案 · 开始分析':'下一步：'+wizardSteps[i+1].name} ${ic('arrow',17)}</button></div>
    </main>${footer()}`;
  }
  function demoProfile(){Object.assign(state.profile,{meNick:'我',meGender:'女',meAge:'21–23岁',meMBTI:'ENFP',meTraits:['主动','热爱分享','感性细腻'],meStatus:'有好感对象',meStyle:'主动直接',meNeed:'互相尊重',taNick:'小林',taGender:'男',taAge:'21–23岁',taMBTI:'INTP',taTraits:['慢热','理性冷静','幽默'],taStyle:'会认真回应、偶尔主动',taEmotional:'慢热、比较克制',taUnsure:'TA 会主动聊音乐和展览，但我还不确定这些是否只是朋友之间的热情。',relation:'同学 / 同校',stage:'暧昧了解中',frequency:'几乎每天',touch:'见过',events:'一起参加过艺术展，TA 主动推荐过音乐和歌单。我们最近聊过周末的展览。',eventItems:[{date:'2026-11-02',text:'一起聊起艺术展'},{date:'2026-11-04',text:'TA 提出下次可以一起去'}],boundaries:'目前没有明确拒绝',goal:'signals',concern:'TA 主动说下次一起去看展，但我不确定是不是友好邀约。'});state.profileSaved=true;state.ownName='我';state.otherName='小林';state.ownMBTI='ENFP';state.otherMBTI='INTP';}


  function profileContext(){
    if(!state.profileSaved)return '';
    const p=state.profile;
    const bits=[p.relation,p.stage,p.frequency].filter(Boolean).map(esc).join(' · ');
    const event=[...(p.eventItems||[]).map(e=>e.text).filter(Boolean),p.events].filter(Boolean).join('；').slice(0,170);
    const concern=(p.concern||'').slice(0,120);const extra=[p.meStyle&&'我的沟通风格：'+p.meStyle,p.taStyle&&'TA 的沟通表现：'+p.taStyle,p.boundaries==='TA 表达过不愿继续'?'提醒：用户报告有明确边界':null].filter(Boolean).map(esc).join(' · ');
    return `<div class="v5-context-in-results"><strong>♡ 已参考人物档案</strong><p>${bits||'未填写关系阶段'}${extra?`<br/>${extra}`:''}${event?`<br/>共同经历：${esc(event)}`:''}${concern?`<br/>当前关注：${esc(concern)}`:''}</p><small>这只是用户填写的背景，不能证明 TA 的真实想法。</small><button data-go="profile">编辑档案 →</button></div>`;
  }

  function modeStrip(){
    const real=state.mode==='real';
    return `<div class="mode-strip" role="region" aria-label="分析模式"><strong>${real?'真实 API':'演示模式'}</strong><button class="mode-choice ${!real?'is-active':''}" data-action="mode-demo" aria-pressed="${!real}">演示模式</button><button class="mode-choice ${real?'is-active':''}" data-action="mode-real" aria-pressed="${real}">真实 API</button><span class="mode-note">${real?(state.apiHealthLoading?'正在检查后端…':state.apiHealth?.status==='ok'?'后端健康检查通过；仅在身份核对及授权后提交。':state.apiHealthError||'请先在 api/config.js 配置后端 HTTPS Base URL。'):'使用虚构 Mock 或浏览器本地规则演示，不调用外部 AI。'}</span>
      ${!real?`<div class="mock-switch"><button data-action="mock-warm" class="${state.mockKey==='warm'?'active':''}">虚构示例 A · 积极交流</button><button data-action="mock-reserved" class="${state.mockKey==='reserved'?'active':''}">虚构示例 B · 尊重边界</button></div>`:''}</div>${state.apiError?`<div class="mode-error" role="alert">${ic('alert',16)} <span>${esc(state.apiError)}</span><button data-action="mode-demo">手动切换演示模式</button></div>`:''}`;
  }
  function workWrap(body) {return `${topbar()}<main class="v4-workspace v4-${state.view}"><div class="v4-work-inner max">${modeStrip()}${state.view!=='import'?profileContext():''}${body}</div></main>${footer()}`;}

  function heading(step,name,description,extra=''){
    const eyebrow={import:'CHAT IMPORT',portraits:'DUAL PORTRAITS',signals:'CHAT SIGNALS',advisor:'ASK YOUR WINGMAN'}[state.view]||'HEART SIGNAL LAB';
    const sticker=state.view==='advisor'?`<img class="v4-heading-face" src="images/ziqiao-photo.jpeg" alt="子乔形象"/>`:`<span class="v4-heading-signet">${ic(state.view==='import'?'upload':state.view==='portraits'?'users':'chart',24)}</span>`;
    return `<div class="page-heading v4-page-heading"><div><span class="v4-overline">${eyebrow} &nbsp; / &nbsp; ${esc(step)}</span><h1>${esc(name)}</h1><p>${esc(description)}</p></div><div class="v4-heading-right">${sticker}${state.demo?'<span class="pill orange">示例数据</span>':''}${extra}</div></div>`;
  }
  const mbtiOptions = ['','ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP','ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ'];
  const mbtiSelect = (label,id,value)=>`<div class="field"><label for="${id}">${label}</label><select id="${id}" data-field="${id}">${mbtiOptions.map(m=>`<option value="${m}" ${m===value?'selected':''}>${m||'不确定 / 不填写'}</option>`).join('')}</select></div>`;
  function importPage() {
    const chat=state.messages; return workWrap(`${heading('STEP 01 / 04','先把聊天交给我们','支持粘贴 Schema 1.0 JSON 或普通聊天文本，也可以导入 .json / .txt / .csv 文件。截图 OCR 在后续版本接入。',`<button class="btn btn-sm btn-white" data-action="sample">${ic('spark',14)} 加载示例</button>`)}
      ${state.profileSaved?`<div class="v5-context-strip">${ic('users',17)} 已加载人物档案：${esc(state.profile.meNick||'我')} &amp; ${esc(state.profile.taNick||'TA')} · ${esc(state.profile.stage||'关系阶段未设置')}<button data-go="profile">编辑背景 →</button></div>`:''}<div class="layout-2"><div class="stack">
      <div class="panel"><div class="panel-header"><h2>01 · 这段故事的主角</h2><span class="pill purple">${ic('users',13)} 基本信息</span></div>
        <div class="field-grid"><div class="field"><label for="ownName">我的聊天昵称</label><input id="ownName" data-field="ownName" value="${esc(state.ownName)}" maxlength="24" placeholder="例如：我"/></div><div class="field"><label for="otherName">TA 的聊天昵称</label><input id="otherName" data-field="otherName" value="${esc(state.otherName)}" maxlength="24" placeholder="例如：小林"/></div>${mbtiSelect('我的 MBTI（可选）','ownMBTI',state.ownMBTI)}${mbtiSelect('TA 自述的 MBTI（可选）','otherMBTI',state.otherMBTI)}</div>
        <div class="mbti-note">${ic('question',13)} MBTI 是可选的自述偏好，不能从聊天文本可靠推断，也不应作为好感或相容性的判断依据。</div>
      </div>
      <div class="panel"><div class="panel-header"><h2>02 · 粘贴聊天记录 / JSON</h2><span class="pill pink">${ic('lock',13)} 本地处理</span></div>
        <div class="import-tabs"><button class="tab ${state.tab==='text'?'active':''}" data-action="tab-text">${ic('file',13)} 文本 / JSON 导入</button><button class="tab ${state.tab==='image'?'active':''}" data-action="tab-image">${ic('upload',13)} 截图导入 · 规划中</button></div>
        ${state.tab==='text'?`<textarea id="chatInput" class="editor" placeholder="试试按这个格式粘贴：\n\n我: 今天的课好难啊\nTA: 哈哈哈我也差点没听懂\n我: 你后来怎么复习的？\nTA: 我整理了笔记，要不要发给你？" spellcheck="false">${esc(state.raw)}</textarea><div class="editor-footer"><div style="display:flex;gap:9px;align-items:center"><label class="file-label" for="fileInput">${ic('upload',15)} 导入文件（JSON / TXT / CSV）</label><input class="upload-file" type="file" id="fileInput" accept=".json,.txt,.csv,application/json,text/plain,text/csv"/><button class="btn btn-sm btn-soft" data-action="sample">试试示例</button></div><small id="charCount">${state.raw.length} 字符 · ${chat.length} 条消息</small></div><div id="parseStatus" class="parse-status ${state.parseResult.error?'error':state.parseResult.format==='json'?'success':''}" role="status" aria-live="polite">${parseStatusHTML()}</div>`:
         `<div class="no-data"><div class="empty-icon">${ic('upload',25)}</div><strong>截图 OCR 即将开放</strong><p>本轮交付聚焦可完整演示的文本分析闭环。<br/>你可以复制聊天文字，或先将截图转为文本再粘贴。</p><button class="btn btn-sm btn-primary" data-action="tab-text">切换到文本导入</button></div>`}
        <label class="check-row"><input id="consent" type="checkbox" ${state.consent?'checked':''}/><span>我已移除不必要的姓名、电话等敏感信息，并确认有权使用这段聊天内容进行分析。</span></label>
        ${state.mode==='real'?`<div class="import-confirm"><small>身份映射：JSON sender=self → ${esc(state.ownName||'我')}，sender=other → ${esc(state.otherName||'TA')}，unknown 不推断归属。文件中的 sender_name 只影响气泡显示。</small><label class="check-row"><input id="identityConfirmed" type="checkbox" ${state.identityConfirmed?'checked':''}/><span>我已核对本次聊天双方身份和映射无误。</span></label><label class="check-row"><input id="sendConsent" type="checkbox" ${state.sendConsent?'checked':''}/><span>我了解真实分析将向配置的后端发送聊天 JSON，并明确同意本次发送。</span></label></div>`:''}
        ${state.apiBusy?`<div class="mode-status-line">正在请求后端分析，请勿重复提交…</div>`:''}
        <div class="import-actions"><button class="btn btn-white" data-action="clear">清空内容</button><button class="btn btn-primary" data-action="analyze" ${state.apiBusy?'disabled':''}>${state.mode==='real'?'确认并提交分析':'生成演示报告'} ${ic('arrow',16)}</button></div>
      </div></div>
      <div class="stack"><div class="panel"><div class="panel-header"><h2>聊天内容预览</h2><span class="pill" id="previewCount">${chat.length} 条消息</span></div><div class="preview-messages" id="previewMessages">${previewHTML(chat)}</div></div>
      <div class="info-note"><span class="note-icon">${ic('shield',19)}</span><span><strong>隐私说明</strong><br/>演示模式只在浏览器内解析，不上传或持久化聊天。切换真实模式时，仅在你确认身份、同意发送并提交后才会触发 API；须由后端另行提供数据保留、删除与隐私政策。</span></div>
      <div class="panel" style="background:#fffdf6"><div class="panel-header"><h2>一个小小的提醒</h2><span>🌷</span></div><p class="helper" style="margin:0">没有哪句话能百分百证明喜欢或不喜欢。报告只整理聊天中的可观察行为，真实感受仍需要尊重对方、通过坦诚交流确认。</p></div></div></div>`);
  }
  // A single normalized message array powers the preview, counters and downstream analysis.
  // JSON sender is authoritative: it is NEVER inferred from display nicknames.
  function parseTextMessages(raw) {
    const msgs=[]; const lines=String(raw||'').split(/\r?\n/).map(line=>line.trim()).filter(Boolean);
    for(const line of lines) {
      // Existing plain text format: [date time] speaker: content, or speaker: content.
      const m=line.match(/^(?:(\d{4}[\-/]\d{1,2}[\-/]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?)\s*|\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*)?([^:：]{1,24})[:：]\s*(.+)$/);
      if(m){
        const speaker=m[3].trim(); if(!speaker || /^https?$/i.test(speaker))continue;
        const body=m[4].trim(), timestamp=m[1]||m[2]||'';
        msgs.push({id:`text-${msgs.length+1}`,timestamp,sender:null,type:'text',content:body,speaker,body,date:m[1]?m[1].slice(0,10).replace(/\//g,'-'):'',format:'text'});
      } else if(msgs.length) {
        msgs[msgs.length-1].content+='\n'+line;
        msgs[msgs.length-1].body=msgs[msgs.length-1].content;
      }
    }
    return msgs.slice(0,5000); // Keep V6's original plain-text limit.
  }
  function isPlainObject(value) {return value!==null&&typeof value==='object'&&!Array.isArray(value);}
  function isValidSchemaTimestamp(value) {
    if(typeof value!=='string')return false;
    const m=value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(Z|[+-]\d{2}:\d{2})?$/);
    if(!m)return false;
    const [,ys,mos,ds,hs,mis,ss='0',fraction='',zone]=m;
    const year=Number(ys),month=Number(mos),day=Number(ds),hour=Number(hs),minute=Number(mis),second=Number(ss);
    const date=new Date(0);date.setUTCHours(0,0,0,0);date.setUTCFullYear(year,month-1,day);
    if(date.getUTCFullYear()!==year||date.getUTCMonth()!==month-1||date.getUTCDate()!==day)return false;
    if(hour>23||minute>59||second>59)return false;
    if(zone&&zone!=='Z'){
      const offset=zone.slice(1).split(':').map(Number);
      if(offset[0]>23||offset[1]>59)return false;
    }
    return true;
  }
  function parseChatInput(raw, forceJson=false) {
    const source=String(raw??'');
    const trimmed=source.trim().replace(/^\uFEFF/,'').trim();
    if(!trimmed)return {format:'empty',messages:[],error:null,warnings:[]};
    const startsWithPlainTime=/^\[\d{1,2}:\d{2}(?::\d{2})?\]/.test(trimmed);
    const looksLikeJson=forceJson||trimmed.startsWith('{')||(trimmed.startsWith('[')&&!startsWithPlainTime)||/^"(?:schema_version|messages|source|chat_type)"\s*:/.test(trimmed);
    if(!looksLikeJson)return {format:'text',messages:parseTextMessages(source),error:null,warnings:[]};
    const failure=(reason)=>({format:'json',messages:[],error:reason,warnings:[]});
    let data;
    try{data=JSON.parse(trimmed);}catch(e){return failure(`JSON 语法错误：${e.message||'无法解析内容'}。请检查逗号、引号和括号。`);}
    if(!isPlainObject(data))return failure('JSON 顶层必须是对象，包含 schema_version、source、chat_type 和 messages。');
    if(data.schema_version!=='1.0')return failure('schema_version 必须是字符串 "1.0"。');
    if(data.source!=='wechat-cli')return failure('source 必须为 "wechat-cli"。');
    if(data.chat_type!=='private')return failure('chat_type 必须为 "private"；当前仅支持私聊。');
    if(!Array.isArray(data.messages))return failure('messages 必须是数组。');
    if(data.metadata!==undefined&&!isPlainObject(data.metadata))return failure('metadata 如果提供，必须是对象。');
    const messages=[],seen=new Set();
    for(let i=0;i<data.messages.length;i++){
      const m=data.messages[i],n=i+1;
      if(!isPlainObject(m))return failure(`messages[${i}]（第 ${n} 条）必须是对象。`);
      if(typeof m.id!=='string'||!m.id.trim())return failure(`第 ${n} 条消息缺少有效的字符串 id。`);
      if(seen.has(m.id))return failure(`第 ${n} 条消息 id 重复：${m.id}。`);
      seen.add(m.id);
      if(!['self','other','unknown'].includes(m.sender))return failure(`第 ${n} 条 sender 必须是 self、other 或 unknown。`);
      if(!isValidSchemaTimestamp(m.timestamp))return failure(`第 ${n} 条 timestamp 必须是有效的 ISO 8601 日期时间，例如 2026-11-07T10:30、2026-11-07T10:30+08:00 或 2026-11-07T10:30:00Z。`);
      const datePart=m.timestamp.slice(0,10),[year,month,day]=datePart.split('-').map(Number);
      if(new Date(Date.UTC(year,month-1,day)).toISOString().slice(0,10)!==datePart)return failure(`第 ${n} 条 timestamp 的日期无效。`);
      if(typeof m.type!=='string'||!m.type.trim())return failure(`第 ${n} 条 type 必须是非空字符串。`);
      if(typeof m.content!=='string')return failure(`第 ${n} 条 content 必须是字符串（允许空字符串）。`);
      // Preserve source order, ID, ISO timestamp including offset, Unicode, emoji and newlines.
      if(m.sender_name!==undefined && (typeof m.sender_name!=='string'||m.sender_name.length>100))return failure(`第 ${n} 条 sender_name 必须是长度不超过 100 的字符串。`);
      messages.push({id:m.id,timestamp:m.timestamp,sender:m.sender,sender_name:m.sender_name||'',type:m.type,content:m.content,speaker:m.sender,body:m.content,date:datePart,format:'json'});
    }
    const warnings=[];
    const naiveCount=messages.filter(m=>!/(?:Z|[+-]\d{2}:\d{2})$/.test(m.timestamp)).length;
    if(naiveCount)warnings.push(`${naiveCount} 条消息没有时区偏移；原始时间已保留，后端按 ASSUME_NAIVE_TZ_OFFSET_HOURS（默认 +8）解释。`);
    if(data.metadata){
      if(Number.isInteger(data.metadata.total_messages)&&data.metadata.total_messages!==messages.length)warnings.push(`metadata.total_messages 为 ${data.metadata.total_messages}，实际解析 ${messages.length} 条；统计以 messages 数组为准。`);
      const unknown=messages.filter(m=>m.sender==='unknown').length;
      if(Number.isInteger(data.metadata.unknown_senders)&&data.metadata.unknown_senders!==unknown)warnings.push(`metadata.unknown_senders 为 ${data.metadata.unknown_senders}，实际为 ${unknown}；以消息字段为准。`);
    }
    return {format:'json',messages,error:null,warnings,document:data,metadata:data.metadata||null};
  }
  function refreshParsedChat(forceJson=false) {
    state.parseResult=parseChatInput(state.raw,forceJson);
    state.messages=state.parseResult.messages;
    return state.parseResult;
  }
  function getRoles(msgs) {
    if(msgs.some(m=>m.format==='json'))return {own:'self',other:'other',labelOwn:state.ownName.trim()||'我',labelOther:state.otherName.trim()||'TA'};
    const speakers=[...new Set(msgs.map(m=>m.speaker))];
    const own=speakers.includes(state.ownName.trim())?state.ownName.trim():speakers[0];
    const other=speakers.includes(state.otherName.trim())&&state.otherName.trim()!==own?state.otherName.trim():(speakers.find(x=>x!==own)||'');
    return {own,other,labelOwn:own||'我',labelOther:other||'TA'};
  }
  function displayTimestamp(timestamp) {
    if(!timestamp)return '';
    // Display source-local time and original offset, without browser timezone conversion.
    return String(timestamp).replace('T',' ').replace(/([+-]\d\d:\d\d|Z)$/,' $1');
  }
  function parseStatusHTML(){
    const r=state.parseResult;
    if(r.error)return `${ic('alert',15)} <strong>导入失败：</strong>${esc(r.error)}`;
    if(r.format==='json'){
      const own=r.messages.filter(m=>m.sender==='self').length,other=r.messages.filter(m=>m.sender==='other').length,unknown=r.messages.length-own-other;
      return `${ic('check',15)} <strong>JSON Schema 1.0 解析成功：</strong>共 ${r.messages.length} 条（我 ${own} · TA ${other} · 未知 ${unknown}）${r.metadata?`<div class="parse-warning">导出来源：${esc(r.metadata.id_origin||'未标注')} · 导出计数：${Number.isInteger(r.metadata.total_messages)?r.metadata.total_messages:'未提供'} · 消息按原始顺序保留</div>`:''}${r.warnings.map(w=>`<div class="parse-warning">${esc(w)}</div>`).join('')}`;
    }
    if(r.format==='text')return `已识别 ${r.messages.length} 条纯文本消息（按“昵称: 内容”格式解析）。`;
    return '支持粘贴 chat.json Schema 1.0 或原有聊天文本；JSON 解析失败时不会退回文本模式。';
  }
  function previewHTML(msgs) {
    if(state.parseResult.error)return `<div class="no-data parse-preview-error"><div class="empty-icon">${ic('alert',25)}</div><strong>JSON 格式校验失败</strong><p>${esc(state.parseResult.error)}</p></div>`;
    if(!msgs.length)return `<div class="no-data"><div class="empty-icon">${ic('chat',25)}</div><strong>还没有聊天内容</strong><p>导入后，这里会出现双方对话预览。<br/>或者先用示例体验一下吧 ♡</p></div>`;
    const roles=getRoles(msgs);
    return msgs.slice(-5).map(m=>{
      const who=m.format==='json'?(m.sender==='unknown'?'未知发送者':(m.sender_name|| (m.sender==='self'?roles.labelOwn:roles.labelOther))):m.speaker;
      const role=m.format==='json'?(m.sender==='self'?'self':m.sender==='other'?'other':'unknown'):(m.speaker===roles.own?'self':'other');
      const meta=[displayTimestamp(m.timestamp),m.format==='json'?`ID: ${m.id}`:'',m.type!=='text'?`类型: ${m.type}`:''].filter(Boolean).join(' · ');
      return `<div class="preview-chat ${role}"><span class="who">${esc(who)}</span><span class="say">${esc(m.content)}</span>${meta?`<span class="preview-meta">${esc(meta)}</span>`:''}</div>`;
    }).join('');
  }
  function updatePreview() {
    const chat=state.messages;
    if($('previewCount'))$('previewCount').textContent=`${chat.length} 条消息`;
    if($('previewMessages'))$('previewMessages').innerHTML=previewHTML(chat);
    if($('charCount'))$('charCount').textContent=`${state.raw.length} 字符 · ${chat.length} 条消息`;
    if($('parseStatus')){
      $('parseStatus').innerHTML=parseStatusHTML();
      $('parseStatus').className=`parse-status ${state.parseResult.error?'error':state.parseResult.format==='json'?'success':''}`;
    }
  }
  function analyze(msgs) {
    const {own,other}=getRoles(msgs);
    const filtered=msgs.filter(m=>m.speaker===own||m.speaker===other);
    const unknown=msgs.filter(m=>m.format==='json'&&m.sender==='unknown');
    const self=filtered.filter(m=>m.speaker===own),ta=filtered.filter(m=>m.speaker===other);
    const asked=m=>m.type==='text'&&(/[？?]/.test(m.body)||/(吗|么|呢|什么|怎么|为什么|要不要|有没有|哪|谁|多少)/.test(m.body));
    const invite=m=>m.type==='text'&&/(一起|下次|周末|有空|约|见面|去看|要不要去|想见)/.test(m.body);
    const warm=m=>m.type==='text'&&/(哈哈哈|好呀|好哇|期待|喜欢|好耶|不错|谢谢|开心|可以呀|当然|🌷|❤️|💕|❤)/.test(m.body);
    const boundary=m=>m.type==='text'&&/(别(再)?联系|不要(再)?联系|请不要(再)?联系|不想(见|聊|和你)|不用再|别打扰|不要打扰|没兴趣|不方便.*(别|不要)|明确拒绝|请停止)/.test(m.body);
    const short=m=>m.type==='text'&&m.body.replace(/\s/g,'').length<5;
    const qMe=self.filter(asked).length,qTa=ta.filter(asked).length;
    const invitation=ta.filter(invite),warmMsgs=ta.filter(warm),shortMsgs=ta.filter(short),boundaryMsgs=ta.filter(boundary);
    const share=Math.round(100*ta.length/(filtered.length||1));
    // Visual proxy only; not a scientifically validated inference of romantic interest.
    const score=clamp(Math.round(36+share*.36+Math.min(qTa,6)*4.5+Math.min(invitation.length,3)*7+Math.min(warmMsgs.length,5)*2.4-Math.min(shortMsgs.length,4)*2.3-(boundaryMsgs.length?38:0)),8,91);
    const keyText=filtered.filter(m=>m.type==='text').map(m=>m.body).join(' ');
    const topics=[['展','展览'],['电影','电影'],['音乐','音乐'],['歌','音乐'],['咖啡','咖啡'],['游戏','游戏'],['课程','课程'],['考试','考试'],['书','读书'],['猫','小猫'],['旅行','旅行']];
    const topic=topics.find(([term])=>keyText.includes(term))?.[1]||'';
    const chunks=[];
    if(filtered.some(x=>x.date)){
      const byDate=new Map();filtered.forEach(x=>{const day=x.date||'未注明';byDate.set(day,(byDate.get(day)||0)+1)});
      [...byDate].slice(-6).forEach(([label,count])=>chunks.push({label:label==='未注明'?'其他':label.slice(5).replace('-','/'),count}));
    }else{for(let i=0;i<Math.min(6,Math.ceil(filtered.length/4));i++){const len=filtered.slice(i*4,(i+1)*4).length;chunks.push({label:`片段${i+1}`,count:len});}}
    return {msgs:filtered,self,ta,own:getRoles(msgs).labelOwn,other:getRoles(msgs).labelOther,unknown,knownTotal:filtered.length,share,score,qMe,qTa,invitation,warmMsgs,shortMsgs,boundaryMsgs,topic,chunks,total:msgs.length,avgMe:Math.round(self.reduce((a,m)=>a+m.body.length,0)/(self.length||1)),avgTa:Math.round(ta.reduce((a,m)=>a+m.body.length,0)/(ta.length||1))};
  }
  function needAnalysis(sampleAction='sample') {return `<div class="empty-state"><div class="huge">💌</div><h2>先给心动一点线索吧</h2><p>这里还没有分析结果。先导入一段双方聊天，再来认识彼此的交流方式。</p><button class="btn btn-primary" data-go="import">去导入聊天 ${ic('arrow',17)}</button><p style="margin:18px auto 0"><button class="privacy-link" data-action="${sampleAction}">或者先体验示例报告</button></p></div>`;}
  function resultStepButtons(prev,next,nextLabel){return `<div class="step-controls"><button class="btn btn-white" data-go="${prev}">${ic('chevron',15)} 返回上一步</button><span class="muted">观察沟通，不替任何人下感情结论</span><button class="btn btn-primary" data-go="${next}">${nextLabel} ${ic('arrow',16)}</button></div>`;}
  const pct=(n)=>`${clamp(Math.round(n),0,100)}%`;
  function portraitsPage() {
    if(!state.analysis)return workWrap(needAnalysis());
    if(state.mode==='real'&&state.report)return realPortraitsPage();
    const a=state.analysis;
    const isMe=(name)=>name===a.own;
    const portrait=(name,which,count,qs,avg,mbti)=>`<article class="portrait-card"><div class="portrait-top ${which}"><div class="portrait-avatar" aria-hidden="true">${which==='me'?'🧑🏻‍💻':'🧑🏻‍🎨'}</div><span class="pill" style="position:absolute;bottom:12px;right:17px;background:#ffffffce">${which==='me'?'我的视角':'TA 的视角'}</span></div><div class="portrait-info"><div class="portrait-name"><h2>${esc(name)}</h2><span class="pill ${which==='me'?'purple':'pink'}">${mbti?esc(mbti):'MBTI 未填写'}</span></div><p class="portrait-sub">从当前导入的聊天片段整理</p><div class="metric-row"><span>发送消息</span><b>${count} 条</b></div><div class="metric-row"><span>提问 / 征询</span><b>${qs} 次</b></div><div class="metric-row"><span>平均消息长度</span><b>${avg} 字</b></div><div class="tag-row"><span class="pill ${which==='me'?'purple':'pink'}">${qs>=2?'会主动提问':'表达相对简短'}</span><span class="pill">${avg>=15?'偏详细表达':'轻量交流风格'}</span></div></div></article>`;
    return workWrap(`${heading('STEP 02 / 04','双向沟通画像','不猜性格、不贴标签，只看看你们在这段聊天里如何表达。')}
      <div class="result-banner" style="margin-bottom:19px"><div><div class="main">两个人，两个视角，一段正在发生的故事。</div><p>已解析 ${a.total} 条消息（双方 ${a.knownTotal} 条${a.unknown.length?`，未知发送者 ${a.unknown.length} 条`:''}）· 不用未知消息推断任何一方。</p></div><span class="heart-sticker">♡</span></div>
      <div class="portrait-grid">${portrait(a.own,'me',a.self.length,a.qMe,a.avgMe,state.ownMBTI)}${portrait(a.other,'them',a.ta.length,a.qTa,a.avgTa,state.otherMBTI)}</div>
      <div class="insight-strip" style="margin-top:19px"><span style="font-size:22px">💡</span><div><strong>子乔观察：</strong> 在这段样本中，你贡献了 ${a.self.length} 条消息，TA 贡献了 ${a.ta.length} 条。TA 发起了 ${a.qTa} 次提问或征询。<br/>这些可以用于理解交流节奏，但不能单独证明喜欢、冷淡或任何人格类型。</div></div>
      ${resultStepButtons('import','signals','查看互动信号')}`);
  }
  function realPortraitsPage() {
    const report=state.report||{},group=report.portraits||{};
    const stats=report.metrics?.message_counts||{};
    const selfCount=Number(stats.self??stats.self_count??0),otherCount=Number(stats.other??stats.other_count??0),unknownCount=Number(stats.unknown??stats.unknown_count??0);
    const renderCard=(title,which,items)=>`<article class="portrait-card"><div class="portrait-top ${which}"><div class="portrait-avatar" aria-hidden="true">${which==='me'?'🧑🏻‍💻':'🧑🏻‍🎨'}</div><span class="pill" style="position:absolute;bottom:12px;right:17px;background:#ffffffce">${which==='me'?'我的视角':'TA 的视角'}</span></div><div class="portrait-info"><div class="portrait-name"><h2>${esc(title)}</h2><span class="pill ${which==='me'?'purple':'pink'}">Agent 交流画像</span></div><p class="portrait-sub">基于本次聊天证据整理，不代表稳定人格。</p>${items.length?items.map(x=>`<div class="metric-row"><span>${esc(x.label||x.key||'交流维度')}</span><b>${esc(x.level||'数据不足')}</b></div><p class="helper" style="margin:4px 0 12px">${esc(x.detail||'暂无足够证据')}</p>`).join(''):'<p class="helper">当前样本不足，暂时没有可展示的画像维度。</p>'}</div></article>`;
    const selfItems=Array.isArray(group.self_portrait)?group.self_portrait:[];
    const otherItems=Array.isArray(group.other_portrait)?group.other_portrait:[];
    const assessment=report.relationship_assessment;
    return workWrap(`${heading('STEP 02 / 04','双向沟通画像','由 Agent 根据聊天证据整理；数据不足的维度会明确标注。')}
      <div class="result-banner" style="margin-bottom:19px"><div><div class="main">这份画像只描述本次样本中的沟通表现。</div><p>共 ${Number(stats.total??(selfCount+otherCount+unknownCount))} 条消息（本人 ${selfCount} · TA ${otherCount} · 未知 ${unknownCount}）。</p></div><span class="heart-sticker">♡</span></div>
      <div class="portrait-grid">${renderCard(state.ownName||'我','me',selfItems)}${renderCard(state.otherName||'TA','them',otherItems)}</div>
      ${assessment?`<div class="insight-strip" style="margin-top:19px"><span style="font-size:22px">💡</span><div><strong>关系观察：${esc(assessment.stage||'信息不足')}</strong><br/>${esc(assessment.summary||'暂无综合判断。')}<p class="helper">判断置信度：${esc(assessment.confidence||'low')}。仍需结合现实交流。</p></div></div>`:''}
      ${Array.isArray(report.limitations)&&report.limitations.length?`<div class="disclaimer">样本限制：${report.limitations.map(esc).join('；')}</div>`:''}
      ${resultStepButtons('import','signals','查看互动信号')}`);
  }
  function signalData() {
    const a=state.analysis;
    const sig=[];
    if(a.qTa>0){const item=a.ta.find(m=>m.type==='text'&&/[？?]|(吗|么|呢|什么|怎么|要不要|有没有|哪)/.test(m.body));sig.push({type:'good',title:`TA 有 ${a.qTa} 次提问 / 征询`,desc:'主动提问可能表示想继续交流，也可能只是正常聊天习惯。',quote:item?.body});}
    if(a.invitation.length){sig.push({type:'good',title:`出现 ${a.invitation.length} 条共同活动相关表达`,desc:'提到“下次”“一起”是值得留意的互动线索，是否构成邀约还要结合语境。',quote:a.invitation[0].body});}
    if(a.warmMsgs.length){sig.push({type:'good',title:`发现 ${a.warmMsgs.length} 条轻松积极的表达`,desc:'积极语气、分享或笑声能反映当下交流氛围，不等于稳定的情感意图。',quote:a.warmMsgs[0].body});}
    if(a.shortMsgs.length){sig.push({type:'warn',title:`有 ${a.shortMsgs.length} 条较短回复`,desc:'回复简短可能来自时间紧、聊天风格等原因，请不要直接等同于敷衍。',quote:a.shortMsgs[0].body});}
    if(a.boundaryMsgs.length){sig.unshift({type:'red',title:'出现明确的边界或拒绝表达',desc:'应优先尊重对方表达的意愿。建议停止推进邀约，不反复追问。',quote:a.boundaryMsgs[0].body});}
    if(!sig.length)sig.push({type:'warn',title:'当前没有足够清晰的互动线索',desc:'样本可能较短。建议优先关注现实交流中的舒适度和双方意愿。',quote:null});
    return sig.slice(0,5);
  }
  function currentDashboard() {
    if(state.dashboard)return state.dashboard;
    if(!state.analysis)return null;
    return HeartSignalDashboard.localFromAnalysis(state.analysis,signalData());
  }
  function signalsPage() {
    if(!state.analysis)return workWrap(needAnalysis());
    const d=currentDashboard();
    const isReal=state.mode==='real';
    const sig=isReal?(d.signals||[]):(d.signals.length?d.signals:signalData());
    const chart=d.chart.length?d.chart:[];
    const max=Math.max(1,...chart.map(c=>c.count));
    const pctText=(n)=>n==null?'数据不足':`${Math.round(n)}%`;
    const scoreText=d.score==null?'—':Math.round(d.score);
    const boundaryAlert=isReal?sig.some(x=>x.type==='red'):(state.analysis.boundaryMsgs?.length||sig.some(x=>x.type==='red'));
    const semanticNote=d.semanticDetection?.note||'';
    const relation=d.relationshipAssessment;
    return workWrap(`${heading('STEP 03 / 04','关系信号气象站','整理你们的互动结构，积极信号与不确定因素都放在桌面上。')}
      ${boundaryAlert?`<div class="info-note red" style="margin-bottom:17px"><span class="note-icon">${ic('alert',18)}</span><span><strong>边界提醒 / 需要留意的互动信号：</strong>请结合原文与替代解释理解，不要将单条信号直接等同于关系结论。</span></div>`:''}
      ${isReal&&d.status==='partial'?`<div class="info-note" style="margin-bottom:17px"><span class="note-icon">${ic('alert',18)}</span><span><strong>部分分析：</strong>${(d.limitations||[]).map(esc).join('；')||'部分字段暂不可用。'}</span></div>`:''}
      <div class="signal-detail-grid"><div class="stack"><div class="panel"><div class="panel-header"><h2>互动信号参考指数</h2><span class="pill pink">${isReal?'真实 Agent 数据':'演示/本地数据'}</span></div><div class="circle-block"><div class="score-ring" style="--score:${d.score==null?0:d.score}"><div class="score-center"><b>${scoreText}</b><small>/100</small><span>互动信号指数</span></div></div><div class="ring-label">${isReal?'后端提供的互动参考指标':'虚构演示指标 / 浏览器本地启发式计算'}<br/><strong>不是好感概率 / 心理测量结果</strong></div></div><div class="tiny-metrics"><div class="tiny-metric"><b>${d.summary.total}</b><span>总消息数</span></div><div class="tiny-metric"><b>${pctText(d.summary.otherShare)}</b><span>TA 消息占比</span></div><div class="tiny-metric"><b>${pctText(d.summary.otherQuestionRatio==null?null:d.summary.otherQuestionRatio*100)}</b><span>TA 提问占比</span></div></div></div>
        <div class="panel"><div class="panel-header"><h2>聊天量分布</h2><span class="illustration-caption">按日期</span></div>${chart.length?`<div class="heart-chart">${chart.map(c=>`<div class="column" title="${esc(c.label)} · ${c.count} 条"><span style="height:${Math.max(13,Math.round(c.count/max*100))}%"></span></div>`).join('')}</div><div class="chart-labels">${chart.map(c=>`<span>${esc(c.label)}</span>`).join('')}</div>`:'<div class="no-data">暂无可用的时间分布数据。</div>'}<div class="disclaimer" style="margin-top:12px">这张图只显示消息数量，不代表关系升温或降温。</div></div></div>
        <div class="stack"><div class="panel"><div class="panel-header"><h2>可观察的互动维度</h2><span class="pill">${isReal?'Agent 计算':'Mock / 本地规则'}</span></div>${barsHTML(d.metrics)}<div class="disclaimer">${esc(d.disclaimer||'比例以实际可分析文本为分母；不代表“喜欢程度”。')}</div>${semanticNote?`<div class="disclaimer">语义识别：${esc(semanticNote)}</div>`:''}</div>
        <div class="panel"><div class="panel-header"><h2>重要信号与原文依据</h2><span class="pill purple">${sig.length} 个观察点</span></div>${sig.length?`<div class="signal-list">${sig.map(s=>`<div class="signal-item"><div class="signal-icon ${s.type==='warn'?'warn':s.type==='red'?'red':''}">${ic(s.type==='good'?'check':'alert',17)}</div><div><strong>${esc(s.title)}</strong><p>${esc(s.desc)}</p>${s.quote?`<div class="quote-box">“${esc(s.quote.slice(0,150))}”</div>`:''}${s.evidenceIds?.length?`<small class="muted">证据消息：${s.evidenceIds.map(esc).join('、')} · 证据强度：${esc(s.evidenceStrength||'未标注')}</small>`:''}</div></div>`).join('')}</div>`:'<div class="no-data">当前没有返回可展示的互动信号，请结合样本限制理解。</div>'}</div>
        ${relation?`<div class="panel"><div class="panel-header"><h2>综合关系观察</h2><span class="pill">${esc(relation.stage||'信息不足')}</span></div><p>${esc(relation.summary||'')}</p>${(relation.supporting_facts||[]).length?`<p><strong>支持事实：</strong>${relation.supporting_facts.map(esc).join('；')}</p>`:''}${(relation.contradicting_facts||[]).length?`<p><strong>需要谨慎：</strong>${relation.contradicting_facts.map(esc).join('；')}</p>`:''}${(relation.neutral_alternatives||[]).length?`<p><strong>其他解释：</strong>${relation.neutral_alternatives.map(esc).join('；')}</p>`:''}</div>`:''}</div></div>
      ${resultStepButtons('portraits','advisor','找子乔聊下一步')}`);
  }
  function barsHTML(metrics) {
    return (metrics||[]).map(b=>`<div class="bar-item"><div class="bar-head"><span>${esc(b.name)}</span><b>${b.val==null?'数据不足':`${Math.round(b.val)}%`}</b></div><div class="bar-track"><div class="bar-fill ${b.color}" style="width:${b.val==null?0:pct(b.val)}"></div></div></div>`).join('');
  }
  function strategyOptions() {
    const a=state.analysis; const stop=a.boundaryMsgs.length>0;
    if(stop)return [
      {tag:'尊重边界',tone:'最推荐',text:'收到，我理解你的想法，也会尊重你的决定。之后不再打扰你了。',desc:'简短、明确，不要求对方解释'},
      {tag:'平静收尾',tone:'不施压',text:'明白了，谢谢你直接告诉我。祝你一切顺利。',desc:'给双方一个体面的结束'},
      {tag:'不发送任何消息',tone:'也可以',text:'此时选择不回复，并停止联系，也是对边界的尊重。',desc:'不必每次都安排“最后一句话”'}
    ];
    const t=a.topic;
    if(t==='展览')return [
      {tag:'自然型',tone:'轻松开启',text:'好呀！你之前说想去的那个展，我看周六下午还有票～要不要一起去看看？',desc:'承接已有话题，邀请清晰'},
      {tag:'俏皮型',tone:'一点幽默',text:'报告！周末发现一个展览副本 🎨 你要不要组队？不方便也完全没关系哈哈',desc:'有趣但保留选择空间'},
      {tag:'温柔型',tone:'低压力',text:'想到你之前提过那个展，如果你这周末有空、也想去的话，我们可以一起；没时间就下次～',desc:'不把邀约变成压力'}
    ];
    const thing=t?`上次聊到的${t}`:'上次聊到的话题';
    return [
      {tag:'自然型',tone:'顺着话题',text:`突然想到${thing}，你后来有新发现吗？感觉还挺有意思的～`,desc:'从真实的共同话题重新开启'},
      {tag:'俏皮型',tone:'轻松一点',text:`今日份话题回访 📮 ${thing}还有后续嘛？`,desc:'轻巧，不需要对方长篇回应'},
      {tag:'温柔型',tone:'尊重节奏',text:'之前聊天挺开心的～最近还好吗？如果你忙也不用急着回。',desc:'让对方能自由选择回复时间'}
    ];
  }
  function strategyPage() {
    if(!state.analysis)return workWrap(needAnalysis());const a=state.analysis,stop=a.boundaryMsgs.length>0,opts=strategyOptions();
    return workWrap(`${heading('STEP 04 / 04',stop?'先尊重边界，再谈下一步':'下一步，怎么自然地靠近？','三种沟通方式供你参考。选择适合自己的表达，不照搬也完全可以。')}
      <div class="result-banner" style="margin-bottom:19px;background:${stop?'linear-gradient(115deg,#fff0f0,#fff7f2)':'linear-gradient(115deg,#f8eefe,#fff3ef)'}"><div><div class="main">${stop?'子乔提醒：尊重对方的明确意愿。':'子乔的第一条建议：真诚，比套路更重要。'}</div><p>${stop?'不要试图通过话术扭转明确拒绝；停止联系、给彼此空间。':'结合你们刚聊过的话题，给下一步交流留一点轻松的余地。'}</p></div><span class="heart-sticker">${stop?'☁':'✦'}</span></div>
      <div class="layout-2"><div class="panel"><div class="panel-header"><h2>今晚回复灵感</h2><span class="pill purple">${opts.length} 种表达</span></div>${opts.map((o,i)=>`<div class="response-card"><div class="response-head"><span class="pill ${i===0?'pink':i===1?'purple':'green'}">${esc(o.tag)}</span><span style="font-size:11px;color:#a18f9d">${esc(o.tone)}</span></div><p>“${esc(o.text)}”</p><div class="response-foot"><small>${esc(o.desc)}</small><button class="btn btn-sm btn-white" data-action="copy" data-copy-index="${i}">${ic('copy',13)} 复制</button></div></div>`).join('')}<p class="disclaimer">示例文本不保证效果，也不应被用来迫使或诱导对方回应。</p></div>
      <div class="stack"><div class="panel"><div class="panel-header"><h2>你的交流时间线</h2><span class="pill orange">可执行 · 不催促</span></div><div class="timeline" style="grid-template-columns:1fr">${(stop?[
        ['01','现在','停止邀约和反复追问；如果已经说清楚，可以不再回复。'],['02','本周','把注意力放回自己的生活，不通过共同朋友打探或施压。'],['03','之后','只有对方明确主动表示愿意沟通时，再重新评估是否回复。']
      ]:[['01','今天','选一个真实、简短的问题，接住你们已经聊过的内容。'],['02','本周','观察双方是否都愿意继续互动，不为了“保持热度”频繁打扰。'],['03','有合适机会时','直接、轻松地提出具体活动，也给对方拒绝的自由。']]).map(t=>`<div class="timeline-step"><div class="num">${t[0]} · ${t[1]}</div><p style="margin-top:9px">${t[2]}</p></div>`).join('')}</div></div><div class="info-note"><span class="note-icon">${ic('book',19)}</span><span>MBTI 可作为讨论沟通偏好的趣味话题，但请优先以 TA 明确说过的话、实际选择与相处感受为依据。</span></div></div></div>
      ${resultStepButtons('signals','advisor','和子乔继续聊')}`);
  }
  function currentAdvisorOptions() {
    if(state.mode==='demo')return strategyOptions();
    return (state.advisorSuggestions||[]).slice(0,3).map((text,i)=>({
      tag:['军师建议','沟通建议','边界提醒'][i]||'军师建议',
      tone:'来自 Agent',text:String(text),desc:'根据当前分析与对话生成'
    }));
  }
  function advisorSettingsHTML() {
    const thinkingSupported=apiFeatureSupportsThinking();
    const searchSupported=apiFeatureSupportsSearch();
    const healthNote=state.apiHealth?.status==='ok'
      ? `当前模型：${esc(state.apiHealth.model?.model||state.apiHealth.model?.provider||'后端已连接')}。${thinkingSupported?esc(state.apiHealth.features?.thinking_note||'思考强度参数可用。'):'当前部署未确认支持思考强度，选择将回退为服务端默认。'} ${searchSupported?'联网搜索工具可用。':'当前部署未提供联网搜索工具。'}`
      : esc(state.apiHealthError||'尚未完成后端健康检查；可先配置 Base URL 并切换真实模式检查。');
    return `<div class="panel advisor-api-settings"><div class="panel-header"><h2>AI 回复设置</h2><div style="display:flex;gap:8px;align-items:center"><span class="pill">后端能力</span><button class="btn btn-sm btn-white" data-action="check-health">重新检查</button></div></div><div class="field-grid"><div class="field"><label for="thinkingLevel">思考强度</label><select id="thinkingLevel"><option value="auto" ${state.thinkingLevel==='auto'?'selected':''}>自动（服务端默认）</option><option value="low" ${state.thinkingLevel==='low'?'selected':''} ${!thinkingSupported?'disabled':''}>低</option><option value="medium" ${state.thinkingLevel==='medium'?'selected':''} ${!thinkingSupported?'disabled':''}>中</option><option value="high" ${state.thinkingLevel==='high'?'selected':''} ${!thinkingSupported?'disabled':''}>高</option></select></div><div class="field"><label class="check-row" for="webSearch"><input type="checkbox" id="webSearch" ${state.webSearch?'checked':''} ${!searchSupported?'disabled':''}/><span>本轮允许联网搜索</span></label><small class="helper">默认关闭；后端只使用当前提问构造搜索词。</small></div></div><p class="disclaimer">${healthNote}</p></div>`;
  }
  function initAdvisor(){
    if(!state.advisorMessages.length){
      const text=state.mode==='real'
        ?'欢迎来到子乔军师室。你可以直接提出当前问题，我会基于这次已完成的聊天分析回答。'
        :state.analysis?.boundaryMsgs?.length
          ?'欢迎来到子乔军师室 🌷 我看到聊天里有需要尊重的明确边界。我们可以先聊聊如何平静、体面地处理这段关系。'
          :'嗨！我是子乔 🌷\n看完你们的互动啦！这里是一个没有套路的军师室。你可以问我「这句话怎么回复？」「要不要邀约？」我会给你尊重双方意愿的建议。\n\n（演示模式：当前为本地预设回复，并非真实大模型。）';
      state.advisorMessages=[{from:'bot',text,status:'sent'}];
    }
  }
  function advisorPage(){
    if(!state.analysis)return workWrap(`${heading('STEP 04 / 04','子乔军师','载入报告后，可继续围绕该报告交流。')}${needAnalysis('sample-advisor')}`);
    initAdvisor();
    const opts=currentAdvisorOptions();
    const aside=opts.length?opts.map((o,i)=>`<div class="response-card"><div class="response-head"><span class="pill ${i===0?'pink':i===1?'purple':'green'}">${esc(o.tag)}</span><span class="muted">${esc(o.tone)}</span></div><p>“${esc(o.text)}”</p><div class="response-foot"><small>${esc(o.desc)}</small><button class="btn btn-sm btn-white" data-action="copy" data-copy-index="${i}">${ic('copy',13)} 复制</button></div></div>`).join(''):`<div class="no-data">${state.mode==='real'?'完成一轮军师交流后，针对当前问题的建议会显示在这里。':'暂无建议。'}</div>`;
    const chatItems=state.advisorMessages.map(m=>{
      const evidence=Array.isArray(m.evidence)?m.evidence:[];
      const evidenceHtml=evidence.length?`<div class="advisor-evidence">${evidence.slice(0,3).map(item=>`<div class="quote-box"><strong>聊天依据 · ${esc(item.id||'')}</strong><p>“${esc(item.content||'')}”</p><small>${esc(item.sender_label||item.sender_name||item.sender||'')} ${esc(item.timestamp||'')}</small></div>`).join('')}</div>`:'';
      const boundaryHtml=Array.isArray(m.boundaryNotes)&&m.boundaryNotes.length?`<div class="info-note red"><strong>边界提醒：</strong>${m.boundaryNotes.map(esc).join('；')}</div>`:'';
      return `<div class="chat-msg ${m.from==='me'?'me':'bot'} ${m.status==='failed'?'failed':m.status==='pending'?'pending':''}"><span class="speaker">${m.from==='me'?'🧑🏻‍💻':'👔'}</span><div class="message">${esc(m.text)}${evidenceHtml}${boundaryHtml}${m.status==='failed'?`<button class="retry-chat" data-action="retry-message" data-message-id="${esc(m.id||'')}">发送失败 · 重新发送</button>`:''}</div></div>`;
    }).join('');
    return workWrap(`${heading('STEP 04 / 04','子乔军师，在线接招','聊聊如何回复、表达心意或自然邀约。子乔的建议以真诚和尊重为前提。',`<button class="btn btn-sm btn-white" data-action="reset-chat">${ic('rotate',14)} 重置对话</button>`)}
      <div class="v4-advisor-grid"><div class="chat-panel v4-chat-panel"><div class="chat-topbar"><div class="avatar-small avatar-photo"><img src="images/ziqiao-photo.jpeg" alt=""/></div><div><h3>子乔 · AI 恋爱军师</h3><p><span class="online"></span> ${state.mode==='demo'?'演示模式 · 预设回复':state.apiHealth?.status==='ok'?'真实 Agent · 已连接':'真实 Agent · 待连接'}${state.sessionId?' · 会话已关联':''}</p></div><span class="pill purple" style="margin-left:auto">轻松聊 · 不玩套路</span></div>
      <div class="chat-scroll" id="chatScroll">${chatItems}${state.advisorBusy?`<div class="mode-status-line" role="status">军师正在回复…</div>`:''}${state.advisorError?`<div class="mode-error" role="alert">${esc(state.advisorError)} <button data-action="mode-demo">手动切换演示模式</button></div>`:''}</div>
      ${state.mode==='real'?advisorSettingsHTML():''}
      <div class="chat-composer"><div class="quick-questions"><button data-action="ask" data-query="TA 很久没回消息，我该怎么办？">TA 很久没回？</button><button data-action="ask" data-query="我想自然地邀请 TA 见面">怎么自然邀约？</button><button data-action="ask" data-query="如何判断对方是否愿意继续聊天？">怎么看互动信号？</button></div><div class="composer-row"><input id="advisorInput" class="composer-input" placeholder="把你的恋爱难题交给子乔…" maxlength="2000" value="${esc(state.advisorInput)}"/><button class="send-btn" data-action="send" aria-label="发送消息" ${state.advisorBusy?'disabled':''}>${ic('send',19)}</button></div><div class="disclaimer">${state.mode==='demo'?'演示模式：本地预设回复，不是 AI 生成。':'真实模式：问题将发送到团队后端；联网搜索默认关闭，模型密钥保存在服务端。'}</div></div></div>
      <aside class="v4-advisor-aside"><div class="v4-advisor-head"><span>YOUR AI WINGMAN</span><h2>子乔的<br/><em>聊天锦囊</em></h2><p>“人生没有彩排，每一天都是现场直播。”</p></div><div class="panel"><div class="panel-header"><h2>给你的下一步建议</h2><span class="pill pink">${opts.length} 条</span></div>${aside}</div></aside></div>
      <div class="v4-pet" aria-label="子乔桌宠风格形象"><img src="images/ziqiao-cutout.png" alt="子乔桌宠"/><span class="v4-pet-speech">有问题，尽管问我！<small>子乔 · 军师在线</small></span></div>`);
  }
  function botReply(text) {
    const a=state.analysis;
    const context=state.profileSaved?[state.profile.stage,state.profile.relation,state.profile.meStyle,state.profile.taStyle].filter(Boolean).join('、'):'';
    if(a?.boundaryMsgs?.length || (state.profileSaved&&state.profile.boundaries==='TA 表达过不愿继续')) return '子乔认真提醒：这段记录里出现过明确的拒绝或边界表达。无论你的问题是什么，都应先尊重对方的意愿。你可以选择简短告别，或不再回复；不要持续追问，也不要设计“挽回套路”。🌷';
    if(/不回|不理|已读|冷淡|忽冷忽热|隔了很久/.test(text))return '先别把“没及时回复”自动翻译成“不喜欢”～可能只是忙、累，或者聊天节奏不同。建议你先保持正常生活，不连发多条追问。如果这种交流模式长期让你不舒服，也可以坦诚说说你的需要。';
    if(/邀|约|见面|周末|一起|吃饭/.test(text))return `子乔建议采用“具体 + 低压力”方式：比如「${a?.topic==='展览'?'我看到周末那个展还有票':'我看到周末有个挺不错的活动'}，如果你也有兴趣可以一起去；没空也没关系～」。对方若拒绝，就接受，不反复追问。`;
    if(/mbti|intp|infp|enfp|entj|性格/i.test(text))return 'MBTI 适合当作轻松聊彼此偏好的切入口，但不能告诉我们 TA 是否喜欢你，也不能预测两人合不合适。更有价值的问题是：「你平时更喜欢怎样沟通？」「遇到压力时希望别人怎么陪你？」';
    if(/拒绝|不愿意|别联系|不喜欢|边界|不舒服/.test(text))return '如果 TA 已明确表达不愿意，最好停止推进，不追问原因、不让共同朋友施压。表达尊重比任何“高情商话术”更重要。也可以把注意力放回自己的生活与情绪上。';
    if(/回复|怎么说|怎么回|消息|哈哈/.test(text))return '可以试试这样想：先回应对方真实说过的内容，再补一句你自己的感受，最后只提出一个容易回答的小问题。比如「哈哈我也这么觉得！你后来怎么样啦？」不过，“哈哈”本身不代表喜欢或敷衍，要结合完整语境哦。';
    return (context?'考虑到你填的关系背景（'+context+'），我们先结合已发生的互动来看。\n\n':'')+'子乔听见啦 🌷 我们可以先分清两件事：聊天里有哪些确实发生的行为？又有哪些只是我们的猜测？你可以具体告诉我 TA 最近的一句话，或点击下方的示例问题，我会给出真诚、尊重边界的回复方向。（此处是本地模拟回复。）';
  }
  function modal(){return state.privacyOpen?`<div id="modalBackdrop" role="presentation" style="position:fixed;inset:0;background:#2d2138a9;z-index:200;display:grid;place-items:center;padding:22px"><div role="dialog" aria-modal="true" aria-label="隐私处理说明" style="max-width:540px;width:100%;background:#fff;border-radius:24px;padding:30px;box-shadow:0 25px 70px #241a3455"><div class="panel-header"><h2 style="font-size:20px">${ic('shield',23)} 隐私与数据使用说明</h2><button data-action="close-modal" class="btn btn-sm btn-white" aria-label="关闭">${ic('close',16)}</button></div><p class="helper">当前前端已预留并接入团队 Agent API。是否真正联网取决于你配置的后端地址及其运行状态；演示模式不会发送聊天记录。</p><div class="signal-list"><div class="signal-item"><div class="signal-icon">${ic('check',17)}</div><div><strong>这版确实做到了</strong><p>演示模式下不发起 API 请求，文本只在浏览器内解析、不持久化；真实模式须再次确认身份及授权后才能发送。</p></div></div><div class="signal-item"><div class="signal-icon warn">${ic('alert',17)}</div><div><strong>真实上线需要额外设计</strong><p>如果未来使用 OCR / 大模型服务，数据可能传给第三方。需增加明确授权、最小化上传、传输加密、保留/删除机制和供应商评估，不能继续无条件承诺“阅后即焚”。</p></div></div><div class="signal-item"><div class="signal-icon warn">${ic('lock',17)}</div><div><strong>请先保护聊天双方</strong><p>导入前先脱敏，不上传他人私人信息；只处理你有权使用的记录。任何分数都不是对 TA 心理的确认。</p></div></div></div><button class="btn btn-primary" data-action="close-modal" style="width:100%;margin-top:19px">我了解了</button></div></div>`:'';}
  function changeWizardStep(step){
    const safe=clamp(Number(step)||0,0,2);
    if(state.view!=='profile'||safe===state.profileStep)return;
    state.profileDirection=safe<state.profileStep?'backward':'forward';state.profileStep=safe;
    render();window.scrollTo({top:0,behavior:'smooth'});
  }
  function saveProfile(){
    state.profileSaved=true;
    state.ownName=state.profile.meNick||'我';state.otherName=state.profile.taNick||'小林';
    state.ownMBTI=state.profile.meMBTI||'';state.otherMBTI=state.profile.taMBTI||'';
    navigate('import');toast('人物档案已关联本次聊天分析，随时可返回修改');
  }
  function render(){
    const view=state.view;
    const html= view==='home'?home():view==='auth'?authPage():view==='profile'?profilePage():view==='import'?importPage():view==='portraits'?portraitsPage():view==='signals'?signalsPage():advisorPage();
    const preview=window.HeartSignalAPIConfig?.localIntegrationPreview
      ? '<aside class="integration-preview" role="note"><strong>本地集成预览</strong> · API 地址已配置为 http://127.0.0.1:8789。模型回复为模拟。进入聊天导入后，选择「真实 API」测试接口。</aside>'
      : '';
    $('app').innerHTML=preview+html+modal();
    if(view==='advisor'&&$('chatScroll'))$('chatScroll').scrollTop=$('chatScroll').scrollHeight;
  }
  function navigate(view) {
    if(!['home','auth','profile',...parts.map(x=>x.id)].includes(view))view='home';
    if(view==='profile'&&!state.loggedIn){state.view='auth';toast('先体验登录，再填写你的三阶段人物档案');}
    else if(['portraits','signals'].includes(view)&&!state.analysis){state.view='import';toast('先导入聊天，或加载示例报告 ♡');}
    else state.view=view;
    render();window.scrollTo({top:0,behavior:'auto'});
    // Hash is navigation only; do not persist any chat data.
    if(location.hash!==`#${state.view}`)history.replaceState(null,'',`#${state.view}`);
  }
  function resetPhaseAnalysis(){
    state.analysisRunToken++;state.chatRunToken++;
    state.analysis=null; state.dashboard=null; state.report=null; state.analysisId=null; state.sessionId=null; state.advisorSuggestions=[]; state.advisorBoundaryNotes=[];
    state.apiError='';state.apiBusy=false;state.advisorError='';state.advisorBusy=false;
    state.advisorMessages=[];state.advisorInput='';state.mockKey=null;
  }
  function loadMock(key='warm',view='portraits') {
    const fixture=window.HeartSignalMockData&&window.HeartSignalMockData[key];
    if(!fixture){toast('未找到该虚构样例');return;}
    state.mode='demo';resetPhaseAnalysis();state.mockKey=key;state.report=null;state.advisorSuggestions=[];state.advisorBoundaryNotes=[];
    state.identityConfirmed=false;state.sendConsent=false;state.demo=true;
    state.analysis=analyze(parseChatInput(JSON.stringify(fixture.chat),true).messages);
    state.dashboard=HeartSignalDashboard.normalize(fixture.dashboard);
    navigate(view);toast(`已加载虚构示例 ${key==='warm'?'A':'B'}，导入草稿已保留`);
  }
  function loadSample(){loadMock('warm');}
  async function checkApiHealth() {
    state.apiHealthLoading=true;state.apiHealthError='';state.apiHealth=null;render();
    try {
      const health=await window.HeartSignalAPI.health();
      if(!health||health.status!=='ok')throw new Error('健康检查未返回 status=ok');
      state.apiHealth=health;
      if(!health.features?.thinking_supported)state.thinkingLevel='auto';
      if(!health.features?.web_search?.supported)state.webSearch=false;
    } catch(err) {
      state.apiHealthError=err.message||'后端健康检查失败';
    } finally {state.apiHealthLoading=false;render();}
  }
  function apiFeatureSupportsThinking() {return state.apiHealth?.features?.thinking_supported===true;}
  function apiFeatureSupportsSearch() {return state.apiHealth?.features?.web_search?.supported===true;}
  async function runAnalyze() {
    const r=state.parseResult;
    if(r.error){toast(`无法分析：${r.error}`);return;}
    if(!state.consent){toast('请先确认隐私和数据使用说明');return;}
    const minimum=r.format==='json'?2:4;
    if(state.messages.length<minimum){toast(`至少需要 ${minimum} 条有效的聊天消息`);return;}
    const roles=getRoles(state.messages);
    const known=state.messages.filter(m=>m.speaker===roles.own||m.speaker===roles.other);
    if(!roles.other||!known.some(m=>m.speaker===roles.own)||!known.some(m=>m.speaker===roles.other)){
      toast('至少需要一条 self 和一条 other 消息；unknown 不会被猜测为任何一方');return;
    }
    if(known.length<minimum){toast(`有效的双方消息不足 ${minimum} 条`);return;}
    if(state.mode==='demo'){
      state.analysis=analyze(state.messages);
      state.mockKey=null;
      state.dashboard=HeartSignalDashboard.localFromAnalysis(state.analysis,signalData());
      state.analysisId=null;state.sessionId=null;state.advisorMessages=[];state.advisorInput='';state.demo=true;
      navigate('portraits');toast('演示模式：本地规则与虚构数据展示，不代表真实 AI 分析');return;
    }
    if(r.format!=='json'||!r.document){state.apiError='真实 API 提交暂要求 Schema 1.0 chat.json；纯文本请先转换为标准 JSON。';render();return;}
    if(!state.identityConfirmed||!state.sendConsent){toast('真实模式须先确认双方身份，并明确授权本次发送');return;}
    if(!window.HeartSignalAPIAdapter?.ready){state.apiError='真实接口尚未联调：等待文青提供 OpenAPI 请求/响应字段；没有发送任何聊天记录。';render();return;}
    const token=++state.analysisRunToken;
    state.apiBusy=true;state.apiError='';render();
    try{
      const adapter=window.HeartSignalAPIAdapter;
      const payload=adapter.buildAnalyzeRequest({chatDocument:r.document,identities:{self:state.ownName,other:state.otherName},profile:state.profileSaved?state.profile:null,clientId:state.clientId,thinkingLevel:state.thinkingLevel});
      const response=await window.HeartSignalAPI.analyze(payload);
      if(token!==state.analysisRunToken||state.mode!=='real')return;
      const result=adapter.readAnalyzeResponse(response);
      if(!result||typeof result.analysisId!=='string'||!result.analysisId.trim())throw new Error('接口响应缺少有效 analysis_id');
      const dashboard=HeartSignalDashboard.normalize(result.dashboard);
      state.analysisId=result.analysisId;state.clientId=result.clientId||state.clientId;state.sessionId=null;
      state.report=result.report;
      state.analysis={source:'agent-api',total:dashboard.summary.total};
      state.dashboard=dashboard;state.advisorSuggestions=result.suggestions||[];state.advisorBoundaryNotes=[];state.demo=false;state.advisorMessages=[];
      navigate('signals');
      toast(result.status==='partial'?'真实分析已返回，但部分内容受样本限制。':'真实 Agent 分析完成。');
    }catch(err){if(token===state.analysisRunToken)state.apiError=`分析调用失败：${err.message||'未知异常'}。不会自动切换演示模式。`;}
    finally{if(token===state.analysisRunToken){state.apiBusy=false;render();}}
  }
  let nextAdvisorId=0;
  async function sendAdvisor(query, retryId) {
    if(state.advisorBusy)return;
    const q=(query??$('advisorInput')?.value??'').trim().slice(0,2000);
    if(!q)return;
    if(query===undefined)state.advisorInput='';
    state.advisorError='';
    let outgoing;
    if(retryId){outgoing=state.advisorMessages.find(m=>m.id===retryId&&m.from==='me');if(!outgoing)return;outgoing.status='pending';}
    else{outgoing={id:`local-${++nextAdvisorId}`,from:'me',text:q,status:'pending'};state.advisorMessages.push(outgoing);}
    const token=++state.chatRunToken;
    state.advisorBusy=true;render();
    try {
      if(state.mode==='demo'){
        state.advisorMessages.push({from:'bot',text:botReply(q),status:'sent'});
      } else {
        if(!state.analysisId)throw new Error('请先完成真实分析并获得 analysis_id');
        const adapter=window.HeartSignalAPIAdapter;
        if(!adapter?.ready)throw new Error('真实 API 适配器尚未就绪');
        const payload=adapter.buildAdvisorRequest({
          question:q,analysisId:state.analysisId,sessionId:state.sessionId,clientId:state.clientId,
          thinkingLevel:state.thinkingLevel,webSearch:state.webSearch && apiFeatureSupportsSearch()
        });
        const response=await window.HeartSignalAPI.advisorChat(payload);
        if(token!==state.chatRunToken||state.mode!=='real')return;
        const result=adapter.readAdvisorResponse(response);
        state.sessionId=result.sessionId;
        if(result.suggestions?.length)state.advisorSuggestions=result.suggestions;
        state.advisorBoundaryNotes=result.boundaryNotes||[];
        state.advisorMessages.push({from:'bot',text:result.reply,status:'sent',evidence:result.evidence||[],evidenceIds:result.evidenceIds||[],suggestions:result.suggestions||[],boundaryNotes:result.boundaryNotes||[],aiConfig:result.aiConfig||null});
      }
      outgoing.status='sent';
    }catch(err){
      if(token===state.chatRunToken){
        outgoing.status='failed';
        if(err.code==='ANALYSIS_EXPIRED'||err.code==='ANALYSIS_NOT_FOUND'){
          state.sessionId=null;
          state.advisorError='本次分析或会话已失效。请重新分析聊天记录，或重置军师对话后再试。';
        } else if(err.code==='ANALYSIS_FORBIDDEN'||err.code==='CLIENT_ID_REQUIRED') {
          state.advisorError='当前客户端身份与分析报告不匹配。请重新分析并刷新页面后重试。';
        } else {
          state.advisorError=`本条消息发送失败：${err.message||'未知异常'}；点击消息里的“重新发送”可重试。`;
        }
      }
    } finally {if(token===state.chatRunToken){state.advisorBusy=false;render();}}
  }
  async function copyText(text){
    try {await navigator.clipboard.writeText(text);toast('已复制到剪贴板 ♡');}
    catch {const tmp=document.createElement('textarea');tmp.value=text;tmp.style.position='fixed';tmp.style.opacity='0';document.body.append(tmp);tmp.select();try{document.execCommand('copy');toast('已复制到剪贴板 ♡');}catch{toast('复制未成功，请手动选中文字');}tmp.remove();}
  }
  document.addEventListener('click', (ev)=>{
    const el=ev.target.closest('[data-action],[data-go],[data-trait],[data-goal],[data-profile-choice],button[data-wizard-step]');if(!el)return;
    if(el.dataset.go){ev.preventDefault();navigate(el.dataset.go);return;}
    const act=el.dataset.action;
    if(act==='method-phone'){state.loginMethod='phone';render();}
    else if(act==='method-wechat'){state.loginMethod='wechat';render();}
    else if(act==='demo-code')toast('当前是离线演示，不会真正发送短信或验证码');
    else if(act==='demo-login'){state.loggedIn=true;state.authTab='login';state.profileStep=0;navigate('profile');toast('欢迎进入演示账号，完善人物档案吧 ♡');}
    else if(act==='toggle-auth'){state.authTab=state.authTab==='login'?'register':'login';render();}
    else if(act==='auth-login'){state.authTab='login';render();}
    else if(act==='auth-register'){state.authTab='register';render();}
    else if(act==='fill-demo-profile'){demoProfile();render();toast('虚构示例已填入三个阶段，可逐页查看修改');}
    else if(act==='clear-profile'){state.profile={meNick:'',meGender:'',meAge:'',meMBTI:'',meTraits:[],meStatus:'',meStyle:'',meNeed:'',taNick:'',taGender:'',taAge:'',taMBTI:'',taTraits:[],taStyle:'',taEmotional:'',taUnsure:'',relation:'',stage:'',frequency:'',events:'',eventItems:[],touch:'',boundaries:'',goal:'signals',concern:''};state.profileSaved=false;state.profileStep=0;render();toast('当前人物档案已清空');}
    else if(act==='wizard-back'){if(state.profileStep===0)navigate('home');else changeWizardStep(state.profileStep-1);}
    else if(act==='wizard-next'){if(state.profileStep<2)changeWizardStep(state.profileStep+1);else saveProfile();}
    else if(act==='add-event'){state.profile.eventItems.push({date:'',text:''});render();}
    else if(act==='remove-event'){state.profile.eventItems.splice(Number(el.dataset.index),1);render();}
    else if(act==='save-profile'){saveProfile();}
    else if(el.dataset.wizardStep!==undefined){changeWizardStep(Number(el.dataset.wizardStep));}
    else if(el.dataset.profileChoice){const k=el.dataset.profileChoice, v=el.dataset.value;state.profile[k]=state.profile[k]===v?'':v;document.querySelectorAll('[data-profile-choice="'+k+'"]').forEach(b=>{const active=b.dataset.value===state.profile[k];b.classList.toggle('is-selected',active);b.setAttribute('aria-pressed',String(active));const svg=b.querySelector('svg');if(svg)svg.remove();if(active)b.insertAdjacentHTML('afterbegin',ic('check',14));});}
    else if(el.dataset.trait){const key=el.dataset.trait, val=el.dataset.value, arr=state.profile[key]||[];state.profile[key]=arr.includes(val)?arr.filter(x=>x!==val):[...arr,val];el.classList.toggle('active');}
    else if(el.dataset.goal){state.profile.goal=el.dataset.goal;document.querySelectorAll('[data-goal]').forEach(b=>b.classList.toggle('active',b.dataset.goal===state.profile.goal));}
    else if(act==='sample')loadSample();
    else if(act==='sample-advisor')loadMock('warm','advisor');
    else if(act==='mode-demo'){state.analysisRunToken++;state.chatRunToken++;state.mode='demo';state.apiError='';state.advisorError='';state.advisorBusy=false;state.apiBusy=false;state.analysisId=null;state.sessionId=null;state.report=null;state.advisorSuggestions=[];state.advisorBoundaryNotes=[];if(state.messages.length){state.analysis=analyze(state.messages);state.dashboard=state.mockKey&&window.HeartSignalMockData?.[state.mockKey]?HeartSignalDashboard.normalize(HeartSignalMockData[state.mockKey].dashboard):HeartSignalDashboard.localFromAnalysis(state.analysis,signalData());}else{state.analysis=null;state.dashboard=null;}state.advisorMessages=[];render();toast('已手动切换演示模式 · 不会调用后端');}
    else if(act==='check-health'){checkApiHealth();}
    else if(act==='mode-real'){state.analysisRunToken++;state.chatRunToken++;state.mode='real';state.apiError='';state.advisorError='';state.dashboard=null;state.report=null;state.analysis=null;state.analysisId=null;state.sessionId=null;state.advisorSuggestions=[];state.advisorBoundaryNotes=[];state.advisorMessages=[];state.identityConfirmed=false;state.sendConsent=false;render();toast(window.HeartSignalAPIConfig?.localIntegrationPreview?'已选本地 API，请核对身份并授权发送':'已切换真实模式，请核对身份并授权发送');checkApiHealth();}
    else if(act==='mock-warm')loadMock('warm');
    else if(act==='mock-reserved')loadMock('reserved');
    else if(act==='retry-message'){const m=state.advisorMessages.find(x=>x.id===el.dataset.messageId);if(m&&m.status==='failed')sendAdvisor(m.text,m.id);}
    else if(act==='privacy'){state.privacyOpen=true;render();}
    else if(act==='close-modal'){state.privacyOpen=false;render();}
    else if(act==='tab-text'){state.tab='text';render();}
    else if(act==='tab-image'){state.tab='image';render();}
    else if(act==='clear'){state.raw='';state.consent=false;state.identityConfirmed=false;state.sendConsent=false;state.demo=false;resetPhaseAnalysis();state.fileFormatHint=null;refreshParsedChat();state.tab='text';render();toast('已清空当前文本与结果');}
    else if(act==='analyze')runAnalyze();
    else if(act==='copy'){const ix=Number(el.dataset.copyIndex);const item=currentAdvisorOptions()[ix];if(item)copyText(item.text);}
    else if(act==='send')sendAdvisor();
    else if(act==='ask')sendAdvisor(el.dataset.query);
    else if(act==='reset-chat'){state.chatRunToken++;state.advisorMessages=[];state.sessionId=null;state.advisorError='';initAdvisor();render();toast('已重置军师对话和本次会话 ID');}
  });
  document.addEventListener('input',(ev)=>{
    const id=ev.target?.id;
    if(ev.target?.dataset?.eventField){const idx=Number(ev.target.dataset.eventIndex);if(state.profile.eventItems[idx])state.profile.eventItems[idx][ev.target.dataset.eventField]=ev.target.value;return;}
    if(ev.target?.dataset?.profile){state.profile[ev.target.dataset.profile]=ev.target.value;return;}
    if(id==='chatInput'){state.raw=ev.target.value;state.fileFormatHint=null;refreshParsedChat();state.demo=false;resetPhaseAnalysis();state.identityConfirmed=false;state.sendConsent=false;updatePreview();}
    else if(id==='ownName'||id==='otherName'){state[id]=ev.target.value;state.identityConfirmed=false;updatePreview();}
    else if(id==='advisorInput'){state.advisorInput=ev.target.value;}
  });
  document.addEventListener('change',(ev)=>{
    const id=ev.target?.id;
    if(ev.target?.dataset?.eventField){const idx=Number(ev.target.dataset.eventIndex);if(state.profile.eventItems[idx])state.profile.eventItems[idx][ev.target.dataset.eventField]=ev.target.value;return;}
    if(ev.target?.dataset?.profile){state.profile[ev.target.dataset.profile]=ev.target.value;return;}
    if(id==='consent')state.consent=ev.target.checked;
    else if(id==='identityConfirmed')state.identityConfirmed=ev.target.checked;
    else if(id==='sendConsent')state.sendConsent=ev.target.checked;
    else if(id==='ownMBTI'||id==='otherMBTI')state[id]=ev.target.value;
    else if(id==='thinkingLevel'){state.thinkingLevel=ev.target.value;render();}
    else if(id==='webSearch'){state.webSearch=ev.target.checked;render();}
    else if(id==='fileInput'&&ev.target.files?.[0]){
      const file=ev.target.files[0];
      const ext=file.name.split('.').pop()?.toLowerCase();
      if(!['json','txt','csv'].includes(ext)){toast('仅支持 .json / .txt / .csv；Markdown 不作为导入格式');ev.target.value='';return;}
      if(file.size>2*1024*1024){toast('为保证浏览器流畅，请上传小于 2 MB 的文件');ev.target.value='';return;}
      const reader=new FileReader();reader.onload=()=>{
        state.raw=String(reader.result||'');state.fileFormatHint=ext==='json'?'json':null;
        const result=refreshParsedChat(state.fileFormatHint==='json');
        resetPhaseAnalysis();state.demo=false;state.consent=false;state.identityConfirmed=false;state.sendConsent=false;state.tab='text';render();
        if(result.error)toast(`${file.name} 导入失败：${result.error}`);
        else toast(`已导入 ${file.name}，实际解析 ${result.messages.length} 条消息`);
      };
      reader.onerror=()=>toast('读取文件失败，请尝试粘贴 JSON 或聊天文本');reader.readAsText(file,'UTF-8');
    }
  });
  document.addEventListener('keydown',(ev)=>{
    if(ev.key==='Enter'&&!ev.isComposing&&ev.target?.id==='advisorInput'){ev.preventDefault();sendAdvisor();}
    if(ev.key==='Escape'&&state.privacyOpen){state.privacyOpen=false;render();}
  });
  document.addEventListener('click',(ev)=>{
    if(ev.target?.id==='modalBackdrop'){state.privacyOpen=false;render();}
  });
  let touchStart=null;
  document.addEventListener('touchstart',ev=>{
    if(state.view!=='profile'||!ev.target.closest('#wizardStage')||ev.target.closest('input,textarea,select,button,label'))return;
    const t=ev.changedTouches[0];touchStart={x:t.clientX,y:t.clientY};
  },{passive:true});
  document.addEventListener('touchend',ev=>{
    if(state.view!=='profile'||!touchStart)return;
    const t=ev.changedTouches[0],dx=t.clientX-touchStart.x,dy=t.clientY-touchStart.y;touchStart=null;
    if(Math.abs(dx)>100&&Math.abs(dx)>Math.abs(dy)*1.4){
      if(dx<0&&state.profileStep<2)changeWizardStep(state.profileStep+1);
      if(dx>0&&state.profileStep>0)changeWizardStep(state.profileStep-1);
    }
  },{passive:true});
  const initial=location.hash.slice(1);
  state.view=['home','import','auth','advisor'].includes(initial)?initial:'home';
  render();
})();
