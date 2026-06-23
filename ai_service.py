"""Groq-backed analysis with deterministic, offline-safe fallbacks."""

from __future__ import annotations

import json
import os
import statistics
import urllib.error
import urllib.request
from typing import Any


class GroqAIService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def analyze(self, product: dict[str, Any], comparables: list[dict[str, Any]]) -> dict[str, Any]:
        fallback = self._local_analysis(product, comparables)
        if not self.enabled:
            return fallback

        prompt = {
            "task": "PC商品を査定し、JSONだけを返してください。",
            "grading": "gradeはS/A/B/C/ジャンク、labelは買い/適正/要確認/見送りのいずれか。",
            "required_keys": ["grade", "score", "label", "market_price", "summary"],
            "product": product,
            "comparables": comparables[:12],
        }
        try:
            result = self._chat(json.dumps(prompt, ensure_ascii=False), json_mode=True)
            parsed = json.loads(result)
            return self._validate_analysis(parsed, fallback)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            fallback["summary"] += "（AI接続失敗のためローカル評価）"
            return fallback

    def generate_listing(self, product: dict[str, Any], notes: str = "") -> dict[str, str]:
        fallback = self._local_listing(product, notes)
        if not self.enabled:
            return fallback
        prompt = (
            "次の商品について、日本のフリマ向け出品文を作成してください。誇張せず、不明点を断定しないでください。"
            "JSONのみで title, description, caution の3キーを返してください。\n"
            f"商品: {json.dumps(product, ensure_ascii=False)}\n補足: {notes}"
        )
        try:
            parsed = json.loads(self._chat(prompt, json_mode=True))
            return {key: str(parsed.get(key, fallback[key])) for key in fallback}
        except (OSError, ValueError, json.JSONDecodeError):
            return fallback

    def research(self, question: str, products: list[dict[str, Any]]) -> str:
        if not self.enabled:
            if products:
                cheapest = min(products, key=lambda item: int(item.get("price", 0)))
                return f"ローカル分析では、該当商品の最安は「{cheapest['title']}」の¥{cheapest['price']:,}です。詳細な調べものにはGroq APIキーを設定してください。"
            return "条件に合う商品がありません。検索条件を広げてみてください。"
        prompt = (
            "あなたは中古PC市場に詳しい査定者です。提示データの範囲だけを根拠に簡潔な日本語で回答し、"
            "データ外の事実は推測と明示してください。\n"
            f"質問: {question}\n商品データ: {json.dumps(products[:30], ensure_ascii=False)}"
        )
        try:
            return self._chat(prompt)
        except OSError:
            return "Groqへの接続に失敗しました。しばらくしてから再試行してください。"

    def _chat(self, prompt: str, json_mode: bool = False) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise OSError("Groq request failed") from exc
        return payload["choices"][0]["message"]["content"]

    @staticmethod
    def _local_analysis(product: dict[str, Any], comparables: list[dict[str, Any]]) -> dict[str, Any]:
        prices = [int(item.get("price", 0)) for item in comparables if int(item.get("price", 0)) > 0]
        price = int(product.get("price", 0))
        market = round(statistics.median(prices)) if prices else price
        ratio = (price / market) if market else 1.0
        source_grade = str(product.get("condition", "B"))
        penalty = {"S": 0, "A": 3, "B": 10, "C": 24, "ジャンク": 55}.get(source_grade, 12)
        value_bonus = max(-18, min(18, round((1 - ratio) * 80)))
        score = max(10, min(98, 82 - penalty + value_bonus))
        grade = "S" if score >= 92 else "A" if score >= 82 else "B" if score >= 68 else "C" if score >= 45 else "ジャンク"
        label = "買い" if score >= 86 else "適正" if score >= 74 else "要確認" if score >= 48 else "見送り"
        delta = round((1 - ratio) * 100)
        comparison = f"相場より約{abs(delta)}%{'安い' if delta >= 0 else '高い'}" if abs(delta) >= 2 else "相場とほぼ同水準"
        return {"grade": grade, "score": score, "label": label, "market_price": market, "summary": f"{comparison}価格です。状態・保証・付属品を確認してください。", "mode": "local"}

    @staticmethod
    def _validate_analysis(value: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        grades = {"S", "A", "B", "C", "ジャンク"}
        labels = {"買い", "適正", "要確認", "見送り"}
        return {
            "grade": value.get("grade") if value.get("grade") in grades else fallback["grade"],
            "score": max(0, min(100, int(value.get("score", fallback["score"])))),
            "label": value.get("label") if value.get("label") in labels else fallback["label"],
            "market_price": max(0, int(value.get("market_price", fallback["market_price"]))),
            "summary": str(value.get("summary", fallback["summary"]))[:240],
            "mode": "groq",
        }

    @staticmethod
    def _local_listing(product: dict[str, Any], notes: str) -> dict[str, str]:
        specs = product.get("specs", {})
        spec_text = " / ".join(f"{key}: {value}" for key, value in specs.items())
        condition = product.get("condition", "B")
        return {
            "title": f"【状態{condition}】{product.get('title', 'PCパーツ')}"[:60],
            "description": f"ご覧いただきありがとうございます。\n\n商品名: {product.get('title', '')}\n仕様: {spec_text}\n状態: {condition}\n{notes}\n\n写真に写っているものが全てです。対応環境をご確認のうえご購入ください。",
            "caution": "傷・動作・付属品など、確認できていない項目は出品前に追記してください。",
        }

