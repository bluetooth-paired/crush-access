/* Adapter for Wenqing's crush-access-agent-backend v1 API contract.
 * Keep backend field names here; UI components consume a normalized dashboard model.
 */
(function (root) {
  'use strict';

  function asEvidenceMap(raw) {
    if (Array.isArray(raw)) return Object.fromEntries(raw.filter(x => x && x.id).map(x => [String(x.id), x]));
    return raw && typeof raw === 'object' ? raw : {};
  }

  function toDashboard(report) {
    const metrics = report.metrics || {};
    const counts = metrics.message_counts || {};
    const total = Number(counts.total ?? report.data_quality?.total_messages ?? 0);
    const selfCount = Number(counts.self ?? counts.self_count ?? 0);
    const otherCount = Number(counts.other ?? counts.other_count ?? 0);
    const unknownCount = Number(counts.unknown ?? counts.unknown_count ?? 0);
    const evidence = asEvidenceMap(report.evidence);
    const ratio = (value) => value == null ? null : Number(value);
    const signals = (Array.isArray(report.signals) ? report.signals : []).map((signal) => {
      const ids = Array.isArray(signal.evidence_ids) ? signal.evidence_ids.map(String) : [];
      const firstEvidence = ids.map(id => evidence[id]).find(Boolean);
      const interpretations = [
        signal.positive_interpretation ? `一种积极解释：${signal.positive_interpretation}` : '',
        signal.alternative_interpretation ? `其他可能：${signal.alternative_interpretation}` : ''
      ].filter(Boolean).join('；');
      const category = signal.category || 'ambiguous';
      return {
        type: category === 'positive' ? 'good' : category === 'negative' ? 'red' : 'warn',
        category,
        title: String(signal.name || '互动观察'),
        desc: [signal.description, interpretations].filter(Boolean).join('。'),
        quote: firstEvidence?.content == null ? null : String(firstEvidence.content),
        evidenceIds: ids,
        evidenceStrength: signal.evidence_strength || 'medium',
        scope: signal.scope || '',
        impact: signal.impact || ''
      };
    });
    const daily = Array.isArray(report.daily_distribution) ? report.daily_distribution : [];
    const dailyChart = daily.map(point => ({
      label: String(point.date || ''),
      count: Number(point.total ?? ((point.self || 0) + (point.other || 0) + (point.unknown || 0))),
      self: Number(point.self ?? point.self_count ?? 0),
      other: Number(point.other ?? point.other_count ?? 0),
      unknown: Number(point.unknown ?? point.unknown_count ?? 0)
    }));
    const otherShare = total > 0 ? (otherCount / total) * 100 : null;
    return {
      score: { value: ratio(metrics.interaction_index), unit: 'percent' },
      metrics: [
        { id: 'balance', name: '双方消息参与平衡', value: ratio(metrics.participation_balance), unit: 'fraction', color: 'pink' },
        { id: 'questions', name: 'TA 提问占比', value: ratio(metrics.other_question_ratio), unit: 'fraction', color: 'violet' },
        { id: 'activities', name: '双方共同活动表达占比', value: ratio(metrics.shared_activity_ratio), unit: 'fraction', color: 'orange' },
        { id: 'warm', name: '双方积极语气表达占比', value: ratio(metrics.positive_tone_ratio), unit: 'fraction', color: 'green' }
      ],
      summary: {
        total,
        selfCount,
        otherCount,
        unknownCount,
        otherShare,
        otherQuestionRatio: ratio(metrics.other_question_ratio)
      },
      chart: dailyChart,
      signals,
      source: 'agent-api',
      disclaimer: metrics.disclaimer || '互动参考指数是启发式参考值，不代表真实好感概率。',
      semanticDetection: metrics.semantic_detection || null,
      dataQuality: report.data_quality || null,
      limitations: Array.isArray(report.limitations) ? report.limitations : [],
      relationshipAssessment: report.relationship_assessment || null,
      evidence,
      portraits: report.portraits || null,
      statistics: report.statistics || null,
      status: report.status || 'completed'
    };
  }

  root.HeartSignalAPIAdapter = Object.freeze({
    ready: true,
    buildAnalyzeRequest({ chatDocument, identities, profile, clientId, thinkingLevel = 'auto' }) {
      if (!chatDocument || !Array.isArray(chatDocument.messages)) throw new Error('缺少有效的 chat.json conversation');
      const userProfile = profile && typeof profile === 'object' ? {
        self: { nickname: identities?.self || '我' },
        other: { nickname: identities?.other || 'TA' },
        user_supplied_profile: profile
      } : {
        self: { nickname: identities?.self || '我' },
        other: { nickname: identities?.other || 'TA' }
      };
      return {
        conversation: chatDocument,
        profile: userProfile,
        client_id: clientId,
        options: { include_advice: true, include_evidence: true, thinking_level: thinkingLevel }
      };
    },
    readAnalyzeResponse(response) {
      if (!response || typeof response !== 'object') throw new Error('分析接口返回内容为空');
      const status = response.status || 'completed';
      if (status === 'failed') {
        const detail = (response.errors || []).map(x => x.message || x.code).filter(Boolean).join('；');
        throw new Error(detail || '后端分析失败，请检查模型配置或稍后重试');
      }
      if (!['completed','partial'].includes(status)) throw new Error(`分析响应状态不可展示：${String(status)}`);
      if (typeof response.analysis_id !== 'string' || !response.analysis_id.trim()) throw new Error('分析响应缺少 analysis_id');
      if (typeof response.client_id !== 'string' || !response.client_id.trim()) throw new Error('分析响应缺少 client_id');
      if (!response.metrics || typeof response.metrics !== 'object' || Array.isArray(response.metrics)) throw new Error('分析响应缺少 metrics');
      if (!response.metrics.message_counts || typeof response.metrics.message_counts !== 'object') throw new Error('分析响应缺少 message_counts');
      if (!Object.prototype.hasOwnProperty.call(response.metrics,'interaction_index')) throw new Error('分析响应缺少 interaction_index');
      const dashboard = toDashboard(response);
      return {
        analysisId: response.analysis_id,
        clientId: response.client_id,
        status,
        dashboard,
        report: response,
        suggestions: Array.isArray(response.advisor?.suggestions) ? response.advisor.suggestions : []
      };
    },
    buildAdvisorRequest({ question, analysisId, sessionId, clientId, thinkingLevel = 'auto', webSearch = false }) {
      if (!analysisId) throw new Error('缺少 analysis_id');
      if (!clientId) throw new Error('缺少 client_id');
      return {
        analysis_id: analysisId,
        session_id: sessionId || null,
        message: String(question || '').trim(),
        client_id: clientId,
        thinking_level: thinkingLevel,
        web_search: Boolean(webSearch)
      };
    },
    readAdvisorResponse(response) {
      if (!response || typeof response !== 'object') throw new Error('军师接口返回内容为空');
      if (typeof response.reply !== 'string' || !response.reply.trim()) throw new Error('军师响应缺少有效 reply');
      if (typeof response.session_id !== 'string' || !response.session_id) throw new Error('军师响应缺少 session_id');
      return {
        reply: response.reply,
        sessionId: response.session_id,
        turn: Number(response.turn) || null,
        evidenceIds: Array.isArray(response.evidence_ids) ? response.evidence_ids : [],
        evidence: Array.isArray(response.evidence) ? response.evidence : [],
        suggestions: Array.isArray(response.suggestions) ? response.suggestions : [],
        boundaryNotes: Array.isArray(response.boundary_notes) ? response.boundary_notes : [],
        aiConfig: response.ai_config || null
      };
    }
  });
})(window);
