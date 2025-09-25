"""
Text Chunking Service
Splits documents into semantic chunks for RAG processing
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Data class for document chunks"""
    content: str
    chunk_index: int
    chunk_size: int
    start_position: int
    end_position: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChunkingService:
    """
    Service for splitting documents into semantic chunks
    Optimized for Portuguese text and RAG retrieval
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize chunking service

        Args:
            chunk_size: Size of each chunk in tokens
            chunk_overlap: Overlap between chunks in tokens
            embedding_model: Model to use for tokenization
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL

        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.embedding_model)
        except Exception as e:
            logger.warning(f"Could not load tokenizer for {self.embedding_model}: {e}")
            logger.info("Using default tokenizer")
            self.tokenizer = AutoTokenizer.from_pretrained("bert-base-multilingual-cased")

        # Portuguese-specific separators for better chunking
        self.separators = [
            "\n\n\n",  # Triple line breaks (major sections)
            "\n\n",    # Double line breaks (paragraphs)
            "\n",      # Single line breaks
            ". ",      # Sentence endings
            "! ",      # Exclamations
            "? ",      # Questions
            "; ",      # Semicolons
            ", ",      # Commas
            " ",       # Spaces
            "",        # Characters
        ]

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self._token_length,
            separators=self.separators,
            keep_separator=True,
        )

    def _token_length(self, text: str) -> int:
        """Calculate token length of text"""
        try:
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
            return len(tokens)
        except Exception:
            # Fallback to character-based estimation
            return len(text) // 4  # Rough approximation

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into chunks

        Args:
            text: Text to split
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        # Pre-process text
        processed_text = self._preprocess_text(text)

        # Extract sections if markdown
        sections = self._extract_sections(processed_text)

        chunks = []
        overall_position = 0

        for section in sections:
            section_title = section.get("title")
            section_text = section.get("content", "")
            page_number = section.get("page_number")

            if not section_text.strip():
                continue

            # Split section into chunks
            section_chunks = self.text_splitter.split_text(section_text)

            for chunk_content in section_chunks:
                if not chunk_content.strip():
                    continue

                chunk_size = self._token_length(chunk_content)
                end_position = overall_position + len(chunk_content)

                chunk = Chunk(
                    content=chunk_content,
                    chunk_index=len(chunks),
                    chunk_size=chunk_size,
                    start_position=overall_position,
                    end_position=end_position,
                    page_number=page_number,
                    section_title=section_title,
                    metadata=metadata,
                )

                chunks.append(chunk)
                overall_position = end_position

        logger.info(f"Created {len(chunks)} chunks from text of length {len(text)}")
        return chunks

    def _preprocess_text(self, text: str) -> str:
        """
        Pre-process text for better chunking

        Args:
            text: Raw text

        Returns:
            Processed text
        """
        # Remove excessive whitespace
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        text = re.sub(r' {2,}', ' ', text)

        # Fix common encoding issues
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u200b', '')   # Zero-width space

        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")

        return text.strip()

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract sections from markdown text

        Args:
            text: Markdown text

        Returns:
            List of sections with titles and content
        """
        sections = []

        # Check if text is markdown
        if not self._is_markdown(text):
            # Return entire text as single section
            return [{"title": None, "content": text}]

        # Split by markdown headers
        header_pattern = r'^(#{1,6})\s+(.+)$'
        lines = text.split('\n')

        current_section = {"title": None, "content": [], "level": 0}
        current_page = None

        for line in lines:
            # Check for page markers
            page_match = re.match(r'<!--\s*page\s*(\d+)\s*-->', line, re.IGNORECASE)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            # Check for headers
            header_match = re.match(header_pattern, line)
            if header_match:
                # Save current section if it has content
                if current_section["content"]:
                    current_section["content"] = '\n'.join(current_section["content"])
                    if current_page:
                        current_section["page_number"] = current_page
                    sections.append(current_section)

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    "title": title,
                    "content": [],
                    "level": level,
                }
            else:
                current_section["content"].append(line)

        # Add last section
        if current_section["content"]:
            current_section["content"] = '\n'.join(current_section["content"])
            if current_page:
                current_section["page_number"] = current_page
            sections.append(current_section)

        # If no sections found, return entire text
        if not sections:
            sections = [{"title": None, "content": text}]

        return sections

    def _is_markdown(self, text: str) -> bool:
        """Check if text appears to be markdown"""
        markdown_indicators = [
            r'^#{1,6}\s+',  # Headers
            r'\[.+\]\(.+\)',  # Links
            r'^\*{1,2}.+\*{1,2}',  # Bold/italic
            r'^\s*[-*+]\s+',  # Lists
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^```',  # Code blocks
        ]

        for pattern in markdown_indicators:
            if re.search(pattern, text, re.MULTILINE):
                return True
        return False

    def smart_chunk(
        self,
        text: str,
        min_chunk_size: int = 100,
        max_chunk_size: Optional[int] = None
    ) -> List[Chunk]:
        """
        Smart chunking that respects semantic boundaries

        Args:
            text: Text to chunk
            min_chunk_size: Minimum chunk size in tokens
            max_chunk_size: Maximum chunk size in tokens

        Returns:
            List of chunks
        """
        max_chunk_size = max_chunk_size or self.chunk_size * 2

        # First, do regular chunking
        initial_chunks = self.chunk_text(text)

        # Merge small chunks
        merged_chunks = []
        buffer_chunk = None

        for chunk in initial_chunks:
            if chunk.chunk_size < min_chunk_size:
                if buffer_chunk is None:
                    buffer_chunk = chunk
                else:
                    # Merge with buffer
                    buffer_chunk = self._merge_chunks(buffer_chunk, chunk)

                    # Check if buffer is now large enough
                    if buffer_chunk.chunk_size >= min_chunk_size:
                        merged_chunks.append(buffer_chunk)
                        buffer_chunk = None
            else:
                # Add buffer if exists
                if buffer_chunk:
                    merged_chunks.append(buffer_chunk)
                    buffer_chunk = None

                # Add current chunk
                merged_chunks.append(chunk)

        # Add remaining buffer
        if buffer_chunk:
            merged_chunks.append(buffer_chunk)

        # Re-index chunks
        for i, chunk in enumerate(merged_chunks):
            chunk.chunk_index = i

        return merged_chunks

    def _merge_chunks(self, chunk1: Chunk, chunk2: Chunk) -> Chunk:
        """Merge two chunks"""
        merged_content = f"{chunk1.content}\n{chunk2.content}"

        return Chunk(
            content=merged_content,
            chunk_index=chunk1.chunk_index,
            chunk_size=self._token_length(merged_content),
            start_position=chunk1.start_position,
            end_position=chunk2.end_position,
            page_number=chunk1.page_number,
            section_title=chunk1.section_title or chunk2.section_title,
            metadata={**(chunk1.metadata or {}), **(chunk2.metadata or {})}
        )

    def create_overlapping_chunks(
        self,
        text: str,
        overlap_ratio: float = 0.2
    ) -> List[Chunk]:
        """
        Create overlapping chunks for better context preservation

        Args:
            text: Text to chunk
            overlap_ratio: Ratio of overlap (0.2 = 20% overlap)

        Returns:
            List of overlapping chunks
        """
        # Calculate overlap in tokens
        overlap_tokens = int(self.chunk_size * overlap_ratio)

        # Update text splitter with new overlap
        original_overlap = self.chunk_overlap
        self.chunk_overlap = overlap_tokens
        self.text_splitter.chunk_overlap = overlap_tokens

        # Create chunks
        chunks = self.chunk_text(text)

        # Restore original overlap
        self.chunk_overlap = original_overlap
        self.text_splitter.chunk_overlap = original_overlap

        return chunks

    async def chunk_text_async(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        document_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Async wrapper for text chunking
        Returns list of dicts for use in background tasks

        Args:
            text: Text to chunk
            chunk_size: Size of chunks (optional)
            chunk_overlap: Overlap between chunks (optional)
            document_id: ID of the document being chunked

        Returns:
            List of chunk dictionaries
        """
        import asyncio

        # Update chunking parameters if provided
        if chunk_size:
            self.chunk_size = chunk_size
            self.text_splitter.chunk_size = chunk_size
        if chunk_overlap:
            self.chunk_overlap = chunk_overlap
            self.text_splitter.chunk_overlap = chunk_overlap

        # Run the sync method in a thread pool
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            None,
            self.chunk_text,
            text,
            {"document_id": document_id} if document_id else None
        )

        # Convert Chunk objects to dicts for serialization
        return [
            {
                "text": chunk.content,
                "chunk_index": chunk.chunk_index,
                "chunk_size": chunk.chunk_size,
                "start_position": chunk.start_position,
                "end_position": chunk.end_position,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "metadata": chunk.metadata or {}
            }
            for chunk in chunks
        ]