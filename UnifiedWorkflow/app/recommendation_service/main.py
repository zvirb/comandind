"""
Recommendation Engine Service - Hybrid Model with LightFM
Provides AI-driven personalization using collaborative and content-based filtering.
Implements both offline training and online inference with near real-time updates.
"""

import asyncio
import json
import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import numpy as np
import pandas as pd
from lightfm import LightFM
from lightfm.data import Dataset
from lightfm.evaluation import precision_at_k, auc_score
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer
import uvicorn
from pydantic import BaseModel
from scipy.sparse import csr_matrix
import joblib

from app.shared.services.jwt_token_adapter import verify_jwt_token
from app.shared.services.metrics_exporter import MetricsExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Recommendation Engine Service",
    description="Hybrid recommendation system with LightFM for personalized suggestions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
redis_client = None
metrics = MetricsExporter("recommendation_service")

class InteractionType(str):
    VIEW = "view"
    CLICK = "click"
    PURCHASE = "purchase"
    LIKE = "like"
    SHARE = "share"
    CART_ADD = "cart_add"

class RecommendationRequest(BaseModel):
    user_id: str
    num_recommendations: int = 10
    item_filters: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

class InteractionData(BaseModel):
    user_id: str
    item_id: str
    interaction_type: str
    weight: float = 1.0
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None

class ItemMetadata(BaseModel):
    item_id: str
    category: str
    tags: List[str] = []
    price: Optional[float] = None
    features: Dict[str, Any] = {}

