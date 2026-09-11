from pathlib import Path

import pytest

from src.ingestion.config import IngestionConfig


def test_config_uses_generic_defaults(tmp_path: Path):
    config = IngestionConfig.from_mapping(
        {
            "source": {"input_dir": str(tmp_path)},
            "output": {"root_dir": str(tmp_path / "out"), "base_name": "manuals"},
        }
    )
    assert config.source.input_dir == tmp_path.resolve()
    assert config.paddle_ocr.language == "pt"
    assert config.paddle_ocr.minimum_confidence == 0.5
    assert config.chunking.chunk_size == 800


@pytest.mark.parametrize("name", ["with spaces", "../escape", ""])
def test_config_rejects_invalid_base_names(tmp_path: Path, name: str):
    with pytest.raises(ValueError):
        IngestionConfig.from_mapping(
            {
                "source": {"input_dir": str(tmp_path)},
                "output": {"base_name": name},
            }
        )


def test_config_rejects_overlap_larger_than_chunk(tmp_path: Path):
    with pytest.raises(ValueError, match="chunk_overlap"):
        IngestionConfig.from_mapping(
            {
                "source": {"input_dir": str(tmp_path)},
                "chunking": {"chunk_size": 100, "chunk_overlap": 100},
            }
        )


def test_config_rejects_invalid_ocr_confidence(tmp_path: Path):
    with pytest.raises(ValueError, match="minimum_confidence"):
        IngestionConfig.from_mapping(
            {
                "source": {"input_dir": str(tmp_path)},
                "paddle_ocr": {"minimum_confidence": 1.1},
            }
        )
