"""Loopback-only review server; no arbitrary file access or remote assets."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import secrets
import threading
from urllib.parse import urlsplit, unquote
from .project import open_report, contained, csv_text, table_rows, canonical, digest
from .state import ReviewState, ConflictError


class ReviewServer:
    def __init__(self, root, port=0):
        self.report = open_report(root, verify_assets=True)
        self.state = ReviewState(self.report)
        self.token = secrets.token_urlsafe(32)
        owner = self
        assets = Path(__file__).parent / "assets"
        allowed = {
            "/": assets / "index.html",
            "/index.html": assets / "index.html",
            "/app.js": assets / "app.js",
            "/style.css": assets / "style.css",
        }
        hashes = {}
        for row in self.report.data["stimuli"]:
            for key in ("before_image", "after_image", "thumbnail"):
                url = "/" + row[key]
                allowed[url] = contained(self.report.root, row[key])
                hashes[url] = row["asset_sha256"][key]

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(
                self,
                status,
                body,
                kind="application/json; charset=utf-8",
                attachment=None,
            ):
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
                )
                if attachment:
                    self.send_header(
                        "Content-Disposition", f'attachment; filename="{attachment}"'
                    )
                self.end_headers()
                self.wfile.write(body)

            def valid_host(self):
                return (
                    self.headers.get("Host") == f"127.0.0.1:{owner.server.server_port}"
                )

            def error(self, status, message):
                self.send(status, canonical({"error": message}))

            def do_GET(self):
                if not self.valid_host():
                    return self.error(403, "Unexpected host")
                url = unquote(urlsplit(self.path).path)
                try:
                    if url == "/api/session":
                        return self.send(
                            200,
                            canonical(
                                {
                                    "token": owner.token,
                                    "report": owner.report.data,
                                    "review": owner.state.snapshot(),
                                }
                            ),
                        )
                    if url == "/api/export.json":
                        return self.send(
                            200,
                            canonical(
                                {
                                    "report": owner.report.data,
                                    "review": owner.state.snapshot(),
                                }
                            ),
                            attachment="shine_review.json",
                        )
                    if url == "/api/export.csv":
                        data = csv_text(
                            table_rows(owner.report.data, owner.state.snapshot())
                        )
                        return self.send(
                            200,
                            ("\ufeff" + data).encode("utf-8"),
                            "text/csv; charset=utf-8",
                            "shine_review.csv",
                        )
                    if url not in allowed:
                        return self.error(404, "Not found")
                    p = allowed[url]
                    if url in hashes and not p.resolve().is_relative_to(
                        owner.report.root
                    ):
                        return self.error(403, "Image path escaped project")
                    data = p.read_bytes()
                    if url in hashes and digest(data) != hashes[url]:
                        return self.error(
                            409, "Review image changed; rebuild from verified inputs"
                        )
                    # Windows registry MIME associations can label .js text/plain.
                    kind = {
                        ".html": "text/html; charset=utf-8",
                        ".js": "text/javascript; charset=utf-8",
                        ".css": "text/css; charset=utf-8",
                        ".png": "image/png",
                    }
                    self.send(
                        200,
                        data,
                        kind.get(p.suffix.lower(), "application/octet-stream"),
                    )
                except (OSError, ValueError):
                    self.error(409, "Review asset unavailable or invalid")

            def do_POST(self):
                if (
                    not self.valid_host()
                    or self.headers.get("Origin") != owner.origin
                    or self.headers.get("X-Review-Token") != owner.token
                ):
                    return self.error(403, "Invalid local review session")
                if self.path != "/api/decision":
                    return self.error(404, "Not found")
                if (
                    self.headers.get("Content-Type", "").split(";")[0]
                    != "application/json"
                ):
                    return self.error(415, "JSON required")
                try:
                    n = int(self.headers.get("Content-Length", "0"))
                    if not 0 < n <= 100000:
                        return self.error(413, "Invalid request size")
                    value = json.loads(self.rfile.read(n))
                    result = owner.state.save(value)
                    self.send(200, canonical(result))
                except ConflictError as e:
                    self.error(409, str(e))
                except (ValueError, KeyError, TypeError, UnicodeError):
                    self.error(400, "Invalid decision")
                except Exception:
                    self.error(
                        500,
                        "Decision was not saved; retry after checking local storage",
                    )

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.url = self.origin + "/"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
