"""
Vector Store wrapper for Qdrant.

Handles storage, searching, and management of face embeddings in a Qdrant collection.
"""
import logging
import uuid

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, UpdateStatus

from app.config import settings
from app.exceptions import StorageError

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class VectorStore:
    """A wrapper class for Qdrant client operations."""

    def __init__(self):
        """
        Initializes the VectorStore, connects to Qdrant, and ensures the collection exists.
        """
        try:
            self.client = QdrantClient(url=settings.QDRANT_URL)
            self.collection_name = settings.QDRANT_COLLECTION_NAME
            self._create_collection_if_not_exists()
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant at {settings.QDRANT_URL}: {e}")
            raise StorageError(f"Could not connect to Qdrant: {e}")

    def _create_collection_if_not_exists(self):
        """
        Creates the Qdrant collection if it doesn't already exist.
        The collection is configured for 512-dimensional vectors with cosine similarity.
        """
        try:
            self.client.get_collection(collection_name=self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists.")
        except Exception:
            logger.info(f"Collection '{self.collection_name}' not found. Creating it now.")
            try:
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=512, distance=Distance.COSINE),
                    # Add HNSW config for performance on large datasets
                    hnsw_config=models.HnswConfigDiff(
                        m=16,
                        ef_construct=200
                    )
                )
                logger.info(f"Successfully created collection '{self.collection_name}'.")
            except Exception as e:
                logger.error(f"Failed to create collection '{self.collection_name}': {e}")
                raise StorageError(f"Failed to create Qdrant collection: {e}")

    def store_embeddings(self, person_id: str, embeddings: list[list[float]]) -> int:
        """
        Stores multiple face embeddings for a given person_id.

        Args:
            person_id: The unique identifier for the person.
            embeddings: A list of 512-dimensional face embeddings.

        Returns:
            The number of embeddings successfully stored.

        Raises:
            StorageError: If the upsert operation fails.
        """
        if not embeddings:
            return 0

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={"person_id": person_id}
            )
            for embedding in embeddings
        ]

        try:
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points
            )
            if operation_info.status != UpdateStatus.COMPLETED:
                raise StorageError(f"Qdrant upsert failed with status: {operation_info.status}")

            logger.info(f"Stored {len(points)} embeddings for person_id '{person_id}'.")
            return len(points)
        except Exception as e:
            logger.error(f"Failed to store embeddings for person_id '{person_id}': {e}")
            raise StorageError(f"Failed to store embeddings: {e}")

    def search(self, embedding: list[float], threshold: float, limit: int = 1) -> list[tuple[str, float]]:
        """
        Searches for the most similar face embedding.

        Args:
            embedding: The 512-dimensional face embedding to search with.
            threshold: The minimum similarity score to consider a match.
            limit: The maximum number of results to return.

        Returns:
            A list of tuples, each containing (person_id, similarity_score).

        Raises:
            StorageError: If the search operation fails.
        """
        try:
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                score_threshold=threshold,
                limit=limit
            )

            results = [
                (hit.payload["person_id"], hit.score)
                for hit in search_results
                if "person_id" in hit.payload
            ]

            logger.debug(f"Search found {len(results)} matches with threshold {threshold}.")
            return results
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            raise StorageError(f"Failed during vector search: {e}")

        # In app/vector_store.py, inside the VectorStore class

    def exists(self, person_id: str) -> bool:
        """
        Checks if any embeddings exist for a given person_id.

        Args:
            person_id: The unique identifier for the person.

        Returns:
            True if at least one embedding exists, False otherwise.
        """
        try:
            # We can use the 'scroll' API with a limit of 1 and a filter to check for existence.
            # This is more efficient than a full search if we don't need the vector data.
            scroll_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="person_id",
                            match=models.MatchValue(value=person_id),
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False
            )
            # The result is a tuple; the first element is the list of points.
            return len(scroll_results[0]) > 0
        except Exception as e:
            logger.error(f"Failed to check existence for person_id '{person_id}': {e}")
            # In case of a storage error, it's safer to assume it might exist to prevent duplicates.
            # Or you could let the StorageError propagate. Let's be safe.
            raise StorageError(f"Failed to check for existing person: {e}")

    def delete_embeddings(self, person_id: str) -> bool:
        """
        Deletes all embeddings associated with a specific person_id.

        Args:
            person_id: The unique identifier for the person.

        Returns:
            True if the deletion was successful.

        Raises:
            StorageError: If the delete operation fails.
        """
        try:
            operation_info = self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="person_id",
                                match=models.MatchValue(value=person_id),
                            )
                        ]
                    )
                ),
                wait=True,
            )
            if operation_info.status != UpdateStatus.COMPLETED:
                raise StorageError(f"Qdrant delete failed with status: {operation_info.status}")

            logger.info(f"Successfully deleted embeddings for person_id '{person_id}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete embeddings for person_id '{person_id}': {e}")
            raise StorageError(f"Failed to delete embeddings: {e}")

    def update_embeddings(self, person_id: str, embeddings: list[list[float]]) -> int:
        """
        Updates the embeddings for a person by deleting all old ones and inserting new ones.

        Args:
            person_id: The unique identifier for the person.
            embeddings: A list of new 512-dimensional face embeddings.

        Returns:
            The number of new embeddings stored.
        """
        logger.info(f"Updating embeddings for person_id '{person_id}'.")
        self.delete_embeddings(person_id)
        return self.store_embeddings(person_id, embeddings)

    def health_check(self) -> bool:
        """
        Performs a health check on the Qdrant connection.

        Returns:
            True if the connection is healthy, False otherwise.
        """
        try:
            # A lightweight way to check for health is to get collection info
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False
