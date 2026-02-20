import { NextResponse, NextRequest } from 'next/server';
import axios from 'axios';
import * as cheerio from 'cheerio';
// fs cannot be used for persistent storage on Vercel
// import fs from 'fs/promises';
// import path from 'path';

export async function GET(request: NextRequest) {
  try {
    // Verify Vercel Cron Secret to prevent unauthorized access
    const authHeader = request.headers.get('authorization');
    if (process.env.CRON_SECRET && authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
      return NextResponse.json({ message: 'Unauthorized' }, { status: 401 });
    }

    const url = 'https://www.jeevandayee.gov.in/MJPJAY/FrontServlet?requestType=PublicViewsRH&actionVal=ViewBedInfoForDisease&City=x%20&Disease=-1&DataFlag=true&DfltHospList=Reports';

    // 1. Fetch the HTML
    const response = await axios.get(url);
    const html = response.data;

    // 2. Parse the HTML with Cheerio
    const $ = cheerio.load(html);

    // 3. Find the table and extract data
    // You MUST inspect the page to get the correct selector.
    
    // Let's assume the table is the first one with a specific style attribute.
    const table = $('div[style*="overflow: auto"]').find('table');
    
    const hospitals: object[] = [];
    const rows = table.find('tr');

    rows.slice(1).each((index, element) => {
      const cells = $(element).find('td');
      if (cells.length >= 6) {
        const hospitalData = {
          srNo: $(cells[0]).text().trim(),
          name: $(cells[1]).text().trim(),
          city: $(cells[2]).text().trim(),
          totalBeds: parseInt($(cells[3]).text().trim(), 10) || 0,
          occupiedBeds: parseInt($(cells[4]).text().trim(), 10) || 0,
          availableBeds: parseInt($(cells[5]).text().trim(), 10) || 0,
          lastUpdated: $(cells[6]).text().trim(),
        };
        hospitals.push(hospitalData);
      }
    });

    if (hospitals.length === 0) {
      throw new Error("No hospitals found. The website structure might have changed.");
    }
    
    // 4. Save the data
    // NOTE: Writing to 'public/' does not persist on Vercel.
    // You should insert 'hospitals' into your Supabase database here.
    // const filePath = path.join(process.cwd(), 'public', 'hospital_data.json');
    // await fs.writeFile(filePath, JSON.stringify({
    //   lastScraped: new Date().toISOString(),
    //   hospitals: hospitals
    // }, null, 2));

    return NextResponse.json({
      message: `Successfully scraped ${hospitals.length} hospitals.`,
      data: hospitals
    });

  } catch (error) {
    console.error('Scraping failed:', error);
    const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
    return NextResponse.json({ message: 'Scraping failed', error: errorMessage }, { status: 500 });
  }
}