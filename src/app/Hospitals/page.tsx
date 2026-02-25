import fs from 'fs/promises';
import path from 'path';
import HospitalFinderClient from './HospitalFinderClient';

// Define types for our scraped data for better code quality
type Hospital = {
  srNo: string;
  name: string;
  city: string;
  totalBeds: number;
  occupiedBeds: number;
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
        <HospitalFinderClient hospitals={hospitals} lastUpdatedTime={lastUpdatedTime} />
      </div>
    </div>
  );
}
