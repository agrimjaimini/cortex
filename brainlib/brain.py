"""
Digital Second Brain - Core Brain Module

This is the main brain of the Digital Second Brain app. It handles:
- Converting your text notes into embeddings so the system can understand them
- Storing notes and their representations in the database
- Retrieving notes when you need them
- Processing PDF files and extracting their text content
"""

import json
import logging
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from sentence_transformers import SentenceTransformer

try:
    from .pdf_processor import PDFProcessor
except ImportError:
    from pdf_processor import PDFProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrainCore:
    """The core brain that handles storing and retrieving your notes with embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Set up the model for understanding text."""
        self.model_name = model_name
        self.model = None
        self.pdf_processor = PDFProcessor()
        self._load_model()
    
    def _load_model(self):
        """Load the model that will understand your notes."""
        try:
            logger.info(f"Loading model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def embed_text(self, note: str) -> List[float]:
        """Convert your text note into an embedding that captures its meaning."""
        if not note or not note.strip():
            raise ValueError("Note cannot be empty")
        
        if self.model is None:
            raise RuntimeError("model not loaded")
        
        try:
            embedding = self.model.encode(note, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to convert text to embedding: {e}")
            raise
    
    def store_note(self, note: str, db_uri: str = "mongodb://localhost:27017") -> str:
        """Save your note along with its embedding in the database."""
        if not note or not note.strip():
            raise ValueError("Note cannot be empty")
        
        embedding = self.embed_text(note)
        
        note_id = str(uuid.uuid4())
        document = {
            "_id": note_id,
            "note": note.strip(),
            "embedding": embedding,
            "type": "text",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        try:
            client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            logger.info("Successfully connected to database")
            
            db = client.notes_db
            collection = db.notes
            
            result = collection.insert_one(document)
            
            if result.inserted_id:
                logger.info(f"Successfully stored note with ID: {note_id}")
                return note_id
            else:
                raise Exception("Failed to save note to database")
                
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Database connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to store note: {e}")
            raise
        finally:
            if 'client' in locals():
                client.close()
    
    def store_pdf(self, pdf_file: bytes, filename: str, db_uri: str = "mongodb://localhost:27017") -> Dict[str, Any]:
        """Process and store a PDF file, extracting its text and creating embeddings."""
        try:
            is_valid, error_message = self.pdf_processor.validate_pdf(pdf_file, filename)
            if not is_valid:
                raise ValueError(error_message)
            
            pdf_data = self.pdf_processor.extract_text_from_pdf(pdf_file, filename)
            
            if not pdf_data["text_content"].strip():
                raise ValueError("No text content could be extracted from the PDF")
            
            embedding = self.embed_text(pdf_data["text_content"])
            
            pdf_id = pdf_data["pdf_id"]
            document = {
                "_id": pdf_id,
                "note": pdf_data["text_content"],
                "embedding": embedding,
                "type": "pdf",
                "filename": filename,
                "pdf_metadata": pdf_data["metadata"],
                "total_pages": pdf_data["total_pages"],
                "pages_with_text": pdf_data["pages_with_text"],
                "file_size_bytes": pdf_data["file_size_bytes"],
                "extraction_timestamp": pdf_data["extraction_timestamp"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            
            db = client.notes_db
            collection = db.notes
            
            result = collection.insert_one(document)
            
            if result.inserted_id:
                logger.info(f"Successfully processed and stored PDF with ID: {pdf_id}")
                return {
                    "pdf_id": pdf_id,
                    "filename": filename,
                    "total_pages": pdf_data["total_pages"],
                    "pages_with_text": pdf_data["pages_with_text"],
                    "file_size_bytes": pdf_data["file_size_bytes"],
                    "success": True
                }
            else:
                raise Exception("Failed to save PDF to database")
                
        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {e}")
            raise
        finally:
            if 'client' in locals():
                client.close()
    
    def get_all_notes(self, db_uri: str = "mongodb://localhost:27017") -> List[Dict[str, Any]]:
        """Retrieve all your stored notes from the database."""
        try:
            client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            
            db = client.notes_db
            collection = db.notes
            
            notes = list(collection.find({}, {
                "_id": 1, 
                "note": 1, 
                "type": 1, 
                "filename": 1,
                "total_pages": 1,
                "created_at": 1, 
                "updated_at": 1
            }))
            
            for note in notes:
                note["_id"] = str(note["_id"])
                note["created_at"] = note["created_at"].isoformat()
                note["updated_at"] = note["updated_at"].isoformat()
            
            return notes
            
        except Exception as e:
            logger.error(f"Failed to retrieve notes: {e}")
            raise
        finally:
            if 'client' in locals():
                client.close()
    
    def get_note_with_embedding(self, note_id: str, db_uri: str = "mongodb://localhost:27017") -> Optional[Dict[str, Any]]:
        """Get a specific note along with its embedding."""
        try:
            client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            
            db = client.notes_db
            collection = db.notes
            
            note = collection.find_one({"_id": note_id})
            
            if note:
                note["_id"] = str(note["_id"])
                note["created_at"] = note["created_at"].isoformat()
                note["updated_at"] = note["updated_at"].isoformat()
            
            return note
            
        except Exception as e:
            logger.error(f"Failed to retrieve note {note_id}: {e}")
            raise
        finally:
            if 'client' in locals():
                client.close()
    
    def delete_note(self, note_id: str, db_uri: str = "mongodb://localhost:27017") -> bool:
        """Remove a note from the database."""
        try:
            client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            
            db = client.notes_db
            collection = db.notes
            
            note = collection.find_one({"_id": note_id})
            if not note:
                logger.warning(f"Note with ID {note_id} not found")
                return False
            
            result = collection.delete_one({"_id": note_id})
            
            if result.deleted_count > 0:
                logger.info(f"Successfully deleted note with ID: {note_id}")
                return True
            else:
                logger.warning(f"Failed to delete note with ID: {note_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete note {note_id}: {e}")
            raise
        finally:
            if 'client' in locals():
                client.close()

brain_core = BrainCore()

def embed_text(note: str) -> List[float]:
    """Convert your text note into an embedding."""
    return brain_core.embed_text(note)

def store_note(note: str, db_uri: str = "mongodb://localhost:27017") -> str:
    """Save your note with its embedding."""
    return brain_core.store_note(note, db_uri)

def store_pdf(pdf_file: bytes, filename: str, db_uri: str = "mongodb://localhost:27017") -> Dict[str, Any]:
    """Process and store a PDF file with embeddings."""
    return brain_core.store_pdf(pdf_file, filename, db_uri)

def get_all_notes(db_uri: str = "mongodb://localhost:27017") -> List[Dict[str, Any]]:
    """Get all your stored notes."""
    return brain_core.get_all_notes(db_uri)

def get_note_with_embedding(note_id: str, db_uri: str = "mongodb://localhost:27017") -> Optional[Dict[str, Any]]:
    """Get a specific note with its embedding."""
    return brain_core.get_note_with_embedding(note_id, db_uri)

def delete_note(note_id: str, db_uri: str = "mongodb://localhost:27017") -> bool:
    """Remove a note from the database."""
    return brain_core.delete_note(note_id, db_uri)

def handle_command_line():
    """Handle requests from the web server to process notes."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Function name required"}))
        return
    
    function_name = sys.argv[1]
    data = {}
    
    if len(sys.argv) > 2:
        try:
            data = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON data"}))
            return
    
    try:
        if function_name == "store_note":
            note = data.get("note", "")
            note_id = store_note(note)
            result = {"noteId": note_id, "success": True}
            
        elif function_name == "store_pdf":
            import base64
            pdf_base64 = data.get("pdf_base64", "")
            filename = data.get("filename", "document.pdf")
            
            if not pdf_base64:
                raise ValueError("PDF data is required")
            
            pdf_bytes = base64.b64decode(pdf_base64)
            pdf_result = store_pdf(pdf_bytes, filename)
            result = {"pdfId": pdf_result["pdf_id"], "success": True, **pdf_result}
            
        elif function_name == "get_all_notes":
            notes = get_all_notes()
            result = {"notes": notes, "success": True}
            
        elif function_name == "embed_text":
            note = data.get("note", "")
            embedding = embed_text(note)
            result = {"embedding": embedding, "success": True}
            
        elif function_name == "get_note_with_embedding":
            note_id = data.get("note_id", "")
            note = get_note_with_embedding(note_id)
            result = {"note": note, "success": True}
            
        elif function_name == "delete_note":
            note_id = data.get("note_id", "")
            deleted = delete_note(note_id)
            result = {"deleted": deleted, "success": True}
            
        else:
            result = {"error": f"Unknown function: {function_name}"}
            
    except Exception as e:
        result = {"error": str(e), "success": False}
    
    print(json.dumps(result))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        handle_command_line()
    else:
        try:
            test_note = "This is a test note for the digital second brain."
            embedding = embed_text(test_note)
            print(f"Embedding generated: {len(embedding)} dimensions")
            
        except Exception as e:
            print(f"Error: {e}") 