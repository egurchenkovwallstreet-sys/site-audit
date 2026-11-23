from __future__ import annotations

import re

_JS_U_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_JS_X_RE = re.compile(r"\\x([0-9a-fA-F]{2})")


def decode_js_unicode_escapes(text: str) -> str:
    """Раскрывает \\uXXXX и \\xXX в тексте Flutter/JS-бандла."""
    if not text or "\\u" not in text and "\\x" not in text:
        return text

    def u_replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    def x_replace(match: re.Match[str]) -> str:
        return chr(int(match.group(1), 16))

    out = _JS_U_RE.sub(u_replace, text)
    return _JS_X_RE.sub(x_replace, out)