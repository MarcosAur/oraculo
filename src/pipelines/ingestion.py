import json
import os
from chunker import ParagraphChunker

class IngestionPipeline:
    """
    Pipeline responsible for loading raw text, dividing it into paragraphs,
    generating chunks with 20% token overlap, and saving the results to a JSON file.
    """
    
    def __init__(self, output_path: str = "data/chunks_cache.json"):
        """
        Initializes the ingestion pipeline.
        
        Args:
            output_path: Path where the processed chunks will be stored.
        """
        self.output_path = output_path
        self.chunker = ParagraphChunker(model_name="gpt-4.1")

    def run(self, raw_text: str) -> None:
        """
        Runs the ingestion pipeline on the provided raw text.
        
        Args:
            raw_text: The base text to ingest.
        """
        # 1. Split text into paragraphs
        paragraphs = self.chunker.split_paragraphs(raw_text)

        
        # 2. Create chunks with 20% overlap
        chunks = self.chunker.create_chunks(paragraphs, overlap_percentage=0.20)
        
        # 3. Persist the chunks to disk (simulated storage)
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=4)
            
        print(f"[Ingestion] Processed base text. Saved {len(chunks)} chunks to {self.output_path}.")
