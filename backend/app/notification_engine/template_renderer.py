from __future__ import annotations

import re
from typing import Any


_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_template_text(template: str | None, payload: dict[str, Any]) -> str:
    text = template or ""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = payload.get(key, "")
        return str(value if value is not None else "")

    return _VAR_PATTERN.sub(_replace, text)
