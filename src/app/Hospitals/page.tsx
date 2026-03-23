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
    <>
      <style>{`
          @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&family=Inter:wght@400;500&display=swap');
          
          @keyframes float-slow {
              0% { transform: translate(0px, 0px) scale(1); }
              33% { transform: translate(30px, -50px) scale(1.1); }
              66% { transform: translate(-20px, 20px) scale(0.9); }
              100% { transform: translate(0px, 0px) scale(1); }
          }
          .animate-float-1 { animation: float-slow 8s ease-in-out infinite; }
          .animate-float-2 { animation: float-slow 10s ease-in-out infinite reverse; }
          .animate-float-3 { animation: float-slow 12s ease-in-out infinite 1s; }
      `}</style>
      <div className="relative min-h-screen bg-gradient-to-br from-[#cbe5ff] via-[#dcedff] to-[#e1f0ff] overflow-hidden font-sans">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-white/60 rounded-full blur-[100px] animate-float-1 pointer-events-none"></div>
        <div className="absolute top-[20%] right-[-5%] w-[400px] h-[400px] bg-blue-300/30 rounded-full blur-[80px] animate-float-2 pointer-events-none"></div>
        <div className="absolute bottom-[-10%] left-[20%] w-[600px] h-[600px] bg-cyan-200/40 rounded-full blur-[100px] animate-float-3 pointer-events-none"></div>
        <div className="container mx-auto px-4 py-8 relative z-10">
          <HospitalFinderClient hospitals={hospitals} lastUpdatedTime={lastUpdatedTime} />
        </div>
      </div>
    </>
  );
}
