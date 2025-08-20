"""
Google Maps API router for location-based services.

Provides endpoints for geocoding, places search, and maps configuration.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from shared.database.models import User
from shared.services.google_maps_service import google_maps_service, PlaceDetails, GeocodingResult

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class GeocodeRequest(BaseModel):
    """Geocoding request model."""
    address: str = Field(..., description="Address to geocode")

class ReverseGeocodeRequest(BaseModel):
    """Reverse geocoding request model."""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")

class PlacesSearchRequest(BaseModel):
    """Places search request model."""
    query: str = Field(..., description="Search query")
    location: Optional[List[float]] = Field(None, description="Optional [lat, lng] for proximity search")
    radius: int = Field(5000, description="Search radius in meters")
    place_type: Optional[str] = Field(None, description="Optional place type filter")

class DistanceMatrixRequest(BaseModel):
    """Distance matrix request model."""
    origins: List[str] = Field(..., description="List of origin addresses or coordinates")
    destinations: List[str] = Field(..., description="List of destination addresses or coordinates")
    mode: str = Field("driving", description="Travel mode: driving, walking, bicycling, transit")

class GeocodeResponse(BaseModel):
    """Geocoding response model."""
    formatted_address: str
    latitude: float
    longitude: float
    place_id: str
    address_components: List[Dict[str, Any]]

class PlaceDetailsResponse(BaseModel):
    """Place details response model."""
    place_id: str
    name: str
    formatted_address: str
    latitude: float
    longitude: float
    rating: Optional[float] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None
    business_status: Optional[str] = None
    types: List[str] = []

class MapsConfigResponse(BaseModel):
    """Maps configuration response model."""
    apiKey: str
    libraries: str
    version: str
    region: str
    language: str

@router.get("/config", response_model=MapsConfigResponse)
async def get_maps_config():
    """
    Get Google Maps JavaScript API configuration for frontend.
    
    Returns the API key and configuration needed to load Google Maps in the frontend.
    """
    try:
        config = google_maps_service.get_javascript_api_config()
        
        return MapsConfigResponse(
            apiKey=config["apiKey"],
            libraries=config["libraries"],
            version=config["version"],
            region=config["region"],
            language=config["language"]
        )
    except Exception as e:
        logger.error(f"Error getting maps config: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve maps configuration"
        )

@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Geocode an address to get coordinates and place information.
    
    Converts a human-readable address into geographic coordinates.
    """
    try:
        result = await google_maps_service.geocode_address(request.address)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Address not found"
            )
        
        return GeocodeResponse(
            formatted_address=result.formatted_address,
            latitude=result.latitude,
            longitude=result.longitude,
            place_id=result.place_id,
            address_components=result.address_components
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error geocoding address: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to geocode address"
        )

@router.post("/reverse-geocode", response_model=GeocodeResponse)
async def reverse_geocode_coordinates(
    request: ReverseGeocodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Reverse geocode coordinates to get address information.
    
    Converts geographic coordinates into a human-readable address.
    """
    try:
        result = await google_maps_service.reverse_geocode(
            request.latitude, 
            request.longitude
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Location not found"
            )
        
        return GeocodeResponse(
            formatted_address=result.formatted_address,
            latitude=result.latitude,
            longitude=result.longitude,
            place_id=result.place_id,
            address_components=result.address_components
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverse geocoding coordinates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to reverse geocode coordinates"
        )

@router.post("/places/search", response_model=List[PlaceDetailsResponse])
async def search_places(
    request: PlacesSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search for places using Google Places API.
    
    Find businesses, landmarks, and other points of interest.
    """
    try:
        location = None
        if request.location and len(request.location) == 2:
            location = (request.location[0], request.location[1])
        
        results = await google_maps_service.search_places(
            query=request.query,
            location=location,
            radius=request.radius,
            place_type=request.place_type
        )
        
        return [
            PlaceDetailsResponse(
                place_id=place.place_id,
                name=place.name,
                formatted_address=place.formatted_address,
                latitude=place.latitude,
                longitude=place.longitude,
                rating=place.rating,
                phone_number=place.phone_number,
                website=place.website,
                business_status=place.business_status,
                types=place.types or []
            )
            for place in results
        ]
    except Exception as e:
        logger.error(f"Error searching places: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to search places"
        )

@router.get("/places/{place_id}", response_model=PlaceDetailsResponse)
async def get_place_details(
    place_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific place.
    
    Retrieve comprehensive details for a place by its Google Place ID.
    """
    try:
        result = await google_maps_service.get_place_details(place_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Place not found"
            )
        
        return PlaceDetailsResponse(
            place_id=result.place_id,
            name=result.name,
            formatted_address=result.formatted_address,
            latitude=result.latitude,
            longitude=result.longitude,
            rating=result.rating,
            phone_number=result.phone_number,
            website=result.website,
            business_status=result.business_status,
            types=result.types or []
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting place details: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get place details"
        )

@router.post("/distance-matrix")
async def calculate_distance_matrix(
    request: DistanceMatrixRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate distance and time between multiple origins and destinations.
    
    Get travel distance and duration for various transportation modes.
    """
    try:
        result = await google_maps_service.calculate_distance_matrix(
            origins=request.origins,
            destinations=request.destinations,
            mode=request.mode
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate distance matrix"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating distance matrix: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to calculate distance matrix"
        )

@router.get("/nearby")
async def find_nearby_places(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    radius: int = Query(1000, description="Search radius in meters"),
    place_type: Optional[str] = Query(None, description="Place type filter"),
    current_user: User = Depends(get_current_user)
):
    """
    Find places near specific coordinates.
    
    Discover businesses and points of interest within a specified radius.
    """
    try:
        # Use a generic search query for nearby places
        query = place_type if place_type else "places"
        
        results = await google_maps_service.search_places(
            query=query,
            location=(latitude, longitude),
            radius=radius,
            place_type=place_type
        )
        
        return [
            PlaceDetailsResponse(
                place_id=place.place_id,
                name=place.name,
                formatted_address=place.formatted_address,
                latitude=place.latitude,
                longitude=place.longitude,
                rating=place.rating,
                phone_number=place.phone_number,
                website=place.website,
                business_status=place.business_status,
                types=place.types or []
            )
            for place in results
        ]
    except Exception as e:
        logger.error(f"Error finding nearby places: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to find nearby places"
        )

@router.get("/health")
async def maps_health_check():
    """
    Health check endpoint for Google Maps service.
    
    Verifies that the Google Maps API integration is working properly.
    """
    try:
        config = google_maps_service.get_javascript_api_config()
        
        # Check if API key is configured
        if not config["apiKey"]:
            return {
                "status": "degraded",
                "message": "Google Maps API key not configured",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        
        return {
            "status": "healthy",
            "message": "Google Maps service is operational",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Maps health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Google Maps service error: {str(e)}",
            "timestamp": "2024-01-01T00:00:00Z"
        }