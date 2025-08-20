"""
External API Integration Service - Anti-Corruption Layer
Centralized facade for third-party APIs with caching, normalization, and error handling.
Implements API Gateway pattern and Anti-Corruption Layer for external dependencies.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

import aiohttp
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

from app.shared.services.jwt_token_adapter import verify_jwt_token
from app.shared.services.metrics_exporter import MetricsExporter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="External API Integration Service",
    description="Unified facade for third-party APIs with caching and normalization",
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
http_session = None
metrics = MetricsExporter("external_api_service")

class APIProvider(str, Enum):
    OPENWEATHERMAP = "openweathermap"
    TOMTOM = "tomtom"
    SHOPIFY = "shopify"
    GOOGLE_MAPS = "google_maps"

class WeatherRequest(BaseModel):
    latitude: float
    longitude: float
    units: str = "metric"  # metric, imperial, kelvin

class TrafficRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    departure_time: Optional[datetime] = None

class EcommerceRequest(BaseModel):
    store_domain: str
    product_query: Optional[str] = None
    category: Optional[str] = None
    limit: int = 10

class ExternalAPIService:
    """Unified external API integration service"""
    
    def __init__(self):
        # API Keys and Configuration
        self.openweather_api_key = self._read_secret_file("OPENWEATHER_API_KEY_FILE", "demo_key")
        self.tomtom_api_key = self._read_secret_file("TOMTOM_API_KEY_FILE", "demo_key")
        self.shopify_access_token = self._read_secret_file("SHOPIFY_ACCESS_TOKEN_FILE", "demo_token")
        self.google_client_id = self._read_secret_file("GOOGLE_CLIENT_ID_FILE", "demo_google_id")
        self.google_client_secret = self._read_secret_file("GOOGLE_CLIENT_SECRET_FILE", "demo_google_secret")
        
        # Cache TTL settings (in seconds)
        self.cache_ttl = {
            "weather": 600,      # 10 minutes
            "traffic": 300,      # 5 minutes
            "ecommerce": 1800,   # 30 minutes
            "geocoding": 86400   # 24 hours
        }
        
        # Rate limiting settings
        self.rate_limits = {
            APIProvider.OPENWEATHERMAP: {"requests_per_minute": 60, "requests_per_day": 1000},
            APIProvider.TOMTOM: {"requests_per_minute": 50, "requests_per_day": 2500},
            APIProvider.SHOPIFY: {"requests_per_minute": 40, "requests_per_day": 10000},
            APIProvider.GOOGLE_MAPS: {"requests_per_minute": 100, "requests_per_day": 25000}
        }
    
    def _read_secret_file(self, env_var: str, default: str) -> str:
        """Read secret from file specified in environment variable"""
        try:
            file_path = os.getenv(env_var)
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read().strip()
            return default
        except Exception as e:
            logger.warning(f"Failed to read secret file {env_var}: {e}")
            return default
    
    async def initialize(self):
        """Initialize HTTP session and Redis connection"""
        global redis_client, http_session
        
        # Initialize Redis
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        
        # Initialize HTTP session with timeout and retry configuration
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        
        http_session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "AI-Workflow-Engine/1.0 External-API-Service"
            }
        )
        
        logger.info("External API Service initialized successfully")
    
    async def get_weather_data(self, request: WeatherRequest) -> Dict[str, Any]:
        """Get weather data from OpenWeatherMap with caching"""
        try:
            # Create cache key
            cache_key = f"weather:{request.latitude}:{request.longitude}:{request.units}"
            
            # Check cache first
            cached_data = await self.get_cached_data(cache_key)
            if cached_data:
                cached_data["source"] = "cache"
                return cached_data
            
            # Check rate limiting
            if not await self.check_rate_limit(APIProvider.OPENWEATHERMAP):
                raise HTTPException(status_code=429, detail="Rate limit exceeded for weather API")
            
            # Fetch from OpenWeatherMap API
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": request.latitude,
                "lon": request.longitude,
                "appid": self.openweather_api_key,
                "units": request.units
            }
            
            async with http_session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenWeatherMap API error: {response.status} - {error_text}")
                    raise HTTPException(status_code=502, detail="Weather API unavailable")
                
                raw_data = await response.json()
            
            # Normalize the data using Anti-Corruption Layer pattern
            normalized_data = self.normalize_weather_data(raw_data)
            
            # Cache the normalized data
            await self.cache_data(cache_key, normalized_data, self.cache_ttl["weather"])
            
            # Record metrics
            await metrics.record_counter("external_api_calls", 1, {
                "provider": APIProvider.OPENWEATHERMAP,
                "endpoint": "weather",
                "cache_hit": "false"
            })
            
            normalized_data["source"] = "api"
            return normalized_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            raise HTTPException(status_code=500, detail=f"Weather service error: {str(e)}")
    
    def normalize_weather_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize OpenWeatherMap data to internal format"""
        try:
            return {
                "temperature": raw_data["main"]["temp"],
                "feels_like": raw_data["main"]["feels_like"],
                "humidity": raw_data["main"]["humidity"],
                "pressure": raw_data["main"]["pressure"],
                "visibility": raw_data.get("visibility", 0) / 1000,  # Convert to km
                "wind_speed": raw_data.get("wind", {}).get("speed", 0),
                "wind_direction": raw_data.get("wind", {}).get("deg", 0),
                "weather_condition": raw_data["weather"][0]["main"],
                "weather_description": raw_data["weather"][0]["description"],
                "cloud_coverage": raw_data["clouds"]["all"],
                "sunrise": datetime.fromtimestamp(raw_data["sys"]["sunrise"]).isoformat(),
                "sunset": datetime.fromtimestamp(raw_data["sys"]["sunset"]).isoformat(),
                "location": {
                    "name": raw_data["name"],
                    "country": raw_data["sys"]["country"],
                    "coordinates": {
                        "latitude": raw_data["coord"]["lat"],
                        "longitude": raw_data["coord"]["lon"]
                    }
                },
                "timestamp": datetime.utcnow().isoformat(),
                "provider": APIProvider.OPENWEATHERMAP
            }
        except KeyError as e:
            logger.error(f"Error normalizing weather data: {e}")
            raise HTTPException(status_code=502, detail="Invalid weather data format")
    
    async def get_traffic_data(self, request: TrafficRequest) -> Dict[str, Any]:
        """Get traffic data from TomTom API with caching"""
        try:
            # Create cache key
            cache_key = f"traffic:{request.origin_lat}:{request.origin_lon}:{request.dest_lat}:{request.dest_lon}"
            
            # Check cache first
            cached_data = await self.get_cached_data(cache_key)
            if cached_data:
                cached_data["source"] = "cache"
                return cached_data
            
            # Check rate limiting
            if not await self.check_rate_limit(APIProvider.TOMTOM):
                raise HTTPException(status_code=429, detail="Rate limit exceeded for traffic API")
            
            # Fetch from TomTom API
            url = f"https://api.tomtom.com/routing/1/calculateRoute/{request.origin_lat},{request.origin_lon}:{request.dest_lat},{request.dest_lon}/json"
            params = {
                "key": self.tomtom_api_key,
                "traffic": "true",
                "travelMode": "car"
            }
            
            if request.departure_time:
                params["departAt"] = request.departure_time.isoformat()
            
            async with http_session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"TomTom API error: {response.status} - {error_text}")
                    raise HTTPException(status_code=502, detail="Traffic API unavailable")
                
                raw_data = await response.json()
            
            # Normalize the data
            normalized_data = self.normalize_traffic_data(raw_data)
            
            # Cache the normalized data
            await self.cache_data(cache_key, normalized_data, self.cache_ttl["traffic"])
            
            # Record metrics
            await metrics.record_counter("external_api_calls", 1, {
                "provider": APIProvider.TOMTOM,
                "endpoint": "traffic",
                "cache_hit": "false"
            })
            
            normalized_data["source"] = "api"
            return normalized_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching traffic data: {e}")
            raise HTTPException(status_code=500, detail=f"Traffic service error: {str(e)}")
    
    def normalize_traffic_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize TomTom traffic data to internal format"""
        try:
            route = raw_data["routes"][0]
            summary = route["summary"]
            
            return {
                "distance_meters": summary["lengthInMeters"],
                "distance_km": round(summary["lengthInMeters"] / 1000, 2),
                "duration_seconds": summary["travelTimeInSeconds"],
                "duration_minutes": round(summary["travelTimeInSeconds"] / 60, 1),
                "traffic_delay_seconds": summary.get("trafficDelayInSeconds", 0),
                "departure_time": summary.get("departureTime", datetime.utcnow().isoformat()),
                "arrival_time": summary.get("arrivalTime"),
                "route_geometry": route.get("legs", [{}])[0].get("points", []),
                "traffic_incidents": self.extract_traffic_incidents(route),
                "timestamp": datetime.utcnow().isoformat(),
                "provider": APIProvider.TOMTOM
            }
        except (KeyError, IndexError) as e:
            logger.error(f"Error normalizing traffic data: {e}")
            raise HTTPException(status_code=502, detail="Invalid traffic data format")
    
    def extract_traffic_incidents(self, route: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract traffic incidents from route data"""
        incidents = []
        
        # TomTom provides traffic incidents in legs
        for leg in route.get("legs", []):
            for point in leg.get("points", []):
                if "trafficIncident" in point:
                    incident = point["trafficIncident"]
                    incidents.append({
                        "type": incident.get("type", "unknown"),
                        "severity": incident.get("magnitude", 0),
                        "description": incident.get("description", ""),
                        "delay_seconds": incident.get("delay", 0),
                        "coordinates": {
                            "latitude": point.get("latitude"),
                            "longitude": point.get("longitude")
                        }
                    })
        
        return incidents
    
    async def get_ecommerce_data(self, request: EcommerceRequest) -> Dict[str, Any]:
        """Get e-commerce data from Shopify API with caching"""
        try:
            # Create cache key
            cache_key = f"ecommerce:{request.store_domain}:{request.product_query or 'all'}:{request.category or 'all'}:{request.limit}"
            
            # Check cache first
            cached_data = await self.get_cached_data(cache_key)
            if cached_data:
                cached_data["source"] = "cache"
                return cached_data
            
            # Check rate limiting
            if not await self.check_rate_limit(APIProvider.SHOPIFY):
                raise HTTPException(status_code=429, detail="Rate limit exceeded for e-commerce API")
            
            # Fetch from Shopify API
            url = f"https://{request.store_domain}/admin/api/2023-10/products.json"
            headers = {
                "X-Shopify-Access-Token": self.shopify_access_token
            }
            params = {
                "limit": min(request.limit, 250),  # Shopify limit
                "status": "active"
            }
            
            if request.product_query:
                params["title"] = request.product_query
            
            if request.category:
                params["product_type"] = request.category
            
            async with http_session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Shopify API error: {response.status} - {error_text}")
                    raise HTTPException(status_code=502, detail="E-commerce API unavailable")
                
                raw_data = await response.json()
            
            # Normalize the data
            normalized_data = self.normalize_ecommerce_data(raw_data)
            
            # Cache the normalized data
            await self.cache_data(cache_key, normalized_data, self.cache_ttl["ecommerce"])
            
            # Record metrics
            await metrics.record_counter("external_api_calls", 1, {
                "provider": APIProvider.SHOPIFY,
                "endpoint": "products",
                "cache_hit": "false"
            })
            
            normalized_data["source"] = "api"
            return normalized_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching e-commerce data: {e}")
            raise HTTPException(status_code=500, detail=f"E-commerce service error: {str(e)}")
    
    def normalize_ecommerce_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Shopify product data to internal format"""
        try:
            products = []
            
            for product in raw_data.get("products", []):
                # Get first variant for pricing (simplified)
                variant = product.get("variants", [{}])[0]
                
                normalized_product = {
                    "id": str(product["id"]),
                    "title": product["title"],
                    "description": product.get("body_html", ""),
                    "category": product.get("product_type", ""),
                    "vendor": product.get("vendor", ""),
                    "tags": product.get("tags", "").split(",") if product.get("tags") else [],
                    "price": float(variant.get("price", 0)),
                    "currency": "USD",  # Default, would be configurable
                    "availability": variant.get("inventory_quantity", 0) > 0,
                    "inventory_count": variant.get("inventory_quantity", 0),
                    "sku": variant.get("sku", ""),
                    "images": [img["src"] for img in product.get("images", [])],
                    "created_at": product.get("created_at"),
                    "updated_at": product.get("updated_at"),
                    "url": f"https://{product.get('handle', '')}"
                }
                
                products.append(normalized_product)
            
            return {
                "products": products,
                "total_count": len(products),
                "timestamp": datetime.utcnow().isoformat(),
                "provider": APIProvider.SHOPIFY
            }
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error normalizing e-commerce data: {e}")
            raise HTTPException(status_code=502, detail="Invalid e-commerce data format")
    
    async def check_rate_limit(self, provider: APIProvider) -> bool:
        """Check if API provider rate limit allows request"""
        try:
            current_minute = int(time.time() / 60)
            rate_key = f"rate_limit:{provider}:{current_minute}"
            
            current_count = await redis_client.get(rate_key)
            current_count = int(current_count) if current_count else 0
            
            limit = self.rate_limits[provider]["requests_per_minute"]
            
            if current_count >= limit:
                return False
            
            # Increment counter
            await redis_client.incr(rate_key)
            await redis_client.expire(rate_key, 60)  # Expire after 1 minute
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow request if check fails
    
    async def get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if available"""
        try:
            cached_json = await redis_client.get(f"api_cache:{cache_key}")
            if cached_json:
                return json.loads(cached_json)
            return None
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None
    
    async def cache_data(self, cache_key: str, data: Dict[str, Any], ttl: int):
        """Cache data with TTL"""
        try:
            cache_key_full = f"api_cache:{cache_key}"
            await redis_client.setex(cache_key_full, ttl, json.dumps(data, default=str))
            
            # Record cache metrics
            await metrics.record_counter("cache_operations", 1, {
                "operation": "set",
                "key_type": cache_key.split(":")[0]
            })
            
        except Exception as e:
            logger.error(f"Error caching data: {e}")

