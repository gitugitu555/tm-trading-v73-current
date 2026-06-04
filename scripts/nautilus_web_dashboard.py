#!/usr/bin/env python3
"""Small local web dashboard for Nautilus BTC catalog and backtest links."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CATALOG = ROOT / "data" / "nautilus" / "catalogs" / "btcusdt_trade_ticks_6y"
HTML_CHART = RESULTS / "nautilus_btcusdt_trade_ticks_demo.html"
HTML_6Y = RESULTS / "nautilus_btcusdt_trade_ticks_6y.html"
OFFICIAL_TEARSHEET = RESULTS / "nautilus_chunkb_backtest_official.html"
SUMMARY = RESULTS / "nautilus_btcusdt_trade_ticks_demo.json"
BACKTEST_SMOKE = RESULTS / "nautilus_chunkb_backtest_smoke.json"
PLOTLY_HOME = "https://plotly.com/"
DEFAULT_PORT = 9091
PORT = DEFAULT_PORT
TAILNET_URL = "https://couricocloud.tail60f516.ts.net/chat?session=agent%3Ajarvis%3Amain"
PUBLIC_PREFIX = "/chat"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT_SCAN = 12


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/chat"}:
            if HTML_CHART.exists():
                self._serve_file(HTML_CHART)
            else:
                self._send_html(render_chat_page(TAILNET_URL))
            return
        if path in {"/favicon.ico", "/chat/favicon.ico"}:
            self.send_response(204)
            self.end_headers()
            return
        if path in {"/robots.txt", "/chat/robots.txt"}:
            self._send_html("User-agent: *\nDisallow: /\n")
            return
        if path in {"/status", "/chat/status"}:
            self._send_json(render_status(TAILNET_URL))
            return
        if path in {"/plotly", "/chat/plotly"}:
            self._serve_file(HTML_CHART)
            return
        if path in {"/tearsheet", "/chat/tearsheet"}:
            self._serve_file(OFFICIAL_TEARSHEET)
            return
        if path in {"/chart", "/chat/chart"}:
            self._serve_file(HTML_CHART)
            return
        if path in {"/chart-6y", "/chat/chart-6y"}:
            self._serve_file(HTML_6Y)
            return
        if path in {"/summary", "/chat/summary"}:
            self._serve_file(SUMMARY)
            return
        if path in {"/backtest-smoke", "/chat/backtest-smoke"}:
            self._serve_file(BACKTEST_SMOKE)
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_html(self, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, path: Path) -> None:
        if not path.exists():
            self.send_error(404, f"Missing file: {path}")
            return
        data = path.read_bytes()
        content_type = "text/html; charset=utf-8" if path.suffix == ".html" else "application/json; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def render_chat_page(tailnet_url: str) -> str:
    chart_href = f"{PUBLIC_PREFIX}/chart"
    status_href = f"{PUBLIC_PREFIX}/status"
    chart6y_exists = HTML_6Y.exists()
    chart6y_href = f"{PUBLIC_PREFIX}/chart-6y" if chart6y_exists else "#"
    summary_href = f"{PUBLIC_PREFIX}/summary"
    smoke_href = f"{PUBLIC_PREFIX}/backtest-smoke"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Nautilus BTC Chat</title>
  <style>
    :root {{
      --bg: #07111a;
      --panel: rgba(10, 18, 29, 0.92);
      --panel-2: rgba(17, 29, 45, 0.92);
      --text: #e8eef6;
      --muted: #90a4b8;
      --accent: #4fd1c5;
      --line: rgba(255,255,255,0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(79, 209, 197, 0.14), transparent 28%),
        radial-gradient(circle at top right, rgba(59, 130, 246, 0.16), transparent 24%),
        linear-gradient(180deg, #07111a 0%, #091420 100%);
      color: var(--text);
      min-height: 100vh;
    }}
    .wrap {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 18px;
      align-items: stretch;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 20px 80px rgba(0, 0, 0, 0.32);
      backdrop-filter: blur(10px);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(30px, 4vw, 54px);
      letter-spacing: -0.03em;
      line-height: 1.02;
    }}
    .sub {{
      color: var(--muted);
      font-size: 15px;
      line-height: 1.6;
      margin: 0 0 16px;
    }}
    .badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255,255,255,0.05);
      border: 1px solid var(--line);
      color: var(--text);
      text-decoration: none;
      font-size: 13px;
    }}
    .badge:hover {{ border-color: rgba(79, 209, 197, 0.65); }}
    .grid {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 18px;
      margin-top: 18px;
    }}
    .stat {{
      display: grid;
      gap: 8px;
      padding: 16px 0;
      border-top: 1px solid var(--line);
    }}
    .stat:first-child {{ border-top: 0; padding-top: 0; }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em; }}
    .value {{ font-size: 18px; }}
    iframe {{
      width: 100%;
      height: 80vh;
      min-height: 760px;
      border: 0;
      border-radius: 18px;
      background: white;
    }}
    .panel-2 {{ background: var(--panel-2); }}
    .hint {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      margin-top: 12px;
    }}
    @media (max-width: 1100px) {{
      .hero, .grid {{ grid-template-columns: 1fr; }}
      iframe {{ height: 70vh; min-height: 620px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <section class="card">
        <h1>Nautilus BTC / Chat</h1>
        <p class="sub">
          Live tailnet access to the imported BTCUSDT catalog and the catalog-backed Chunk B smoke result.
          Use this page to inspect the chart and jump to the raw status pages.
        </p>
        <div class="badges">
          <a class="badge" href="{chart_href}" target="_blank" rel="noreferrer">Open chart</a>
          <a class="badge" href="{chart6y_href}" target="_blank" rel="noreferrer" aria-disabled="{str(not chart6y_exists).lower()}">6y chart</a>
          <a class="badge" href="{status_href}" target="_blank" rel="noreferrer">Status JSON</a>
          <a class="badge" href="{smoke_href}" target="_blank" rel="noreferrer">Backtest smoke</a>
          <a class="badge" href="{summary_href}" target="_blank" rel="noreferrer">Summary JSON</a>
        </div>
      </section>
      <section class="card panel-2">
        <div class="stat">
          <div class="label">Catalog</div>
          <div class="value">{CATALOG}</div>
        </div>
        <div class="stat">
          <div class="label">Chart</div>
          <div class="value">/chart</div>
        </div>
        <div class="stat">
          <div class="label">Tailnet URL</div>
          <div class="value">{tailnet_url}</div>
        </div>
        <div class="hint">
          The tailnet endpoint proxies to this local dashboard. The full 6-year chart will appear here once it is generated.
        </div>
      </section>
    </div>
    <div class="grid">
      <section class="card">
        <div class="label">Quick status</div>
        <iframe src="{status_href}"></iframe>
      </section>
      <section class="card">
        <div class="label">BTC chart</div>
        <iframe src="{chart_href}"></iframe>
      </section>
    </div>
  </div>
</body>
</html>"""
    return html


