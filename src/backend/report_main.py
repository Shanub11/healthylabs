from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
from pypdf import PdfReader
from PIL import Image
import io
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime
import urllib.parse
import platform
import requests

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Define allowed origins
origins = [
    "http://localhost:3000",
]

# Add production frontend URL from environment variable
if os.getenv("FRONTEND_URL"):
    origins.append(os.getenv("FRONTEND_URL"))

# Configure CORS to allow requests from Next.js (port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MongoDB Setup ---
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")

if MONGO_USER and MONGO_PASSWORD and MONGO_CLUSTER:
    # Clean up cluster address in case it includes protocol or options
    clean_cluster = MONGO_CLUSTER.replace("mongodb+srv://", "").split("?")[0].strip("/")
    MONGO_URI = f"mongodb+srv://{urllib.parse.quote_plus(MONGO_USER)}:{urllib.parse.quote_plus(MONGO_PASSWORD)}@{clean_cluster}/?retryWrites=true&w=majority"

mongo_client = None
db = None

if MONGO_URI:
    try:
        mongo_client = MongoClient(MONGO_URI)
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        db = mongo_client["healthylabs"]
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")
        if "must be escaped" in str(e):
            print("💡 HINT: Your MongoDB password contains special characters. You need to URL-encode it.")
            print("   Run: python -c \"import urllib.parse; print(urllib.parse.quote_plus('YOUR_PASSWORD'))\"")
        elif "key=value" in str(e):
            print("💡 HINT: The connection string options are malformed. Check your MONGO_CLUSTER variable.")
            if MONGO_URI and "@" in MONGO_URI:
                print(f"   Debug: ...@{MONGO_URI.split('@')[1]}")
else:
    print("⚠️ MONGODB_URI not found in .env, skipping database connection.")

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
    
    # 1. Try pypdf extraction
    print("Trying pypdf extraction...")
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"pypdf Error: {e}")

    if text.strip():
        print("✅ Text found with pypdf")
        return text

    # 2. Try pdfplumber extraction
    print("Trying pdfplumber extraction...")
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except ImportError:
        print("⚠️ pdfplumber not installed. Skipping.")
    except Exception as e:
        print(f"pdfplumber Error: {e}")

    if text.strip():
        print("✅ Text found with pdfplumber")
        return text

    # 3. OCR fallback (EasyOCR)
    print("⚠️ No text found. Attempting OCR with EasyOCR...")
    try:
        reader = get_ocr_reader()
        # Re-open with pypdf to extract images for OCR
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
        print(f"Image Extraction Error: {e}")
        raise HTTPException(status_code=500, detail=f"Image Extraction Error: {str(e)}")

def clean_text(text):
    # Remove extra spaces, newlines, and weird symbols
    return " ".join(text.split())

def call_llm_analysis(text):
    # Prompt Engineering
    prompt = f"""
    You are a medical assistant.

    Analyze the following medical report and:
    1. Explain findings in simple language
    2. Highlight abnormal values
    3. Suggest what patient should discuss with doctor
    4. DO NOT provide diagnosis
    5. Use layman-friendly wording

    Report:
    {text[:4000]} 
    """

    # Mistral API Key
    api_key = os.getenv("MISTRAL_API_KEY")
    
    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "mistral-tiny",
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"AI Analysis Failed: {str(e)}"

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "ok", "message": "HealthyLabs API is running"}

@app.post("/analyze-report")
async def analyze_report(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    extracted_text = ""
    
    # 1. Determine Source and Extract
    if text:
        extracted_text = text
    elif file:
        content = await file.read()
        if file.filename.lower().endswith(".pdf"):
            extracted_text = extract_pdf_text(content)
        elif file.content_type.startswith("image/"):
            extracted_text = extract_image_text(content)
        else:
            # Try decoding as plain text
            extracted_text = content.decode("utf-8", errors="ignore")
    
    if not extracted_text or not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the provided file. The image might be blurry, contain no text, or OCR failed.")

    # 2. Clean
    cleaned_text = clean_text(extracted_text)
    
    # 3. Analyze
    ai_summary = call_llm_analysis(cleaned_text)
    
    # 4. Save to MongoDB (if configured and user_id is present)
    if db is not None and user_id:
        report_data = {
            "user_id": user_id,
            "original_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text, # Store snippet or full text
            "ai_summary": ai_summary,
            "confidence": "medium",
            "created_at": datetime.utcnow(),
            "source": "file" if file else "text"
        }
        result = db["report_analyses"].insert_one(report_data)
        print(f"💾 Report saved to MongoDB for user {user_id} with ID: {result.inserted_id}")

    return {
        "summary": ai_summary,
        "confidence": "medium", # Placeholder
        "original_text_length": len(cleaned_text)
    }

@app.get("/history/{user_id}")
async def get_user_history(user_id: str):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Fetch reports, sort by newest first
    reports = list(db["report_analyses"].find({"user_id": user_id}).sort("created_at", -1))
    
    # Serialize ObjectId and datetime
    for report in reports:
        report["_id"] = str(report["_id"])
        if "created_at" in report and isinstance(report["created_at"], datetime):
            report["created_at"] = report["created_at"].isoformat()
            
    return reports

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)