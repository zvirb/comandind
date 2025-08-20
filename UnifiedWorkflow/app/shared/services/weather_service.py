"""
Weather API integration service using OpenWeatherMap API.

Provides comprehensive weather data including current conditions, forecasts,
and weather maps for location-based features.
"""

import os
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class WeatherUnits(Enum):
    """Weather data units."""
    STANDARD = "standard"  # Kelvin, meters/sec
    METRIC = "metric"      # Celsius, meters/sec
    IMPERIAL = "imperial"  # Fahrenheit, miles/hour

@dataclass
class WeatherCondition:
    """Weather condition details."""
    id: int
    main: str
    description: str
    icon: str

@dataclass
class WeatherData:
    """Current weather data."""
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    visibility: Optional[int]
    uv_index: Optional[float]
    wind_speed: float
    wind_direction: int
    cloudiness: int
    condition: WeatherCondition
    sunrise: datetime
    sunset: datetime
    timezone_offset: int

@dataclass
class ForecastItem:
    """Single forecast data point."""
    datetime: datetime
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    wind_direction: int
    cloudiness: int
    condition: WeatherCondition
    pop: float  # Probability of precipitation

@dataclass
class WeatherForecast:
    """Weather forecast data."""
    location: str
    latitude: float
    longitude: float
    current: WeatherData
    hourly: List[ForecastItem]
    daily: List[ForecastItem]

@dataclass
class WeatherAlert:
    """Weather alert/warning."""
    event: str
    start: datetime
    end: datetime
    description: str
    sender_name: str

