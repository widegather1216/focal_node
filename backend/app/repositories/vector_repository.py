from typing import List, Dict, Any, Optional
from chroma import get_chroma_collection

class VectorRepository:
    """
    Encapsulates all vector embedding interactions with ChromaDB.
    """
    def __init__(self):
        pass

    @property
    def collection(self):
        return get_chroma_collection()

    def count(self) -> int:
        return self.collection.count()

    def upsert(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if ids:
            self.collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def delete(self, ids: List[str]):
        if ids:
            for i in range(0, len(ids), 900):
                chunk = ids[i:i+900]
                try:
                    self.collection.delete(ids=chunk)
                except Exception as chroma_err:
                    print(f"[VectorRepository] Failed to delete chunk from ChromaDB: {chroma_err}", flush=True)

    def query_similar_by_embedding(self, query_embedding: List[float], n_results: int) -> List[str]:
        if self.count() == 0:
            return []
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        if results and results.get('ids') and len(results['ids']) > 0 and len(results['ids'][0]) > 0:
            return results['ids'][0]
        return []

    def get_embedding_by_id(self, photo_id: str) -> Optional[List[float]]:
        if self.count() == 0:
            return None
        target_data = self.collection.get(
            ids=[photo_id],
            include=["embeddings"]
        )
        if target_data and target_data.get('embeddings') and len(target_data['embeddings']) > 0:
            return target_data['embeddings'][0]
        return None
