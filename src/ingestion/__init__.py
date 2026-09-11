"""Generic PDF ingestion pipeline."""

from .config import IngestionConfig
from .pipeline import IngestionPipeline

__all__ = ["IngestionConfig", "IngestionPipeline"]

