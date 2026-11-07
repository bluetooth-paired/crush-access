/* Small fetch client for the FastAPI backend. No model secrets belong in this file. */
(function (root) {
  'use strict';
  class ApiError extends Error {
    constructor(message, kind, status, details, code) {
      super(message);
      this.name = 'ApiError';
      this.kind = kind || 'unknown';
      this.status = status == null ? null : status;
      this.details = details || null;
      this.code = code || details?.error?.code || null;
    }
  }
  function settings() {
    const c = root.HeartSignalAPIConfig || {};
    return {
      baseUrl: String(c.baseUrl || '').trim().replace(/\/+$/, ''),
      timeoutMs: Math.max(500, Number(c.timeoutMs) || 90000),
      enabled: c.enabled === true
    };
  }
  async function request(method, path, body) {
    const c = settings();
    if (!c.enabled || !c.baseUrl) throw new ApiError('真实 API 尚未配置：请先在 api/config.js 填写后端 HTTPS Base URL。', 'unconfigured');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), c.timeoutMs);
    try {
      const headers = { 'Accept': 'application/json' };
      if (body !== undefined) headers['Content-Type'] = 'application/json';
      const clientId = body && typeof body.client_id === 'string' ? body.client_id : '';
      if (clientId) headers['X-Client-Id'] = clientId;
      const response = await fetch(c.baseUrl + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
        credentials: 'omit'
      });
      const raw = await response.text();
      let payload;
      try { payload = raw ? JSON.parse(raw) : null; }
      catch { throw new ApiError('服务器响应不是合法 JSON。', 'response', response.status); }
      if (!response.ok) {
        const error = payload?.error || {};
        throw new ApiError(error.message || `请求失败：HTTP ${response.status}`, 'http', response.status, payload, error.code);
      }
      return payload;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      if (err && err.name === 'AbortError') throw new ApiError('请求超时，请稍后重试。', 'timeout');
      throw new ApiError('无法连接服务，请检查网络、后端地址及 CORS 配置。', 'network');
    } finally { clearTimeout(timer); }
  }
  root.HeartSignalAPI = Object.freeze({
    ApiError,
    config: settings,
    health: () => request('GET', '/health'),
    analyze: (payload) => request('POST', '/api/v1/analyze', payload),
    advisorChat: (payload) => request('POST', '/api/v1/advisor/chat', payload)
  });
})(window);
