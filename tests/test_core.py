import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from ai_service import GroqAIService
from app import AppHandler, filtered_products
from sample_data import SAMPLE_PRODUCTS
from scraper import SeleniumScraper


class ProductFilterTests(unittest.TestCase):
    def test_filters_by_category(self):
        items = filtered_products({"category": ["中古PC"]})
        self.assertEqual(2, len(items))
        self.assertTrue(all(item["category"] == "中古PC" for item in items))

    def test_filters_by_query_and_price(self):
        items = filtered_products({"q": ["ryzen"], "price_max": ["60000"]})
        self.assertEqual(["demo-002"], [item["id"] for item in items])

    def test_excludes_keywords(self):
        items = filtered_products({"exclude": ["ジャンク"]})
        self.assertNotIn("demo-012", [item["id"] for item in items])


class AIServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = GroqAIService()
        self.service.api_key = ""

    def test_local_analysis_returns_supported_schema(self):
        product = {"title": "Test CPU", "price": 8000, "condition": "A", "specs": {}}
        comparables = [{"price": 10000}, {"price": 12000}, {"price": 14000}]
        result = self.service.analyze(product, comparables)
        self.assertIn(result["grade"], {"S", "A", "B", "C", "ジャンク"})
        self.assertGreaterEqual(result["score"], 0)
        self.assertEqual("local", result["mode"])
        self.assertEqual(12000, result["market_price"])

    def test_listing_fallback(self):
        result = self.service.generate_listing(SAMPLE_PRODUCTS[0], "動作確認済み")
        self.assertIn("Core i7", result["title"])
        self.assertIn("動作確認済み", result["description"])
        self.assertIn("caution", result)

    def test_analyze_many_local(self):
        products = [dict(SAMPLE_PRODUCTS[0]), dict(SAMPLE_PRODUCTS[1])]
        results = self.service.analyze_many(products)
        self.assertEqual(2, len(results))
        self.assertTrue(all(item["ai"]["mode"] == "local" for item in results))


class ScraperHelpersTests(unittest.TestCase):
    def test_parallel_search_collects_all_targets(self):
        scraper = SeleniumScraper()
        scraper.enabled = True
        calls = []

        def collect(targets, query):
            calls.append(query)
            return ([
                {"id": target.name, "title": target.name, "price": 1000, "part_type": "PC"}
                for target in targets
            ], [])

        scraper._collect_chunk = collect
        results, warnings = scraper.search("test")
        first_call_count = len(calls)
        cached_results, _ = scraper.search("test")
        self.assertEqual(len(set(item["id"] for item in results)), len(results))
        self.assertEqual(results, cached_results)
        self.assertGreater(first_call_count, 0)
        self.assertEqual(first_call_count, len(calls))
        self.assertFalse(warnings)

    def test_part_detection(self):
        self.assertEqual("CPU", SeleniumScraper._part_type("Intel Core i7-14700K"))
        self.assertEqual("GPU", SeleniumScraper._part_type("GeForce RTX 4070"))
        self.assertEqual("ストレージ", SeleniumScraper._part_type("NVMe SSD 2TB"))

    def test_extract_specs(self):
        specs = SeleniumScraper._extract_specs("DDR5 32GB 5600MT/s")
        self.assertEqual("DDR5", specs["standard"])
        self.assertEqual("32GB", specs["capacity"])
        self.assertEqual("5600MT/s", specs["speed"])


class HTTPIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def read_json(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_health(self):
        payload = self.read_json("/api/health")
        self.assertTrue(payload["ok"])

    def test_product_endpoint(self):
        payload = self.read_json("/api/products?category=%E4%B8%AD%E5%8F%A4PC")
        self.assertEqual(2, payload["total"])

    def test_index_is_served(self):
        with urllib.request.urlopen(self.base + "/") as response:
            body = response.read().decode("utf-8")
        self.assertIn("PC Scout AI", body)


if __name__ == "__main__":
    unittest.main()
