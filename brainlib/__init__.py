# Cortex - Brain Library
# This package provides core functionality for embedding text and storing notes

from .brain import (
    embed_text,
    store_note,
    get_all_notes,
    get_note_with_embedding,
    BrainCore
)

from .cluster import (
    get_clusters,
    get_cluster_summary,
    get_notes_with_embeddings,
    find_optimal_k,
    BrainClusterer
)

__all__ = [
    # Core brain functions
    'embed_text',
    'store_note', 
    'get_all_notes',
    'get_note_with_embedding',
    'BrainCore',
    
    # Clustering functions
    'get_clusters',
    'get_cluster_summary',
    'get_notes_with_embeddings',
    'find_optimal_k',
    'BrainClusterer'
] 