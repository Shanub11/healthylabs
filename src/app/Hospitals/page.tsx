import fs from 'fs/promises';
import path from 'path';
import MapComponent from './MapComponent'; // Import the client component

// Define types for our scraped data for better code quality
type Hospital = {
  name: string;
  city: string;
  availableBeds: number;
  lastUpdated: string;
};

type ScrapedData = {
  lastScraped: string;
  hospitals: Hospital[];
};

// This server-side function reads the data from your JSON file
async function getHospitalData(): Promise<ScrapedData> {
  const filePath = path.join(process.cwd(), 'public', 'hospital_data.json');
  try {
    const fileContents = await fs.readFile(filePath, 'utf8');
    return JSON.parse(fileContents);
  } catch (error) {
    console.error("Could not read hospital data file:", error);
    return { lastScraped: new Date().toISOString(), hospitals: [] };
  }
}

// A helper function to determine the status color based on bed count
const getBedStatusColor = (beds: number) => {
  if (beds > 10) return 'text-green-600';
  if (beds > 0) return 'text-yellow-600';
  return 'text-red-600';
};

// The main page component, now async to fetch data on the server
export default async function HospitalFinderPage() {
  const { lastScraped, hospitals } = await getHospitalData();

  const lastUpdatedTime = new Date(lastScraped).toLocaleString('en-IN', {
    dateStyle: 'long',
    timeStyle: 'short',
  });

  return (
    <div className="container mx-auto px-4 py-8 bg-gray-50">
      <div id="page-hospital-finder" className="page-content">
        <div className="space-y-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-800">Real-time Hospital Finder</h1>
            <p className="text-sm text-gray-500 mt-2">
              Data last updated: {lastUpdatedTime}
            </p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <MapComponent hospitals={hospitals} />

            <div id="hospital-list" className="space-y-4 max-h-[450px] overflow-y-auto pr-2">
              {hospitals.length > 0 ? (
                hospitals.map((hospital, index) => (
                  <div key={index} className="bg-white cursor-pointer rounded-lg shadow-md p-4 hover:shadow-xl hover:scale-105 transition-all duration-200">
                    <h2 className="text-xl font-semibold text-gray-800">{hospital.name}</h2>
                    <p className="text-gray-600">City: {hospital.city}</p>
                    <p className={`font-bold text-lg ${getBedStatusColor(hospital.availableBeds)}`}>
                      Available Beds: {hospital.availableBeds}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Last hospital update: {hospital.lastUpdated}
                    </p>
                  </div>
                ))
              ) : (
                <div className="text-center py-10">
                  <p className="text-gray-500">No hospital data available at the moment.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}