"""Offline image generation tests: every image/provider response is synthetic."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publishing-wechat-articles" / "scripts"))
from wechat_pipeline import config as config_module


class ImageConfigTest(unittest.TestCase):
    def test_optional_config_defaults_off_and_loads_only_local_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skill"
            (skill / "config").mkdir(parents=True)
            for name in ("accounts.toml", "runtime.example.toml"):
                shutil.copyfile(ROOT / "publishing-wechat-articles" / "config" / name,
                                skill / "config" / name)
            loaded = config_module.load_repository_config(skill)
            self.assertTrue(hasattr(loaded.runtime, "image_generation"),
                            "optional image generation config is missing")
            self.assertFalse(loaded.runtime.image_generation.enabled)
            self.assertEqual(loaded.runtime.image_generation.model, "gpt-image-2")
            example = (skill / "config/runtime.example.toml").read_text()
            # A synthetic private fixture, never the repository's private config.
            import tomllib
            if "image_generation" in tomllib.loads(example):
                example = example[:example.index("[image_generation]")]
            (skill / "config/runtime.local.toml").write_text(example + '''
[image_generation]
enabled = true
endpoint = "https://images.example/v1/images/generations"
api_key = "TEST-ONLY-SECRET"
model = "gpt-image-2"
timeout_seconds = 20
allowed_download_hosts = ["cdn.example"]
''')
            configured = config_module.load_repository_config(skill).runtime.image_generation
            self.assertTrue(configured.enabled)
            self.assertEqual(configured.allowed_download_hosts, ("cdn.example",))
            self.assertNotIn("TEST-ONLY-SECRET", repr(configured))


class ImageGenerationTest(unittest.TestCase):
    def api(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("wechat_pipeline.image_generation"),
                             "image generation implementation is missing")
        from wechat_pipeline import image_generation
        return image_generation

    @staticmethod
    def fixture_image():
        # Deliberately synthetic test-only fixture: off-center bands test crop.
        from PIL import Image, ImageDraw
        from io import BytesIO
        image = Image.new("RGB", (1536, 1024), "red")
        ImageDraw.Draw(image).rectangle((0, 200, 1535, 823), fill="green")
        stream = BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()

    @staticmethod
    def public_dns(host, port):
        import socket
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    def test_authorization_gates_never_call_transport(self):
        api = self.api()
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            for enabled, authorized in ((False, False), (False, True), (True, False), (1, True), (True, 1)):
                with self.subTest(enabled=enabled, authorized=authorized):
                    with self.assertRaises(api.ImageGenerationError):
                        api.generate_image_cover("test", Path(tmp) / "cover.png",
                            config=config_module.ImageGenerationConfig(enabled=enabled, api_key="test-key"),
                            authorize_cost=authorized, transport=lambda **kw: calls.append(kw))
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual(calls, [])

    def test_invalid_config_or_prompt_rejected_before_transport(self):
        api = self.api()
        from dataclasses import replace
        config = config_module.ImageGenerationConfig(enabled=True, api_key="test-key")
        cases = [{"model": "gpt-image-1"}, {"api_key": ""}, {"api_key": "x\r\nx"},
                 {"timeout_seconds": 0}, {"timeout_seconds": 121}, {"timeout_seconds": float("nan")},
                 {"timeout_seconds": True}, {"allowed_download_hosts": ("*.example",)},
                 {"allowed_download_hosts": "cdn.example"}]
        calls = []
        def forbidden_transport(**kwargs):
            self.fail("invalid configuration reached transport")
        with tempfile.TemporaryDirectory() as tmp:
            for changes in cases:
                with self.subTest(changes=changes), self.assertRaises(api.ImageGenerationError):
                    api.generate_image_cover("test", Path(tmp) / "cover.png", config=replace(config, **changes),
                        authorize_cost=True, transport=forbidden_transport)
            for prompt in ("", "  ", "x" * 32001, "includes test-key credential"):
                with self.assertRaises(api.ImageGenerationError):
                    api.generate_image_cover(prompt, Path(tmp) / "cover.png", config=config,
                        authorize_cost=True, transport=forbidden_transport)
        self.assertEqual(calls, [])

    def test_unsafe_endpoints_never_reach_transport(self):
        api = self.api()
        from dataclasses import replace
        config = config_module.ImageGenerationConfig(enabled=True, api_key="test-key")
        endpoints = ["http://images.example/v1/images/generations", "https://user:pass@images.example/x",
                     "https://images.example/x?api_key=secret", "https://images.example/x#secret",
                     "https://images.example:8443/x", "https://127.0.0.1/x", "https://[::1]/x",
                     "https://169.254.169.254/latest", "https://10.0.0.1/x", "https://images.example/\nfoo"]
        calls = []
        def forbidden_transport(**kwargs):
            calls.append(kwargs)
            raise api.ImageGenerationError("test transport must not be reached")
        with tempfile.TemporaryDirectory() as tmp:
            for endpoint in endpoints:
                with self.subTest(endpoint=endpoint), self.assertRaises(api.ImageGenerationError):
                    api.generate_image_cover("test", Path(tmp) / "cover.png", config=replace(config, endpoint=endpoint),
                        authorize_cost=True, transport=forbidden_transport, resolver=self.public_dns)
            # Reject the entire DNS answer if any address is private.
            def mixed_dns(host, port):
                return self.public_dns(host, port) + [(2, 1, 6, "", ("192.168.1.1", port))]
            with self.assertRaises(api.ImageGenerationError):
                api.generate_image_cover("test", Path(tmp) / "cover.png", config=config,
                    authorize_cost=True, transport=forbidden_transport, resolver=mixed_dns)
        self.assertEqual(calls, [], "SSRF validation must happen before transport")

    def test_allowlisted_url_download_is_pinned_and_has_no_authorization(self):
        api = self.api()
        import json
        calls = []
        def transport(**kwargs):
            calls.append(kwargs)
            if kwargs["method"] == "POST":
                return 200, json.dumps({"data": [{"url": "https://cdn.example/image.png?sig=TEST-ONLY-SECRET"}]}).encode()
            return 200, self.fixture_image()
        config = config_module.ImageGenerationConfig(enabled=True, api_key="test-key", allowed_download_hosts=("cdn.example",))
        with tempfile.TemporaryDirectory() as tmp:
            try:
                result = api.generate_image_cover("test", Path(tmp) / "cover.png", config=config,
                    authorize_cost=True, transport=transport, resolver=self.public_dns)
            except Exception as exc:
                self.fail("URL response support missing: " + type(exc).__name__)
            self.assertNotIn("TEST-ONLY-SECRET", result.provenance_path.read_text())
        self.assertEqual([call["method"] for call in calls], ["POST", "GET"])
        self.assertNotIn("Authorization", calls[1]["headers"])
        self.assertEqual([call["resolved_ip"] for call in calls], ["93.184.216.34"] * 2)
        self.assertLessEqual(calls[1]["timeout"], config.timeout_seconds)

    def assert_response_rejected(self, response, *, status=200, config=None, resolver=None):
        api = self.api()
        import json
        import traceback
        calls = []
        def transport(**kwargs):
            calls.append(kwargs)
            return status, response if isinstance(response, bytes) else json.dumps(response).encode()
        config = config or config_module.ImageGenerationConfig(enabled=True, api_key="test-key")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                api.generate_image_cover("test", Path(tmp) / "cover.png", config=config,
                    authorize_cost=True, transport=transport, resolver=resolver or self.public_dns)
            except api.ImageGenerationError:
                self.assertNotIn("TEST-ONLY-SECRET", traceback.format_exc())
            except Exception as exc:
                self.fail("provider response escaped safe error boundary: " + type(exc).__name__)
            else:
                self.fail("invalid provider response accepted")
            self.assertEqual(list(Path(tmp).iterdir()), [])
        return calls

    def test_malformed_response_is_rejected_without_secret_leak(self):
        import base64
        image = base64.b64encode(self.fixture_image()).decode()
        cases = [b"not JSON TEST-ONLY-SECRET", {}, {"data": []}, {"data": [None]},
                 {"data": [{"b64_json": "TEST-ONLY-SECRET!"}]},
                 {"data": [{"b64_json": base64.b64encode(b"not image TEST-ONLY-SECRET").decode()}]},
                 {"data": [{"b64_json": image}, {"b64_json": image}]},
                 {"model": "gpt-image-1", "data": [{"b64_json": image}]},
                 {"data": [{"b64_json": image, "url": "https://cdn.example/x"}]}]
        for index, response in enumerate(cases):
            with self.subTest(index=index):
                self.assert_response_rejected(response)

    def test_wrong_image_dimensions_are_rejected_not_stretched(self):
        import base64
        from io import BytesIO
        from PIL import Image
        stream = BytesIO()
        Image.new("RGB", (1200, 540), "blue").save(stream, format="PNG")
        self.assert_response_rejected({"data": [{"b64_json": base64.b64encode(stream.getvalue()).decode()}]})

    def test_error_and_redirect_responses_never_retry(self):
        for status in (301, 302, 307, 400, 401, 429, 500):
            with self.subTest(status=status):
                calls = self.assert_response_rejected(b"TEST-ONLY-SECRET", status=status)
                self.assertEqual(len(calls), 1)

    def test_untrusted_download_urls_never_get_fetched(self):
        urls = ["http://cdn.example/x", "https://other.example/x", "https://cdn.example.evil/x",
                "https://127.0.0.1/x", "https://user:pass@cdn.example/x", "https://cdn.example:8443/x"]
        config = config_module.ImageGenerationConfig(enabled=True, api_key="test-key", allowed_download_hosts=("cdn.example",))
        for url in urls:
            with self.subTest(url=url):
                calls = self.assert_response_rejected({"data": [{"url": url}]}, config=config)
                self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.assert_response_rejected({"data": [{"url": "https://cdn.example/x"}]})), 1)

    def test_response_and_decoded_image_limits(self):
        api = self.api()
        from unittest.mock import patch
        import base64
        with patch.object(api, "MAX_RESPONSE_BYTES", 8):
            self.assert_response_rejected(b"x" * 9)
        with patch.object(api, "MAX_IMAGE_BYTES", 8):
            self.assert_response_rejected({"data": [{"b64_json": base64.b64encode(self.fixture_image()).decode()}]})

    def test_transport_exception_is_redacted_and_not_retried(self):
        api = self.api()
        import traceback
        calls = []
        def transport(**kwargs):
            calls.append(kwargs)
            raise OSError("TEST-ONLY-SECRET")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                api.generate_image_cover("test", Path(tmp) / "cover.png",
                    config=config_module.ImageGenerationConfig(enabled=True, api_key="test-key"),
                    authorize_cost=True, transport=transport, resolver=self.public_dns)
            except api.ImageGenerationError:
                self.assertNotIn("TEST-ONLY-SECRET", traceback.format_exc())
            else:
                self.fail("transport exception was not raised")
            self.assertEqual(len(calls), 1)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_default_https_transport_uses_pinned_ip_verified_tls_and_no_redirects(self):
        api = self.api()
        self.assertTrue(hasattr(api, "_https_transport"), "production HTTPS transport is missing")
        from io import BytesIO
        from unittest.mock import patch
        import ssl
        events = []
        class Socket:
            def settimeout(self, value):
                events.append(("timeout", value))
            def connect(self, address):
                events.append(("connect", address))
            def sendall(self, value):
                events.append(("send", value))
            def do_handshake(self):
                events.append(("handshake",))
            def makefile(self, mode):
                return BytesIO(b"HTTP/1.1 302 Found\r\nContent-Length: 2\r\nLocation: http://127.0.0.1/\r\n\r\n{}")
            def close(self):
                events.append(("close",))
            def shutdown(self, how):
                events.append(("shutdown",))
        sock = Socket()
        def wrap(context, raw, *, server_hostname, do_handshake_on_connect):
            self.assertFalse(do_handshake_on_connect)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertEqual(server_hostname, "images.example")
            self.assertIs(raw, sock)
            return sock
        with patch.object(api.socket, "socket", return_value=sock), \
             patch.object(api.socket, "getaddrinfo", side_effect=AssertionError("must not resolve again")), \
             patch.object(api.ssl.SSLContext, "wrap_socket", autospec=True, side_effect=wrap):
            status, data = api._https_transport(method="POST", url="https://images.example/v1/images/generations",
                resolved_ip="93.184.216.34", headers={"Content-Type": "application/json"}, body=b"{}",
                timeout=3, max_bytes=1024)
        self.assertEqual(status, 302)
        self.assertEqual(data, b"{}")
        self.assertEqual([event for event in events if event[0] == "connect"], [("connect", ("93.184.216.34", 443))])
        sent = b"".join(event[1] for event in events if event[0] == "send")
        self.assertIn(b"Host: images.example", sent)
        self.assertIn(("close",), events)

    def test_dns_resolution_is_time_bounded(self):
        api = self.api()
        self.assertTrue(hasattr(api, "_resolve_bounded"), "DNS timeout is missing")
        import time
        from threading import Event
        event = Event()
        def stalled(host, port):
            event.wait(1)
            return self.public_dns(host, port)
        started = time.monotonic()
        try:
            with self.assertRaises(api.ImageGenerationError):
                api._resolve_bounded(stalled, "images.example", time.monotonic() + 0.02)
            self.assertLess(time.monotonic() - started, 0.5)
        finally:
            event.set()

    def test_authorized_base64_produces_cropped_png_and_safe_provenance(self):
        api = self.api()
        import base64
        import hashlib
        import json
        from PIL import Image
        calls = []
        image = self.fixture_image()

        def transport(**kwargs):
            calls.append(kwargs)
            return 200, json.dumps({"data": [{"b64_json": base64.b64encode(image).decode(),
                                              "revised_prompt": "TEST-ONLY-SECRET"}]}).encode()

        config = config_module.ImageGenerationConfig(enabled=True, api_key="TEST-ONLY-SECRET")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "cover.png"
            result = api.generate_image_cover("Test-only centered composition", output,
                config=config, authorize_cost=True, transport=transport, resolver=self.public_dns)
            self.assertEqual(result.cover_path, output)
            with Image.open(output) as cover:
                self.assertEqual(cover.size, (1200, 540))
                self.assertEqual(cover.getpixel((600, 270)), (0, 128, 0))
                self.assertEqual(cover.getpixel((600, 0)), (255, 0, 0))
            with Image.open(result.source_path) as source:
                self.assertEqual(source.size, (1536, 1024))
            provenance = json.loads(result.provenance_path.read_text())
            self.assertEqual(provenance["model"], "gpt-image-2")
            self.assertEqual(provenance["cover_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertEqual(provenance["transform"], {"resize": [1200, 800], "crop_box": [0, 130, 1200, 670]})
            self.assertEqual(result.prompt_path.read_text(), "Test-only centered composition")
            for path in Path(tmp).iterdir():
                self.assertNotIn(b"TEST-ONLY-SECRET", path.read_bytes())
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["method"], "POST")
        self.assertEqual(json.loads(calls[0]["body"]), {"model": "gpt-image-2", "prompt": "Test-only centered composition", "n": 1, "size": "1536x1024"})


if __name__ == "__main__":
    unittest.main()
