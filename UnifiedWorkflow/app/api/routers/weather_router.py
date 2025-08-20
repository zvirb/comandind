"""
Weather API router for weather-based services.

Provides endpoints for current weather, forecasts, and weather alerts.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime

from api.dependencies import get_current_user
from shared.database.models import User
from shared.services.weather_service import weather_service, WeatherUnits, WeatherData, WeatherForecast, WeatherAlert

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class WeatherRequest(BaseModel):
    """Weather request model."""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    units: str = Field("metric", description="Units: metric, imperial, standard")

class CityWeatherRequest(BaseModel):
    """City weather request model."""
    city_name: str = Field(..., description="City name")
    country_code: Optional[str] = Field(None, description="2-letter country code")
    units: str = Field("metric", description="Units: metric, imperial, standard")

class BatchWeatherRequest(BaseModel):
    """Batch weather request model."""
    coordinates: List[List[float]] = Field(..., description="List of [lat, lng] coordinate pairs")
    units: str = Field("metric", description="Units: metric, imperial, standard")

class WeatherConditionResponse(BaseModel):
    """Weather condition response model."""
    id: int
    main: str
    description: str
    icon: str

class WeatherDataResponse(BaseModel):
    """Weather data response model."""
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    visibility: Optional[int]
    uv_index: Optional[float]
    wind_speed: float
    wind_direction: int
    cloudiness: int
    condition: WeatherConditionResponse
    sunrise: datetime
    sunset: datetime
    timezone_offset: int

class ForecastItemResponse(BaseModel):
    """Forecast item response model."""
    datetime: datetime
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    wind_direction: int
    cloudiness: int
    condition: WeatherConditionResponse
    pop: float  # Probability of precipitation

class WeatherForecastResponse(BaseModel):
    """Weather forecast response model."""
    location: str
    latitude: float
    longitude: float
    current: WeatherDataResponse
    hourly: List[ForecastItemResponse]
    daily: List[ForecastItemResponse]

class WeatherAlertResponse(BaseModel):
    """Weather alert response model."""
    event: str
    start: datetime
    end: datetime
    description: str
    sender_name: str

def _convert_weather_data(weather_data: WeatherData) -> WeatherDataResponse:
    """Convert WeatherData to response model."""
    return WeatherDataResponse(
        temperature=weather_data.temperature,
        feels_like=weather_data.feels_like,
        humidity=weather_data.humidity,
        pressure=weather_data.pressure,
        visibility=weather_data.visibility,
        uv_index=weather_data.uv_index,
        wind_speed=weather_data.wind_speed,
        wind_direction=weather_data.wind_direction,
        cloudiness=weather_data.cloudiness,
        condition=WeatherConditionResponse(
            id=weather_data.condition.id,
            main=weather_data.condition.main,
            description=weather_data.condition.description,
            icon=weather_data.condition.icon
        ),
        sunrise=weather_data.sunrise,
        sunset=weather_data.sunset,
        timezone_offset=weather_data.timezone_offset
    )

def _convert_forecast_item(forecast_item) -> ForecastItemResponse:
    """Convert forecast item to response model."""
    return ForecastItemResponse(
        datetime=forecast_item.datetime,
        temperature=forecast_item.temperature,
        feels_like=forecast_item.feels_like,
        humidity=forecast_item.humidity,
        pressure=forecast_item.pressure,
        wind_speed=forecast_item.wind_speed,
        wind_direction=forecast_item.wind_direction,
        cloudiness=forecast_item.cloudiness,
        condition=WeatherConditionResponse(
            id=forecast_item.condition.id,
            main=forecast_item.condition.main,
            description=forecast_item.condition.description,
            icon=forecast_item.condition.icon
        ),
        pop=forecast_item.pop
    )

@router.get("/current", response_model=WeatherDataResponse)
async def get_current_weather(
    lat: float = Query(..., description="Latitude coordinate"),
    lng: float = Query(..., description="Longitude coordinate"),
    units: str = Query("metric", description="Units: metric, imperial, standard"),
    current_user: User = Depends(get_current_user)
):
    """
    Get current weather for specific coordinates.
    
    Returns real-time weather conditions including temperature, humidity, wind, etc.
    """
    try:
        # Validate units
        try:
            weather_units = WeatherUnits(units)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid units. Use: metric, imperial, or standard"
            )
        
        result = await weather_service.get_current_weather(lat, lng, weather_units)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Weather data not available for this location"
            )
        
        return _convert_weather_data(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve current weather"
        )

@router.post("/current", response_model=WeatherDataResponse)
async def get_current_weather_post(
    request: WeatherRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get current weather for specific coordinates (POST method).
    
    Alternative POST endpoint for getting current weather data.
    """
    try:
        # Validate units
        try:
            weather_units = WeatherUnits(request.units)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid units. Use: metric, imperial, or standard"
            )
        
        result = await weather_service.get_current_weather(
            request.latitude, 
            request.longitude, 
            weather_units
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Weather data not available for this location"
            )
        
        return _convert_weather_data(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve current weather"
        )

