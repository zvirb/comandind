import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Loader } from '@googlemaps/js-api-loader';

/**
 * Google Maps React Component with Weather Integration
 * 
 * Features:
 * - Interactive Google Maps with places search
 * - Weather overlay data
 * - Location geocoding and reverse geocoding
 * - Custom markers and info windows
 * - Responsive design
 */
const GoogleMapsComponent = ({
  center = { lat: 37.7749, lng: -122.4194 }, // Default to San Francisco
  zoom = 10,
  height = '400px',
  width = '100%',
  showWeather = true,
  showPlaces = true,
  onLocationSelect = null,
  onWeatherUpdate = null,
  searchQuery = '',
  markers = [],
  className = ''
}) => {
  const mapRef = useRef(null);
  const [map, setMap] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [places, setPlaces] = useState([]);
  const [currentLocation, setCurrentLocation] = useState(center);
  const markersRef = useRef([]);
  const infoWindowRef = useRef(null);

  // Load Google Maps API
  useEffect(() => {
    const loadGoogleMaps = async () => {
      try {
        // Get API configuration from backend
        const response = await fetch('/api/v1/maps/config');
        if (!response.ok) {
          throw new Error('Failed to load maps configuration');
        }
        
        const config = await response.json();
        
        if (!config.apiKey) {
          throw new Error('Google Maps API key not configured');
        }

        const loader = new Loader({
          apiKey: config.apiKey,
          version: config.version || 'weekly',
          libraries: config.libraries?.split(',') || ['places', 'geometry'],
          region: config.region || 'US',
          language: config.language || 'en'
        });

        await loader.load();
        setIsLoaded(true);
      } catch (err) {
        console.error('Error loading Google Maps:', err);
        setError(err.message);
      }
    };

    loadGoogleMaps();
  }, []);

  // Initialize map when Google Maps is loaded
  useEffect(() => {
    if (isLoaded && mapRef.current && !map) {
      const mapInstance = new window.google.maps.Map(mapRef.current, {
        center: currentLocation,
        zoom: zoom,
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true,
        zoomControl: true,
        styles: [
          {
            featureType: 'poi',
            elementType: 'labels',
            stylers: [{ visibility: 'simplified' }]
          }
        ]
      });

      // Add click listener for location selection
      mapInstance.addListener('click', (event) => {
        const clickedLocation = {
          lat: event.latLng.lat(),
          lng: event.latLng.lng()
        };
        setCurrentLocation(clickedLocation);
        
        if (onLocationSelect) {
          onLocationSelect(clickedLocation);
        }

        // Update weather for clicked location
        if (showWeather) {
          fetchWeatherData(clickedLocation);
        }
      });

      setMap(mapInstance);
    }
  }, [isLoaded, map, currentLocation, zoom, onLocationSelect, showWeather]);

  // Fetch weather data for location
  const fetchWeatherData = useCallback(async (location) => {
    try {
      const response = await fetch(
        `/api/v1/weather/current?lat=${location.lat}&lng=${location.lng}&units=metric`
      );
      
      if (response.ok) {
        const weather = await response.json();
        setWeatherData(weather);
        
        if (onWeatherUpdate) {
          onWeatherUpdate(weather);
        }
      }
    } catch (err) {
      console.error('Error fetching weather data:', err);
    }
  }, [onWeatherUpdate]);

  // Search for places
  const searchPlaces = useCallback(async (query, location) => {
    if (!map || !query.trim()) return;

    try {
      const response = await fetch('/api/v1/maps/places/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          location: location ? [location.lat, location.lng] : null,
          radius: 5000
        })
      });

      if (response.ok) {
        const searchResults = await response.json();
        setPlaces(searchResults);
        
        // Add markers for search results
        clearMarkers();
        searchResults.forEach((place, index) => {
          addPlaceMarker(place, index);
        });
      }
    } catch (err) {
      console.error('Error searching places:', err);
    }
  }, [map]);

  // Add marker for place
  const addPlaceMarker = useCallback((place, index) => {
    if (!map) return;

    const marker = new window.google.maps.Marker({
      position: { lat: place.latitude, lng: place.longitude },
      map: map,
      title: place.name,
      icon: {
        url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
        scaledSize: new window.google.maps.Size(32, 32)
      }
    });

    // Add info window
    const infoWindow = new window.google.maps.InfoWindow({
      content: `
        <div class="p-3 max-w-xs">
          <h3 class="font-semibold text-lg">${place.name}</h3>
          <p class="text-sm text-gray-600 mt-1">${place.formatted_address}</p>
          ${place.rating ? `<p class="text-sm mt-1">⭐ ${place.rating}/5</p>` : ''}
          ${place.phone_number ? `<p class="text-sm mt-1">📞 ${place.phone_number}</p>` : ''}
          ${place.website ? `<p class="text-sm mt-1"><a href="${place.website}" target="_blank" class="text-blue-500 hover:underline">Website</a></p>` : ''}
        </div>
      `
    });

    marker.addListener('click', () => {
      if (infoWindowRef.current) {
        infoWindowRef.current.close();
      }
      infoWindow.open(map, marker);
      infoWindowRef.current = infoWindow;
    });

    markersRef.current.push(marker);
  }, [map]);

  // Clear all markers
  const clearMarkers = useCallback(() => {
    markersRef.current.forEach(marker => {
      marker.setMap(null);
    });
    markersRef.current = [];
    
    if (infoWindowRef.current) {
      infoWindowRef.current.close();
    }
  }, []);

  // Add custom markers
  useEffect(() => {
    if (!map || !markers.length) return;

    clearMarkers();
    
    markers.forEach((markerData, index) => {
      const marker = new window.google.maps.Marker({
        position: { lat: markerData.lat, lng: markerData.lng },
        map: map,
        title: markerData.title,
        icon: markerData.icon || {
          url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
          scaledSize: new window.google.maps.Size(32, 32)
        }
      });

      if (markerData.content) {
        const infoWindow = new window.google.maps.InfoWindow({
          content: markerData.content
        });

        marker.addListener('click', () => {
          if (infoWindowRef.current) {
            infoWindowRef.current.close();
          }
          infoWindow.open(map, marker);
          infoWindowRef.current = infoWindow;
        });
      }

      markersRef.current.push(marker);
    });
  }, [map, markers, clearMarkers]);

  // Handle search query changes
  useEffect(() => {
    if (searchQuery && showPlaces) {
      searchPlaces(searchQuery, currentLocation);
    }
  }, [searchQuery, showPlaces, currentLocation, searchPlaces]);

  // Update weather when location changes
  useEffect(() => {
    if (showWeather && currentLocation) {
      fetchWeatherData(currentLocation);
    }
  }, [showWeather, currentLocation, fetchWeatherData]);

  // Center map on location changes
  useEffect(() => {
    if (map && center) {
      map.setCenter(center);
      setCurrentLocation(center);
    }
  }, [map, center]);

  // Get user's current location
  const getCurrentLocation = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const userLocation = {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          };
          
          if (map) {
            map.setCenter(userLocation);
            map.setZoom(15);
          }
          
          setCurrentLocation(userLocation);
          
          if (onLocationSelect) {
            onLocationSelect(userLocation);
          }
        },
        (error) => {
          console.error('Error getting user location:', error);
        }
      );
    }
  }, [map, onLocationSelect]);

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 rounded-lg ${className}`} 
           style={{ height, width }}>
        <div className="text-center p-4">
          <div className="text-red-500 mb-2">⚠️</div>
          <div className="text-sm text-gray-600">
            Maps unavailable: {error}
          </div>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 rounded-lg ${className}`} 
           style={{ height, width }}>
        <div className="text-center p-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <div className="text-sm text-gray-600">Loading maps...</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`} style={{ height, width }}>
      {/* Map Container */}
      <div 
        ref={mapRef} 
        className="w-full h-full rounded-lg"
        style={{ height, width }}
      />
      
      {/* Control Panel */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-2">
        <button
          onClick={getCurrentLocation}
          className="flex items-center space-x-2 px-3 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          title="Get current location"
        >
          <span>📍</span>
          <span>My Location</span>
        </button>
      </div>
      
      {/* Weather Panel */}
      {showWeather && weatherData && (
        <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg p-3 max-w-xs">
          <div className="flex items-center space-x-2 mb-2">
            <img 
              src={`https://openweathermap.org/img/wn/${weatherData.condition.icon}@2x.png`}
              alt={weatherData.condition.description}
              className="w-10 h-10"
            />
            <div>
              <div className="font-semibold">{Math.round(weatherData.temperature)}°C</div>
              <div className="text-xs text-gray-600 capitalize">
                {weatherData.condition.description}
              </div>
            </div>
          </div>
          <div className="text-xs space-y-1">
            <div>Feels like: {Math.round(weatherData.feels_like)}°C</div>
            <div>Humidity: {weatherData.humidity}%</div>
            <div>Wind: {Math.round(weatherData.wind_speed)} m/s</div>
          </div>
        </div>
      )}
      
      {/* Places List */}
      {showPlaces && places.length > 0 && (
        <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-3 max-w-xs max-h-48 overflow-y-auto">
          <h3 className="font-semibold mb-2">Search Results</h3>
          <div className="space-y-2">
            {places.slice(0, 5).map((place, index) => (
              <div 
                key={place.place_id} 
                className="text-sm p-2 border rounded hover:bg-gray-50 cursor-pointer"
                onClick={() => {
                  map.setCenter({ lat: place.latitude, lng: place.longitude });
                  map.setZoom(16);
                }}
              >
                <div className="font-medium">{place.name}</div>
                <div className="text-gray-600 text-xs">{place.formatted_address}</div>
                {place.rating && (
                  <div className="text-xs text-yellow-600">⭐ {place.rating}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GoogleMapsComponent;