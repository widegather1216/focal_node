import threading
from typing import List, Dict, Any, Optional
from chroma import get_chroma_collection

_vector_lock = threading.RLock()

class VectorRepository:
    """
    Encapsulates all vector embedding interactions with ChromaDB.
    Guarantees thread-safe access across indexing background threads and API search queries.
    """
    def __init__(self):
        pass

    @property
    def collection(self):
        return get_chroma_collection()

    def count(self) -> int:
        with _vector_lock:
            return self.collection.count()

    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if ids:
            with _vector_lock:
                self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def delete(self, ids: List[str]):
        if ids:
            with _vector_lock:
                for i in range(0, len(ids), 900):
                    chunk = ids[i:i+900]
                    try:
                        self.collection.delete(ids=chunk)
                    except Exception as chroma_err:
                        print(f"[VectorRepository] Failed to delete chunk from ChromaDB: {chroma_err}", flush=True)

    def query_similar_by_embedding(self, query_embedding: List[float], n_results: int) -> List[str]:
        with _vector_lock:
            total = self.count()
            if total == 0 or n_results <= 0:
                return []
            safe_n = max(1, min(n_results, total))
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=safe_n
            )
            if results and results.get('ids') and len(results['ids']) > 0 and len(results['ids'][0]) > 0:
                return results['ids'][0]
            return []

    def get_embedding_by_id(self, photo_id: str) -> Optional[List[float]]:
        with _vector_lock:
            if self.count() == 0:
                return None
            target_data = self.collection.get(
                ids=[photo_id],
                include=["embeddings"]
            )
            if target_data and target_data.get('embeddings') and len(target_data['embeddings']) > 0:
                return target_data['embeddings'][0]
            return None