class WeatherService:
    """Service for weather data using OpenWeatherMap API."""
    
    def __init__(self):
        """Initialize the weather service."""
        self.api_key = self._load_api_key()
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.onecall_url = "https://api.openweathermap.org/data/3.0/onecall"
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _load_api_key(self) -> str:
        """Load OpenWeather API key from secrets file."""
        try:
            # Try loading from file first (Docker secrets)
            key_file = os.getenv("OPENWEATHER_API_KEY_FILE", "/run/secrets/openweather_api_key")
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not load weather API key from file: {e}")
        
        # Fallback to environment variable
        api_key = os.getenv("OPENWEATHER_API_KEY", "")
        if not api_key:
            logger.warning("OpenWeather API key not configured")
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
    
    def _parse_weather_condition(self, weather_data: Dict) -> WeatherCondition:
        """Parse weather condition from API response."""
        return WeatherCondition(
            id=weather_data["id"],
            main=weather_data["main"],
            description=weather_data["description"],
            icon=weather_data["icon"]
        )
    
    def _parse_current_weather(self, data: Dict, timezone_offset: int = 0) -> WeatherData:
        """Parse current weather data from API response."""
        return WeatherData(
            temperature=data["temp"],
            feels_like=data["feels_like"],
            humidity=data["humidity"],
            pressure=data["pressure"],
            visibility=data.get("visibility"),
            uv_index=data.get("uvi"),
            wind_speed=data["wind_speed"],
            wind_direction=data.get("wind_deg", 0),
            cloudiness=data["clouds"],
            condition=self._parse_weather_condition(data["weather"][0]),
            sunrise=datetime.fromtimestamp(data["sunrise"] + timezone_offset),
            sunset=datetime.fromtimestamp(data["sunset"] + timezone_offset),
            timezone_offset=timezone_offset
        )
    
    def _parse_forecast_item(self, data: Dict, timezone_offset: int = 0) -> ForecastItem:
        """Parse forecast item from API response."""
        # Handle both hourly and daily forecast formats
        if "temp" in data and isinstance(data["temp"], dict):
            # Daily forecast format
            temperature = data["temp"]["day"]
            feels_like = data["feels_like"]["day"]
        else:
            # Hourly forecast format
            temperature = data["temp"]
            feels_like = data["feels_like"]
        
        return ForecastItem(
            datetime=datetime.fromtimestamp(data["dt"] + timezone_offset),
            temperature=temperature,
            feels_like=feels_like,
            humidity=data["humidity"],
            pressure=data["pressure"],
            wind_speed=data["wind_speed"],
            wind_direction=data.get("wind_deg", 0),
            cloudiness=data["clouds"],
            condition=self._parse_weather_condition(data["weather"][0]),
            pop=data.get("pop", 0.0)
        )
    
    async def get_current_weather(
        self, 
        latitude: float, 
        longitude: float,
        units: WeatherUnits = WeatherUnits.METRIC
    ) -> Optional[WeatherData]:
        """
        Get current weather for coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            units: Units for temperature and wind speed
            
        Returns:
            WeatherData object or None if error
        """
        if not self.api_key:
            logger.error("OpenWeather API key not configured")
            return None
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/weather"
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": units.value
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert to WeatherData format
                    current_data = {
                        "temp": data["main"]["temp"],
                        "feels_like": data["main"]["feels_like"],
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "visibility": data.get("visibility"),
                        "uvi": None,  # Not available in current weather API
                        "wind_speed": data.get("wind", {}).get("speed", 0),
                        "wind_deg": data.get("wind", {}).get("deg", 0),
                        "clouds": data.get("clouds", {}).get("all", 0),
                        "weather": data["weather"],
                        "sunrise": data["sys"]["sunrise"],
                        "sunset": data["sys"]["sunset"]
                    }
                    
                    return self._parse_current_weather(current_data, data.get("timezone", 0))
                else:
                    logger.error(f"Current weather API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting current weather: {e}")
            return None
    
    async def get_weather_forecast(
        self, 
        latitude: float, 
        longitude: float,
        units: WeatherUnits = WeatherUnits.METRIC,
        exclude: Optional[List[str]] = None
    ) -> Optional[WeatherForecast]:
        """
        Get comprehensive weather forecast including current, hourly, and daily data.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            units: Units for temperature and wind speed
            exclude: Optional list of data parts to exclude (minutely, hourly, daily, alerts)
            
        Returns:
            WeatherForecast object or None if error
        """
        if not self.api_key:
            logger.error("OpenWeather API key not configured")
            return None
            
        try:
            session = await self._get_session()
            url = f"{self.onecall_url}"
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": units.value
            }
            
            if exclude:
                params["exclude"] = ",".join(exclude)
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    timezone_offset = data.get("timezone_offset", 0)
                    
                    # Parse current weather
                    current = self._parse_current_weather(data["current"], timezone_offset)
                    
                    # Parse hourly forecast (next 48 hours)
                    hourly = []
                    for hour_data in data.get("hourly", [])[:24]:  # Limit to 24 hours
                        hourly.append(self._parse_forecast_item(hour_data, timezone_offset))
                    
                    # Parse daily forecast (next 7 days)
                    daily = []
                    for day_data in data.get("daily", [])[:7]:  # Limit to 7 days
                        daily.append(self._parse_forecast_item(day_data, timezone_offset))
                    
                    return WeatherForecast(
                        location=f"{latitude:.2f}, {longitude:.2f}",
                        latitude=latitude,
                        longitude=longitude,
                        current=current,
                        hourly=hourly,
                        daily=daily
                    )
                else:
                    logger.error(f"Weather forecast API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting weather forecast: {e}")
            return None
    
    async def get_weather_by_city(
        self, 
        city_name: str,
        country_code: Optional[str] = None,
        units: WeatherUnits = WeatherUnits.METRIC
    ) -> Optional[WeatherData]:
        """
        Get current weather by city name.
        
        Args:
            city_name: Name of the city
            country_code: Optional 2-letter country code
            units: Units for temperature and wind speed
            
        Returns:
            WeatherData object or None if error
        """
        if not self.api_key:
            logger.error("OpenWeather API key not configured")
            return None
            
        try:
            session = await self._get_session()
            url = f"{self.base_url}/weather"
            
            query = city_name
            if country_code:
                query = f"{city_name},{country_code}"
                
            params = {
                "q": query,
                "appid": self.api_key,
                "units": units.value
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert to WeatherData format
                    current_data = {
                        "temp": data["main"]["temp"],
                        "feels_like": data["main"]["feels_like"],
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "visibility": data.get("visibility"),
                        "uvi": None,
                        "wind_speed": data.get("wind", {}).get("speed", 0),
                        "wind_deg": data.get("wind", {}).get("deg", 0),
                        "clouds": data.get("clouds", {}).get("all", 0),
                        "weather": data["weather"],
                        "sunrise": data["sys"]["sunrise"],
                        "sunset": data["sys"]["sunset"]
                    }
                    
                    return self._parse_current_weather(current_data, data.get("timezone", 0))
                else:
                    logger.error(f"Weather by city API request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting weather by city: {e}")
            return None
    
    async def get_weather_alerts(
        self, 
        latitude: float, 
        longitude: float
    ) -> List[WeatherAlert]:
        """
        Get weather alerts for coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            List of WeatherAlert objects
        """
        if not self.api_key:
            logger.error("OpenWeather API key not configured")
            return []
            
        try:
            session = await self._get_session()
            url = f"{self.onecall_url}"
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "exclude": "current,minutely,hourly,daily"  # Only get alerts
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    alerts = []
                    
                    for alert_data in data.get("alerts", []):
                        alert = WeatherAlert(
                            event=alert_data["event"],
                            start=datetime.fromtimestamp(alert_data["start"]),
                            end=datetime.fromtimestamp(alert_data["end"]),
                            description=alert_data["description"],
                            sender_name=alert_data["sender_name"]
                        )
                        alerts.append(alert)
                    
                    return alerts
                else:
                    logger.error(f"Weather alerts API request failed: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting weather alerts: {e}")
            return []
    
    def get_weather_icon_url(self, icon_code: str, size: str = "2x") -> str:
        """
        Get URL for weather icon.
        
        Args:
            icon_code: Weather icon code from API
            size: Icon size (1x, 2x, 4x)
            
        Returns:
            URL for weather icon
        """
        return f"https://openweathermap.org/img/wn/{icon_code}@{size}.png"
    
    def get_weather_map_url(
        self, 
        layer: str,
        zoom: int,
        x: int,
        y: int
    ) -> str:
        """
        Get URL for weather map tile.
        
        Args:
            layer: Map layer (clouds_new, precipitation_new, pressure_new, wind_new, temp_new)
            zoom: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate
            
        Returns:
            URL for weather map tile
        """
        return f"https://tile.openweathermap.org/map/{layer}/{zoom}/{x}/{y}.png?appid={self.api_key}"
    
    async def search_weather_by_coordinates_batch(
        self, 
        coordinates: List[Tuple[float, float]],
        units: WeatherUnits = WeatherUnits.METRIC
    ) -> Dict[str, Optional[WeatherData]]:
        """
        Get weather for multiple coordinates in parallel.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            units: Units for temperature and wind speed
            
        Returns:
            Dictionary mapping coordinate strings to WeatherData objects
        """
        if not self.api_key:
            logger.error("OpenWeather API key not configured")
            return {}
        
        results = {}
        
        # Process coordinates in parallel
        tasks = []
        for lat, lon in coordinates:
            task = self.get_current_weather(lat, lon, units)
            tasks.append((f"{lat},{lon}", task))
        
        # Execute all requests concurrently
        import asyncio
        completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Map results back to coordinates
        for (coord_key, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                logger.error(f"Error getting weather for {coord_key}: {result}")
                results[coord_key] = None
            else:
                results[coord_key] = result
        
        return results

# Global service instance
weather_service = WeatherService()