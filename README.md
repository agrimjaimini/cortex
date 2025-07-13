# Cortex 🧠

A web app that serves as your digital second brain. It helps you store and organize your notes using semantic embeddings. Think of it as a smart notebook where you can dump any notes (in text or PDF format) that groups similar ideas together automatically.

## Project Architecture

```
cortex/
├── brainlib/           # Python embedding and clustering logic
│   ├── __init__.py
│   ├── brain.py       # Core functions for storing and retrieving notes
│   ├── cluster.py     # Groups similar notes together
│   └── pdf_processor.py # Extracts text from PDF files
├── client/            # The web interface you interact with
├── server/            # Connects the frontend to the AI backend
├── requirements.txt   # Python packages needed
└── README.md
```

## How it works

### The Brain Module (`brainlib/brain.py`)

- **Converts text to vectors**: Turns your notes into 384-dimensional AI embeddings using SentenceTransformers
- **Stores everything**: Saves notes and their embeddings in MongoDB
- **Retrieves data**: Fetches notes when you need them
- **Processes PDFs**: Extracts and embeds text from uploaded PDF files

#### Basic Usage

```python
from brainlib.brain import embed_text, store_note, get_all_notes

# Store a new note
note_id = store_note("Meeting notes from today's client call")

# Get all your notes
notes = get_all_notes()
```

#### How notes are stored

```json
{
  "_id": "unique-id-here",
  "note": "Your actual note text",
  "embedding": [0.1, 0.2, ...],  // AI representation of your note
  "type": "text",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Technology Stack

- **Python**: Powers the AI and data processing
- **SentenceTransformers**: Converts your text into AI embeddings
- **MongoDB**: Stores all your notes and their AI representations
- **Node.js/Express**: Handles web requests and connects everything
- **React**: The user interface you interact with

## Development Notes

- The brain module is designed to be easily swapped out if you want to try different AI models
- You can change the embedding model by updating the `model_name` parameter
- MongoDB connection settings are configurable via the `db_uri` parameter
- PDF processing extracts both text content and metadata