@router.get("/forecast", response_model=WeatherForecastResponse)
async def get_weather_forecast(
    lat: float = Query(..., description="Latitude coordinate"),
    lng: float = Query(..., description="Longitude coordinate"),
    units: str = Query("metric", description="Units: metric, imperial, standard"),
    exclude: Optional[str] = Query(None, description="Comma-separated parts to exclude: minutely,hourly,daily,alerts"),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive weather forecast for specific coordinates.
    
    Returns current weather plus hourly and daily forecasts.
    """
    try:
        # Validate units
        try:
            weather_units = WeatherUnits(units)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid units. Use: metric, imperial, or standard"
            )
        
        exclude_list = None
        if exclude:
            exclude_list = [part.strip() for part in exclude.split(",")]
        
        result = await weather_service.get_weather_forecast(
            lat, lng, weather_units, exclude_list
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Weather forecast not available for this location"
            )
        
        return WeatherForecastResponse(
            location=result.location,
            latitude=result.latitude,
            longitude=result.longitude,
            current=_convert_weather_data(result.current),
            hourly=[_convert_forecast_item(item) for item in result.hourly],
            daily=[_convert_forecast_item(item) for item in result.daily]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve weather forecast"
        )

@router.post("/city", response_model=WeatherDataResponse)
async def get_weather_by_city(
    request: CityWeatherRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get current weather by city name.
    
    Find weather conditions for a named city, optionally with country code.
    """
    try:
        # Validate units
        try:
            weather_units = WeatherUnits(request.units)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid units. Use: metric, imperial, or standard"
            )
        
        result = await weather_service.get_weather_by_city(
            request.city_name,
            request.country_code,
            weather_units
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Weather data not available for this city"
            )
        
        return _convert_weather_data(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weather by city: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve weather by city"
        )

@router.get("/alerts", response_model=List[WeatherAlertResponse])
async def get_weather_alerts(
    lat: float = Query(..., description="Latitude coordinate"),
    lng: float = Query(..., description="Longitude coordinate"),
    current_user: User = Depends(get_current_user)
):
    """
    Get weather alerts for specific coordinates.
    
    Returns active weather warnings and advisories for the location.
    """
    try:
        results = await weather_service.get_weather_alerts(lat, lng)
        
        return [
            WeatherAlertResponse(
                event=alert.event,
                start=alert.start,
                end=alert.end,
                description=alert.description,
                sender_name=alert.sender_name
            )
            for alert in results
        ]
    except Exception as e:
        logger.error(f"Error getting weather alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve weather alerts"
        )

@router.post("/batch", response_model=Dict[str, Optional[WeatherDataResponse]])
async def get_batch_weather(
    request: BatchWeatherRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get weather for multiple coordinates in parallel.
    
    Efficiently retrieve weather data for multiple locations at once.
    """
    try:
        # Validate units
        try:
            weather_units = WeatherUnits(request.units)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid units. Use: metric, imperial, or standard"
            )
        
        # Convert coordinates to tuples
        coordinate_tuples = []
        for coord in request.coordinates:
            if len(coord) != 2:
                raise HTTPException(
                    status_code=400,
                    detail="Each coordinate must be [latitude, longitude]"
                )
            coordinate_tuples.append((coord[0], coord[1]))
        
        results = await weather_service.search_weather_by_coordinates_batch(
            coordinate_tuples, weather_units
        )
        
        # Convert results to response format
        response = {}
        for coord_key, weather_data in results.items():
            if weather_data:
                response[coord_key] = _convert_weather_data(weather_data)
            else:
                response[coord_key] = None
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch weather: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve batch weather data"
        )

@router.get("/icon/{icon_code}")
async def get_weather_icon_url(
    icon_code: str,
    size: str = Query("2x", description="Icon size: 1x, 2x, 4x")
):
    """
    Get URL for weather icon.
    
    Returns the URL for the weather condition icon from OpenWeatherMap.
    """
    try:
        icon_url = weather_service.get_weather_icon_url(icon_code, size)
        return {"url": icon_url}
    except Exception as e:
        logger.error(f"Error getting weather icon URL: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate weather icon URL"
        )

@router.get("/map/{layer}/{zoom}/{x}/{y}")
async def get_weather_map_tile(
    layer: str,
    zoom: int,
    x: int,
    y: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get URL for weather map tile.
    
    Returns the URL for weather map tiles (clouds, precipitation, temperature, etc.).
    Available layers: clouds_new, precipitation_new, pressure_new, wind_new, temp_new
    """
    try:
        valid_layers = ["clouds_new", "precipitation_new", "pressure_new", "wind_new", "temp_new"]
        if layer not in valid_layers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid layer. Available layers: {', '.join(valid_layers)}"
            )
        
        tile_url = weather_service.get_weather_map_url(layer, zoom, x, y)
        return {"url": tile_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weather map tile URL: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate weather map tile URL"
        )

@router.get("/health")
async def weather_health_check():
    """
    Health check endpoint for weather service.
    
    Verifies that the OpenWeatherMap API integration is working properly.
    """
    try:
        # Check if API key is configured
        if not weather_service.api_key:
            return {
                "status": "degraded",
                "message": "OpenWeather API key not configured",
                "timestamp": datetime.now().isoformat()
            }
        
        # Test with a simple request (San Francisco coordinates)
        test_weather = await weather_service.get_current_weather(37.7749, -122.4194)
        
        if test_weather:
            return {
                "status": "healthy",
                "message": "Weather service is operational",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "message": "Weather API not responding",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Weather health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Weather service error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }