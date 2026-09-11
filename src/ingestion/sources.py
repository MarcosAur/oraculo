from __future__ import annotations

from pathlib import Path

from .models import SourceDocument


class DirectoryPdfSource:
    """Discovers PDF files under one local directory."""

    def __init__(self, input_dir: Path, recursive: bool = True):
        self.input_dir = input_dir
        self.recursive = recursive

    def discover(self) -> list[SourceDocument]:
        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_dir}")
        if not self.input_dir.is_dir():
            raise NotADirectoryError(
                f"Configured input path is not a directory: {self.input_dir}"
            )

        iterator = self.input_dir.rglob("*") if self.recursive else self.input_dir.iterdir()
        paths = sorted(
            (
                path
                for path in iterator
                if path.is_file() and path.suffix.lower() == ".pdf"
            ),
            key=lambda path: path.relative_to(self.input_dir).as_posix().casefold(),
        )
        return [
            SourceDocument(
                path=str(path.resolve()),
                relative_path=path.relative_to(self.input_dir).as_posix(),
                file_name=path.name,
                size_bytes=path.stat().st_size,
            )
            for path in paths
        ]

