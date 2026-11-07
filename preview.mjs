import { createServer, request } from 'node:http';
import { readFile } from 'node:fs/promises';

const host = '127.0.0.1';
const port = 8789;
const origin = `http://${host}:${port}`;
const routes = new Map([
  ['/health', 'GET'],
  ['/api/v1/analyze', 'POST'],
  ['/api/v1/advisor/chat', 'POST'],
]);
const mime = { html: 'text/html', js: 'text/javascript', css: 'text/css', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', svg: 'image/svg+xml' };

function proxy(req, res, path) {
  if (req.method !== routes.get(path)) return res.writeHead(405).end();
  if (req.headers.origin && req.headers.origin !== origin) return res.writeHead(403).end();
  const headers = {};
  for (const key of ['content-type', 'content-length', 'x-client-id', 'authorization']) {
    if (req.headers[key]) headers[key] = req.headers[key];
  }
  const upstream = request({ hostname: host, port: 8010, path, method: req.method, headers }, reply => {
    res.writeHead(reply.statusCode, {
      'content-type': reply.headers['content-type'] || 'application/json',
      'cache-control': 'no-store',
    });
    reply.pipe(res);
  });
  upstream.setTimeout(95000, () => upstream.destroy());
  upstream.on('error', () => {
    if (res.headersSent) return res.destroy();
    res.writeHead(502, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: { code: 'PREVIEW_BACKEND_UNAVAILABLE', message: 'Local preview backend is unavailable.' } }));
  });
  res.on('close', () => upstream.destroy());
  req.on('error', () => upstream.destroy());
  req.pipe(upstream);
}

const server = createServer(async (req, res) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  if (req.headers.host !== `${host}:${port}`) return res.writeHead(403).end();
  const path = req.url.split('?')[0];
  if (routes.has(path)) return proxy(req, res, path);
  if (req.method !== 'GET') return res.writeHead(405).end();
  const asset = path === '/' ? '/index.html' : path;
  const ext = asset.split('.').pop();
  if (!mime[ext] || !/^\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.[a-z]+$/.test(asset)) {
    return res.writeHead(404).end();
  }
  try {
    const bytes = await readFile(new URL('./frontend' + asset, import.meta.url));
    res.writeHead(200, { 'content-type': mime[ext] + (['html', 'js', 'css'].includes(ext) ? '; charset=utf-8' : ''), 'cache-control': 'no-store' });
    res.end(bytes);
  } catch {
    res.writeHead(404).end();
  }
});
server.listen(port, host, () => console.log(`Preview ready at ${origin}/`));
