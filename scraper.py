"""Selenium product collector with conservative rate and offline fallback."""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus, urlparse


@dataclass(frozen=True)
class Target:
    name: str
    search_url: str
    category: str


TARGETS = [
    Target("価格.com", "https://search.kakaku.com/{query}/", "all"),
    Target("パソコン工房", "https://www.pc-koubou.jp/products/list.php?name={query}", "all"),
    Target("メルカリ", "https://jp.mercari.com/search?keyword={query}", "used"),
    Target("Yahoo!フリマ", "https://paypayfleamarket.yahoo.co.jp/search/{query}", "used"),
    Target("eBay", "https://www.ebay.co.jp/sch/i.html?_nkw={query}", "all"),
    Target("AliExpress", "https://ja.aliexpress.com/w/wholesale-{query}.html", "new"),
    Target("じゃんぱら", "https://www.janpara.co.jp/sale/search/result/?KEYWORDS={query}", "used"),
    Target("ドスパラ", "https://www.dospara.co.jp/on/demandware.store/Sites-dospara-Site/ja_JP/Search-Show?q={query}", "all"),
    Target("ツクモ", "https://shop.tsukumo.co.jp/search/?q={query}", "new"),
    Target("Amazon", "https://www.amazon.co.jp/s?k={query}", "new"),
    Target("ハードオフ", "https://netmall.hardoff.co.jp/search/?q={query}", "used"),
]

# Category landing pages retained as explicit crawl seeds for scheduled/category scans.
DISCOVERY_URLS = dict([["価格.com 中古PC", "https://kakaku.com/used/pc/ca=0020/s1=23/?s1=24"], ["価格.com PC", "https://kakaku.com/pc/"], ["パソコン工房 中古パーツ", "https://www.pc-koubou.jp/pc/used_parts.php"], ["Core Ultra 9", "https://www.pc-koubou.jp/pc/used_intel_cpu_core_ultra_9.php"], ["Core Ultra 7", "https://www.pc-koubou.jp/pc/used_intel_cpu_core_ultra_7.php"], ["Core Ultra 5", "https://www.pc-koubou.jp/pc/used_intel_cpu_core_ultra_5.php"], ["Core i9", "https://www.pc-koubou.jp/pc/used_intel_cpu_corei9.php"], ["Core i7", "https://www.pc-koubou.jp/pc/used_intel_cpu_corei7.php"], ["Core i5", "https://www.pc-koubou.jp/pc/used_intel_cpu_corei5.php"], ["Core i3", "https://www.pc-koubou.jp/pc/used_intel_cpu_corei3.php"], ["Pentium", "https://www.pc-koubou.jp/pc/used_intel_cpu_pentium.php"], ["Celeron", "https://www.pc-koubou.jp/pc/used_intel_cpu_celeron.php"], ["Xeon", "https://www.pc-koubou.jp/pc/used_intel_cpu_xeon.php"], ["Ryzen 9", "https://www.pc-koubou.jp/pc/used_amd_cpu_ryzen9.php?pre=used_parts"], ["Ryzen 7", "https://www.pc-koubou.jp/pc/used_amd_cpu_ryzen7.php?pre=used_parts"], ["Ryzen 5", "https://www.pc-koubou.jp/pc/used_amd_cpu_ryzen5.php?pre=used_parts"], ["Ryzen 3", "https://www.pc-koubou.jp/pc/used_amd_cpu_ryzen3.php?pre=used_parts"], ["AMD その他", "https://www.pc-koubou.jp/pc/used_amd_cpu_sonota.php"], ["メモリ バルク", "https://www.pc-koubou.jp/pc/used_memory_bulk.php"], ["DDR5 デスクトップ", "https://www.pc-koubou.jp/pc/used_memory_d_ddr5.php"], ["DDR4 デスクトップ", "https://www.pc-koubou.jp/pc/used_memory_d_ddr4.php"], ["DDR5 ノート", "https://www.pc-koubou.jp/pc/used_memory_n_ddr5.php"], ["DDR4 ノート", "https://www.pc-koubou.jp/pc/used_memory_n_ddr4.php"], ["NVIDIA GPU", "https://www.pc-koubou.jp/pc/used_nvidia_videocard.php"], ["AMD GPU", "https://www.pc-koubou.jp/pc/used_amd_videocard.php"], ["Intel GPU", "https://www.pc-koubou.jp/pc/used_intel_videocard.php"], ["Intel マザーボード", "https://www.pc-koubou.jp/pc/used_intel_motherboard.php"], ["AMD マザーボード", "https://www.pc-koubou.jp/pc/used_amd_motherboard.php"], ["その他パーツ", "https://www.pc-koubou.jp/pc/used_parts_other.php"]])


