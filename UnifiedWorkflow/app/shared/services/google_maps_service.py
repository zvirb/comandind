"""
Google Maps API integration service for location-based features.

Provides access to Google Maps JavaScript API, Places API, and Geocoding API
using the existing Google project credentials.
"""

import os
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class PlaceDetails:
    """Represents a place from Google Places API."""
    place_id: str
    name: str
    formatted_address: str
    latitude: float
    longitude: float
    rating: Optional[float] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None
    business_status: Optional[str] = None
    types: List[str] = None

@dataclass
class GeocodingResult:
    """Represents a geocoding result."""
    formatted_address: str
    latitude: float
    longitude: float
    place_id: str
    address_components: List[Dict[str, Any]]

class GoogleMapsService:
    """Service for interacting with Google Maps APIs."""
    
    def __init__(self):
        """Initialize the Google Maps service."""
        self.api_key = self._load_api_key()
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _load_api_key(self) -> str:
        """Load Google Maps API key from secrets file."""
        try:
            # Try loading from file first (Docker secrets)
            key_file = os.getenv("GOOGLE_MAPS_API_KEY_FILE", "/run/secrets/google_maps_api_key")
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not load API key from file: {e}")
        
        # Fallback to environment variable
        api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        if not api_key or api_key == "demo_google_maps_key":
            logger.warning("Google Maps API key not configured or using demo key")
            return ""
        
        return api_key
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "AI-Workflow-Engine/1.0"}
            )
        return self.session
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def geocode_address(self, address: str) -> Optional[GeocodingResult]:
        """
        Geocode an address to get coordinates and place information.
        
        Args:
            address: The address to geocode
            
        Returns:
            GeocodingResult object or None if not found
        """
        if not self.api_key:
            logger.error("Google Maps API key not configured")
            return None
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/geocode/json"
            params = {
                "address": address,
                "key": self.api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "OK" and data.get("results"):
                        result = data["results"][0]
                        location = result["geometry"]["location"]
                        
                        return GeocodingResult(
                            formatted_address=result["formatted_address"],
                            latitude=location["lat"],
                            longitude=location["lng"],
                            place_id=result["place_id"],
                            address_components=result.get("address_components", [])
                        )
                    else:
                        logger.warning(f"Geocoding failed: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                        return None
                else:
                    logger.error(f"Geocoding API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error during geocoding: {e}")
            return None
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeocodingResult]:
        """
        Reverse geocode coordinates to get address information.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            GeocodingResult object or None if not found
        """
        if not self.api_key:
            logger.error("Google Maps API key not configured")
            return None
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/geocode/json"
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "OK" and data.get("results"):
                        result = data["results"][0]
                        location = result["geometry"]["location"]
                        
                        return GeocodingResult(
                            formatted_address=result["formatted_address"],
                            latitude=location["lat"],
                            longitude=location["lng"],
                            place_id=result["place_id"],
                            address_components=result.get("address_components", [])
                        )
                    else:
                        logger.warning(f"Reverse geocoding failed: {data.get('status')}")
                        return None
                else:
                    logger.error(f"Reverse geocoding API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error during reverse geocoding: {e}")
            return None
    
    async def search_places(
        self, 
        query: str, 
        location: Optional[Tuple[float, float]] = None,
        radius: int = 5000,
        place_type: Optional[str] = None
    ) -> List[PlaceDetails]:
        """
        Search for places using Google Places API.
        
        Args:
            query: Search query
            location: Optional (lat, lng) tuple for proximity search
            radius: Search radius in meters (default 5000)
            place_type: Optional place type filter
            
        Returns:
            List of PlaceDetails objects
        """
        if not self.api_key:
            logger.error("Google Maps API key not configured")
            return []
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/place/textsearch/json"
            params = {
                "query": query,
                "key": self.api_key
            }
            
            if location:
                params["location"] = f"{location[0]},{location[1]}"
                params["radius"] = radius
                
            if place_type:
                params["type"] = place_type
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "OK":
                        places = []
                        for result in data.get("results", []):
                            location = result["geometry"]["location"]
                            place = PlaceDetails(
                                place_id=result["place_id"],
                                name=result["name"],
                                formatted_address=result.get("formatted_address", ""),
                                latitude=location["lat"],
                                longitude=location["lng"],
                                rating=result.get("rating"),
                                business_status=result.get("business_status"),
                                types=result.get("types", [])
                            )
                            places.append(place)
                        return places
                    else:
                        logger.warning(f"Places search failed: {data.get('status')}")
                        return []
                else:
                    logger.error(f"Places API request failed: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error during places search: {e}")
            return []
    
    async def get_place_details(self, place_id: str) -> Optional[PlaceDetails]:
        """
        Get detailed information about a specific place.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            PlaceDetails object or None if not found
        """
        if not self.api_key:
            logger.error("Google Maps API key not configured")
            return None
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/place/details/json"
            params = {
                "place_id": place_id,
                "fields": "place_id,name,formatted_address,geometry,rating,formatted_phone_number,website,business_status,types",
                "key": self.api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "OK" and data.get("result"):
                        result = data["result"]
                        location = result["geometry"]["location"]
                        
                        return PlaceDetails(
                            place_id=result["place_id"],
                            name=result["name"],
                            formatted_address=result.get("formatted_address", ""),
                            latitude=location["lat"],
                            longitude=location["lng"],
                            rating=result.get("rating"),
                            phone_number=result.get("formatted_phone_number"),
                            website=result.get("website"),
                            business_status=result.get("business_status"),
                            types=result.get("types", [])
                        )
                    else:
                        logger.warning(f"Place details failed: {data.get('status')}")
                        return None
                else:
                    logger.error(f"Place details API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting place details: {e}")
            return None
    
    async def calculate_distance_matrix(
        self, 
        origins: List[str], 
        destinations: List[str],
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """
        Calculate distance and time between multiple origins and destinations.
        
        Args:
            origins: List of origin addresses or coordinates
            destinations: List of destination addresses or coordinates
            mode: Travel mode (driving, walking, bicycling, transit)
            
        Returns:
            Distance matrix data
        """
        if not self.api_key:
            logger.error("Google Maps API key not configured")
            return {}
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/distancematrix/json"
            params = {
                "origins": "|".join(origins),
                "destinations": "|".join(destinations),
                "mode": mode,
                "units": "metric",
                "key": self.api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") == "OK":
                        return data
                    else:
                        logger.warning(f"Distance matrix failed: {data.get('status')}")
                        return {}
                else:
                    logger.error(f"Distance matrix API request failed: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error calculating distance matrix: {e}")
            return {}
    
    def get_javascript_api_config(self) -> Dict[str, str]:
        """
        Get configuration for Google Maps JavaScript API frontend integration.
        
        Returns:
            Dictionary with API configuration
        """
        return {
            "apiKey": self.api_key if self.api_key and self.api_key != "demo_google_maps_key" else "",
            "libraries": "places,geometry,drawing",
            "version": "weekly",
            "region": "US",
            "language": "en"
        }

# Global service instance
google_maps_service = GoogleMapsService()