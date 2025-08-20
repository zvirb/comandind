"""
This service provides a singleton interface for interacting with the
Qdrant vector database, ensuring a single, reusable client instance.
"""
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import SecretStr
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import UpdateStatus

# Import from the shared module for centralized configuration
from shared.utils.config import get_settings, Settings


# --- Constants ---
settings: Settings = get_settings()
QDRANT_URL = str(settings.qdrant_url)
# Correctly handle the optional SecretStr type
QDRANT_API_KEY = settings.QDRANT_API_KEY.get_secret_value() if isinstance(settings.QDRANT_API_KEY, SecretStr) else None
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "documents")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QdrantException(Exception):
    """Custom exception for Qdrant service-related errors."""
    pass

class QdrantService:
    """
    A singleton service for interacting with the Qdrant vector database.
    """
    _instance: Optional["QdrantService"] = None
    _client: Optional[AsyncQdrantClient] = None
    _batch_points: List[models.PointStruct]

    def __new__(cls) -> "QdrantService":
        if cls._instance is None:
            cls._instance = super(QdrantService, cls).__new__(cls)
            cls._instance._batch_points = []
        return cls._instance

    @property
    async def client(self) -> AsyncQdrantClient:
        """Provides access to the AsyncQdrantClient, initializing it if necessary."""
        if self._client is None:
            await self.initialize()
        assert self._client is not None, "Client should be initialized."
        return self._client

    async def initialize(self) -> None:
        """Initializes the async Qdrant client and ensures the collection exists."""
        if self._client is not None:
            return

        logger.info("Initializing Qdrant client at %s...", QDRANT_URL)

        # When TLS is enabled, a path to the CA certificate is required for verification.
        # This check ensures the application fails fast with a clear error
        # if the configuration is incomplete for a secure connection.
        if settings.QDRANT_USE_TLS and not settings.QDRANT_CERT_PATH:
            raise QdrantException(
                "QDRANT_USE_TLS is true, but QDRANT_CERT_PATH is not set. "
                "Provide the path to the CA certificate for TLS verification."
            )

        self._client = AsyncQdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60,
            verify=False,  # Disable SSL verification for internal Docker network
        )

        try:
            collections_response = await self._client.get_collections()
            collection_names = [
                collection.name for collection in collections_response.collections
            ]

            if COLLECTION_NAME not in collection_names:
                logger.info("Collection '%s' not found. Creating it...", COLLECTION_NAME)
                vector_size = settings.EMBEDDING_DIM
                await self._client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=vector_size, distance=models.Distance.COSINE
                    ),
                )
                logger.info("Collection '%s' created successfully.", COLLECTION_NAME)
            else:
                logger.info("Collection '%s' already exists.", COLLECTION_NAME)

        except Exception as e:
            logger.error("Failed to initialize Qdrant or create collection: %s", e)
            self._client = None
            raise QdrantException("Failed to initialize Qdrant") from e

    async def upsert_points(self, points: List[models.PointStruct]) -> Dict[str, Any]:
        """Upserts a list of points into the default Qdrant collection."""
        client = await self.client
        logger.info("Upserting %d points to collection '%s'.", len(points), COLLECTION_NAME)
        try:
            operation_info = await client.upsert(
                collection_name=COLLECTION_NAME, wait=True, points=points
            )
            logger.info("Successfully upserted points.")
            return operation_info.model_dump()
        except Exception as e:
            logger.error("Error during upsert to Qdrant: %s", e, exc_info=True)
            raise QdrantException("Failed to upsert points to Qdrant") from e

    async def delete_document_points(self, document_id: str) -> Dict[str, Any]:
        """Deletes all points associated with a specific document_id."""
        client = await self.client
        logger.info(
            "Attempting to delete points for document_id: %s from '%s'.",
            document_id, COLLECTION_NAME
        )
        try:
            must_filter: List[models.Condition] = [
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=str(document_id)),
                )
            ]

            delete_result = await client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=must_filter)
                ),
            )
            logger.info(
                "Deletion request for document %s completed with status: %s",
                document_id, delete_result.status
            )
            if delete_result.status == UpdateStatus.COMPLETED:
                logger.info("Successfully deleted points for document %s.", document_id)
            else:
                logger.warning(
                    "Deletion for document %s may not be complete. Status: %s",
                    document_id, delete_result.status
                )
            return delete_result.model_dump()

        except Exception as e:
            logger.error(
                "Error deleting points for document %s from Qdrant: %s",
                document_id, e, exc_info=True,
            )
            raise QdrantException("Failed to delete points from Qdrant") from e

    async def search(
        self,
        vector: List[float],
        user_id: int,
        limit: int = 5,
        document_ids: Optional[List[UUID]] = None,
    ) -> List[models.ScoredPoint]:
        """Performs a vector search, filtering by user and optionally document IDs."""
        client = await self.client
        must_conditions: list[models.Condition] = [
            models.FieldCondition(
                key="user_id", match=models.MatchValue(value=user_id)
            ),
        ]

        if document_ids:
            str_document_ids = [str(doc_id) for doc_id in document_ids]
            must_conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=str_document_ids),
                )
            )

        search_params = models.SearchParams(
            hnsw_ef=128,
            exact=False,
        )

        try:
            search_result = await client.search(
                collection_name=COLLECTION_NAME,
                query_vector=vector,
                query_filter=models.Filter(must=must_conditions),
                search_params=search_params,
                limit=limit,
            )
            return search_result
        except Exception as e:
            logger.error("Error during search in Qdrant: %s", e, exc_info=True)
            raise QdrantException("Failed to search in Qdrant") from e

    def add_to_batch(self, vector_id: str, vector: List[float], payload: Dict[str, Any]) -> None:
        """Adds a point to the batch for later upsert."""
        point = models.PointStruct(
            id=vector_id,
            vector=vector,
            payload=payload
        )
        self._batch_points.append(point)
        logger.debug("Added point %s to batch. Batch size: %d", vector_id, len(self._batch_points))

    async def upsert_batch(self) -> Dict[str, Any]:
        """Upserts all points in the batch and clears the batch."""
        if not self._batch_points:
            logger.warning("No points in batch to upsert.")
            return {"status": "no_points"}
        
        try:
            result = await self.upsert_points(self._batch_points)
            points_count = len(self._batch_points)
            self._batch_points.clear()
            logger.info("Successfully upserted batch of %d points.", points_count)
            return result
        except Exception as e:
            logger.error("Failed to upsert batch: %s", e, exc_info=True)
            # Clear the batch even on failure to prevent memory leaks
            self._batch_points.clear()
            raise

    def clear_batch(self) -> None:
        """Clears the current batch without upserting."""
        points_count = len(self._batch_points)
        self._batch_points.clear()
        logger.info("Cleared batch of %d points.", points_count)

    def get_batch_size(self) -> int:
        """Returns the current number of points in the batch."""
        return len(self._batch_points)

    async def store_chat_message(self, message_id: str, content: str, user_id: int, 
                                 session_id: str, message_type: str, message_order: int,
                                 conversation_domain: Optional[str] = None,
                                 tool_used: Optional[str] = None,
                                 plan_step: Optional[int] = None) -> str:
        """
        Store a chat message to Qdrant for semantic search.
        Returns the point ID used in Qdrant.
        """
        try:
            # Import datetime for timestamp
            from datetime import datetime
            # Generate embedding for the message content
            from worker.services.ollama_service import generate_embeddings
            
            embeddings = await generate_embeddings([content])
            if not embeddings or len(embeddings) == 0:
                raise QdrantException("Failed to generate embeddings for chat message")
            
            embedding_vector = embeddings[0]
            
            # Create point ID for Qdrant
            qdrant_point_id = f"chat_{message_id}"
            
            # Prepare payload with rich metadata
            payload = {
                "message_id": message_id,
                "user_id": user_id,
                "session_id": session_id,
                "text": content,
                "message_type": message_type,
                "message_order": message_order,
                "source": "chat_message",
                "timestamp": datetime.now().isoformat(),
                "conversation_domain": conversation_domain,
                "tool_used": tool_used,
                "plan_step": plan_step,
                "content_type": "chat"
            }
            
            # Create point
            point = models.PointStruct(
                id=qdrant_point_id,
                vector=embedding_vector,
                payload=payload
            )
            
            # Store to Qdrant
            await self.upsert_points([point])
            
            logger.info(f"Stored chat message {message_id} to Qdrant with point ID: {qdrant_point_id}")
            return qdrant_point_id
            
        except Exception as e:
            logger.error(f"Error storing chat message to Qdrant: {e}", exc_info=True)
            raise QdrantException("Failed to store chat message to Qdrant") from e

    async def search_points(self, query_text: str, limit: int = 5, 
                           user_id: Optional[int] = None,
                           content_types: Optional[List[str]] = None,
                           session_ids: Optional[List[str]] = None) -> List[models.ScoredPoint]:
        """
        Enhanced search that can filter by content types and session IDs.
        """
        try:
            from worker.services.ollama_service import generate_embeddings
            
            # Generate embedding for query
            embeddings = await generate_embeddings([query_text])
            if not embeddings or len(embeddings) == 0:
                raise QdrantException("Failed to generate embeddings for search query")
            
            query_vector = embeddings[0]
            
            # Build filter conditions
            must_conditions: List[models.Condition] = []
            
            if user_id is not None:
                must_conditions.append(
                    models.FieldCondition(
                        key="user_id", 
                        match=models.MatchValue(value=user_id)
                    )
                )
            
            if content_types:
                must_conditions.append(
                    models.FieldCondition(
                        key="content_type",
                        match=models.MatchAny(any=content_types)
                    )
                )
            
            if session_ids:
                must_conditions.append(
                    models.FieldCondition(
                        key="session_id",
                        match=models.MatchAny(any=session_ids)
                    )
                )
            
            # Perform search
            client = await self.client
            search_result = await client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=models.Filter(must=must_conditions) if must_conditions else None,
                limit=limit,
                search_params=models.SearchParams(hnsw_ef=128, exact=False)
            )
            
            return search_result
            
        except Exception as e:
            logger.error(f"Error in enhanced search: {e}", exc_info=True)
            raise QdrantException("Failed to perform enhanced search") from e

    async def list_collections(self) -> List[str]:
        """List all collections in Qdrant."""
        try:
            client = await self.client
            collections_response = await client.get_collections()
            collection_names = [collection.name for collection in collections_response.collections]
            return collection_names
        except Exception as e:
            logger.error(f"Error listing Qdrant collections: {e}")
            return []
    
    async def create_collection(self, collection_name: str, vector_size: int, distance: str = "Cosine") -> bool:
        """Create a new collection in Qdrant."""
        try:
            client = await self.client
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=getattr(models.Distance, distance.upper(), models.Distance.COSINE)
                )
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating Qdrant collection {collection_name}: {e}")
            return False

    async def add_point(self, collection_name: str, point_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a single point to a Qdrant collection with embedding generation.
        Returns True if successful, False otherwise.
        """
        try:
            # Generate embedding for the text
            from worker.services.ollama_service import generate_embeddings
            
            embeddings = await generate_embeddings([text])
            if not embeddings or len(embeddings) == 0:
                logger.error(f"Failed to generate embeddings for text: {text[:100]}...")
                return False
            
            embedding_vector = embeddings[0]
            
            # Create point
            point = models.PointStruct(
                id=point_id,
                vector=embedding_vector,
                payload={
                    "text": text,
                    **metadata
                }
            )
            
            # Upsert single point
            client = await self.client
            result = await client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            if result.status == UpdateStatus.COMPLETED:
                logger.debug(f"Successfully added point {point_id} to collection {collection_name}")
                return True
            else:
                logger.error(f"Failed to add point {point_id}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding point to Qdrant: {e}", exc_info=True)
            return False

    async def close(self) -> None:
        """Closes the Qdrant client connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Qdrant client closed.")
