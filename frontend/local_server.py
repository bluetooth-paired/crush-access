"""Local-only static preview launcher. No backend or remote server required."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
HOST = '127.0.0.1'
ASSET = re.compile(r'/(?:api/|images/|mocks/)?[a-zA-Z0-9_-]+\.(?:html|css|js|jpe?g|png)')


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        if self.headers.get('Host') != f'{HOST}:{self.server.server_port}':
            self.send_error(403)
            return None
        path = self.path.partition('?')[0]
        if path != '/' and not ASSET.fullmatch(path):
            self.send_error(404)
            return None
        if path == '/':
            self.path = '/index.html'
        return super().send_head()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, 0), partial(Handler, directory=str(ROOT)))
    url = f'http://{HOST}:{server.server_port}/index.html'
    print('Crush Access - 本地演示网页')
    print('浏览器地址：', url)
    print('演示模式使用虚构数据，不连接 Coze 或正式 AI 后端。')
    print('关闭此窗口或按 Ctrl+C 可停止本地服务。')
    browser = threading.Timer(0.8, webbrowser.open, args=(url,))
    browser.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        browser.cancel()
        server.server_close()
