"""Small, non-executing dotenv reader for one explicitly selected local file.

Syntax is line-oriented: NAME=value, optional ``export``, blank lines, comments,
single/double quotes and empty values. Unquoted comments start at ``#`` after
whitespace; quoted ``#`` is literal. Single quotes are literal; double quotes
recognize \\n, \\r, \\t, \\\\ and \\". Unknown escapes are preserved. Duplicate
names use the last assignment. Multiline values/continuations are not supported.
There is no interpolation, command substitution, shell evaluation or env update.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat


MAX_DOTENV_BYTES = 64 * 1024
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_DOUBLE_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}


class DotenvError(ValueError):
    """Safe to display: never includes a file's contents or underlying error."""


def _syntax_error(line_number: int) -> DotenvError:
    return DotenvError(f"invalid .env syntax at line {line_number}")


def _parse_value(value: str, line_number: int) -> str:
    if not value or value.startswith("#"):
        return ""
    if value[0] not in {"'", '"'}:
        for index, character in enumerate(value):
            if character == "#" and index and value[index - 1] in " \t":
                return value[:index].rstrip(" \t")
        return value
    quote = value[0]
    result: list[str] = []
    index = 1
    while index < len(value):
        character = value[index]
        if character == quote:
            trailing = value[index + 1:].lstrip(" \t")
            if trailing and not trailing.startswith("#"):
                raise _syntax_error(line_number)
            return "".join(result)
        if quote == '"' and character == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            if escaped in _DOUBLE_ESCAPES:
                result.append(_DOUBLE_ESCAPES[escaped])
                index += 2
                continue
        result.append(character)
        index += 1
    raise _syntax_error(line_number)


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse UTF-8 text without changing process state or expanding values."""
    if text.startswith("\ufeff"):
        text = text[1:]
    values: dict[str, str] = {}
    for line_number, raw in enumerate(text.split("\n"), 1):
        # Support CRLF, but never silently treat embedded controls as separators.
        line = raw.removesuffix("\r").strip(" \t")
        if any(ord(character) < 32 and character != "\t" for character in line):
            raise _syntax_error(line_number)
        if not line or line.startswith("#"):
            continue
        if line.startswith(("export ", "export\t")):
            line = line[6:].lstrip(" \t")
        name, separator, value = line.partition("=")
        name = name.rstrip(" \t")
        if not separator or not _NAME.fullmatch(name):
            raise _syntax_error(line_number)
        values[name] = _parse_value(value.strip(" \t"), line_number)
    return values


def read_private_text(path: Path, *, label: str, max_bytes: int = MAX_DOTENV_BYTES) -> str | None:
    """Read a bounded regular file without links; missing files return None.

    ``label`` must be a fixed, public source label, not a value read from a file.
    Permissions are reported separately by preflight, which checks every loaded
    private source even when some/all of its settings have environment overrides.
    """
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        raise DotenvError(f"cannot read {label}") from None
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise DotenvError(f"{label} must be a regular file without links")
    if before.st_size > max_bytes:
        raise DotenvError(f"{label} exceeds the size limit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            ):
                raise DotenvError(f"{label} changed while opening")
            if opened.st_size > max_bytes:
                raise DotenvError(f"{label} exceeds the size limit")
            # closefd=False keeps descriptor lifetime in the single finally below.
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                content = stream.read(max_bytes + 1)
        finally:
            os.close(descriptor)
    except OSError:
        raise DotenvError(f"cannot read {label}") from None
    if len(content) > max_bytes:
        raise DotenvError(f"{label} exceeds the size limit")
    try:
        return content.decode("utf-8").removeprefix("\ufeff")
    except UnicodeDecodeError as exc:
        line_number = content[:exc.start].count(b"\n") + 1
        raise DotenvError(f"invalid {label} encoding at line {line_number}") from None


def read_dotenv(path: Path) -> dict[str, str] | None:
    """Read only ``path``; never search ancestors, a home directory, or the cwd."""
    text = read_private_text(path, label=".env")
    return None if text is None else parse_dotenv(text)
