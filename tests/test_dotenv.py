"""Offline dotenv tests use synthetic values and isolated temporary files."""
from pathlib import Path
import os
import sys
import tempfile
import traceback
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "publishing-wechat-articles" / "scripts"))

from wechat_pipeline.dotenv import DotenvError, MAX_DOTENV_BYTES, parse_dotenv, read_dotenv  # noqa: E402


class DotenvParserTest(unittest.TestCase):
    def test_comments_export_quotes_empty_values_and_crlf(self):
        text = (
            "\ufeff# comment\r\n\r\n"
            " export KEY = plain value # trailing comment\r\n"
            "SINGLE=' spaces # literal $HOME ' # comment\r\n"
            'DOUBLE="quoted # text"\r\n'
            "EMPTY=\r\nEMPTY_SINGLE=''\r\nEMPTY_DOUBLE=\"\"\r\n"
            "HASH=value#fragment\r\nONLY_COMMENT= # comment\r\n"
        )
        self.assertEqual(parse_dotenv(text), {
            "KEY": "plain value", "SINGLE": " spaces # literal $HOME ",
            "DOUBLE": "quoted # text", "EMPTY": "", "EMPTY_SINGLE": "",
            "EMPTY_DOUBLE": "", "HASH": "value#fragment", "ONLY_COMMENT": "",
        })

    def test_double_quote_escapes_and_literal_single_quotes(self):
        values = parse_dotenv(r'''DOUBLE="a\n\r\t\\\"z\q"
SINGLE='a\n\t\\$HOME'
''')
        self.assertEqual(values["DOUBLE"], 'a\n\r\t\\"z\\q')
        self.assertEqual(values["SINGLE"], r"a\n\t\\$HOME")

    def test_shell_payloads_and_variable_references_remain_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "must-not-exist"
            payload = f"$(touch {marker}); `touch {marker}`; $HOME; ${{OTHER}}"
            before = dict(os.environ)
            for value in (payload, f"'{payload}'", f'"{payload}"'):
                with self.subTest(quote=value[:1]):
                    self.assertEqual(parse_dotenv("KEY=" + value)["KEY"], payload)
            self.assertFalse(marker.exists())
            self.assertEqual(dict(os.environ), before)

    def test_duplicate_keys_use_last_assignment_in_same_file(self):
        self.assertEqual(parse_dotenv("KEY=first\nKEY=\n"), {"KEY": ""})

    def test_invalid_syntax_reports_only_line_number(self):
        lines = (
            'SECRET="synthetic-secret',
            "SECRET='synthetic-secret",
            'SECRET="synthetic-secret" trailing',
            "export synthetic-secret",
            "synthetic-secret=value",
            "1SECRET=synthetic-secret",
            "SECRET.synthetic-secret=value",
            "SECRET=synthetic-secret\x00",
            "SECRET=synthetic-secret\x0b",
            'SECRET="synthetic-secret\ncontinued"',
        )
        for line in lines:
            with self.subTest(case=lines.index(line)):
                try:
                    parse_dotenv("# safe first line\n" + line)
                except DotenvError as exc:
                    self.assertEqual(str(exc), "invalid .env syntax at line 2")
                    self.assertNotIn("synthetic-secret", "".join(traceback.format_exception(exc)))
                else:
                    self.fail("malformed dotenv input was accepted")


class DotenvFileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / ".env"

    def write(self, content):
        self.path.write_bytes(content)
        self.path.chmod(0o600)

    def test_missing_dotenv_is_optional(self):
        self.assertIsNone(read_dotenv(self.path))

    def test_empty_existing_dotenv_is_distinct_from_absence(self):
        self.write(b"")
        self.assertEqual(read_dotenv(self.path), {})

    def test_valid_utf8_file_loads_without_changing_process_environment(self):
        self.write("export KEY='测试值'\n".encode())
        with patch.dict("os.environ", {"KEY": "process-value"}, clear=True):
            self.assertEqual(read_dotenv(self.path), {"KEY": "测试值"})
            self.assertEqual(dict(os.environ), {"KEY": "process-value"})

    def test_symlinks_including_dangling_ones_are_rejected_before_read(self):
        target = self.root / "target"
        for exists in (False, True):
            with self.subTest(target_exists=exists):
                if exists:
                    target.write_text("KEY=synthetic-secret")
                self.path.symlink_to(target)
                with patch("wechat_pipeline.dotenv.os.open") as open_file:
                    with self.assertRaises(DotenvError):
                        read_dotenv(self.path)
                    open_file.assert_not_called()
                self.path.unlink()

    def test_directory_is_not_a_dotenv_file(self):
        self.path.mkdir()
        with self.assertRaises(DotenvError):
            read_dotenv(self.path)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires FIFO support")
    def test_fifo_is_rejected_without_blocking_or_reading(self):
        os.mkfifo(self.path)
        with patch("wechat_pipeline.dotenv.os.open") as open_file:
            with self.assertRaises(DotenvError):
                read_dotenv(self.path)
            open_file.assert_not_called()

    def test_hardlink_is_not_an_implicit_credential_source(self):
        target = self.root / "target"
        target.write_text("KEY=synthetic-secret")
        os.link(target, self.path)
        with self.assertRaises(DotenvError):
            read_dotenv(self.path)

    def test_file_size_is_bounded_before_reading(self):
        self.write(b"KEY=" + b"x" * MAX_DOTENV_BYTES)
        with patch("wechat_pipeline.dotenv.os.open") as open_file:
            with self.assertRaises(DotenvError):
                read_dotenv(self.path)
            open_file.assert_not_called()

    def test_invalid_utf8_error_is_redacted(self):
        self.write(b"# first line\nKEY=synthetic-secret\xff\n")
        try:
            read_dotenv(self.path)
        except DotenvError as exc:
            self.assertIn("line 2", str(exc))
            self.assertNotIn("synthetic-secret", "".join(traceback.format_exception(exc)))
        else:
            self.fail("invalid UTF-8 was accepted")

    def test_utf8_bom_does_not_shift_invalid_encoding_line_number(self):
        self.write(b"\xef\xbb\xbf#\n\xff")
        with self.assertRaisesRegex(DotenvError, r"^invalid .env encoding at line 2$"):
            read_dotenv(self.path)

    def test_open_time_replacement_is_rejected_before_reading(self):
        self.write(b"KEY=first")
        replacement = self.root / "replacement"
        replacement.write_bytes(b"KEY=second")
        original_open = os.open

        def replace_then_open(path, flags):
            replacement.replace(path)
            return original_open(path, flags)

        with patch("wechat_pipeline.dotenv.os.open", side_effect=replace_then_open):
            with patch("wechat_pipeline.dotenv.os.fdopen") as reader:
                with self.assertRaises(DotenvError):
                    read_dotenv(self.path)
                reader.assert_not_called()

    def test_size_limit_is_rechecked_after_open_and_read_is_bounded(self):
        self.write(b"KEY=short")
        with patch("wechat_pipeline.dotenv.os.fdopen") as reader:
            stream = reader.return_value.__enter__.return_value
            stream.read.return_value = b"x" * (MAX_DOTENV_BYTES + 1)
            with self.assertRaises(DotenvError):
                read_dotenv(self.path)
            stream.read.assert_called_once_with(MAX_DOTENV_BYTES + 1)

    def test_io_error_does_not_echo_exception_details(self):
        self.write(b"KEY=synthetic-secret")
        with patch("wechat_pipeline.dotenv.os.open", side_effect=PermissionError("synthetic-secret")):
            try:
                read_dotenv(self.path)
            except DotenvError as exc:
                self.assertNotIn("synthetic-secret", "".join(traceback.format_exception(exc)))
            else:
                self.fail("I/O failure was ignored")


if __name__ == "__main__":
    unittest.main()
