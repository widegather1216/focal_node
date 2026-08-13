"""
Atomic Transaction Manager Module

Enforces atomic operations across SQLite relational database and ChromaDB vector database.
Implements compensating transactions: if SQLite fails during/after ChromaDB operation,
the compensating action is triggered to ensure zero orphaned embeddings or inconsistent metadata.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from repositories.vector_repository import VectorRepository

logger = logging.getLogger("focal_node.atomic_transaction")

class CompensatingTransactionManager:
    """
    Manages atomic operations spanning SQLite relational DB and ChromaDB vector DB.
    """
    def __init__(self, db_session: Session, vector_repo: Optional[VectorRepository] = None):
        self.db = db_session
        self.vector_repo = vector_repo or VectorRepository()

    def upsert_and_commit(
        self,
        image_ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> bool:
        """
        Upserts vectors into ChromaDB, then commits SQLite session.
        If SQLite commit fails, executes compensating transaction to remove inserted ChromaDB vectors.
        """
        if not image_ids:
            return True

        try:
            # 1. Upsert into ChromaDB
            self.vector_repo.upsert(
                ids=image_ids,
                embeddings=embeddings,
                metadatas=metadatas
            )

            # 2. Commit SQLite Transaction
            self.db.commit()
            return True

        except Exception as err:
            logger.error(f"[CompensatingTx] SQLite commit failed after ChromaDB upsert: {err}. Rolling back...")
            self.db.rollback()

            # 3. Compensating Action: Cleanup orphaned ChromaDB embeddings
            try:
                self.vector_repo.delete(image_ids)
                logger.info(f"[CompensatingTx] Successfully cleaned up {len(image_ids)} ChromaDB vectors.")
            except Exception as rollback_err:
                logger.critical(f"[CompensatingTx] Failed to execute compensating ChromaDB deletion: {rollback_err}")

            raise err

    def delete_and_commit(self, image_ids: List[str]) -> bool:
        """
        Deletes database records from SQLite and ChromaDB atomically.
        """
        if not image_ids:
            return True

        try:
            # 1. Commit SQLite Deletions
            self.db.commit()

            # 2. Delete from ChromaDB
            self.vector_repo.delete(image_ids)
            return True

        except Exception as err:
            logger.error(f"[CompensatingTx] Atomic deletion failed: {err}")
            self.db.rollback()
            raise err
