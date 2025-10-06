"""
Document Processing Service using Docling
Handles PDF, DOCX, PPTX, and other document formats
"""
import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# Docling imports
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


class DocumentProcessorService:
    """
    Service for processing documents using Docling
    Converts various formats to markdown for RAG processing
    """

    def __init__(self):
        """Initialize Docling converter with optimized settings"""
        try:
            # Initialize converter with basic settings for v2
            self.converter = DocumentConverter()
            logger.info("✅ Docling converter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            raise

    def process_document(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
        enable_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        Process a document and convert to markdown

        Args:
            file_path: Path to the document file
            output_dir: Directory to save processed files
            enable_ocr: Whether to enable OCR for scanned documents

        Returns:
            Dictionary with processing results
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            file_path_obj = Path(file_path)
            file_size = file_path_obj.stat().st_size
            file_ext = file_path_obj.suffix.lower()

            # Calculate file checksum
            checksum = self._calculate_checksum(file_path)

            # Determine output directory
            if not output_dir:
                output_dir = file_path_obj.parent / "processed"

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Processing document: {file_path}")

            # Convert document
            start_time = datetime.now(timezone.utc)

            # Check if format is supported by Docling
            if file_ext in ['.txt', '.text']:
                # Handle plain text files with intelligent markdown conversion
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                markdown_content = self._convert_text_to_markdown(text_content)
                metadata = {
                    "page_count": 1,
                    "format": "text",
                    "converted_to_markdown": True
                }
            else:
                # Use Docling for supported formats
                result = self.converter.convert(file_path)

                # Extract markdown content from v2 API
                # In Docling v2, we need to access the document and export to markdown
                if hasattr(result, 'document') and result.document:
                    doc = result.document
                    if hasattr(doc, 'export_to_markdown'):
                        markdown_content = doc.export_to_markdown()
                    else:
                        # Try alternative methods
                        markdown_content = str(doc)
                elif hasattr(result, 'to_markdown'):
                    markdown_content = result.to_markdown()
                elif hasattr(result, 'export_to_markdown'):
                    markdown_content = result.export_to_markdown()
                else:
                    # Last fallback: try to get text representation
                    markdown_content = str(result)

                # Extract metadata
                metadata = self._extract_metadata(result)

            # Save markdown file
            markdown_file = output_path / f"{file_path_obj.stem}.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

            # Prepare result
            result_dict = {
                "success": True,
                "file_path": str(file_path),
                "output_path": str(markdown_file),
                "markdown_content": markdown_content,
                "file_size": file_size,
                "checksum": checksum,
                "processing_time": processing_time,
                "metadata": metadata,
                "page_count": metadata.get("page_count", 0),
                "word_count": len(markdown_content.split()),
                "character_count": len(markdown_content),
            }

            logger.info(f"Document processed successfully: {file_path}")
            return result_dict

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {
                "success": False,
                "file_path": str(file_path),
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_metadata(self, result) -> Dict[str, Any]:
        """Extract metadata from Docling result"""
        metadata = {}

        try:
            # Extract metadata based on Docling v2 structure
            doc = result if not hasattr(result, 'document') else result.document

            # Try to get page count
            if hasattr(doc, 'pages'):
                metadata["page_count"] = len(doc.pages)
            elif hasattr(doc, 'num_pages'):
                metadata["page_count"] = doc.num_pages
            else:
                metadata["page_count"] = 1

            # Try to extract other metadata if available
            if hasattr(doc, 'metadata'):
                doc_meta = doc.metadata
                if isinstance(doc_meta, dict):
                    metadata.update(doc_meta)
                else:
                    for attr in ['title', 'author', 'subject', 'keywords']:
                        if hasattr(doc_meta, attr):
                            metadata[attr] = getattr(doc_meta, attr, '')

        except Exception as e:
            logger.warning(f"Could not extract some metadata: {e}")

        return metadata

    def _convert_text_to_markdown(self, text_content: str) -> str:
        """
        Convert plain text to markdown with intelligent formatting

        Args:
            text_content: Raw text content

        Returns:
            Formatted markdown content
        """
        import re

        # Split into lines for processing
        lines = text_content.split('\n')
        markdown_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                # Empty line
                markdown_lines.append('')
                i += 1
                continue

            # Check for section headers (lines followed by underlines or starting with common header patterns)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and all(c in '=-~^' for c in next_line) and len(next_line) >= len(stripped) // 2:
                    # This looks like an underlined header
                    if '=' in next_line:
                        markdown_lines.append(f"# {stripped}")
                    else:
                        markdown_lines.append(f"## {stripped}")
                    i += 2  # Skip the underline
                    continue

            # Check for numbered sections like "Seção 1:", "1.", "1)", "Section 1", etc.
            if re.match(r'^(seção|section|capítulo|chapter|parte|part)\s*\d+[:.)]?\s*[-:]?\s*', stripped, re.IGNORECASE):
                markdown_lines.append(f"## {stripped}")
                i += 1
                continue

            # Check for list items starting with -, *, +, or numbers
            if re.match(r'^[-*+•]\s+', stripped) or re.match(r'^\d+[.)]\s+', stripped):
                markdown_lines.append(stripped)
                i += 1
                continue

            # Check for lines that look like titles (short lines, possibly followed by empty line)
            if (len(stripped) < 80 and
                not stripped.endswith('.') and
                not stripped.endswith(',') and
                not stripped.endswith(':') and
                i + 1 < len(lines) and
                lines[i + 1].strip() == ''):
                # Could be a header
                markdown_lines.append(f"## {stripped}")
                i += 1
                continue

            # Check for lines ending with colon (could be subheaders)
            if stripped.endswith(':') and len(stripped) < 100:
                markdown_lines.append(f"### {stripped[:-1]}")
                i += 1
                continue

            # Regular paragraph text
            markdown_lines.append(stripped)
            i += 1

        # Join lines and clean up formatting
        markdown_content = '\n'.join(markdown_lines)

        # Clean up multiple consecutive empty lines
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)

        # Ensure proper spacing around headers
        markdown_content = re.sub(r'(\n#{1,6}[^\n]+)', r'\n\1', markdown_content)
        markdown_content = re.sub(r'(#{1,6}[^\n]+)\n(?=[^\n#])', r'\1\n\n', markdown_content)

        return markdown_content.strip()

    def batch_process(
        self,
        file_paths: List[str],
        output_dir: Optional[str] = None,
        enable_ocr: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch

        Args:
            file_paths: List of file paths to process
            output_dir: Directory to save processed files
            enable_ocr: Whether to enable OCR

        Returns:
            List of processing results
        """
        results = []
        total = len(file_paths)

        for idx, file_path in enumerate(file_paths, 1):
            logger.info(f"Processing document {idx}/{total}: {file_path}")
            result = self.process_document(file_path, output_dir, enable_ocr)
            results.append(result)

        # Summary statistics
        successful = sum(1 for r in results if r.get("success"))
        failed = total - successful

        logger.info(f"Batch processing complete: {successful} successful, {failed} failed")

        return results

    def extract_text_only(self, file_path: str) -> Optional[str]:
        """
        Quick text extraction without full processing

        Args:
            file_path: Path to the document

        Returns:
            Extracted text or None if failed
        """
        try:
            result = self.converter.convert(file_path)
            if hasattr(result, 'to_markdown'):
                return result.to_markdown()
            elif hasattr(result, 'export_to_markdown'):
                return result.export_to_markdown()
            else:
                return str(result)
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return None

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return [
            ".pdf",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".xlsx",
            ".xls",
            ".html",
            ".md",
            ".txt",
            ".rtf",
            ".odt",
            ".epub",
        ]

    def is_format_supported(self, file_path: str) -> bool:
        """Check if file format is supported"""
        ext = Path(file_path).suffix.lower()
        return ext in self.get_supported_formats()

    async def process_document_async(
        self,
        file_path: str,
        output_dir: Optional[str] = None,
        enable_ocr: bool = False
    ) -> str:
        """
        Async wrapper for document processing
        Returns markdown content directly for use in background tasks

        Args:
            file_path: Path to the document file
            output_dir: Directory to save processed files
            enable_ocr: Whether to enable OCR for scanned documents

        Returns:
            Markdown content as string
        """
        import asyncio

        # Run the sync method in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.process_document,
            file_path,
            output_dir,
            enable_ocr
        )

        if result.get("success"):
            return result.get("markdown_content", "")
        else:
            raise Exception(f"Document processing failed: {result.get('error', 'Unknown error')}")