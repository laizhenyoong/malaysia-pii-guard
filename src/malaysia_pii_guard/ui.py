"""A local web UI for trying the library out.

Serves one page and a small JSON endpoint that runs the real engines, so what
the page shows is what the library does, not a re-implementation of it.
"""

import argparse
import json
import platform
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from malaysia_pii_guard.analyzer import AnalyzerEngine
from malaysia_pii_guard.anonymizer import AnonymizerEngine, resolve

PAGE = Path(__file__).with_name("ui.html")

# One text is one request, so a whole page of it is already generous.
MAX_TEXT_BYTES = 200_000

_analyzer = AnalyzerEngine()
_anonymizer = AnonymizerEngine()


def _version() -> str:
    """The installed version, or a marker when running from a source tree."""
    try:
        from importlib.metadata import version

        return version("malaysia-pii-guard")
    except Exception:
        return "source"


def meta() -> Dict[str, Any]:
    """What engine the page is talking to."""
    return {"version": _version(), "python": platform.python_version()}


def run(text: str, threshold: float = 0.4) -> Dict[str, Any]:
    """Analyze and mask one text the way a caller would."""
    findings = _analyzer.analyze(text, score_threshold=threshold)
    result = _anonymizer.anonymize(text, findings)

    # anonymize walks resolve() in order, so the nth item is the nth span.
    spans = resolve(findings)
    detections: List[Dict[str, Any]] = [
        {
            "entity": item.entity_type,
            "label": item.label,
            "original": item.original,
            "score": round(span.score, 2),
            "start": span.start,
            "end": span.end,
        }
        for item, span in zip(result.items, spans)
    ]

    return {"masked": result.text, "detections": detections}


class Handler(BaseHTTPRequestHandler):
    """Serves the page, the engine metadata, and one analyze call per request."""

    server_version = "malaysia-pii-guard"
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet: the console shows the URL, not every request for it."""

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        self._send(
            status,
            json.dumps(payload).encode(),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802 - the name BaseHTTPRequestHandler calls
        """The page itself, or what the page asks about the engine."""
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/meta":
            self._send_json(200, meta())
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - the name BaseHTTPRequestHandler calls
        """Run one text through the engines."""
        if self.path.split("?", 1)[0] != "/api/analyze":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_TEXT_BYTES:
            self._send_json(413, {"error": "text too long"})
            return

        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            result = run(payload.get("text", ""), float(payload.get("threshold", 0.4)))
        except (TypeError, ValueError) as error:
            self._send_json(400, {"error": str(error)})
            return
        self._send_json(200, result)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    """Serve the UI until interrupted."""
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_address[1]}/"

    info = meta()
    print(f"malaysia-pii-guard {info['version']} on Python {info['python']}")
    print(f"UI at {url}  (ctrl-c to stop)", flush=True)

    if open_browser:
        threading.Timer(0.4, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point: `python -m malaysia_pii_guard`."""
    parser = argparse.ArgumentParser(
        prog="malaysia-pii-guard",
        description="Start a local web UI for testing the library.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="default: 127.0.0.1")
    parser.add_argument(
        "--port", type=int, default=8765, help="default: 8765, 0 picks a free one"
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="do not open a browser"
    )
    args = parser.parse_args(argv)

    try:
        serve(args.host, args.port, not args.no_browser)
    except OSError as error:
        print(f"cannot serve on {args.host}:{args.port}: {error}", file=sys.stderr)
        return 1
    return 0
