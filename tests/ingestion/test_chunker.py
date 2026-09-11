from src.ingestion.chunkers import MarkdownChunker
from src.ingestion.config import ChunkingConfig
from src.ingestion.extractors import PAGE_BREAK_MARKER
from src.ingestion.normalizers import MarkdownNormalizer


def make_chunker(size: int = 50, overlap: int = 10) -> MarkdownChunker:
    return MarkdownChunker(
        ChunkingConfig(
            chunk_size=size,
            chunk_overlap=overlap,
            minimum_chunk_size=0,
        )
    )


def test_chunker_preserves_sections_pages_and_limits():
    markdown = (
        "# Manual\n\n"
        + "Primeira seção com conteúdo detalhado. " * 8
        + f"\n\n{PAGE_BREAK_MARKER}\n\n"
        + "## Instalação\n\n"
        + "Segunda seção com outros detalhes importantes. " * 8
    )
    chunks = make_chunker().create_chunks(markdown)
    assert len(chunks) >= 2
    assert all(chunk.token_count <= 50 for chunk in chunks)
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    assert chunks[-1].section_path == ["Manual", "Instalação"]


def test_large_table_repeats_header_when_split():
    rows = "\n".join(f"| Item {index} | Descrição extensa {index} |" for index in range(30))
    markdown = "| Item | Descrição |\n| --- | --- |\n" + rows
    chunks = make_chunker(size=80, overlap=10).create_chunks(markdown)
    assert len(chunks) > 1
    assert all(chunk.text.startswith("| Item | Descrição |") for chunk in chunks)
    assert all(chunk.token_count <= 80 for chunk in chunks)


def test_normalizer_preserves_page_marker_and_markdown():
    raw = "# Título  \r\n\r\n\r\nTexto  \r\n<!-- page-break -->\r\n| A | B |\r\n"
    normalized = MarkdownNormalizer().normalize(raw)
    assert "# Título\n\nTexto" in normalized
    assert f"\n\n{PAGE_BREAK_MARKER}\n\n" in normalized
    assert "| A | B |" in normalized
