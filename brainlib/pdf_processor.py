"""
Cortex - PDF Processing Module

This module provides PDF processing functionality for:
- Extracting text from PDF files
- Handling PDF metadata
- Preparing PDF content for storage and clustering
"""

import os
import logging
import tempfile
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

# PDF Processing
import PyPDF2
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF processing functionality for text extraction and metadata handling."""
    
    def __init__(self):
        """Initialize the PDF processor."""
        pass
    
    def extract_text_from_pdf(self, pdf_file: bytes, filename: str) -> Dict[str, Any]:
        """Extract text and metadata from a PDF file."""
        try:
            pdf_stream = BytesIO(pdf_file)
            
            # Open PDF with PyPDF2
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            text_content = []
            total_pages = len(pdf_reader.pages)
            
            for page_num in range(total_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content.append(page_text.strip())
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
            
            full_text = "\n\n--- Page Break ---\n\n".join(text_content)
            
            metadata = self._extract_metadata(pdf_reader, filename)
            
            pdf_id = str(uuid.uuid4())
            
            result = {
                "pdf_id": pdf_id,
                "filename": filename,
                "text_content": full_text,
                "total_pages": total_pages,
                "pages_with_text": len(text_content),
                "metadata": metadata,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "file_size_bytes": len(pdf_file)
            }
            
            logger.info(f"Successfully extracted text from PDF: {filename} ({total_pages} pages)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {filename}: {e}")
            raise
    
    def _extract_metadata(self, pdf_reader: PyPDF2.PdfReader, filename: str) -> Dict[str, Any]:
        """Extract metadata from PDF reader object."""
        metadata = {
            "filename": filename,
            "total_pages": len(pdf_reader.pages),
            "pdf_version": None,
            "title": None,
            "author": None,
            "subject": None,
            "creator": None,
            "producer": None,
            "creation_date": None,
            "modification_date": None
        }
        
        try:
            if pdf_reader.metadata:
                metadata.update({
                    "title": pdf_reader.metadata.get('/Title'),
                    "author": pdf_reader.metadata.get('/Author'),
                    "subject": pdf_reader.metadata.get('/Subject'),
                    "creator": pdf_reader.metadata.get('/Creator'),
                    "producer": pdf_reader.metadata.get('/Producer'),
                    "creation_date": pdf_reader.metadata.get('/CreationDate'),
                    "modification_date": pdf_reader.metadata.get('/ModDate')
                })
        except Exception as e:
            logger.warning(f"Failed to extract metadata from PDF {filename}: {e}")
        
        return metadata
    
    def validate_pdf(self, pdf_file: bytes, filename: str) -> Tuple[bool, str]:
        """Validate that the file is a valid PDF."""
        try:
            if not filename.lower().endswith('.pdf'):
                return False, "File must have .pdf extension"
            
            # Check file size (max 50MB)
            if len(pdf_file) > 50 * 1024 * 1024:
                return False, "File size must be less than 50MB"
            
            pdf_stream = BytesIO(pdf_file)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            if len(pdf_reader.pages) == 0:
                return False, "PDF file appears to be empty or corrupted"
            
            return True, "PDF is valid"
            
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"
    
    def split_text_into_chunks(self, text: str, max_chunk_size: int = 1000) -> list[str]:
        """Split large text content into manageable chunks for processing."""
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

# Standalone functions for command line usage
def extract_text_from_pdf_file(pdf_file_path: str) -> Dict[str, Any]:
    """Extract text from a PDF file on disk."""
    try:
        with open(pdf_file_path, 'rb') as file:
            pdf_bytes = file.read()
        
        processor = PDFProcessor()
        return processor.extract_text_from_pdf(pdf_bytes, os.path.basename(pdf_file_path))
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF file {pdf_file_path}: {e}")
        raise

def validate_pdf_file(pdf_file_path: str) -> Tuple[bool, str]:
    """Validate a PDF file on disk."""
    try:
        with open(pdf_file_path, 'rb') as file:
            pdf_bytes = file.read()
        
        processor = PDFProcessor()
        return processor.validate_pdf(pdf_bytes, os.path.basename(pdf_file_path))
        
    except Exception as e:
        return False, f"Failed to validate PDF file {pdf_file_path}: {str(e)}"

def handle_command_line():
    """Handle command line arguments for standalone PDF processing."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "PDF file path required"}))
        return
    
    pdf_file_path = sys.argv[1]
    
    try:
        is_valid, error_message = validate_pdf_file(pdf_file_path)
        if not is_valid:
            print(json.dumps({"error": error_message}))
            return
        
        result = extract_text_from_pdf_file(pdf_file_path)
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    import json
    import sys
    handle_command_line() 