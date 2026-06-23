"""PC Scout AI server: zero-dependency HTTP API plus static frontend."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import posixpath
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from ai_service import GroqAIService
from sample_data import SAMPLE_PRODUCTS
from scraper import SeleniumScraper, TARGETS

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
ai_service = GroqAIService()
scraper = SeleniumScraper()


def filtered_products(params: dict[str, list[str]], products: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    items = list(products or SAMPLE_PRODUCTS)
    query = params.get("q", [""])[0].strip().lower()
    category = params.get("category", [""])[0]
    part_type = params.get("part_type", [""])[0]
    brand = params.get("brand", [""])[0].lower()
    condition = params.get("condition", [""])[0]
    exclude = [word.strip().lower() for word in params.get("exclude", [""])[0].split(",") if word.strip()]
    try:
        price_min = int(params.get("price_min", ["0"])[0] or 0)
        price_max = int(params.get("price_max", ["999999999"])[0] or 999999999)
    except ValueError:
        price_min, price_max = 0, 999999999

    def searchable(item: dict[str, Any]) -> str:
        return " ".join([item.get("title", ""), item.get("source", ""), json.dumps(item.get("specs", {}), ensure_ascii=False)]).lower()

    result = []
    for item in items:
        haystack = searchable(item)
        if query and query not in haystack:
            continue
        if category and category != "すべて" and item.get("category") != category:
            continue
        if part_type and item.get("part_type") != part_type:
            continue
        if brand and brand not in haystack:
            continue
        if condition and item.get("condition") != condition:
            continue
        if any(word in haystack for word in exclude):
            continue
        if not price_min <= int(item.get("price", 0)) <= price_max:
            continue
        result.append(item)
    return result


class AppHandler(BaseHTTPRequestHandler):
    server_version = "PCScout/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self.send_json({"ok": True, "groq": ai_service.enabled, "live_scraping": scraper.enabled})
        if parsed.path == "/api/config":
            return self.send_json({
                "groq_enabled": ai_service.enabled,
                "live_scraping_enabled": scraper.enabled,
                "sources": [target.name for target in TARGETS],
            })
        if parsed.path == "/api/products":
            items = filtered_products(parse_qs(parsed.query, keep_blank_values=True))
            return self.send_json({"items": items, "total": len(items), "mode": "demo"})
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        try:
            body = self.read_json()
            if self.path == "/api/search":
                return self.handle_search(body)
            if self.path == "/api/ai/analyze":
                product = body.get("product", {})
                comparables = body.get("comparables") or SAMPLE_PRODUCTS
                return self.send_json(ai_service.analyze(product, comparables))
            if self.path == "/api/ai/listing":
                return self.send_json(ai_service.generate_listing(body.get("product", {}), str(body.get("notes", ""))))
            if self.path == "/api/ai/research":
                return self.send_json({"answer": ai_service.research(str(body.get("question", "")), body.get("products") or SAMPLE_PRODUCTS)})
            self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except RuntimeError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
        except Exception:
            self.send_json({"error": "サーバー処理中にエラーが発生しました。"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_search(self, body: dict[str, Any]) -> None:
        query = str(body.get("query", "")).strip()
        use_live = bool(body.get("live"))
        if use_live:
            live_items, warnings = scraper.search(query or "ゲーミングPC", body.get("sources"))
            live_items = ai_service.analyze_many(live_items)
            if live_items:
                return self.send_json({"items": live_items, "total": len(live_items), "mode": "live", "warnings": warnings})
            demo = filtered_products({"q": [query]})
            return self.send_json({"items": demo, "total": len(demo), "mode": "demo", "warnings": warnings + ["デモデータを表示しています。"]})
        items = filtered_products({"q": [query]})
        return self.send_json({"items": items, "total": len(items), "mode": "demo", "warnings": []})

    def serve_static(self, request_path: str) -> None:
        request_path = "/index.html" if request_path in {"", "/"} else request_path
        normalized = posixpath.normpath(unquote(request_path)).lstrip("/")
        candidate = (STATIC / normalized).resolve()
        if STATIC.resolve() not in candidate.parents and candidate != STATIC.resolve():
            return self.send_error(HTTPStatus.FORBIDDEN)
        if not candidate.is_file():
            candidate = STATIC / "index.html"
        data = candidate.read_bytes()
        content_type, _ = mimetypes.guess_type(str(candidate))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("リクエストが大きすぎます。")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PC Scout AI local server")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"PC Scout AI: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