class RecommendationEngine:
    """Hybrid recommendation engine using LightFM"""
    
    def __init__(self):
        self.model = None
        self.dataset = None
        self.user_features = None
        self.item_features = None
        self.user_id_map = {}
        self.item_id_map = {}
        self.reverse_user_map = {}
        self.reverse_item_map = {}
        self.last_training_time = None
        self.model_version = "v1.0"
        self.models_dir = Path("/app/models")
        self.models_dir.mkdir(exist_ok=True)
        
        # Interaction weights for different types
        self.interaction_weights = {
            InteractionType.VIEW: 1.0,
            InteractionType.CLICK: 2.0,
            InteractionType.CART_ADD: 3.0,
            InteractionType.LIKE: 4.0,
            InteractionType.SHARE: 5.0,
            InteractionType.PURCHASE: 10.0
        }
    
    async def initialize(self):
        """Initialize the recommendation engine"""
        global redis_client
        
        # Initialize Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        
        # Try to load existing model
        await self.load_model()
        
        # If no model exists, create with sample data
        if self.model is None:
            await self.initialize_with_sample_data()
        
        # Start background tasks
        asyncio.create_task(self.periodic_training())
        asyncio.create_task(self.consume_interaction_stream())
        
        logger.info("Recommendation engine initialized successfully")
    
    async def initialize_with_sample_data(self):
        """Initialize with sample data for demonstration"""
        try:
            logger.info("Initializing with sample data...")
            
            # Create sample interactions
            sample_interactions = []
            sample_items = []
            
            # Generate sample items
            categories = ["electronics", "books", "clothing", "home", "sports"]
            for i in range(100):
                item_id = f"item_{i}"
                category = categories[i % len(categories)]
                sample_items.append(ItemMetadata(
                    item_id=item_id,
                    category=category,
                    tags=[category, f"tag_{i%10}"],
                    price=float(10 + (i % 100)),
                    features={"popularity": i % 10, "rating": 3.0 + (i % 3)}
                ))
            
            # Generate sample interactions
            for user_i in range(50):
                user_id = f"user_{user_i}"
                for item_i in range(5 + (user_i % 10)):  # Variable interactions per user
                    item_id = f"item_{item_i + (user_i % 50)}"
                    interaction_type = [InteractionType.VIEW, InteractionType.CLICK, InteractionType.PURCHASE][item_i % 3]
                    
                    sample_interactions.append(InteractionData(
                        user_id=user_id,
                        item_id=item_id,
                        interaction_type=interaction_type,
                        weight=self.interaction_weights[interaction_type],
                        timestamp=datetime.utcnow() - timedelta(days=item_i)
                    ))
            
            # Train initial model
            await self.train_model(sample_interactions, sample_items)
            logger.info(f"Initialized with {len(sample_interactions)} sample interactions and {len(sample_items)} items")
            
        except Exception as e:
            logger.error(f"Error initializing with sample data: {e}")
    
    async def train_model(self, interactions: List[InteractionData], items: List[ItemMetadata]):
        """Train the LightFM hybrid model"""
        try:
            logger.info("Starting model training...")
            start_time = time.time()
            
            # Create LightFM dataset
            self.dataset = Dataset()
            
            # Collect all users, items, and features
            user_ids = list(set([interaction.user_id for interaction in interactions]))
            item_ids = list(set([interaction.item_id for interaction in interactions]))
            
            # Collect item features
            item_categories = list(set([item.category for item in items]))
            item_tags = list(set([tag for item in items for tag in item.tags]))
            item_features = item_categories + item_tags + ["price_low", "price_medium", "price_high"]
            
            # Fit the dataset
            self.dataset.fit(
                users=user_ids,
                items=item_ids,
                item_features=item_features
            )
            
            # Create ID mappings
            self.user_id_map = {user_id: idx for idx, user_id in enumerate(user_ids)}
            self.item_id_map = {item_id: idx for idx, item_id in enumerate(item_ids)}
            self.reverse_user_map = {idx: user_id for user_id, idx in self.user_id_map.items()}
            self.reverse_item_map = {idx: item_id for item_id, idx in self.item_id_map.items()}
            
            # Build interactions matrix
            interactions_list = []
            weights_list = []
            
            for interaction in interactions:
                if interaction.user_id in self.user_id_map and interaction.item_id in self.item_id_map:
                    interactions_list.append((interaction.user_id, interaction.item_id))
                    weights_list.append(interaction.weight)
            
            interactions_matrix, weights_matrix = self.dataset.build_interactions(
                interactions_list, weights=weights_list
            )
            
            # Build item features matrix
            item_features_list = []
            for item in items:
                if item.item_id in self.item_id_map:
                    features = [item.category] + item.tags
                    
                    # Add price category
                    if item.price:
                        if item.price < 20:
                            features.append("price_low")
                        elif item.price < 50:
                            features.append("price_medium")
                        else:
                            features.append("price_high")
                    
                    item_features_list.append((item.item_id, features))
            
            item_features_matrix = self.dataset.build_item_features(item_features_list)
            
            # Train LightFM model
            self.model = LightFM(
                loss='warp',  # WARP loss for implicit feedback
                learning_rate=0.05,
                item_alpha=1e-6,
                user_alpha=1e-6,
                max_sampled=10
            )
            
            # Fit the model
            self.model.fit(
                interactions_matrix,
                item_features=item_features_matrix,
                epochs=50,
                num_threads=4,
                verbose=True
            )
            
            # Evaluate model
            train_precision = precision_at_k(self.model, interactions_matrix, k=10).mean()
            train_auc = auc_score(self.model, interactions_matrix).mean()
            
            self.last_training_time = datetime.utcnow()
            training_time = time.time() - start_time
            
            # Save model
            await self.save_model()
            
            # Record metrics
            await metrics.record_histogram("model_training_duration", training_time)
            await metrics.record_gauge("model_precision_at_10", train_precision)
            await metrics.record_gauge("model_auc_score", train_auc)
            
            logger.info(f"Model training completed in {training_time:.2f}s")
            logger.info(f"Precision@10: {train_precision:.3f}, AUC: {train_auc:.3f}")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            raise
    
    async def get_recommendations(self, user_id: str, num_recommendations: int = 10, 
                                 item_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get personalized recommendations for a user"""
        try:
            if self.model is None:
                raise HTTPException(status_code=503, detail="Model not trained yet")
            
            if user_id not in self.user_id_map:
                # Cold start: return popular items
                return await self.get_popular_items(num_recommendations)
            
            user_idx = self.user_id_map[user_id]
            
            # Get all item indices
            item_indices = list(range(len(self.item_id_map)))
            
            # Predict scores for all items
            scores = self.model.predict(
                user_ids=[user_idx] * len(item_indices),
                item_ids=item_indices,
                item_features=getattr(self, 'item_features_matrix', None)
            )
            
            # Get user's past interactions to filter them out
            past_items = await self.get_user_past_interactions(user_id)
            past_item_indices = [self.item_id_map[item_id] for item_id in past_items 
                               if item_id in self.item_id_map]
            
            # Create recommendations list
            recommendations = []
            for item_idx, score in enumerate(scores):
                if item_idx not in past_item_indices:  # Filter out past interactions
                    item_id = self.reverse_item_map[item_idx]
                    
                    # Apply filters if provided
                    if item_filters and not await self.item_matches_filters(item_id, item_filters):
                        continue
                    
                    recommendations.append({
                        "item_id": item_id,
                        "score": float(score),
                        "reason": "personalized"
                    })
            
            # Sort by score and return top N
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            recommendations = recommendations[:num_recommendations]
            
            # Enrich with item metadata
            for rec in recommendations:
                item_metadata = await self.get_item_metadata(rec["item_id"])
                rec.update(item_metadata)
            
            # Record metrics
            await metrics.record_counter("recommendations_generated", 1, {
                "user_type": "existing" if user_id in self.user_id_map else "new",
                "num_items": str(len(recommendations))
            })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")
    
    async def get_popular_items(self, num_items: int = 10) -> List[Dict[str, Any]]:
        """Get popular items for cold start scenarios"""
        try:
            # Get item popularity from Redis
            popular_items = []
            
            # In a real implementation, this would be calculated from interaction data
            # For now, return sample popular items
            for i in range(min(num_items, 10)):
                popular_items.append({
                    "item_id": f"item_{i}",
                    "score": 0.9 - (i * 0.1),
                    "reason": "popular",
                    "category": "electronics" if i % 2 == 0 else "books",
                    "tags": ["popular", "trending"]
                })
            
            return popular_items
            
        except Exception as e:
            logger.error(f"Error getting popular items: {e}")
            return []
    
    async def record_interaction(self, interaction: InteractionData):
        """Record a new user interaction"""
        try:
            # Store in Redis for real-time processing
            interaction_key = f"interaction:{interaction.user_id}:{interaction.item_id}:{int(time.time())}"
            interaction_data = {
                "user_id": interaction.user_id,
                "item_id": interaction.item_id,
                "interaction_type": interaction.interaction_type,
                "weight": interaction.weight,
                "timestamp": (interaction.timestamp or datetime.utcnow()).isoformat(),
                "context": json.dumps(interaction.context or {})
            }
            
            await redis_client.hmset(interaction_key, interaction_data)
            await redis_client.expire(interaction_key, 86400 * 30)  # 30 days
            
            # Update user's recent interactions
            user_interactions_key = f"user_interactions:{interaction.user_id}"
            await redis_client.lpush(user_interactions_key, interaction.item_id)
            await redis_client.ltrim(user_interactions_key, 0, 99)  # Keep last 100
            await redis_client.expire(user_interactions_key, 86400 * 30)
            
            # Record metrics
            await metrics.record_counter("interactions_recorded", 1, {
                "interaction_type": interaction.interaction_type,
                "user_id": interaction.user_id[:8]  # Partial for privacy
            })
            
            logger.debug(f"Recorded interaction: {interaction.user_id} -> {interaction.item_id}")
            
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
    
    async def get_user_past_interactions(self, user_id: str) -> List[str]:
        """Get user's past interactions"""
        try:
            user_interactions_key = f"user_interactions:{user_id}"
            interactions = await redis_client.lrange(user_interactions_key, 0, -1)
            return interactions or []
        except Exception:
            return []
    
    async def get_item_metadata(self, item_id: str) -> Dict[str, Any]:
        """Get item metadata"""
        try:
            item_key = f"item_metadata:{item_id}"
            metadata = await redis_client.hgetall(item_key)
            
            if metadata:
                return {
                    "category": metadata.get("category", "unknown"),
                    "tags": json.loads(metadata.get("tags", "[]")),
                    "price": float(metadata.get("price", 0)) if metadata.get("price") else None
                }
            else:
                # Return default metadata for sample items
                return {
                    "category": "electronics",
                    "tags": ["sample"],
                    "price": 29.99
                }
        except Exception:
            return {"category": "unknown", "tags": [], "price": None}
    
    async def item_matches_filters(self, item_id: str, filters: Dict[str, Any]) -> bool:
        """Check if item matches the provided filters"""
        try:
            metadata = await self.get_item_metadata(item_id)
            
            # Category filter
            if "category" in filters and metadata.get("category") != filters["category"]:
                return False
            
            # Price range filter
            if "price_min" in filters or "price_max" in filters:
                price = metadata.get("price")
                if price is None:
                    return False
                if "price_min" in filters and price < filters["price_min"]:
                    return False
                if "price_max" in filters and price > filters["price_max"]:
                    return False
            
            # Tag filter
            if "tags" in filters:
                item_tags = set(metadata.get("tags", []))
                required_tags = set(filters["tags"])
                if not required_tags.issubset(item_tags):
                    return False
            
            return True
            
        except Exception:
            return True  # Default to include if check fails
    
    async def save_model(self):
        """Save the trained model and metadata"""
        try:
            model_path = self.models_dir / f"lightfm_model_{self.model_version}.pkl"
            metadata_path = self.models_dir / f"model_metadata_{self.model_version}.pkl"
            
            # Save model
            with open(model_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            # Save metadata
            metadata = {
                "user_id_map": self.user_id_map,
                "item_id_map": self.item_id_map,
                "reverse_user_map": self.reverse_user_map,
                "reverse_item_map": self.reverse_item_map,
                "last_training_time": self.last_training_time.isoformat() if self.last_training_time else None,
                "model_version": self.model_version
            }
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"Model saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    async def load_model(self):
        """Load a previously trained model"""
        try:
            model_path = self.models_dir / f"lightfm_model_{self.model_version}.pkl"
            metadata_path = self.models_dir / f"model_metadata_{self.model_version}.pkl"
            
            if model_path.exists() and metadata_path.exists():
                # Load model
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                
                # Load metadata
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                
                self.user_id_map = metadata["user_id_map"]
                self.item_id_map = metadata["item_id_map"]
                self.reverse_user_map = metadata["reverse_user_map"]
                self.reverse_item_map = metadata["reverse_item_map"]
                self.last_training_time = datetime.fromisoformat(metadata["last_training_time"]) if metadata["last_training_time"] else None
                self.model_version = metadata["model_version"]
                
                logger.info(f"Model loaded from {model_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    async def periodic_training(self):
        """Periodically retrain the model with new data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Check if retraining is needed
                if self.should_retrain():
                    logger.info("Starting periodic model retraining...")
                    
                    # Get fresh interaction data
                    interactions = await self.get_recent_interactions()
                    items = await self.get_item_catalog()
                    
                    if len(interactions) > 10:  # Minimum interactions threshold
                        await self.train_model(interactions, items)
                        logger.info("Periodic retraining completed")
                    else:
                        logger.info("Insufficient data for retraining")
                
            except Exception as e:
                logger.error(f"Error in periodic training: {e}")
    
    def should_retrain(self) -> bool:
        """Determine if model should be retrained"""
        if self.last_training_time is None:
            return True
        
        # Retrain if more than 6 hours since last training
        time_since_training = datetime.utcnow() - self.last_training_time
        return time_since_training > timedelta(hours=6)
    
    async def get_recent_interactions(self) -> List[InteractionData]:
        """Get recent interactions for retraining"""
        try:
            interactions = []
            
            # Scan for interaction keys
            pattern = "interaction:*"
            async for key in redis_client.scan_iter(match=pattern):
                interaction_data = await redis_client.hgetall(key)
                if interaction_data:
                    interactions.append(InteractionData(
                        user_id=interaction_data["user_id"],
                        item_id=interaction_data["item_id"],
                        interaction_type=interaction_data["interaction_type"],
                        weight=float(interaction_data["weight"]),
                        timestamp=datetime.fromisoformat(interaction_data["timestamp"])
                    ))
            
            return interactions
            
        except Exception as e:
            logger.error(f"Error getting recent interactions: {e}")
            return []
    
    async def get_item_catalog(self) -> List[ItemMetadata]:
        """Get current item catalog"""
        try:
            items = []
            
            # Scan for item metadata keys
            pattern = "item_metadata:*"
            async for key in redis_client.scan_iter(match=pattern):
                item_data = await redis_client.hgetall(key)
                if item_data:
                    item_id = key.split(":")[-1]
                    items.append(ItemMetadata(
                        item_id=item_id,
                        category=item_data.get("category", "unknown"),
                        tags=json.loads(item_data.get("tags", "[]")),
                        price=float(item_data.get("price", 0)) if item_data.get("price") else None,
                        features=json.loads(item_data.get("features", "{}"))
                    ))
            
            return items
            
        except Exception as e:
            logger.error(f"Error getting item catalog: {e}")
            return []
    
    async def consume_interaction_stream(self):
        """Consume interaction events from Kafka for real-time updates"""
        try:
            consumer = KafkaConsumer(
                'user-interactions',
                bootstrap_servers=os.getenv("KAFKA_SERVERS", "kafka:9092").split(','),
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='recommendation-service-consumer'
            )
            
            logger.info("Started Kafka consumer for user interactions")
            
            for message in consumer:
                try:
                    event_data = message.value
                    if event_data.get("event_type") in ["product_viewed", "add_to_cart", "purchase_completed"]:
                        # Convert to interaction data
                        interaction = InteractionData(
                            user_id=event_data.get("user_id"),
                            item_id=event_data.get("properties", {}).get("product_id", ""),
                            interaction_type=event_data.get("event_type"),
                            weight=self.interaction_weights.get(event_data.get("event_type"), 1.0),
                            timestamp=datetime.fromisoformat(event_data.get("timestamp"))
                        )
                        
                        await self.record_interaction(interaction)
                        
                except Exception as e:
                    logger.error(f"Error processing Kafka message: {e}")
                    
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {e}")

# Global service instance
rec_engine = RecommendationEngine()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await rec_engine.initialize()
    logger.info("Recommendation Engine Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    logger.info("Recommendation Engine Service stopped")

async def get_current_user(token: str = Depends(verify_jwt_token)) -> Dict[str, Any]:
    """Get current authenticated user"""
    return token

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_status = "unknown"
        if redis_client:
            await redis_client.ping()
            redis_status = "connected"
        
        return {
            "status": "healthy",
            "service": "recommendation-engine",
            "model": {
                "trained": rec_engine.model is not None,
                "version": rec_engine.model_version,
                "last_training": rec_engine.last_training_time.isoformat() if rec_engine.last_training_time else None,
                "users_count": len(rec_engine.user_id_map),
                "items_count": len(rec_engine.item_id_map)
            },
            "dependencies": {
                "redis": redis_status
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/recommendations")
async def get_recommendations(
    request: RecommendationRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get personalized recommendations for a user"""
    try:
        # Validate user authorization
        if request.user_id != user.get("user_id") and not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Cannot get recommendations for other users")
        
        recommendations = await rec_engine.get_recommendations(
            user_id=request.user_id,
            num_recommendations=request.num_recommendations,
            item_filters=request.item_filters
        )
        
        return {
            "user_id": request.user_id,
            "recommendations": recommendations,
            "total": len(recommendations),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@app.post("/interactions")
async def record_interaction(
    interaction: InteractionData,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Record a user interaction"""
    try:
        # Validate user authorization
        if interaction.user_id != user.get("user_id"):
            raise HTTPException(status_code=403, detail="Cannot record interactions for other users")
        
        # Set default weight based on interaction type
        if interaction.weight == 1.0:  # Default value
            interaction.weight = rec_engine.interaction_weights.get(interaction.interaction_type, 1.0)
        
        await rec_engine.record_interaction(interaction)
        
        return {
            "status": "recorded",
            "interaction_type": interaction.interaction_type,
            "user_id": interaction.user_id,
            "item_id": interaction.item_id,
            "weight": interaction.weight
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording interaction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to record interaction: {str(e)}")

@app.post("/items")
async def add_item_metadata(
    item: ItemMetadata,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Add or update item metadata (admin only)"""
    try:
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Store item metadata in Redis
        item_key = f"item_metadata:{item.item_id}"
        item_data = {
            "category": item.category,
            "tags": json.dumps(item.tags),
            "price": str(item.price) if item.price else "",
            "features": json.dumps(item.features)
        }
        
        await redis_client.hmset(item_key, item_data)
        await redis_client.expire(item_key, 86400 * 365)  # 1 year
        
        return {"status": "added", "item_id": item.item_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add item: {str(e)}")

@app.post("/retrain")
async def trigger_retraining(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Trigger model retraining (admin only)"""
    try:
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        async def retrain_task():
            try:
                interactions = await rec_engine.get_recent_interactions()
                items = await rec_engine.get_item_catalog()
                
                if len(interactions) > 10:
                    await rec_engine.train_model(interactions, items)
                    logger.info("Manual retraining completed successfully")
                else:
                    logger.warning("Insufficient data for retraining")
            except Exception as e:
                logger.error(f"Error in manual retraining: {e}")
        
        background_tasks.add_task(retrain_task)
        
        return {"status": "retraining_started", "message": "Model retraining initiated in background"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering retraining: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger retraining: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,
        reload=False,
        log_level="info"
    )