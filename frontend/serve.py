"""SPA fallback static server with API proxy for production."""
import http.server
import os
import sys
import requests

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIR = sys.argv[2] if len(sys.argv) > 2 else "dist"
API_TARGET = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"


class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def _proxy_api(self):
        """Proxy /api/* requests to the backend using requests library."""
        target_url = API_TARGET.rstrip("/") + self.path

        body = None
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)

        try:
            resp = requests.request(
                method=self.command,
                url=target_url,
                data=body,
                headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
                timeout=30,
            )

            self.send_response(resp.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.content)
        except requests.ConnectionError:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"detail":"Backend service unavailable"}')
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"detail":"Proxy error: {str(e)}"}}'.encode())

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy_api()

        path = self.translate_path(self.path)
        if not os.path.exists(path) or os.path.isdir(path):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._proxy_api()
        return super().do_POST()

    def do_PUT(self):
        if self.path.startswith("/api/"):
            return self._proxy_api()
        return super().do_PUT()

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            return self._proxy_api()
        return super().do_DELETE()


httpd = http.server.HTTPServer(("0.0.0.0", PORT), ProxyHandler)
print(f"Serving {DIR} on 0.0.0.0:{PORT} (API proxy → {API_TARGET})")
httpd.serve_forever()
