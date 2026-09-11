from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .extractors import PAGE_BREAK_MARKER


class MarkdownNormalizer:
    """Applies conservative cleanup while preserving Markdown structure."""

    def normalize(self, markdown: str) -> str:
        text = unicodedata.normalize("NFC", markdown)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)
        text = re.sub(
            rf"\s*{re.escape(PAGE_BREAK_MARKER)}\s*",
            f"\n\n{PAGE_BREAK_MARKER}\n\n",
            text,
        )
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    def normalize_file(self, raw_path: Path, destination_path: Path) -> str:
        normalized = self.normalize(raw_path.read_text(encoding="utf-8"))
        destination_path.write_text(normalized, encoding="utf-8")
        return normalized

