from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    input_dir: Path
    recursive: bool = True


@dataclass(frozen=True)
class OutputConfig:
    root_dir: Path = Path("data/bases")
    base_name: str = "default"


@dataclass(frozen=True)
class PaddleOcrConfig:
    language: str = "pt"
    device: str = "cpu"
    minimum_confidence: float = 0.5
    use_doc_orientation_classify: bool = False
    use_doc_unwarping: bool = False
    use_textline_orientation: bool = False


@dataclass(frozen=True)
class ChunkingConfig:
    tokenizer_model: str = "gpt-4.1"
    chunk_size: int = 800
    chunk_overlap: int = 120
    minimum_chunk_size: int = 80


@dataclass(frozen=True)
class VectorStoreConfig:
    enabled: bool = True
    embedding_model: str = "intfloat/multilingual-e5-small"
    device: str | None = None
    batch_size: int = 32


@dataclass(frozen=True)
class RuntimeConfig:
    force: bool = False
    continue_on_error: bool = True


@dataclass(frozen=True)
class ClassificationConfig:
    """Controls automatic native vs scanned PDF detection."""

    min_chars_per_page: int = 50
    native_threshold: float = 0.80
    scanned_threshold: float = 0.20


@dataclass(frozen=True)
class IngestionConfig:
    source: SourceConfig
    output: OutputConfig = field(default_factory=OutputConfig)
    paddle_ocr: PaddleOcrConfig = field(default_factory=PaddleOcrConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "IngestionConfig":
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required to read ingestion configuration files."
            ) from exc

        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as stream:
            payload = yaml.safe_load(stream) or {}
        if not isinstance(payload, dict):
            raise ValueError("The YAML root must be a mapping.")
        return cls.from_mapping(payload)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "IngestionConfig":
        source_data = payload.get("source", {})
        output_data = payload.get("output", {})
        paddle_ocr_data = payload.get("paddle_ocr", {})
        chunking_data = payload.get("chunking", {})
        vector_store_data = payload.get("vector_store", {})
        runtime_data = payload.get("runtime", {})
        classification_data = payload.get("classification", {})

        input_dir = source_data.get("input_dir")
        if not input_dir:
            raise ValueError("source.input_dir is required.")

        config = cls(
            source=SourceConfig(
                input_dir=Path(input_dir).expanduser().resolve(),
                recursive=bool(source_data.get("recursive", True)),
            ),
            output=OutputConfig(
                root_dir=Path(output_data.get("root_dir", "data/bases"))
                .expanduser()
                .resolve(),
                base_name=str(output_data.get("base_name", "default")),
            ),
            paddle_ocr=PaddleOcrConfig(
                language=str(paddle_ocr_data.get("language", "pt")),
                device=str(paddle_ocr_data.get("device", "cpu")),
                minimum_confidence=float(
                    paddle_ocr_data.get("minimum_confidence", 0.5)
                ),
                use_doc_orientation_classify=bool(
                    paddle_ocr_data.get("use_doc_orientation_classify", False)
                ),
                use_doc_unwarping=bool(
                    paddle_ocr_data.get("use_doc_unwarping", False)
                ),
                use_textline_orientation=bool(
                    paddle_ocr_data.get("use_textline_orientation", False)
                ),
            ),
            chunking=ChunkingConfig(
                tokenizer_model=str(
                    chunking_data.get("tokenizer_model", "gpt-4.1")
                ),
                chunk_size=int(chunking_data.get("chunk_size", 800)),
                chunk_overlap=int(chunking_data.get("chunk_overlap", 120)),
                minimum_chunk_size=int(
                    chunking_data.get("minimum_chunk_size", 80)
                ),
            ),
            vector_store=VectorStoreConfig(
                enabled=bool(vector_store_data.get("enabled", True)),
                embedding_model=str(
                    vector_store_data.get(
                        "embedding_model", "intfloat/multilingual-e5-small"
                    )
                ),
                device=vector_store_data.get("device"),
                batch_size=int(vector_store_data.get("batch_size", 32)),
            ),
            runtime=RuntimeConfig(
                force=bool(runtime_data.get("force", False)),
                continue_on_error=bool(
                    runtime_data.get("continue_on_error", True)
                ),
            ),
            classification=ClassificationConfig(
                min_chars_per_page=int(
                    classification_data.get("min_chars_per_page", 50)
                ),
                native_threshold=float(
                    classification_data.get("native_threshold", 0.80)
                ),
                scanned_threshold=float(
                    classification_data.get("scanned_threshold", 0.20)
                ),
            ),
        )
        config.validate()
        return config

    @classmethod
    def for_directory(
        cls,
        input_dir: str | Path,
        base_name: str = "default",
        output_dir: str | Path = "data/bases",
        force: bool = False,
    ) -> "IngestionConfig":
        return cls.from_mapping(
            {
                "source": {"input_dir": str(input_dir)},
                "output": {
                    "root_dir": str(output_dir),
                    "base_name": base_name,
                },
                "runtime": {"force": force},
            }
        )

    @property
    def base_dir(self) -> Path:
        return self.output.root_dir / self.output.base_name

    def validate(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", self.output.base_name):
            raise ValueError(
                "output.base_name must contain only letters, numbers, '.', '_' or '-'."
            )
        if not self.paddle_ocr.language.strip():
            raise ValueError("paddle_ocr.language cannot be empty.")
        if not 0 <= self.paddle_ocr.minimum_confidence <= 1:
            raise ValueError(
                "paddle_ocr.minimum_confidence must be between zero and one."
            )
        if self.chunking.chunk_size <= 0:
            raise ValueError("chunking.chunk_size must be greater than zero.")
        if self.chunking.chunk_overlap < 0:
            raise ValueError("chunking.chunk_overlap cannot be negative.")
        if self.chunking.chunk_overlap >= self.chunking.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size.")
        if not 0 <= self.chunking.minimum_chunk_size <= self.chunking.chunk_size:
            raise ValueError("minimum_chunk_size must be between zero and chunk_size.")
        if not self.vector_store.embedding_model.strip():
            raise ValueError("vector_store.embedding_model cannot be empty.")
        if self.vector_store.batch_size <= 0:
            raise ValueError("vector_store.batch_size must be greater than zero.")

    def to_manifest_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source"]["input_dir"] = str(self.source.input_dir)
        data["output"]["root_dir"] = str(self.output.root_dir)
        return data
