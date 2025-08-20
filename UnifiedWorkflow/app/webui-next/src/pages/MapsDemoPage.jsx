import React, { useState, useCallback } from 'react';
import GoogleMapsComponent from '../components/GoogleMapsComponent';

/**
 * Demo page for Google Maps and Weather integration
 * 
 * Demonstrates:
 * - Interactive Google Maps with places search
 * - Weather data overlay
 * - Location selection and geocoding
 * - Integration with backend APIs
 */
const MapsDemoPage = () => {
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [geocodeResult, setGeocodeResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Handle location selection from map
  const handleLocationSelect = useCallback(async (location) => {
    setSelectedLocation(location);
    setError(null);
    
    // Reverse geocode the selected location
    try {
      setIsLoading(true);
      const response = await fetch('/api/v1/maps/reverse-geocode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          latitude: location.lat,
          longitude: location.lng
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setGeocodeResult(result);
      }
    } catch (err) {
      console.error('Error reverse geocoding:', err);
      setError('Failed to get address for location');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle weather data updates
  const handleWeatherUpdate = useCallback((weather) => {
    setWeatherData(weather);
  }, []);

  // Handle geocoding search
  const handleGeocodeSearch = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch('/api/v1/maps/geocode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          address: searchQuery
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setGeocodeResult(result);
        setSelectedLocation({
          lat: result.latitude,
          lng: result.longitude
        });
      } else {
        setError('Address not found');
      }
    } catch (err) {
      console.error('Error geocoding:', err);
      setError('Failed to geocode address');
    } finally {
      setIsLoading(false);
    }
  };

  // Get weather forecast
  const handleGetForecast = async () => {
    if (!selectedLocation) return;
    
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(
        `/api/v1/weather/forecast?lat=${selectedLocation.lat}&lng=${selectedLocation.lng}&units=metric`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      if (response.ok) {
        const forecast = await response.json();
        console.log('Weather forecast:', forecast);
        // You could set this to state and display it
      } else {
        setError('Failed to get weather forecast');
      }
    } catch (err) {
      console.error('Error getting forecast:', err);
      setError('Failed to get weather forecast');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Google Maps & Weather Integration Demo
        </h1>
        
        {/* Search Controls */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Search & Controls</h2>
          
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter an address to search..."
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                onKeyPress={(e) => e.key === 'Enter' && handleGeocodeSearch()}
              />
            </div>
            <button
              onClick={handleGeocodeSearch}
              disabled={isLoading || !searchQuery.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </div>
          
          {selectedLocation && (
            <div className="flex gap-4">
              <button
                onClick={handleGetForecast}
                disabled={isLoading}
                className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:bg-gray-400 transition-colors"
              >
                Get Weather Forecast
              </button>
            </div>
          )}
          
          {error && (
            <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}
        </div>
        
        {/* Maps Component */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Interactive Map</h2>
          <GoogleMapsComponent
            center={selectedLocation || { lat: 37.7749, lng: -122.4194 }}
            zoom={selectedLocation ? 15 : 10}
            height="500px"
            showWeather={true}
            showPlaces={true}
            searchQuery={searchQuery}
            onLocationSelect={handleLocationSelect}
            onWeatherUpdate={handleWeatherUpdate}
            className="w-full"
          />
        </div>
        
        {/* Information Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Location Information */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Location Information</h2>
            
            {selectedLocation ? (
              <div className="space-y-3">
                <div>
                  <span className="font-medium">Coordinates:</span>
                  <div className="text-sm text-gray-600">
                    Lat: {selectedLocation.lat.toFixed(6)}, 
                    Lng: {selectedLocation.lng.toFixed(6)}
                  </div>
                </div>
                
                {geocodeResult && (
                  <div>
                    <span className="font-medium">Address:</span>
                    <div className="text-sm text-gray-600">
                      {geocodeResult.formatted_address}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Place ID: {geocodeResult.place_id}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">
                Click on the map or search for an address to see location details.
              </div>
            )}
          </div>
          
          {/* Weather Information */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Weather Information</h2>
            
            {weatherData ? (
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <img 
                    src={`https://openweathermap.org/img/wn/${weatherData.condition.icon}@2x.png`}
                    alt={weatherData.condition.description}
                    className="w-12 h-12"
                  />
                  <div>
                    <div className="text-2xl font-bold">
                      {Math.round(weatherData.temperature)}°C
                    </div>
                    <div className="text-sm text-gray-600 capitalize">
                      {weatherData.condition.description}
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Feels like:</span>
                    <div>{Math.round(weatherData.feels_like)}°C</div>
                  </div>
                  <div>
                    <span className="font-medium">Humidity:</span>
                    <div>{weatherData.humidity}%</div>
                  </div>
                  <div>
                    <span className="font-medium">Pressure:</span>
                    <div>{weatherData.pressure} hPa</div>
                  </div>
                  <div>
                    <span className="font-medium">Wind:</span>
                    <div>{Math.round(weatherData.wind_speed)} m/s</div>
                  </div>
                  <div>
                    <span className="font-medium">Cloudiness:</span>
                    <div>{weatherData.cloudiness}%</div>
                  </div>
                  {weatherData.uv_index && (
                    <div>
                      <span className="font-medium">UV Index:</span>
                      <div>{weatherData.uv_index}</div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">
                Select a location on the map to see weather information.
              </div>
            )}
          </div>
        </div>
        
        {/* API Documentation */}
        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Available APIs</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-lg mb-2">Google Maps APIs</h3>
              <ul className="text-sm space-y-1 text-gray-600">
                <li>• GET /api/v1/maps/config - Maps configuration</li>
                <li>• POST /api/v1/maps/geocode - Address to coordinates</li>
                <li>• POST /api/v1/maps/reverse-geocode - Coordinates to address</li>
                <li>• POST /api/v1/maps/places/search - Search places</li>
                <li>• GET /api/v1/maps/places/:id - Place details</li>
                <li>• GET /api/v1/maps/nearby - Find nearby places</li>
                <li>• POST /api/v1/maps/distance-matrix - Travel distances</li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-lg mb-2">Weather APIs</h3>
              <ul className="text-sm space-y-1 text-gray-600">
                <li>• GET /api/v1/weather/current - Current weather</li>
                <li>• GET /api/v1/weather/forecast - Weather forecast</li>
                <li>• POST /api/v1/weather/city - Weather by city</li>
                <li>• GET /api/v1/weather/alerts - Weather alerts</li>
                <li>• POST /api/v1/weather/batch - Batch weather data</li>
                <li>• GET /api/v1/weather/icon/:code - Weather icon URL</li>
                <li>• GET /api/v1/weather/map/:layer/:z/:x/:y - Weather map tiles</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapsDemoPage;