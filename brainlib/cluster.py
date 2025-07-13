"""
Cortex - Clustering Module

This module provides clustering functionality for:
- Retrieving notes and embeddings from MongoDB
- Clustering notes using KMeans based on semantic embeddings
- Automatically determining optimal cluster count using Silhouette Score
- Returning clustered notes for visualization and organization
"""

import json
import logging
import sys
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# MongoDB
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Clustering
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrainClusterer:
    """Clustering functionality for semantic note organization."""
    
    def __init__(self):
        """Initialize the brain clusterer."""
        self.scaler = StandardScaler()
    
    def get_notes_with_embeddings(self, db_uri: str = "mongodb://localhost:27017") -> List[Dict[str, Any]]:
        """
        Retrieve all notes with their embeddings from MongoDB.
        
        Args:
            db_uri: MongoDB connection URI
            
        Returns:
            List of note documents with embeddings
        """
        try:
            client = MongoClient(db_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            
            db = client.notes_db
            collection = db.notes
            
            # Get all notes with embeddings
            notes = list(collection.find({}, {
                "_id": 1, 
                "note": 1, 
                "embedding": 1, 
                "created_at": 1, 
                "updated_at": 1
            }))
            
            # Convert ObjectId to string for JSON serialization
            for note in notes:
                note["_id"] = str(note["_id"])
                note["created_at"] = note["created_at"].isoformat()
                note["updated_at"] = note["updated_at"].isoformat()
            
            return notes
            
        except Exception as e:
            logger.error(f"Failed to retrieve notes with embeddings: {e}")
            raise
        finally:
            if 'client' in locals():
                client.close()
    
    def find_optimal_k(self, embeddings: np.ndarray, max_k: int = 10) -> Tuple[int, float]:
        """
        Find the optimal number of clusters using Silhouette Score.
        
        Args:
            embeddings: Array of embeddings to cluster
            max_k: Maximum number of clusters to test
            
        Returns:
            Tuple of (optimal_k, best_silhouette_score)
        """
        if len(embeddings) < 2:
            return 1, 0.0
        
        # Limit max_k to number of samples
        max_k = min(max_k, len(embeddings) - 1)
        if max_k < 2:
            return 1, 0.0
        
        best_score = -1
        optimal_k = 2
        
        # Test different values of k
        for k in range(2, max_k + 1):
            try:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(embeddings)
                
                # Calculate silhouette score - handle edge cases
                if len(np.unique(cluster_labels)) < 2:
                    # Skip if we can't form at least 2 clusters
                    continue
                
                silhouette_avg = silhouette_score(embeddings, cluster_labels)
                
                logger.info(f"k={k}: Silhouette Score = {silhouette_avg:.4f}")
                
                if silhouette_avg > best_score:
                    best_score = silhouette_avg
                    optimal_k = k
                    
            except Exception as e:
                logger.warning(f"Failed to calculate silhouette score for k={k}: {e}")
                continue
        
        logger.info(f"Optimal k: {optimal_k} (Silhouette Score: {best_score:.4f})")
        return optimal_k, best_score
    
    def get_clusters(self, k: Optional[int] = None, db_uri: str = "mongodb://localhost:27017", 
                    auto_k: bool = True, max_k: int = 10) -> Dict[int, List[Dict[str, Any]]]:
        """
        Cluster notes based on their semantic embeddings using KMeans.
        
        Args:
            k: Number of clusters to create (if None and auto_k=True, will be determined automatically)
            db_uri: MongoDB connection URI
            auto_k: Whether to automatically determine optimal k using Silhouette Score
            max_k: Maximum number of clusters to test when auto_k=True
            
        Returns:
            Dictionary mapping cluster indices to lists of notes
        """
        try:
            # Get all notes with embeddings
            notes = self.get_notes_with_embeddings(db_uri)
            
            if not notes:
                logger.warning("No notes found for clustering")
                return {}
            
            # Handle edge case: only one note
            if len(notes) == 1:
                logger.info("Only one note found, returning single cluster")
                return {0: notes}
            
            embeddings = [note["embedding"] for note in notes]
            embeddings_array = np.array(embeddings)
            
            # Standardize embeddings
            embeddings_scaled = self.scaler.fit_transform(embeddings_array)
            
            # Determine optimal k if auto_k is enabled
            if auto_k and k is None:
                if len(notes) < 3:
                    # With very few notes, just use 1 cluster
                    k = 1
                    logger.info(f"Very few notes ({len(notes)}), using k=1")
                else:
                    optimal_k, silhouette_score_val = self.find_optimal_k(embeddings_scaled, max_k)
                    k = optimal_k
                    logger.info(f"Automatically determined optimal k: {k}")
            elif k is None:
                k = min(3, len(notes))  

            # ensure we don't try to create more clusters than notes
            if len(notes) < k:
                logger.warning(f"Number of notes ({len(notes)}) is less than requested clusters ({k})")
                k = len(notes)
            
            # if k=1, just return all notes in one cluster
            if k == 1:
                logger.info("k=1, returning single cluster with all notes")
                return {0: notes}
            
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(embeddings_scaled)
            
            if len(np.unique(cluster_labels)) > 1:
                try:
                    final_silhouette = silhouette_score(embeddings_scaled, cluster_labels)
                    logger.info(f"Final clustering with k={k}: Silhouette Score = {final_silhouette:.4f}")
                except Exception as e:
                    logger.warning(f"Could not calculate silhouette score: {e}")
            else:
                logger.info(f"Final clustering with k={k}: Single cluster formed")
            
            # Group notes by cluster
            clusters = {}
            for i, note in enumerate(notes):
                cluster_idx = int(cluster_labels[i])
                if cluster_idx not in clusters:
                    clusters[cluster_idx] = []
                clusters[cluster_idx].append(note)
            
            logger.info(f"Successfully clustered {len(notes)} notes into {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            logger.error(f"Failed to cluster notes: {e}")
            try:
                notes = self.get_notes_with_embeddings(db_uri)
                if notes:
                    logger.info("Returning fallback single cluster")
                    return {0: notes}
                else:
                    return {}
            except Exception as fallback_error:
                logger.error(f"Fallback clustering also failed: {fallback_error}")
                return {}
    
    def get_cluster_summary(self, k: Optional[int] = None, db_uri: str = "mongodb://localhost:27017",
                           auto_k: bool = True, max_k: int = 10) -> Dict[str, Any]:
        """
        Get a summary of clusters with statistics.
        
        Args:
            k: Number of clusters to create (if None and auto_k=True, will be determined automatically)
            db_uri: MongoDB connection URI
            auto_k: Whether to automatically determine optimal k using Silhouette Score
            max_k: Maximum number of clusters to test when auto_k=True
            
        Returns:
            Dictionary with cluster summary information
        """
        try:
            clusters = self.get_clusters(k, db_uri, auto_k, max_k)
            
            summary = {
                "total_notes": sum(len(notes) for notes in clusters.values()),
                "num_clusters": len(clusters),
                "auto_determined_k": auto_k and k is None,
                "clusters": {}
            }
            
            for cluster_idx, notes in clusters.items():
                sample_notes = [note["note"][:100] + "..." if len(note["note"]) > 100 else note["note"] 
                              for note in notes[:3]]
                
                summary["clusters"][cluster_idx] = {
                    "size": len(notes),
                    "sample_notes": sample_notes,
                    "notes": notes
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get cluster summary: {e}")
            raise

brain_clusterer = BrainClusterer()

def get_clusters(k: Optional[int] = None, db_uri: str = "mongodb://localhost:27017", 
                auto_k: bool = True, max_k: int = 10) -> Dict[int, List[Dict[str, Any]]]:
    """Cluster notes based on their semantic embeddings."""
    return brain_clusterer.get_clusters(k, db_uri, auto_k, max_k)

def get_cluster_summary(k: Optional[int] = None, db_uri: str = "mongodb://localhost:27017",
                       auto_k: bool = True, max_k: int = 10) -> Dict[str, Any]:
    """Get a summary of clusters with statistics."""
    return brain_clusterer.get_cluster_summary(k, db_uri, auto_k, max_k)

def get_notes_with_embeddings(db_uri: str = "mongodb://localhost:27017") -> List[Dict[str, Any]]:
    """Retrieve all notes with their embeddings from MongoDB."""
    return brain_clusterer.get_notes_with_embeddings(db_uri)

def find_optimal_k(embeddings: np.ndarray, max_k: int = 10) -> Tuple[int, float]:
    """Find the optimal number of clusters using Silhouette Score."""
    return brain_clusterer.find_optimal_k(embeddings, max_k)

def handle_command_line():
    """Handle command line arguments for Node.js integration."""
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
        if function_name == "get_clusters":
            k = data.get("k")
            auto_k = data.get("auto_k", True)
            max_k = data.get("max_k", 10)
            clusters = get_clusters(k, auto_k=auto_k, max_k=max_k)
            result = {"clusters": clusters, "success": True}
            
        elif function_name == "get_cluster_summary":
            k = data.get("k")
            auto_k = data.get("auto_k", True)
            max_k = data.get("max_k", 10)
            summary = get_cluster_summary(k, auto_k=auto_k, max_k=max_k)
            result = {"summary": summary, "success": True}
            
        elif function_name == "get_notes_with_embeddings":
            notes = get_notes_with_embeddings()
            result = {"notes": notes, "success": True}
            
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
            print("Testing clustering functionality...")
            
            summary = get_cluster_summary(auto_k=True, max_k=5)
            print(f"Cluster summary: {summary['total_notes']} notes in {summary['num_clusters']} clusters")
            print(f"Auto-determined k: {summary['auto_determined_k']}")
            
            for cluster_idx, cluster_info in summary["clusters"].items():
                print(f"Cluster {cluster_idx}: {cluster_info['size']} notes")
                for sample in cluster_info["sample_notes"]:
                    print(f"  - {sample}")
            
        except Exception as e:
            print(f"Error: {e}") 