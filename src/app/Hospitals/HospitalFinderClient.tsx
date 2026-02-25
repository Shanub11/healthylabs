'use client';

import { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import MapComponent from './MapComponent';
import { MapPin, Bed, Filter, ArrowUpDown, Home } from 'lucide-react';

type Hospital = {
  srNo: string;
  name: string;
  city: string;
  totalBeds: number;
  occupiedBeds: number;
  availableBeds: number;
  lastUpdated: string;
};

const CITY_COORDINATES: Record<string, { lat: number; lng: number }> = {
  "THANE": { lat: 19.2183, lng: 72.9781 },
  "MUMBAI": { lat: 19.0760, lng: 72.8777 },
  "MUMBAI SUBURBAN": { lat: 19.15, lng: 72.85 },
  "NAGPUR": { lat: 21.1458, lng: 79.0882 },
  "AKOLA": { lat: 20.7002, lng: 77.0082 },
  "NANDED": { lat: 19.1383, lng: 77.3210 },
  "BEED": { lat: 18.9891, lng: 75.7601 },
  "PUNE": { lat: 18.5204, lng: 73.8567 },
  "DHARASHIV": { lat: 18.1853, lng: 76.0420 },
  "SOLAPUR": { lat: 17.6599, lng: 75.9064 },
  "SANGLI": { lat: 16.8524, lng: 74.5815 },
  "AMRAVATI": { lat: 20.9320, lng: 77.7523 },
  "CHATTRAPATHI SAMBHAJI NAGAR": { lat: 19.8762, lng: 75.3433 },
  "YAVATMAL": { lat: 20.3888, lng: 78.1204 },
  "KOLHAPUR": { lat: 16.7050, lng: 74.2433 },
  "PALGHAR": { lat: 19.6936, lng: 72.7655 },
  "PARBHANI": { lat: 19.2644, lng: 76.7855 },
  "JALGAON": { lat: 21.0077, lng: 75.5626 },
  "SATARA": { lat: 17.6805, lng: 74.0183 },
  "GONDIYA": { lat: 21.4624, lng: 80.2210 },
  "BULDHANA": { lat: 20.5305, lng: 76.1844 },
  "NASHIK": { lat: 19.9975, lng: 73.7898 },
  "RAIGAD": { lat: 18.5158, lng: 73.1822 },
  "LATUR": { lat: 18.4088, lng: 76.5604 },
  "BHANDARA": { lat: 21.1777, lng: 79.6570 },
  "HINGOLI": { lat: 19.7178, lng: 77.1467 },
  "NANDURBAR": { lat: 21.3738, lng: 74.2446 },
  "SINDHUDURG": { lat: 16.1180, lng: 73.7114 },
  "WARDHA": { lat: 20.7453, lng: 78.6022 },
  "GADCHIROLI": { lat: 20.1849, lng: 79.9948 },
  "CHANDRAPUR": { lat: 19.9615, lng: 79.2961 },
  "DHULE": { lat: 20.9042, lng: 74.7749 },
  "SHIRPUR": { lat: 21.3514, lng: 74.8801 },
  "PANDHARPUR": { lat: 17.6774, lng: 75.3320 },
  "PANVEL": { lat: 18.9894, lng: 73.1175 },
  "SHIRDI": { lat: 19.7645, lng: 74.4762 },
  "BARSHI": { lat: 18.2334, lng: 75.6933 },
  "WASHIM": { lat: 20.1116, lng: 77.1317 },
  "JALNA": { lat: 19.8297, lng: 75.8800 }
};

function deg2rad(deg: number) {
  return deg * (Math.PI / 180);
}

function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371; // Radius of the earth in km
  const dLat = deg2rad(lat2 - lat1);
  const dLon = deg2rad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in km
}

const getBedStatusColor = (beds: number) => {
  if (beds > 10) return 'text-green-600';
  if (beds > 0) return 'text-yellow-600';
  return 'text-red-600';
};

