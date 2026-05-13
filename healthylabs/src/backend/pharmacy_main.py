from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uvicorn
from pypdf import PdfReader
from PIL import Image
import io
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
import urllib.parse
import requests
import json
import certifi

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="HealthyLabs Pharma Intelligence")

# Define allowed origins
origins = [
    "http://localhost:3000",
]
if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGODB_URI")
db = None

if MONGO_URI:
    try:
        # Use certifi for SSL verification to prevent handshake errors
        mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        db = mongo_client["healthylabs"]
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")

# --- Helper Functions ---

# Global EasyOCR reader (lazy loaded)
ocr_reader = None

def get_ocr_reader():
    global ocr_reader
    if ocr_reader is None:
        import easyocr
        print("Loading EasyOCR model...")
        ocr_reader = easyocr.Reader(['en'])
    return ocr_reader

def extract_pdf_text(file_bytes):
    text = ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"pypdf Error: {e}")

    if text.strip():
        return text

    # Fallback to OCR for PDF images
    try:
        reader = get_ocr_reader()
        pdf_reader = PdfReader(io.BytesIO(file_bytes))
        for page in pdf_reader.pages:
            for image_file in page.images:
                results = reader.readtext(image_file.data, detail=0)
                text += " ".join(results) + "\n"
    except Exception as e:
        print(f"OCR Error: {e}")
        
    return text

def extract_image_text(file_bytes):
    try:
        reader = get_ocr_reader()
        results = reader.readtext(file_bytes, detail=0)
        return " ".join(results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image Extraction Error: {str(e)}")

def clean_text(text):
    return " ".join(text.split())

def call_mistral(prompt):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Mistral API Key missing")
        
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "mistral-tiny",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        # Attempt to clean markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# --- Pydantic Models ---

class InteractionRequest(BaseModel):
    medicines: List[str]

class ReminderRequest(BaseModel):
    user_id: str
    medicine_name: str
    dosage: str
    frequency_hours: int
    start_date: Optional[str] = None

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Pharma Intelligence API"}

# 1. Medicine Search
@app.get("/medicine/search")
async def search_medicine(query: str):
    prompt = f"""
    You are a pharmaceutical assistant. Provide details for the medicine: "{query}".
    Return a valid JSON object (NO markdown) with:
    - generic_name: string
    - use_cases: list of strings
    - side_effects: list of strings
    - warnings: list of strings
    """
    result = call_mistral(prompt)
    try:
        return json.loads(result)
    except:
        return {"raw_result": result}

# 1.5 Medicine Autocomplete
@app.get("/medicine/autocomplete")
async def autocomplete_medicine(query: str):
    if not query or len(query) < 1:
        return {"suggestions": []}
        
    prompt = f"""
    List 5 popular medicine names that start with "{query}".
    Return a valid JSON object (NO markdown) with:
    - suggestions: list of strings
    """
    result = call_mistral(prompt)
    try:
        return json.loads(result)
    except:
        return {"suggestions": []}

# 2. Drug Interaction Checker
@app.post("/medicine/interactions")
async def check_interactions(request: InteractionRequest):
    if not request.medicines or len(request.medicines) < 2:
        return {"error": "Please provide at least two medicines."}
        
    prompt = f"""
    Check for drug interactions between: {', '.join(request.medicines)}.
    Return a valid JSON object (NO markdown) with:
    - interactions: list of objects {{ "medicine_a": string, "medicine_b": string, "severity": "Low"|"Medium"|"High", "description": string }}
    - safe_to_combine: boolean
    - recommendation: string
    """
    result = call_mistral(prompt)
    try:
        return json.loads(result)
    except:
        return {"raw_result": result}

# 3. Condition-Based Suggestions
@app.get("/medicine/suggestions")
async def get_suggestions(condition: str):
    prompt = f"""
    Suggest OTC medicine categories for the condition: "{condition}".
    Do NOT prescribe specific prescription-only drugs. Focus on OTC categories (e.g., Antihistamines, Decongestants).
    Return a valid JSON object (NO markdown) with:
    - condition: string
    - otc_categories: list of strings
    - lifestyle_tips: list of strings
    - when_to_see_doctor: string
    """
    result = call_mistral(prompt)
    try:
        return json.loads(result)
    except:
        return {"raw_result": result}

# 4. Prescription OCR
@app.post("/medicine/ocr")
async def parse_prescription(file: UploadFile = File(...)):
    content = await file.read()
    extracted_text = ""
    
    try:
        if file.filename.lower().endswith(".pdf"):
            extracted_text = extract_pdf_text(content)
        else:
            extracted_text = extract_image_text(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OCR Failed: {str(e)}")
        
    if not extracted_text.strip():
         raise HTTPException(status_code=400, detail="No text found in prescription.")

    cleaned_text = clean_text(extracted_text)
    
    prompt = f"""
    Extract medicines from this prescription text:
    "{cleaned_text[:3000]}"
    
    Return a valid JSON object (NO markdown) with:
    - medicines: list of objects {{ "name": string, "dosage": string, "frequency": string, "explanation": string }}
    - doctor_notes: string
    """
    
    ai_response = call_mistral(prompt)
    try:
        parsed_response = json.loads(ai_response)
    except:
        parsed_response = {"raw_analysis": ai_response}
    
    return {
        "extracted_text": cleaned_text,
        "analysis": parsed_response
    }

# 5. Price Comparison / Generic Alternatives
@app.get("/medicine/alternatives")
async def get_alternatives(medicine: str):
    prompt = f"""
    Suggest generic alternatives for the medicine: "{medicine}".
    Return a valid JSON object (NO markdown) with:
    - brand_name: string
    - generic_name: string
    - alternatives: list of objects {{ "name": string, "approx_price_tier": "Low"|"Medium"|"High" }}
    """
    result = call_mistral(prompt)
    try:
        return json.loads(result)
    except:
        return {"raw_result": result}

# 6. Nearby Pharmacies
@app.get("/pharmacies/nearby")
async def nearby_pharmacies(lat: float, lon: float):
    # Generates a Google Maps search URL
    map_url = f"https://www.google.com/maps/search/pharmacies/@{lat},{lon},15z"
    return {
        "map_url": map_url,
        "note": "Redirect user to this URL to see nearby pharmacies with availability tags on Google Maps."
    }

# 7. Refill Reminder
@app.post("/reminders")
async def add_reminder(reminder: ReminderRequest):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    start = datetime.utcnow()
    if reminder.start_date:
        try:
            start = datetime.fromisoformat(reminder.start_date.replace("Z", "+00:00"))
        except:
            pass
            
    reminder_doc = {
        "user_id": reminder.user_id,
        "medicine_name": reminder.medicine_name,
        "dosage": reminder.dosage,
        "frequency_hours": reminder.frequency_hours,
        "start_date": start,
        "next_dose": start + timedelta(hours=reminder.frequency_hours),
        "active": True
    }
    
    result = db["refill_reminders"].insert_one(reminder_doc)
    return {"status": "success", "id": str(result.inserted_id)}

@app.get("/reminders/{user_id}")
async def get_user_reminders(user_id: str):
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
        
    reminders = list(db["refill_reminders"].find({"user_id": user_id, "active": True}))
    for r in reminders:
        r["_id"] = str(r["_id"])
        r["start_date"] = r["start_date"].isoformat()
        r["next_dose"] = r["next_dose"].isoformat()
        
    return reminders

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001)) # Default to 8001 to avoid conflict if running locally with main.py
    uvicorn.run(app, host="0.0.0.0", port=port)