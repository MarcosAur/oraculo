from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import tiktoken

from .config import ChunkingConfig
from .extractors import PAGE_BREAK_MARKER


@dataclass(frozen=True)
class MarkdownBlock:
    text: str
    page_start: int
    page_end: int
    section_path: tuple[str, ...]
    is_table: bool = False


@dataclass(frozen=True)
class ChunkDraft:
    text: str
    token_count: int
    page_start: int
    page_end: int
    section_path: list[str]
    overlap_token_count: int


class MarkdownChunker:
    """Structure-aware Markdown chunker with token-bounded overlap."""

    _heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

    def __init__(self, config: ChunkingConfig):
        self.config = config
        try:
            self.encoding = tiktoken.encoding_for_model(config.tokenizer_model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _is_table(self, text: str) -> bool:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return (
            len(lines) >= 2
            and lines[0].startswith("|")
            and lines[1].startswith("|")
            and "---" in lines[1]
        )

    def _parse_blocks(self, markdown: str) -> list[MarkdownBlock]:
        sections: list[str] = []
        blocks: list[MarkdownBlock] = []
        pages = markdown.split(PAGE_BREAK_MARKER)

        for page_number, page_text in enumerate(pages, start=1):
            for raw_block in re.split(r"\n{2,}", page_text):
                text = raw_block.strip()
                if not text:
                    continue
                heading = self._heading_pattern.match(text.splitlines()[0])
                if heading:
                    level = len(heading.group(1))
                    title = heading.group(2).strip()
                    sections = sections[: level - 1]
                    sections.append(title)
                blocks.append(
                    MarkdownBlock(
                        text=text,
                        page_start=page_number,
                        page_end=page_number,
                        section_path=tuple(sections),
                        is_table=self._is_table(text),
                    )
                )
        return blocks

    def _split_table(self, block: MarkdownBlock) -> list[MarkdownBlock]:
        lines = [line for line in block.text.splitlines() if line.strip()]
        if len(lines) <= 2:
            return [block]
        header = lines[:2]
        rows = lines[2:]
        pieces: list[MarkdownBlock] = []
        current = header.copy()
        for row in rows:
            candidate = "\n".join(current + [row])
            if len(current) > 2 and self.count_tokens(candidate) > self.config.chunk_size:
                pieces.append(
                    MarkdownBlock(
                        text="\n".join(current),
                        page_start=block.page_start,
                        page_end=block.page_end,
                        section_path=block.section_path,
                        is_table=True,
                    )
                )
                current = header + [row]
            else:
                current.append(row)
        if len(current) > 2:
            pieces.append(
                MarkdownBlock(
                    text="\n".join(current),
                    page_start=block.page_start,
                    page_end=block.page_end,
                    section_path=block.section_path,
                    is_table=True,
                )
            )
        return pieces or [block]

    def _split_oversized(self, block: MarkdownBlock) -> list[MarkdownBlock]:
        if self.count_tokens(block.text) <= self.config.chunk_size:
            return [block]
        if block.is_table:
            table_parts = self._split_table(block)
            if all(
                self.count_tokens(part.text) <= self.config.chunk_size
                for part in table_parts
            ):
                return table_parts

        tokens = self.encoding.encode(block.text)
        step = self.config.chunk_size - self.config.chunk_overlap
        pieces = []
        for start in range(0, len(tokens), step):
            token_slice = tokens[start : start + self.config.chunk_size]
            if not token_slice:
                break
            pieces.append(
                MarkdownBlock(
                    text=self.encoding.decode(token_slice).strip(),
                    page_start=block.page_start,
                    page_end=block.page_end,
                    section_path=block.section_path,
                    is_table=block.is_table,
                )
            )
            if start + self.config.chunk_size >= len(tokens):
                break
        return pieces

    def _expanded_blocks(self, blocks: Iterable[MarkdownBlock]) -> list[MarkdownBlock]:
        expanded: list[MarkdownBlock] = []
        for block in blocks:
            expanded.extend(self._split_oversized(block))
        return expanded

    def _join(self, blocks: list[MarkdownBlock]) -> str:
        return "\n\n".join(block.text for block in blocks).strip()

    def _overlap_blocks(self, blocks: list[MarkdownBlock]) -> list[MarkdownBlock]:
        if self.config.chunk_overlap == 0:
            return []
        selected: list[MarkdownBlock] = []
        used = 0
        for block in reversed(blocks):
            size = self.count_tokens(block.text)
            if used + size <= self.config.chunk_overlap:
                selected.append(block)
                used += size
                continue
            remaining = self.config.chunk_overlap - used
            if remaining > 0 and not block.is_table and not selected:
                tokens = self.encoding.encode(block.text)
                selected.append(
                    MarkdownBlock(
                        text=self.encoding.decode(tokens[-remaining:]).strip(),
                        page_start=block.page_start,
                        page_end=block.page_end,
                        section_path=block.section_path,
                    )
                )
            break
        return list(reversed(selected))

    def _draft(self, blocks: list[MarkdownBlock], overlap: int) -> ChunkDraft:
        text = self._join(blocks)
        return ChunkDraft(
            text=text,
            token_count=self.count_tokens(text),
            page_start=min(block.page_start for block in blocks),
            page_end=max(block.page_end for block in blocks),
            section_path=list(blocks[-1].section_path),
            overlap_token_count=overlap,
        )

    def create_chunks(self, markdown: str) -> list[ChunkDraft]:
        blocks = self._expanded_blocks(self._parse_blocks(markdown))
        if not blocks:
            return []

        drafts: list[ChunkDraft] = []
        buffer: list[MarkdownBlock] = []
        overlap_count = 0

        for block in blocks:
            candidate = buffer + [block]
            if buffer and self.count_tokens(self._join(candidate)) > self.config.chunk_size:
                drafts.append(self._draft(buffer, overlap_count))
                overlap = self._overlap_blocks(buffer)
                if overlap and self.count_tokens(self._join(overlap + [block])) <= self.config.chunk_size:
                    buffer = overlap
                    overlap_count = self.count_tokens(self._join(overlap))
                else:
                    buffer = []
                    overlap_count = 0
            buffer.append(block)

        if buffer:
            drafts.append(self._draft(buffer, overlap_count))

        if (
            len(drafts) > 1
            and drafts[-1].token_count < self.config.minimum_chunk_size
            and self.count_tokens(drafts[-2].text + "\n\n" + drafts[-1].text)
            <= self.config.chunk_size
        ):
            previous = drafts[-2]
            last = drafts[-1]
            drafts[-2:] = [
                ChunkDraft(
                    text=previous.text + "\n\n" + last.text,
                    token_count=self.count_tokens(previous.text + "\n\n" + last.text),
                    page_start=previous.page_start,
                    page_end=last.page_end,
                    section_path=last.section_path,
                    overlap_token_count=previous.overlap_token_count,
                )
            ]
        return drafts

