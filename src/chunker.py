import tiktoken
from typing import List, Dict, Any

class ParagraphChunker:
    """
    A processor to split text into paragraph-based chunks,
    with a configurable token-based overlap from the previous paragraph.
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        """
        Initializes the chunker with a tiktoken encoder.
        
        Args:
            model_name: The model to choose the tokenizer encoding (e.g., 'gpt-4', 'gpt-3.5-turbo').
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base if model name is not found
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def split_paragraphs(self, text: str) -> List[str]:
        """
        Splits input text into paragraphs by double newlines.
        
        Args:
            text: The raw input text.
            
        Returns:
            A list of non-empty cleaned paragraphs.
        """
        raw_paragraphs = text.split("\n\n")
        paragraphs = []
        for p in raw_paragraphs:
            clean_p = p.strip()
            if clean_p:
                paragraphs.append(clean_p)
        return paragraphs

    def create_chunks(self, paragraphs: List[str], overlap_percentage: float = 0.20) -> List[Dict[str, Any]]:
        """
        Creates chunks from paragraphs where each chunk i contains Paragraph i,
        prepended with the last overlap_percentage of tokens from Paragraph i-1.
        
        Args:
            paragraphs: List of paragraph strings.
            overlap_percentage: Float representing the fraction of previous paragraph tokens to overlap.
            
        Returns:
            A list of dictionaries containing metadata, chunk text, and token lists.
        """
        chunks = []
        
        # Tokenize all paragraphs
        tokenized_paragraphs = [self.encoding.encode(p) for p in paragraphs]
        
        for i, current_tokens in enumerate(tokenized_paragraphs):
            overlap_tokens = []
            if i > 0:
                prev_tokens = tokenized_paragraphs[i - 1]
                # Calculate overlap length as 20% of previous paragraph's tokens
                overlap_len = int(round(len(prev_tokens) * overlap_percentage))
                if overlap_len > 0:
                    overlap_tokens = prev_tokens[-overlap_len:]
            
            # Combine overlap from previous paragraph + current paragraph tokens
            combined_tokens = overlap_tokens + current_tokens
            
            # Decode back to string
            chunk_text = self.encoding.decode(combined_tokens)
            overlap_text = self.encoding.decode(overlap_tokens) if overlap_tokens else ""
            
            chunks.append({
                "chunk_index": i + 1,
                "text": chunk_text,
                "overlap_text": overlap_text,
                "paragraph_text": paragraphs[i],
                "tokens": combined_tokens,
                "token_count": len(combined_tokens),
                "overlap_token_count": len(overlap_tokens),
                "original_token_count": len(current_tokens)
            })
            
        return chunks
