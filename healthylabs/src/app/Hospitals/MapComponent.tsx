import { useEffect, useRef, useState } from 'react';

// Define types for our scraped data for better code quality
type Hospital = {
  name: string;
  city: string;
  availableBeds: number;
  lastUpdated: string;
};

// Declare google as a global variable for TypeScript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const google: any;

export default function MapComponent({ hospitals: _hospitals, userLocation }: { hospitals: Hospital[], userLocation: { lat: number; lng: number } | null }) {
  const mapRef = useRef(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 2. Load the Google Maps script with the 'places' library
  useEffect(() => {
    if (mapLoaded || error) return;

    const googleMapsApiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (!googleMapsApiKey) {
      setError("Google Maps API key is not set.");
      return;
    }

    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${googleMapsApiKey}&callback=initMap&libraries=places`;
    script.async = true;
    script.defer = true;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).initMap = () => setMapLoaded(true);
    document.head.appendChild(script);

    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      delete (window as any).initMap;
      document.head.removeChild(script);
    };
  }, [mapLoaded, error]);

  // 3. Initialize the map and place markers
  useEffect(() => {
    if (!mapLoaded || !userLocation || !mapRef.current) return;

    const map = new google.maps.Map(mapRef.current, {
      center: userLocation,
      zoom: 12,
    });

    // Create a marker for the user's current location
    new google.maps.Marker({
      position: userLocation,
      map: map,
      title: 'Your Location',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#4285F4',
        fillOpacity: 1,
        strokeWeight: 2,
        strokeColor: 'white',
      },
    });

    const infoWindow = new google.maps.InfoWindow();
    const service = new google.maps.places.PlacesService(map);

    // Perform a nearby search for hospitals
    service.nearbySearch(
      {
        location: userLocation,
        radius: 5000, // 5 km radius
        type: 'hospital',
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (results: any, status: any) => {
        if (status === google.maps.places.PlacesServiceStatus.OK && results) {
          for (let i = 0; i < results.length; i++) {
            const place = results[i];
            const marker = new google.maps.Marker({
              map: map,
              position: place.geometry.location,
              title: place.name,
            });

            marker.addListener('click', () => {
              infoWindow.setContent(`
                <div>
                  <h3 style="font-weight: bold;">${place.name}</h3>
                  <p>Rating: ${place.rating || 'N/A'}</p>
                  <p>Vicinity: ${place.vicinity}</p>
                </div>
              `);
              infoWindow.open(map, marker);
            });
          }
        }
      }
    );
  }, [mapLoaded, userLocation]);

  return (
    <div className="lg:col-span-2 relative h-96 bg-white/40 backdrop-blur-xl border border-white/80 shadow-[0_8px_32px_0_rgba(31,38,135,0.05)] rounded-3xl overflow-hidden">
      <div className="absolute top-4 left-4 z-10 p-4 bg-white/90 backdrop-blur-md rounded-2xl shadow-lg border border-white/50">
        <p className="text-xs font-bold mb-2 text-slate-800 uppercase tracking-wider">Map Legend</p>
        <div className="flex items-center space-x-2 mb-1">
          <span className="h-3 w-3 bg-blue-500 rounded-full shadow-sm"></span>
          <span className="text-xs font-medium text-slate-700">Your Location</span>
        </div>
        <div className="flex items-center space-x-2 mt-1">
          <span className="text-xs font-medium text-slate-700">🏥 Nearby Hospital</span>
        </div>
      </div>
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50 bg-opacity-80 p-4 text-center">
          <p className="text-red-500 text-sm font-medium">{error}</p>
        </div>
      )}
      {!userLocation && !error && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-400 font-semibold text-lg animate-pulse">
          Finding your location...
        </div>
      )}
      <div ref={mapRef} className="w-full h-full"></div>
    </div>
  );
}
