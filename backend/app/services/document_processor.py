"""
Document Processing Service using Docling
Handles PDF, DOCX, PPTX, and other document formats
"""
import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Docling imports
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

logger = logging.getLogger(__name__)


class DocumentProcessorService:
    """
    Service for processing documents using Docling
    Converts various formats to markdown for RAG processing
    """

    def __init__(self):
        """Initialize Docling converter with optimized settings"""
        try:
            # Configure pipeline options for best quality
            pipeline_options = PipelineOptions(
                do_ocr=False,  # Disable OCR initially for faster processing
                do_table_structure=True,  # Enable table extraction
                table_structure_options={
                    "mode": "fast",  # Use fast mode for tables
                    "do_cell_matching": True,
                }
            )

            # Initialize converter
            self.converter = DocumentConverter(
                pipeline_options=pipeline_options,
                pdf_backend=PyPdfiumDocumentBackend,  # Use PyPdfium2 for better PDF support
            )

            logger.info("Docling converter initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            # Fallback to basic converter
            self.converter = DocumentConverter()

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

            # Calculate file checksum
            checksum = self._calculate_checksum(file_path)

            # Determine output directory
            if not output_dir:
                output_dir = file_path_obj.parent / "processed"

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Processing document: {file_path}")

            # Convert document
            start_time = datetime.utcnow()

            # Update OCR setting if needed
            if enable_ocr and hasattr(self.converter, 'pipeline_options'):
                self.converter.pipeline_options.do_ocr = True

            # Perform conversion
            result = self.converter.convert(file_path)

            # Extract markdown content
            markdown_content = result.document.export_to_markdown()

            # Extract metadata
            metadata = self._extract_metadata(result)

            # Save markdown file
            markdown_file = output_path / f"{file_path_obj.stem}.md"
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            processing_time = (datetime.utcnow() - start_time).total_seconds()

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
            # Get document metadata if available
            if hasattr(result, 'document'):
                doc = result.document

                # Extract basic metadata
                if hasattr(doc, 'metadata'):
                    doc_meta = doc.metadata
                    metadata.update({
                        "title": getattr(doc_meta, 'title', ''),
                        "author": getattr(doc_meta, 'author', ''),
                        "subject": getattr(doc_meta, 'subject', ''),
                        "keywords": getattr(doc_meta, 'keywords', ''),
                        "creation_date": str(getattr(doc_meta, 'creation_date', '')),
                        "modification_date": str(getattr(doc_meta, 'modification_date', '')),
                    })

                # Extract page information
                if hasattr(doc, 'pages'):
                    metadata["page_count"] = len(doc.pages)

                # Extract table information
                if hasattr(doc, 'tables'):
                    metadata["table_count"] = len(doc.tables)
                    metadata["has_tables"] = len(doc.tables) > 0

                # Extract image information
                if hasattr(doc, 'figures'):
                    metadata["figure_count"] = len(doc.figures)
                    metadata["has_figures"] = len(doc.figures) > 0

        except Exception as e:
            logger.warning(f"Could not extract some metadata: {e}")

        return metadata

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
            return result.document.export_to_markdown()
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