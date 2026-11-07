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
    view:'home', tab:'text', raw:'', ownName:'我', otherName:'小林', ownMBTI:'', otherMBTI:'', demo:false, consent:false,
    analysis:null, messages:[], advisorMessages:[], advisorInput:'', privacyOpen:false, loggedIn:false, authTab:'login', loginMethod:'phone', authName:'', profileSaved:false, profileStep:0, profileDirection:'forward', profile:{meNick:'',meGender:'',meAge:'',meMBTI:'',meTraits:[],meStatus:'',meStyle:'',meNeed:'',taNick:'',taGender:'',taAge:'',taMBTI:'',taTraits:[],taStyle:'',taEmotional:'',taUnsure:'',relation:'',stage:'',frequency:'',events:'',eventItems:[],touch:'',boundaries:'',goal:'signals',concern:''}
  };
  const advisorBase = (document.querySelector('meta[name="advisor-api-base"]')?.content || '').trim().replace(/\/$/,'');
  const advisor = {status:'idle',model:'',requiresAccessToken:false,token:'',includeContext:false,request:null,error:''};
  const advisorDemo = {messages:[],input:''};
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
        <div class="v4-copy"><span class="eyebrow"><span class="tiny-dot"></span> 你的专属恋爱军师</span><h1>申请查看<br/>你的<span class="special">好感度。</span></h1><p>聊天记录里藏着什么小秘密？<br/>导入你和 TA 的对话，让子乔军师帮你看清互动节奏，找到更自然的下一步。</p>
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
    if(!state.profileSaved||state.demo)return '';
    const p=state.profile;
    const bits=[p.relation,p.stage,p.frequency].filter(Boolean).map(esc).join(' · ');
    const event=[...(p.eventItems||[]).map(e=>e.text).filter(Boolean),p.events].filter(Boolean).join('；').slice(0,170);
    const concern=(p.concern||'').slice(0,120);const extra=[p.meStyle&&'我的沟通风格：'+p.meStyle,p.taStyle&&'TA 的沟通表现：'+p.taStyle,p.boundaries==='TA 表达过不愿继续'?'提醒：用户报告有明确边界':null].filter(Boolean).map(esc).join(' · ');
    return `<div class="v5-context-in-results"><strong>♡ 已参考人物档案</strong><p>${bits||'未填写关系阶段'}${extra?`<br/>${extra}`:''}${event?`<br/>共同经历：${esc(event)}`:''}${concern?`<br/>当前关注：${esc(concern)}`:''}</p><small>这只是用户填写的背景，不能证明 TA 的真实想法。</small><button data-go="profile">编辑档案 →</button></div>`;
  }

  function workWrap(body) {return `${topbar()}<main class="v4-workspace v4-${state.view}"><div class="v4-work-inner max">${state.view!=='import'?profileContext():''}${body}</div></main>${footer()}`;}
  function heading(step,name,description,extra=''){
    const eyebrow={import:'CHAT IMPORT',portraits:'DUAL PORTRAITS',signals:'CHAT SIGNALS',advisor:'ASK YOUR WINGMAN'}[state.view]||'HEART SIGNAL LAB';
    const sticker=state.view==='advisor'?`<img class="v4-heading-face" src="images/ziqiao-photo.jpeg" alt="子乔形象"/>`:`<span class="v4-heading-signet">${ic(state.view==='import'?'upload':state.view==='portraits'?'users':'chart',24)}</span>`;
    return `<div class="page-heading v4-page-heading"><div><span class="v4-overline">${eyebrow} &nbsp; / &nbsp; ${esc(step)}</span><h1>${esc(name)}</h1><p>${esc(description)}</p></div><div class="v4-heading-right">${sticker}${state.demo&&state.view!=='import'?'<span class="pill orange">示例数据</span>':''}${extra}</div></div>`;
  }
  const mbtiOptions = ['','ISTJ','ISFJ','INFJ','INTJ','ISTP','ISFP','INFP','INTP','ESTP','ESFP','ENFP','ENTP','ESTJ','ESFJ','ENFJ','ENTJ'];
  const mbtiSelect = (label,id,value)=>`<div class="field"><label for="${id}">${label}</label><select id="${id}" data-field="${id}">${mbtiOptions.map(m=>`<option value="${m}" ${m===value?'selected':''}>${m||'不确定 / 不填写'}</option>`).join('')}</select></div>`;
  function importPage() {
    const chat=parsedMessages(state.raw); return workWrap(`${heading('STEP 01 / 04','先把聊天交给我们','支持聊天文本、带发送者与内容列的 CSV，以及 wechat-cli 导出的 JSON 和 Markdown。',`<button class="btn btn-sm btn-white" data-action="sample">${ic('spark',14)} 加载示例</button>`)}
      ${state.profileSaved?`<div class="v5-context-strip">${ic('users',17)} 已加载人物档案：${esc(state.profile.meNick||'我')} &amp; ${esc(state.profile.taNick||'TA')} · ${esc(state.profile.stage||'关系阶段未设置')}<button data-go="profile">编辑背景 →</button></div>`:''}<div class="layout-2"><div class="stack">
      <div class="panel"><div class="panel-header"><h2>01 · 这段故事的主角</h2><span class="pill purple">${ic('users',13)} 基本信息</span></div>
        <div class="field-grid"><div class="field"><label for="ownName">我的聊天昵称</label><input id="ownName" data-field="ownName" value="${esc(state.ownName)}" maxlength="24" placeholder="例如：我"/></div><div class="field"><label for="otherName">TA 的聊天昵称</label><input id="otherName" data-field="otherName" value="${esc(state.otherName)}" maxlength="24" placeholder="例如：小林"/></div>${mbtiSelect('我的 MBTI（可选）','ownMBTI',state.ownMBTI)}${mbtiSelect('TA 自述的 MBTI（可选）','otherMBTI',state.otherMBTI)}</div>
        <div class="mbti-note">${ic('question',13)} MBTI 是可选的自述偏好，不能从聊天文本可靠推断，也不应作为好感或相容性的判断依据。</div>
      </div>
      <div class="panel"><div class="panel-header"><h2>02 · 粘贴聊天记录</h2><span class="pill pink">${ic('lock',13)} 本地处理</span></div>
        <div class="import-tabs"><button class="tab ${state.tab==='text'?'active':''}" data-action="tab-text">${ic('file',13)} 文本导入</button><button class="tab ${state.tab==='image'?'active':''}" data-action="tab-image">${ic('upload',13)} 截图导入 · 规划中</button></div>
        ${state.tab==='text'?`<textarea id="chatInput" class="editor" placeholder="试试按这个格式粘贴：\n\n我: 今天的课好难啊\nTA: 哈哈哈我也差点没听懂\n我: 你后来怎么复习的？\nTA: 我整理了笔记，要不要发给你？" spellcheck="false">${esc(state.raw)}</textarea><div class="editor-footer"><div style="display:flex;gap:9px;align-items:center"><label class="file-label" for="fileInput">${ic('upload',15)} 导入聊天文件</label><input class="upload-file" type="file" id="fileInput" accept=".txt,.csv,.md,.json,text/plain,text/csv,text/markdown,application/json"/><button class="btn btn-sm btn-soft" data-action="sample">试试示例</button></div><small id="charCount">${state.raw.length} 字符 · ${chat.length} 条消息</small></div>`:
         `<div class="no-data"><div class="empty-icon">${ic('upload',25)}</div><strong>截图 OCR 即将开放</strong><p>本轮交付聚焦可完整演示的文本分析闭环。<br/>你可以复制聊天文字，或先将截图转为文本再粘贴。</p><button class="btn btn-sm btn-primary" data-action="tab-text">切换到文本导入</button></div>`}
        <label class="check-row"><input id="consent" type="checkbox" ${state.consent?'checked':''}/><span>我已移除不必要的姓名、电话等敏感信息，并确认有权使用这段聊天内容进行分析。</span></label>
        <div class="import-actions"><button class="btn btn-white" data-action="clear">清空内容</button><button class="btn btn-primary" data-action="analyze">生成本地互动报告 ${ic('arrow',16)}</button></div>
      </div></div>
      <div class="stack"><div class="panel"><div class="panel-header"><h2>聊天内容预览</h2><span class="pill" id="previewCount">${chat.length} 条消息</span></div><div class="preview-messages" id="previewMessages">${previewHTML(chat)}</div></div>
      <div class="info-note"><span class="note-icon">${ic('shield',19)}</span><span><strong>原型隐私说明</strong><br/>聊天导入与互动报告在浏览器内处理。军师交流会将你主动发送的对话交给模型服务；只有勾选时才会附带互动统计和档案选项。</span></div>
      <div class="panel" style="background:#fffdf6"><div class="panel-header"><h2>一个小小的提醒</h2><span>🌷</span></div><p class="helper" style="margin:0">没有哪句话能百分百证明喜欢或不喜欢。报告只整理聊天中的可观察行为，真实感受仍需要尊重对方、通过坦诚交流确认。</p></div></div></div>`);
  }
  function exportSpeaker(role) {
    return ({self:'我',other:'对方',unknown:'未知'})[role] || '未知';
  }
  function parseWechatExport(text) {
    if (text.startsWith('{')) {
      try {
        const data = JSON.parse(text);
        if (data.source !== 'wechat-cli' || data.chat_type !== 'private' || !Array.isArray(data.messages)) return [];
        return data.messages.filter(m=>m?.type==='text'&&typeof m.content==='string'&&m.content.trim()).map(m=>({
          speaker:exportSpeaker(m.sender), role:m.sender, unknown:m.sender!=='self'&&m.sender!=='other',
          date:typeof m.timestamp==='string' ? m.timestamp.slice(0,10) : '', body:m.content
        }));
      } catch { return []; }
    }
    if (!text.startsWith('# 微信聊天记录')) return null;
    const messages = [];
    let message=null, body=[], fence='', wrapped=false;
    const save=()=>{
      const content=body.join('\n');
      if(message&&content.trim())messages.push({...message,body:wrapped?content:content.trim()});
    };
    for (const line of text.split(/\r?\n/)) {
      if(fence){
        if(line===fence)fence='';
        else body.push(line);
        continue;
      }
      const heading=/^### (.+?) \| (我|对方|未知)[ \t]*$/.exec(line);
      if(heading){
        save();
        const speaker=heading[2],role=({'我':'self','对方':'other','未知':'unknown'})[speaker];
        message={date:/^\d{4}-\d{2}-\d{2}/.exec(heading[1])?.[0]||'',speaker,role,unknown:role==='unknown'};
        body=[];wrapped=false;
      }else if(message&&!wrapped){
        const opening=/^(`{3,})text$/.exec(line);
        if(opening&&body.every(part=>!part.trim())){fence=opening[1];body=[];wrapped=true;}
        else body.push(line);
      }
    }
    save();
    return messages;
  }
  function parseCsv(text) {
    const header = text.split(/\r?\n/,1)[0];
    if (!header.includes(',')) return null;
    const field = /(?:"((?:[^"]|"")*)"|([^",\r\n]*))(,|\r\n|\n|\r|$)/gy;
    const rows = [];
    let row = [];
    while (field.lastIndex < text.length) {
      const match = field.exec(text);
      if (!match || !match[0]) return null;
      row.push(match[1] === undefined ? match[2] : match[1].replace(/""/g,'"'));
      if (match[3] !== ',') { rows.push(row); row=[]; }
    }
    if(row.length) rows.push([...row,'']);
    const columns = rows.shift()?.map(value=>value.trim().toLowerCase()) || [];
    const find = (...names)=>columns.findIndex(column=>names.includes(column));
    const speaker = find('speaker','sender','昵称','发送者');
    const body = find('message','content','text','消息','内容');
    const date = find('timestamp','date','time','时间','日期');
    if (speaker < 0 || body < 0) return null;
    return rows.flatMap(values=>{
      const name=values[speaker]?.trim(), content=values[body];
      return name&&content?.trim() ? [{speaker:name,body:content,date:/^\d{4}[-/]\d{1,2}[-/]\d{1,2}/.exec(values[date]||'')?.[0]||''}] : [];
    });
  }
  function parsedMessages(raw) {
    const text=String(raw||'').replace(/^\uFEFF/,'').trimStart();
    const imported=parseWechatExport(text)??parseCsv(text);
    if(imported) return imported.slice(0,5000);
    const msgs=[]; const lines=text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
    for(const line of lines) {
      // optional YYYY-MM-DD HH:MM, or [HH:MM], followed by speaker and message
      const m=line.match(/^(?:(\d{4}[\-/]\d{1,2}[\-/]\d{1,2})[ T]\d{1,2}:\d{2}(?::\d{2})?\s*|\[\d{1,2}:\d{2}(?::\d{2})?\]\s*)?([^:：]{1,24})[:：]\s*(.+)$/);
      if(m){ const speaker=m[2].trim(); if(!speaker || /^https?$/i.test(speaker)) continue; msgs.push({date:m[1]||'',speaker,body:m[3].trim()}); }
      else if(msgs.length){ msgs[msgs.length-1].body+='\n'+line; }
    }
    return msgs.slice(0,5000);
  }
  function getRoles(msgs, ownName=state.ownName, otherName=state.otherName) {
    if(msgs.some(m=>m.role))return {own:'我',other:'对方'};
    const speakers=[...new Set(msgs.filter(m=>!m.unknown).map(m=>m.speaker))];
    let own=speakers.includes(ownName.trim())?ownName.trim():speakers[0];
    let other=speakers.includes(otherName.trim()) && otherName.trim()!==own ?otherName.trim():(speakers.find(x=>x!==own)||'');
    return {own,other};
  }
  function previewHTML(msgs) {
    if(!msgs.length)return `<div class="no-data"><div class="empty-icon">${ic('chat',25)}</div><strong>还没有聊天内容</strong><p>导入后，这里会出现双方对话预览。<br/>或者先用示例体验一下吧 ♡</p></div>`;
    const roles=getRoles(msgs);
    return msgs.slice(-5).map(m=>`<div class="preview-chat ${m.speaker===roles.own?'self':'other'}"><span class="who">${esc(m.speaker)}</span><span class="say">${esc(m.body.slice(0,180))}</span></div>`).join('');
  }
  function updatePreview() {
    const parsed=parsedMessages(state.raw);
    if($('previewCount'))$('previewCount').textContent=`${parsed.length} 条消息`;
    if($('previewMessages'))$('previewMessages').innerHTML=previewHTML(parsed);
    if($('charCount'))$('charCount').textContent=`${state.raw.length} 字符 · ${parsed.length} 条消息`;
  }
  function analyze(msgs, ownName, otherName) {
    const {own,other}=getRoles(msgs, ownName, otherName);
    const filtered=msgs.filter(m=>!m.unknown&&(m.speaker===own||m.speaker===other));
    const self=filtered.filter(m=>m.speaker===own),ta=filtered.filter(m=>m.speaker===other);
    const asked=m=>/[？?]/.test(m.body)||/(吗|么|呢|什么|怎么|为什么|要不要|有没有|哪|谁|多少)/.test(m.body);
    const invite=m=>/(一起|下次|周末|有空|约|见面|去看|要不要去|想见)/.test(m.body);
    const warm=m=>/(哈哈哈|好呀|好哇|期待|喜欢|好耶|不错|谢谢|开心|可以呀|当然|🌷|❤️|💕|❤)/.test(m.body);
    const boundary=m=>/(别(再)?联系|不要(再)?联系|请不要(再)?联系|不想(见|聊|和你)|不用再|别打扰|不要打扰|没兴趣|不方便.*(别|不要)|明确拒绝|请停止)/.test(m.body);
    const short=m=>m.body.replace(/\s/g,'').length<5;
    const qMe=self.filter(asked).length,qTa=ta.filter(asked).length;
    const invitation=ta.filter(invite),warmMsgs=ta.filter(warm),shortMsgs=ta.filter(short),boundaryMsgs=ta.filter(boundary);
    const share=Math.round(100*ta.length/(filtered.length||1));
    // Visual proxy only; not a scientifically validated inference of romantic interest.
    const score=clamp(Math.round(36+share*.36+Math.min(qTa,6)*4.5+Math.min(invitation.length,3)*7+Math.min(warmMsgs.length,5)*2.4-Math.min(shortMsgs.length,4)*2.3-(boundaryMsgs.length?38:0)),8,91);
    const keyText=filtered.map(m=>m.body).join(' ');
    const topics=[['展','展览'],['电影','电影'],['音乐','音乐'],['歌','音乐'],['咖啡','咖啡'],['游戏','游戏'],['课程','课程'],['考试','考试'],['书','读书'],['猫','小猫'],['旅行','旅行']];
    const topic=topics.find(([term])=>keyText.includes(term))?.[1]||'';
    const chunks=[];
    if(filtered.some(x=>x.date)){
      const byDate=new Map();filtered.forEach(x=>{const day=x.date||'未注明';byDate.set(day,(byDate.get(day)||0)+1)});
      [...byDate].slice(-6).forEach(([label,count])=>chunks.push({label:label==='未注明'?'其他':label.slice(5).replace('-','/'),count}));
    }else{for(let i=0;i<Math.min(6,Math.ceil(filtered.length/4));i++){const len=filtered.slice(i*4,(i+1)*4).length;chunks.push({label:`片段${i+1}`,count:len});}}
    return {msgs:filtered,self,ta,own,other,share,score,qMe,qTa,invitation,warmMsgs,shortMsgs,boundaryMsgs,topic,chunks,total:filtered.length,avgMe:Math.round(self.reduce((a,m)=>a+m.body.length,0)/(self.length||1)),avgTa:Math.round(ta.reduce((a,m)=>a+m.body.length,0)/(ta.length||1))};
  }
  function needAnalysis() {return `<div class="empty-state"><div class="huge">💌</div><h2>先给心动一点线索吧</h2><p>这里还没有分析结果。先导入一段双方聊天，再来认识彼此的交流方式。</p><button class="btn btn-primary" data-go="import">去导入聊天 ${ic('arrow',17)}</button><p style="margin:18px auto 0"><button class="privacy-link" data-action="sample">或者先体验示例报告</button></p></div>`;}
  function resultStepButtons(prev,next,nextLabel){return `<div class="step-controls"><button class="btn btn-white" data-go="${prev}">${ic('chevron',15)} 返回上一步</button><span class="muted">观察沟通，不替任何人下感情结论</span><button class="btn btn-primary" data-go="${next}">${nextLabel} ${ic('arrow',16)}</button></div>`;}
  const pct=(n)=>`${clamp(Math.round(n),0,100)}%`;
  function portraitsPage() {
    if(!state.analysis)return workWrap(needAnalysis()); const a=state.analysis;
    const isMe=(name)=>name===a.own;
    const portrait=(name,which,count,qs,avg,mbti)=>`<article class="portrait-card"><div class="portrait-top ${which}"><div class="portrait-avatar" aria-hidden="true">${which==='me'?'🧑🏻‍💻':'🧑🏻‍🎨'}</div><span class="pill" style="position:absolute;bottom:12px;right:17px;background:#ffffffce">${which==='me'?'我的视角':'TA 的视角'}</span></div><div class="portrait-info"><div class="portrait-name"><h2>${esc(name)}</h2><span class="pill ${which==='me'?'purple':'pink'}">${mbti?esc(mbti):'MBTI 未填写'}</span></div><p class="portrait-sub">从当前导入的聊天片段整理</p><div class="metric-row"><span>发送消息</span><b>${count} 条</b></div><div class="metric-row"><span>提问 / 征询</span><b>${qs} 次</b></div><div class="metric-row"><span>平均消息长度</span><b>${avg} 字</b></div><div class="tag-row"><span class="pill ${which==='me'?'purple':'pink'}">${qs>=2?'会主动提问':'表达相对简短'}</span><span class="pill">${avg>=15?'偏详细表达':'轻量交流风格'}</span></div></div></article>`;
    return workWrap(`${heading('STEP 02 / 04','双向沟通画像','不猜性格、不贴标签，只看看你们在这段聊天里如何表达。')}
      <div class="result-banner" style="margin-bottom:19px"><div><div class="main">两个人，两个视角，一段正在发生的故事。</div><p>已整理 ${a.total} 条双方消息 · 观察聊天行为，而不是判定某个人的固定性格。</p></div><span class="heart-sticker">♡</span></div>
      <div class="portrait-grid">${portrait(a.own,'me',a.self.length,a.qMe,a.avgMe,state.ownMBTI)}${portrait(a.other,'them',a.ta.length,a.qTa,a.avgTa,state.otherMBTI)}</div>
      <div class="insight-strip" style="margin-top:19px"><span style="font-size:22px">💡</span><div><strong>子乔观察：</strong> 在这段样本中，你贡献了 ${a.self.length} 条消息，TA 贡献了 ${a.ta.length} 条。TA 发起了 ${a.qTa} 次提问或征询。<br/>这些可以用于理解交流节奏，但不能单独证明喜欢、冷淡或任何人格类型。</div></div>
      ${resultStepButtons('import','signals','查看互动信号')}`);
  }
  function signalData() {
    const a=state.analysis;
    const sig=[];
    if(a.qTa>0){const item=a.ta.find(m=>/[？?]|(吗|么|呢|什么|怎么|要不要|有没有|哪)/.test(m.body));sig.push({type:'good',title:`TA 有 ${a.qTa} 次提问 / 征询`,desc:'主动提问可能表示想继续交流，也可能只是正常聊天习惯。',quote:item?.body});}
    if(a.invitation.length){sig.push({type:'good',title:`出现 ${a.invitation.length} 条共同活动相关表达`,desc:'提到“下次”“一起”是值得留意的互动线索，是否构成邀约还要结合语境。',quote:a.invitation[0].body});}
    if(a.warmMsgs.length){sig.push({type:'good',title:`发现 ${a.warmMsgs.length} 条轻松积极的表达`,desc:'积极语气、分享或笑声能反映当下交流氛围，不等于稳定的情感意图。',quote:a.warmMsgs[0].body});}
    if(a.shortMsgs.length){sig.push({type:'warn',title:`有 ${a.shortMsgs.length} 条较短回复`,desc:'回复简短可能来自时间紧、聊天风格等原因，请不要直接等同于敷衍。',quote:a.shortMsgs[0].body});}
    if(a.boundaryMsgs.length){sig.unshift({type:'red',title:'出现明确的边界或拒绝表达',desc:'应优先尊重对方表达的意愿。建议停止推进邀约，不反复追问。',quote:a.boundaryMsgs[0].body});}
    if(!sig.length)sig.push({type:'warn',title:'当前没有足够清晰的互动线索',desc:'样本可能较短。建议优先关注现实交流中的舒适度和双方意愿。',quote:null});
    return sig.slice(0,5);
  }
  function signalsPage() {
    if(!state.analysis)return workWrap(needAnalysis());const a=state.analysis;
    const bars=[{name:'双方消息参与平衡',val:Math.round(100-2*Math.abs(a.share-50)),color:'pink'},
      {name:'TA 在消息中的提问占比',val:Math.round(100*a.qTa/(a.ta.length||1)),color:'violet'},
      {name:'TA 的共同活动表达占比',val:Math.round(100*a.invitation.length/(a.ta.length||1)),color:'orange'},
      {name:'TA 的积极语气表达占比',val:Math.round(100*a.warmMsgs.length/(a.ta.length||1)),color:'green'}];
    const sig=signalData();const chart=a.chunks.length?a.chunks:[{label:'片段1',count:a.total}]; const max=Math.max(1,...chart.map(c=>c.count));
    return workWrap(`${heading('STEP 03 / 04','关系信号气象站','整理你们的互动结构，积极信号与不确定因素都放在桌面上。')}
      ${a.boundaryMsgs.length?`<div class="info-note red" style="margin-bottom:17px"><span class="note-icon">${ic('alert',18)}</span><span><strong>边界提醒：</strong>聊天中出现拒绝或不愿继续交流的表达。请优先尊重对方的决定，不追问或施压。</span></div>`:''}
      <div class="signal-detail-grid"><div class="stack"><div class="panel"><div class="panel-header"><h2>互动信号参考指数</h2><span class="pill pink">启发式演示</span></div><div class="circle-block"><div class="score-ring" style="--score:${a.score}"><div class="score-center"><b>${a.score}</b><small>/100</small><span>互动信号指数</span></div></div><div class="ring-label">仅是当前文本的规则化可视化分数<br/><strong>不是好感概率 / 心理测量结果</strong></div></div><div class="tiny-metrics"><div class="tiny-metric"><b>${a.total}</b><span>总消息数</span></div><div class="tiny-metric"><b>${a.share}%</b><span>TA 消息占比</span></div><div class="tiny-metric"><b>${a.qTa}</b><span>TA 的提问次数</span></div></div></div>
        <div class="panel"><div class="panel-header"><h2>聊天量分布</h2><span class="illustration-caption">按日期 / 导入片段</span></div><div class="heart-chart">${chart.map(c=>`<div class="column" title="${esc(c.label)} · ${c.count} 条"><span style="height:${Math.max(13,Math.round(c.count/max*100))}%"></span></div>`).join('')}</div><div class="chart-labels">${chart.map(c=>`<span>${esc(c.label)}</span>`).join('')}</div><div class="disclaimer" style="margin-top:12px">这张图只显示消息数量，不代表关系升温或降温。</div></div></div>
        <div class="stack"><div class="panel"><div class="panel-header"><h2>可观察的互动维度</h2><span class="pill">基于当前文本</span></div>${bars.map(b=>`<div class="bar-item"><div class="bar-head"><span>${b.name}</span><b>${pct(b.val)}</b></div><div class="bar-track"><div class="bar-fill ${b.color}" style="width:${pct(b.val)}"></div></div></div>`).join('')}<div class="disclaimer">百分比是消息中的简单词句计数或比例，并非“喜欢程度”。</div></div>
        <div class="panel"><div class="panel-header"><h2>重要信号与原文依据</h2><span class="pill purple">${sig.length} 个观察点</span></div><div class="signal-list">${sig.map(s=>`<div class="signal-item"><div class="signal-icon ${s.type==='warn'?'warn':s.type==='red'?'red':''}">${ic(s.type==='good'?'check':'alert',17)}</div><div><strong>${esc(s.title)}</strong><p>${esc(s.desc)}</p>${s.quote?`<div class="quote-box">“${esc(s.quote.slice(0,150))}”</div>`:''}</div></div>`).join('')}</div></div></div></div>
      ${resultStepButtons('portraits','advisor','找子乔聊下一步')}`);
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
  function initAdvisor(){
    if(!state.advisorMessages.length){
      state.advisorMessages=[{from:'bot',welcome:true,text:'嗨，我是子乔。你可以直接问我怎么回复、怎么表达心意，或如何尊重对方的边界。'}];
    }
  }
  function advisorStatusText(){
    if(state.demo)return '本地规则演示 · 无需 API';
    if(advisor.status==='ready')return 'DeepSeek 配置就绪 · '+advisor.model;
    if(advisor.status==='unconfigured')return 'DeepSeek 密钥尚未在服务端配置';
    if(advisor.status==='unavailable')return 'DeepSeek 后端未连接';
    return '正在检查 DeepSeek 后端…';
  }
  async function checkAdvisorStatus(){
    advisor.status='checking';
    if($('advisorStatus'))$('advisorStatus').textContent=advisorStatusText();
    try {
      const response=await fetch(advisorBase+'/api/status',{cache:'no-store',signal:AbortSignal.timeout(5000)});
      if(!response.ok)throw new Error('status');
      const result=await response.json();
      advisor.status=result.configured===true?'ready':'unconfigured';
      advisor.model=typeof result.model==='string'?result.model:'DeepSeek';
      advisor.requiresAccessToken=result.requiresAccessToken===true;
    }catch{advisor.status='unavailable';}
    if($('advisorStatus'))$('advisorStatus').textContent=advisorStatusText();
    if($('advisorTokenField'))$('advisorTokenField').hidden=!advisor.requiresAccessToken;
  }
  function advisorPage(){
    initAdvisor();const opts=state.analysis?strategyOptions():[];
    const messages=state.demo ? [{from:'bot',text:'这里是军师对话演示。可以点击一个示例问题，或输入问题试试。'},...advisorDemo.messages] : state.advisorMessages;
    return workWrap(`${heading('STEP 04 / 04','子乔军师，在线接招','聊聊如何回复、表达心意或自然邀约。子乔的建议以真诚和尊重为前提。',`<button class="btn btn-sm btn-white" data-action="reset-chat">${ic('rotate',14)} 重置对话</button>`)}
      <div class="v4-advisor-grid"><div class="chat-panel v4-chat-panel"><div class="chat-topbar"><div class="avatar-small avatar-photo"><img src="images/ziqiao-photo.jpeg" alt=""/></div><div><h3>吕子乔 · AI 恋爱军师</h3><p id="advisorStatus" role="status">${esc(advisorStatusText())}</p></div><span class="pill purple" style="margin-left:auto">轻松聊 · 不玩套路</span></div>
      <div class="chat-scroll" id="chatScroll">${messages.map(m=>`<div class="chat-msg ${m.from==='me'?'me':'bot'}"><span class="speaker">${m.from==='me'?'🧑🏻‍💻':'👔'}</span><div class="message">${esc(m.text)}</div></div>`).join('')}</div>
      <div class="chat-composer"><div class="quick-questions"><button data-action="ask" data-query="TA 很久没回消息，我该怎么办？">TA 很久没回？</button><button data-action="ask" data-query="我想自然地邀请 TA 见面">怎么自然邀约？</button><button data-action="ask" data-query="如何判断对方是否愿意继续聊天？">怎么看互动信号？</button></div><div class="composer-row"><input id="advisorInput" class="composer-input" placeholder="把你的恋爱难题交给子乔…" maxlength="500" value="${esc(state.demo?advisorDemo.input:state.advisorInput)}"/><button class="send-btn" data-action="send" aria-label="发送消息" ${!state.demo&&advisor.request?'disabled':''}>${ic('send',19)}</button></div>${state.demo?'<p class="disclaimer">示例回复由浏览器生成。<button type="button" class="privacy-link" data-action="exit-advisor-demo">切换到真实对话</button></p>':`<p class="disclaimer">发送后，当前对话将由后端交给 DeepSeek 处理。<button type="button" class="privacy-link" data-action="check-advisor">检查连接</button></p><label id="advisorTokenField" ${advisor.requiresAccessToken?'':'hidden'}>应用访问令牌 <input id="advisorToken" type="password" autocomplete="off" value="${esc(advisor.token)}" /></label>${((state.analysis&&!state.demo)||state.profileSaved)?`<label class="check-row"><input id="advisorContext" type="checkbox" ${advisor.includeContext?'checked':''}/>附带互动统计和档案选项（不含聊天原文、昵称或自由填写内容）</label>`:''}<p id="advisorError" class="disclaimer" role="status">${esc(advisor.error || (advisor.request?'正在等待模型回复…':''))}</p>${state.analysis?'':'<button type="button" class="privacy-link" data-action="sample-advisor">查看示例</button>'}`}</div></div>
      <aside class="v4-advisor-aside"><div class="v4-advisor-head"><span>YOUR AI WINGMAN</span><h2>子乔的<br/><em>聊天锦囊</em></h2><p>“人生没有彩排，每一天都是现场直播。”</p></div><div class="panel"><div class="panel-header"><h2>给你的下一步建议</h2><span class="pill pink">${opts.length} 种表达</span></div>${opts.length?'':'<p class="helper">导入聊天并生成报告后，这里会显示基于报告的建议。</p>'}${opts.map((o,i)=>`<div class="response-card"><div class="response-head"><span class="pill ${i===0?'pink':i===1?'purple':'green'}">${esc(o.tag)}</span><span class="muted">${esc(o.tone)}</span></div><p>“${esc(o.text)}”</p><div class="response-foot"><small>${esc(o.desc)}</small><button class="btn btn-sm btn-white" data-action="copy" data-copy-index="${i}">${ic('copy',13)} 复制</button></div></div>`).join('')}</div></aside></div>
      <div class="v4-pet" aria-label="吕子乔桌宠风格形象"><img src="images/ziqiao-cutout.png" alt="吕子乔桌宠"/><span class="v4-pet-speech">有问题，尽管问我！<small>子乔 · 军师交流</small></span></div>`);
  }
  function modal(){return state.privacyOpen?`<div id="modalBackdrop" role="presentation" style="position:fixed;inset:0;background:#2d2138a9;z-index:200;display:grid;place-items:center;padding:22px"><div role="dialog" aria-modal="true" aria-label="隐私处理说明" style="max-width:540px;width:100%;background:#fff;border-radius:24px;padding:30px;box-shadow:0 25px 70px #241a3455"><div class="panel-header"><h2 style="font-size:20px">${ic('shield',23)} 隐私与数据使用说明</h2><button data-action="close-modal" class="btn btn-sm btn-white" aria-label="关闭">${ic('close',16)}</button></div><p class="helper">互动报告在本地生成。军师交流通过配置好的后端调用 DeepSeek。</p><div class="signal-list"><div class="signal-item"><div class="signal-icon">${ic('check',17)}</div><div><strong>这版确实做到了</strong><p>导入的聊天文本在浏览器内解析。草稿和对话保存在当前页面，刷新后清空。</p></div></div><div class="signal-item"><div class="signal-icon warn">${ic('alert',17)}</div><div><strong>使用 DeepSeek 时</strong><p>在军师交流点击发送后，对话会传给后端及 DeepSeek。勾选后才附带互动统计和档案选项。</p></div></div><div class="signal-item"><div class="signal-icon warn">${ic('lock',17)}</div><div><strong>请先保护聊天双方</strong><p>导入前先脱敏，不上传他人私人信息；只处理你有权使用的记录。任何分数都不是对 TA 心理的确认。</p></div></div></div><button class="btn btn-primary" data-action="close-modal" style="width:100%;margin-top:19px">我了解了</button></div></div>`:'';}
  function changeWizardStep(step){
    const safe=clamp(Number(step)||0,0,2);
    if(state.view!=='profile')return;
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
    $('app').innerHTML=html+modal();
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
    if(state.view==='advisor'&&!state.demo&&advisor.status==='idle')checkAdvisorStatus();
  }
  function loadSample(view='portraits') {
    state.demo=true;
    advisor.includeContext=false;
    advisorDemo.messages=[];
    advisorDemo.input='';
    state.messages=parsedMessages(sampleText);
    state.analysis=analyze(state.messages,'我','小林');
    navigate(view);toast('正在查看虚构示例，导入页草稿已保留');
  }
  function runAnalyze() {
    const msgs=parsedMessages(state.raw);
    if(!state.consent){toast('请先确认隐私和数据使用说明');return;}
    if(msgs.length<4){toast('至少需要 4 条可识别的聊天消息');return;}
    const roles=getRoles(msgs);
    if(!roles.other || !msgs.some(m=>m.speaker===roles.own)||!msgs.some(m=>m.speaker===roles.other)){
      toast('至少需要来自两位不同昵称的消息');return;
    }
    if(msgs.filter(m=>m.speaker===roles.own||m.speaker===roles.other).length<4){toast('有效的双方消息不足 4 条');return;}
    state.demo=false;state.messages=msgs;state.analysis=analyze(msgs);
    navigate('portraits');toast('聊天整理完成：已生成本地互动报告');
  }
  function demoAdvisorReply(question) {
    if(/拒绝|边界|别联系|不愿意/.test(question))return '如果对方明确表达了不愿意，就给对方空间，避免继续追问。';
    if(/不回|没回|已读|冷淡/.test(question))return '没及时回复可能有很多原因。先给对方一点时间，避免连续追问。如果这样的交流节奏经常让你不舒服，可以找合适的时机坦诚聊聊。';
    if(/邀|约|见面|周末/.test(question))return '可以试着给出具体、低压力的邀请，例如「周六我想去看这个展，你有兴趣一起吗？没空也没关系。」';
    return '可以看看对方是否主动开启话题、回应你的问题，或提出下一次见面的安排。把这些当作交流线索，尊重对方明确表达的意愿。';
  }
  async function sendAdvisor(query) {
    const q=(query??$('advisorInput')?.value??'').trim().slice(0,500);if(!q)return;
    if(state.demo){
      advisorDemo.messages=[...advisorDemo.messages,{from:'me',text:q},{from:'bot',text:demoAdvisorReply(q)}];
      if(query===undefined)advisorDemo.input='';
      render();
      return;
    }
    if(advisor.request)return;
    if(advisor.status!=='ready'){toast('请先配置并检查 DeepSeek 后端连接');return;}
    if(advisor.requiresAccessToken&&!advisor.token.trim()){toast('请输入后端提供的应用访问令牌');return;}

    const request=new AbortController();
    const question={from:'me',text:q};
    const messages=[...state.advisorMessages.filter(m=>!m.welcome).slice(-10),question].map(m=>({
      role:m.from==='me'?'user':'assistant',content:m.text.slice(0,2000)
    }));
    const report=advisor.includeContext&&!state.demo?state.analysis:null;
    const profile=advisor.includeContext&&state.profileSaved ? [
      state.profile.stage,state.profile.meStyle,state.profile.taStyle,state.profile.boundaries
    ].filter(Boolean) : [];
    const context=[
      report && `本地统计：共 ${report.total} 条消息，对方提出 ${report.qTa} 个问题；${report.boundaryMsgs.length?'识别到可能的边界表达':'未识别到明确边界表达'}。`,
      profile.length && '用户选择的档案选项：'+profile.join('、')
    ].filter(Boolean).join('\n') || undefined;
    const headers={'Content-Type':'application/json'};
    if(advisor.requiresAccessToken)headers.Authorization='Bearer '+advisor.token.trim();
    advisor.request=request;
    advisor.error='';
    if(query===undefined)state.advisorInput='';
    state.advisorMessages=[...state.advisorMessages,question];
    render();
    try{
      const response=await fetch(advisorBase+'/api/chat',{
        method:'POST',headers,body:JSON.stringify({messages,context}),
        signal:AbortSignal.any([request.signal,AbortSignal.timeout(50000)])
      });
      const result=await response.json();
      if(!response.ok)throw new Error(typeof result.error==='string'?result.error.slice(0,160):'模型服务暂时不可用');
      if(typeof result.reply!=='string'||!result.reply.trim())throw new Error('模型没有返回可显示的回复');
      if(advisor.request===request)state.advisorMessages=[...state.advisorMessages,{from:'bot',text:result.reply}];
    }catch(error){
      if(advisor.request===request){
        advisor.error=error.name==='TimeoutError'?'模型回复超时，请重试。':(error instanceof TypeError?'连接失败，请检查后端后重试。':error.message);
        state.advisorMessages=state.advisorMessages.filter(m=>m!==question);
        if(!state.advisorInput)state.advisorInput=q;
      }
    }finally{
      if(advisor.request===request){
        advisor.request=null;
        if(state.view==='advisor')render();
      }
    }
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
    else if(act==='sample-advisor')loadSample('advisor');
    else if(act==='exit-advisor-demo'){
      state.demo=false;state.analysis=null;state.messages=[];
      navigate('advisor');
    }
    else if(act==='privacy'){state.privacyOpen=true;render();}
    else if(act==='close-modal'){state.privacyOpen=false;render();}
    else if(act==='tab-text'){state.tab='text';render();}
    else if(act==='tab-image'){state.tab='image';render();}
    else if(act==='clear'){state.raw='';state.consent=false;state.demo=false;state.analysis=null;state.messages=[];advisor.includeContext=false;state.tab='text';render();toast('已清空当前文本与结果');}
    else if(act==='analyze')runAnalyze();
    else if(act==='copy'){const ix=Number(el.dataset.copyIndex);const item=strategyOptions()[ix];if(item)copyText(item.text);}
    else if(act==='send')sendAdvisor();
    else if(act==='ask')sendAdvisor(el.dataset.query);
    else if(act==='check-advisor'&&advisor.status!=='checking')checkAdvisorStatus();
    else if(act==='reset-chat'){
      if(state.demo){advisorDemo.messages=[];advisorDemo.input='';render();return;}
      advisor.request?.abort();advisor.request=null;advisor.error='';state.advisorInput='';
      state.advisorMessages=[];render();toast('已重置军师对话');
    }
  });
  document.addEventListener('input',(ev)=>{
    const id=ev.target?.id;
    if(ev.target?.dataset?.eventField){const idx=Number(ev.target.dataset.eventIndex);if(state.profile.eventItems[idx])state.profile.eventItems[idx][ev.target.dataset.eventField]=ev.target.value;return;}
    if(ev.target?.dataset?.profile){state.profile[ev.target.dataset.profile]=ev.target.value;return;}
    if(id==='chatInput'){state.raw=ev.target.value;state.demo=false;state.analysis=null;advisor.includeContext=false;updatePreview();}
    else if(id==='ownName'||id==='otherName'){state[id]=ev.target.value;updatePreview();}
    else if(id==='advisorInput'){
      if(state.demo)advisorDemo.input=ev.target.value;
      else state.advisorInput=ev.target.value;
    }
    else if(id==='advisorToken'){advisor.token=ev.target.value;}
  });
  document.addEventListener('change',(ev)=>{
    const id=ev.target?.id;
    if(ev.target?.dataset?.eventField){const idx=Number(ev.target.dataset.eventIndex);if(state.profile.eventItems[idx])state.profile.eventItems[idx][ev.target.dataset.eventField]=ev.target.value;return;}
    if(ev.target?.dataset?.profile){state.profile[ev.target.dataset.profile]=ev.target.value;return;}
    if(id==='consent')state.consent=ev.target.checked;
    else if(id==='advisorContext')advisor.includeContext=ev.target.checked;
    else if(id==='ownMBTI'||id==='otherMBTI')state[id]=ev.target.value;
    else if(id==='fileInput'&&ev.target.files?.[0]){
      const file=ev.target.files[0];if(file.size>2*1024*1024){toast('为保证浏览器流畅，请上传小于 2 MB 的文件');return;}
      const reader=new FileReader();reader.onload=()=>{state.raw=String(reader.result||'');state.analysis=null;state.demo=false;state.consent=false;advisor.includeContext=false;render();toast(`已读取 ${file.name}，请检查双方昵称`);};
      reader.onerror=()=>toast('读取文件失败，请尝试粘贴文本');reader.readAsText(file,'UTF-8');
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
  navigate(initial||'home');
})();