def render_status(tailnet_url: str) -> dict:
    return {
        "catalog": str(CATALOG),
        "catalog_exists": CATALOG.exists(),
        "official_tearsheet": str(OFFICIAL_TEARSHEET),
        "official_tearsheet_exists": OFFICIAL_TEARSHEET.exists(),
        "plotly_home": PLOTLY_HOME,
        "plotly_chart": f"{PUBLIC_PREFIX}/plotly",
        "plotly_tearsheet": f"{PUBLIC_PREFIX}/tearsheet",
        "plotly_js_embedded": html_contains_plotly(HTML_CHART),
        "chart": str(HTML_CHART),
        "chart_exists": HTML_CHART.exists(),
        "chart_6y": str(HTML_6Y),
        "chart_6y_exists": HTML_6Y.exists(),
        "backtest_smoke": str(BACKTEST_SMOKE),
        "backtest_smoke_exists": BACKTEST_SMOKE.exists(),
        "tailnet": tailnet_url,
    }


def html_contains_plotly(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8", errors="ignore") as file:
        return "plotly.js" in file.read(64_000).lower()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("legacy_port", nargs="?", type=int)
    parser.add_argument("legacy_tailnet_url", nargs="?")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", dest="port_option", type=int)
    parser.add_argument("--tailnet-url", dest="tailnet_url_option")
    parser.add_argument(
        "--port-scan",
        type=int,
        default=DEFAULT_PORT_SCAN,
        help="How many sequential ports to try if the requested port is unavailable.",
    )
    return parser.parse_args()


def iter_candidate_ports(port: int, scan_count: int) -> list[int]:
    if port <= 0:
        return [0]
    ports = [port]
    for offset in range(1, max(scan_count, 1)):
        ports.append(port + offset)
    return ports


def bind_server(host: str, port: int, scan_count: int) -> tuple[ReusableThreadingHTTPServer, int]:
    last_error: OSError | None = None
    for candidate in iter_candidate_ports(port, scan_count):
        try:
            server = ReusableThreadingHTTPServer((host, candidate), DashboardHandler)
        except OSError as exc:
            last_error = exc
            continue
        actual_port = server.server_address[1]
        return server, actual_port
    if last_error is not None:
        raise last_error
    raise OSError("unable to bind dashboard server")


def main() -> int:
    global PORT, TAILNET_URL
    args = parse_args()
    requested_port = args.port_option
    if requested_port is None:
        requested_port = args.legacy_port if args.legacy_port is not None else DEFAULT_PORT
    TAILNET_URL = (
        args.tailnet_url_option
        if args.tailnet_url_option is not None
        else args.legacy_tailnet_url
        if args.legacy_tailnet_url is not None
        else "https://couricocloud.tail60f516.ts.net/chat?session=agent%3Ajarvis%3Amain"
    )
    PORT = requested_port
    server, actual_port = bind_server(args.host, requested_port, args.port_scan)
    PORT = actual_port
    print(f"serving on http://{args.host}:{actual_port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
