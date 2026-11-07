/* UI dashboard normalization. Backend values are mapped by api/adapter.js. */
(function (root) {
  'use strict';
  const clamp=(x,min,max)=>Math.max(min,Math.min(max,x));
  function asPercent(value, unit) {
    if (value == null) return null;
    if (unit !== 'fraction' && unit !== 'percent') throw new Error('Dashboard 指标必须明确 unit=fraction 或 percent');
    if (!Number.isFinite(value) || value < 0) throw new Error('Dashboard 指标必须是非负有限数');
    if (unit === 'fraction' && value > 1) throw new Error('fraction 值必须在 0~1 之间');
    if (unit === 'percent' && value > 100) throw new Error('percent 值必须在 0~100 之间');
    return unit === 'fraction' ? value * 100 : value;
  }
  function normalize(src) {
    if (!src || !src.score || !Array.isArray(src.metrics) || !Array.isArray(src.chart)) throw new Error('缺少 Dashboard 所需数据');
    const score=asPercent(src.score.value == null ? null : Number(src.score.value),src.score.unit);
    const metrics=src.metrics.map(m=>{
      const value=m.value == null ? null : Number(m.value);
      return {id:String(m.id),name:String(m.name),color:['pink','violet','orange','green'].includes(m.color)?m.color:'pink',val:asPercent(value,m.unit),available:value!=null && Number.isFinite(value)};
    });
    const chart=src.chart.map(c=>({label:String(c.label),count:Math.max(0, Number(c.count)||0),self:Number(c.self)||0,other:Number(c.other)||0,unknown:Number(c.unknown)||0}));
    const summary=src.summary || {};
    const otherShare=summary.otherShare==null?null:(typeof summary.otherShare==='object'?asPercent(Number(summary.otherShare.value),summary.otherShare.unit||'percent'):Number(summary.otherShare));
    const questionRatio=summary.otherQuestionRatio==null?null:Number(summary.otherQuestionRatio);
    const signals=Array.isArray(src.signals)?src.signals.map(s=>({
      type:['good','warn','red'].includes(s.type)?s.type:'warn',
      category:s.category||'ambiguous',title:String(s.title||''),desc:String(s.desc||''),
      quote:s.quote == null?null:String(s.quote),evidenceIds:Array.isArray(s.evidenceIds)?s.evidenceIds:[],
      evidenceStrength:s.evidenceStrength||'medium',scope:s.scope||'',impact:s.impact||''
    })):[];
    return {
      score,metrics,chart,signals,
      summary:{total:Number(summary.total)||0,selfCount:Number(summary.selfCount)||0,otherCount:Number(summary.otherCount)||0,unknownCount:Number(summary.unknownCount)||0,otherShare,otherQuestionRatio:questionRatio,qTa:summary.qTa==null?null:Number(summary.qTa)},
      source:src.source||'demo',disclaimer:src.disclaimer||'',semanticDetection:src.semanticDetection||null,
      dataQuality:src.dataQuality||null,limitations:Array.isArray(src.limitations)?src.limitations:[],
      relationshipAssessment:src.relationshipAssessment||null,evidence:src.evidence||{},portraits:src.portraits||null,
      statistics:src.statistics||null,status:src.status||'completed'
    };
  }
  function localFromAnalysis(a, signals) {
    const known=a.self.length+a.ta.length;
    const other=a.ta.length;
    return normalize({
      score:{value:a.score,unit:'percent'},
      metrics:[
        {id:'balance',name:'双方消息参与平衡',value:known?1-Math.abs(a.self.length-other)/known:0,unit:'fraction',color:'pink'},
        {id:'questions',name:'TA 在消息中的提问占比',value:other?a.qTa/other:0,unit:'fraction',color:'violet'},
        {id:'activities',name:'双方共同活动表达占比',value:known?a.invitation.length/known:0,unit:'fraction',color:'orange'},
        {id:'warm',name:'双方积极语气表达占比',value:known?a.warmMsgs.length/known:0,unit:'fraction',color:'green'}
      ],
      summary:{total:a.total,selfCount:a.self.length,otherCount:a.ta.length,unknownCount:a.unknown.length,otherShare:a.total?100*other/a.total:null,otherQuestionRatio:other?a.qTa/other:null,qTa:a.qTa},
      chart:a.chunks.map(c=>({label:c.label,count:c.count})),signals:signals||[],source:'local-demo',
      disclaimer:'本地演示规则仅用于展示，不是 AI 分析，也不代表真实好感概率。'
    });
  }
  root.HeartSignalDashboard=Object.freeze({normalize,asPercent,localFromAnalysis});
})(window);