export default function HospitalFinderClient({ hospitals, lastUpdatedTime }: { hospitals: Hospital[], lastUpdatedTime: string }) {
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [selectedCity, setSelectedCity] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'distance' | 'beds' | 'name'>('distance');

  // Get User Location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => console.error("Error getting location:", error)
      );
    }
  }, []);

  // Extract unique cities
  const cities = useMemo(() => {
    const citySet = new Set(hospitals.map(h => h.city).filter(Boolean));
    return ['All', ...Array.from(citySet).sort()];
  }, [hospitals]);

  // Filter and Sort
  const processedHospitals = useMemo(() => {
    let result = [...hospitals];

    // Filter by City
    if (selectedCity !== 'All') {
      result = result.filter(h => h.city === selectedCity);
    }

    // Sort
    if (sortBy === 'beds') {
      result.sort((a, b) => b.availableBeds - a.availableBeds);
    } else if (sortBy === 'name') {
      result.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === 'distance') {
       if (userLocation) {
         result.sort((a, b) => {
           const coordsA = CITY_COORDINATES[a.city?.trim().toUpperCase()];
           const coordsB = CITY_COORDINATES[b.city?.trim().toUpperCase()];
           
           if (!coordsA && !coordsB) return 0;
           if (!coordsA) return 1;
           if (!coordsB) return -1;
           const distA = calculateDistance(userLocation.lat, userLocation.lng, coordsA.lat, coordsA.lng);
           const distB = calculateDistance(userLocation.lat, userLocation.lng, coordsB.lat, coordsB.lng);
           return distA - distB;
         });
       }
    }

    return result;
  }, [hospitals, selectedCity, sortBy, userLocation]);

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row items-center justify-center relative">
        <div className="self-start md:absolute md:left-0 md:top-1/2 md:-translate-y-1/2 mb-4 md:mb-0">
          <Link 
            href="/dashboard" 
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors font-medium"
          >
            <Home className="w-5 h-5" />
            <span>Home</span>
          </Link>
        </div>
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-800">Real-time Hospital Finder</h1>
          <p className="text-sm text-gray-500 mt-2">
            Data last updated: {lastUpdatedTime}
          </p>
        </div>
      </div>
      
      {/* Filters and Sorting */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="flex items-center gap-2 w-full md:w-auto">
            <Filter className="w-5 h-5 text-gray-500" />
            <label className="text-gray-700 font-medium whitespace-nowrap">Filter by City:</label>
            <select 
                value={selectedCity} 
                onChange={(e) => setSelectedCity(e.target.value)}
                className="p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 outline-none w-full md:w-64 text-gray-700"
            >
                {cities.map(city => (
                    <option key={city} value={city}>{city}</option>
                ))}
            </select>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
            <ArrowUpDown className="w-5 h-5 text-gray-500" />
            <label className="text-gray-700 font-medium whitespace-nowrap">Sort by:</label>
            <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value as any)}
                className="p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 outline-none w-full md:w-64 text-gray-700"
            >
                <option value="distance">Distance (Default)</option>
                <option value="beds">Available Beds</option>
                <option value="name">Name</option>
            </select>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <MapComponent hospitals={hospitals} userLocation={userLocation} />

        <div id="hospital-list" className="space-y-4 max-h-[600px] overflow-y-auto pr-2 lg:col-span-1">
          {processedHospitals.length > 0 ? (
            processedHospitals.map((hospital, index) => (
              <a 
                key={index}
                href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${hospital.name} ${hospital.city}`)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="block bg-white cursor-pointer rounded-lg shadow-md p-4 hover:shadow-xl hover:scale-105 transition-all duration-200 border-l-4 border-pink-500"
              >
                <h2 className="text-lg font-bold text-gray-800 mb-1">{hospital.name}</h2>
                <div className="flex items-center text-gray-600 mb-2">
                    <MapPin className="w-4 h-4 mr-1" />
                    <span className="text-sm">{hospital.city}</span>
                </div>
                <div className="flex justify-between items-center bg-gray-50 p-2 rounded-lg">
                    <div className="flex items-center">
                        <Bed className="w-5 h-5 text-gray-500 mr-2" />
                        <span className="text-sm font-medium text-gray-700">Available:</span>
                    </div>
                    <span className={`font-bold text-lg ${getBedStatusColor(hospital.availableBeds)}`}>
                      {hospital.availableBeds}
                    </span>
                </div>
                <div className="mt-3 flex justify-between text-xs text-gray-400">
                    <span>Total: {hospital.totalBeds}</span>
                    <span>Occupied: {hospital.occupiedBeds}</span>
                </div>
                <p className="text-xs text-gray-400 mt-2 text-right">
                  Updated: {hospital.lastUpdated}
                </p>
              </a>
            ))
          ) : (
            <div className="text-center py-10 bg-white rounded-lg shadow">
              <p className="text-gray-500">No hospitals found matching your criteria.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