class SeleniumScraper:
    def __init__(self, max_per_source: int = 8) -> None:
        self.max_per_source = max_per_source
        self.enabled = os.getenv("ENABLE_LIVE_SCRAPING", "0").lower() in {"1", "true", "yes"}
        self.cache_seconds = max(0, int(os.getenv("SCRAPER_CACHE_SECONDS", "180")))
        self._cache: dict[tuple[str, tuple[str, ...]], tuple[float, list[dict[str, Any]], list[str]]] = {}
        self._cache_lock = threading.Lock()

    def search(self, query: str, source_names: list[str] | None = None) -> tuple[list[dict[str, Any]], list[str]]:
        if not self.enabled:
            return [], ["LIVE巡回は無効です。ENABLE_LIVE_SCRAPING=1 で有効化できます。"]
        cache_key = (query.strip().lower(), tuple(sorted(source_names or [])))
        with self._cache_lock:
            cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] <= self.cache_seconds:
            return [dict(item) for item in cached[1]], list(cached[2])

        selected = [target for target in TARGETS if not source_names or target.name in source_names]
        if not selected:
            return [], ["巡回対象サイトが選択されていません。"]

        worker_count = max(1, min(int(os.getenv("SCRAPER_WORKERS", "3")), len(selected)))
        chunks = [selected[index::worker_count] for index in range(worker_count)]
        results: list[dict[str, Any]] = []
        warnings: list[str] = []
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="scraper") as executor:
            futures = [executor.submit(self._collect_chunk, chunk, query) for chunk in chunks if chunk]
            for future in as_completed(futures):
                chunk_items, chunk_warnings = future.result()
                results.extend(chunk_items)
                warnings.extend(chunk_warnings)
        unique = self._deduplicate(results)
        with self._cache_lock:
            self._cache[cache_key] = (time.monotonic(), [dict(item) for item in unique], list(warnings))
        return unique, warnings

    def _collect_chunk(self, targets: list[Target], query: str) -> tuple[list[dict[str, Any]], list[str]]:
        driver = self._create_driver()
        items: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            for target in targets:
                try:
                    items.extend(self._collect(driver, target, query))
                except Exception as exc:  # Site layouts and anti-bot responses are inherently variable.
                    warnings.append(f"{target.name}: 取得できませんでした（{type(exc).__name__}）")
                time.sleep(0.2)
        finally:
            driver.quit()
        return items, warnings

    @staticmethod
    def _create_driver():
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.edge.options import Options as EdgeOptions
        except ImportError as exc:
            raise RuntimeError("Seleniumが未インストールです。pip install -r requirements.txt を実行してください。") from exc

        attempts = []
        chrome_options = ChromeOptions()
        chrome_options.page_load_strategy = "eager"
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1440,1200")
        chrome_options.add_argument("--lang=ja-JP")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        attempts.append(lambda: webdriver.Chrome(options=chrome_options))

        edge_options = EdgeOptions()
        edge_options.page_load_strategy = "eager"
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--window-size=1440,1200")
        edge_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        attempts.append(lambda: webdriver.Edge(options=edge_options))
        if os.name != "nt":
            attempts.append(lambda: webdriver.Safari())

        last_error: Exception | None = None
        for attempt in attempts:
            try:
                driver = attempt()
                driver.set_page_load_timeout(14)
                return driver
            except Exception as exc:
                last_error = exc
        raise RuntimeError("利用可能なWebDriverを起動できませんでした。") from last_error

    def _collect(self, driver: Any, target: Target, query: str) -> list[dict[str, Any]]:
        url = target.search_url.format(query=quote_plus(query))
        driver.get(url)
        time.sleep(0.35)
        raw_items = driver.execute_script(
            """
            const priceRe = /(?:￥|¥|税込|価格)\\s*([0-9][0-9,]{2,})/;
            const seen = new Set(), out = [];
            const candidates = [...document.querySelectorAll('article, li, [class*="item"], [class*="product"], [data-testid*="item"]')];
            for (const el of candidates) {
              const text = (el.innerText || '').replace(/\\s+/g, ' ').trim();
              const match = text.match(priceRe);
              const link = el.querySelector('a[href]');
              if (!match || !link || text.length < 8 || text.length > 900) continue;
              const href = link.href;
              if (seen.has(href)) continue;
              const img = el.querySelector('img');
              const titleNode = el.querySelector('h2,h3,h4,[class*="title"],[class*="name"]');
              const title = (titleNode?.innerText || link.getAttribute('title') || img?.alt || text.split('￥')[0]).trim();
              if (title.length < 3) continue;
              seen.add(href);
              out.push({title: title.slice(0,160), price: match[1], url: href, image: img?.currentSrc || img?.src || ''});
              if (out.length >= arguments[0]) break;
            }
            return out;
            """,
            self.max_per_source,
        )
        products = []
        for item in raw_items:
            price = self._price(item.get("price", ""))
            title = str(item.get("title", "")).strip()
            if not price or not title:
                continue
            products.append({
                "id": "live-" + hashlib.sha1(f"{target.name}{item['url']}".encode()).hexdigest()[:12],
                "title": title,
                "price": price,
                "category": "中古PCパーツ" if target.category == "used" else "新品PCパーツ",
                "part_type": self._part_type(title),
                "condition": "B" if target.category == "used" else "S",
                "source": target.name,
                "url": item["url"],
                "image": item.get("image") or "/assets/pc.svg",
                "specs": self._extract_specs(title),
            })
        return products

    @staticmethod
    def _price(value: str) -> int:
        digits = re.sub(r"[^0-9]", "", value)
        return int(digits) if digits else 0

    @staticmethod
    def _part_type(title: str) -> str:
        lower = title.lower()
        if re.search(r"core\s*i[3579]|ryzen|xeon|celeron|pentium", lower):
            return "CPU"
        if re.search(r"rtx|gtx|radeon|arc\s+[ab]", lower):
            return "GPU"
        if "ddr" in lower or "メモリ" in lower:
            return "メモリ"
        if re.search(r"ssd|hdd|nvme|ストレージ", lower):
            return "ストレージ"
        return "PC"

    @staticmethod
    def _extract_specs(title: str) -> dict[str, str]:
        specs: dict[str, str] = {}
        for label, pattern in {
            "capacity": r"\b(\d+(?:\.\d+)?\s*(?:TB|GB))\b",
            "standard": r"\b(DDR[345]|NVMe|SATA)\b",
            "speed": r"\b(\d{3,5}\s*(?:MHz|MT/s|MB/s))\b",
        }.items():
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                specs[label] = match.group(1)
        return specs

    @staticmethod
    def _deduplicate(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, int]] = set()
        unique = []
        for product in products:
            key = (re.sub(r"\W", "", product["title"].lower())[:50], product["price"])
            if key not in seen:
                seen.add(key)
                unique.append(product)
        return unique

