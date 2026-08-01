from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "publishing-wechat-articles" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wechat_pipeline.security import (
    SecurityError,
    normalize_slug,
    safe_output_path,
    sanitize_resource_url,
    validate_public_url,
)


class SecurityPolicyTest(unittest.TestCase):
    def test_rejects_non_http_and_private_targets(self):
        bad_urls = [
            "file:///etc/passwd",
            "http://127.0.0.1/admin",
            "http://10.0.0.1/",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
        ]
        for url in bad_urls:
            with self.subTest(url=url), self.assertRaises(SecurityError):
                validate_public_url(url)

    def test_allows_public_https_literal(self):
        self.assertEqual(
            validate_public_url("https://93.184.216.34/article"),
            "https://93.184.216.34/article",
        )

    def test_sanitizes_resource_schemes(self):
        self.assertEqual(sanitize_resource_url("javascript:alert(1)"), "")
        self.assertEqual(sanitize_resource_url("data:text/html,boom"), "")
        self.assertEqual(sanitize_resource_url("https://example.com/a.png"), "https://example.com/a.png")

    def test_normalizes_slug_and_blocks_path_escape(self):
        self.assertEqual(normalize_slug("Swift Agent v2 / 中文"), "swift-agent-v2")
        root = ROOT / "workspace"
        self.assertEqual(safe_output_path(root, "runs/demo.json"), root / "runs/demo.json")
        with self.assertRaises(SecurityError):
            safe_output_path(root, "../../outside")


if __name__ == "__main__":
    unittest.main()