# Global service instance
external_api_service = ExternalAPIService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await external_api_service.initialize()
    logger.info("External API Integration Service started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    if http_session:
        await http_session.close()
    logger.info("External API Integration Service stopped")

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
        
        # Check HTTP session
        http_status = "connected" if http_session and not http_session.closed else "disconnected"
        
        return {
            "status": "healthy",
            "service": "external-api-integration",
            "dependencies": {
                "redis": redis_status,
                "http_session": http_status
            },
            "api_providers": {
                "openweathermap": "configured" if external_api_service.openweather_api_key != "demo_key" else "demo",
                "tomtom": "configured" if external_api_service.tomtom_api_key != "demo_key" else "demo",
                "shopify": "configured" if external_api_service.shopify_access_token != "demo_token" else "demo",
                "google_oauth": "configured" if external_api_service.google_client_id != "demo_google_id" else "demo"
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/weather")
async def get_weather(
    request: WeatherRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get weather data for specified coordinates"""
    return await external_api_service.get_weather_data(request)

@app.post("/traffic")
async def get_traffic(
    request: TrafficRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get traffic data for route between two points"""
    return await external_api_service.get_traffic_data(request)

@app.post("/ecommerce/products")
async def get_products(
    request: EcommerceRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get e-commerce product data"""
    return await external_api_service.get_ecommerce_data(request)

@app.get("/cache/stats")
async def get_cache_stats(user: Dict[str, Any] = Depends(get_current_user)):
    """Get cache statistics"""
    try:
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get cache keys statistics
        cache_patterns = ["api_cache:weather:*", "api_cache:traffic:*", "api_cache:ecommerce:*"]
        cache_stats = {}
        
        for pattern in cache_patterns:
            cache_type = pattern.split(":")[1]
            count = 0
            async for key in redis_client.scan_iter(match=pattern):
                count += 1
            cache_stats[cache_type] = count
        
        # Get rate limit statistics
        rate_limit_stats = {}
        for provider in APIProvider:
            current_minute = int(time.time() / 60)
            rate_key = f"rate_limit:{provider}:{current_minute}"
            current_count = await redis_client.get(rate_key)
            rate_limit_stats[provider] = {
                "current_minute_requests": int(current_count) if current_count else 0,
                "limit_per_minute": external_api_service.rate_limits[provider]["requests_per_minute"]
            }
        
        return {
            "cache_statistics": cache_stats,
            "rate_limit_statistics": rate_limit_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@app.delete("/cache/clear")
async def clear_cache(
    cache_type: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Clear cache (admin only)"""
    try:
        if not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if cache_type:
            pattern = f"api_cache:{cache_type}:*"
        else:
            pattern = "api_cache:*"
        
        deleted_count = 0
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
            deleted_count += 1
        
        return {
            "status": "cleared",
            "deleted_keys": deleted_count,
            "cache_type": cache_type or "all"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8010,
        reload=False,
        log_level="info"
    )