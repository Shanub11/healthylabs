import requests
import json
import time
from datetime import datetime, timezone

# The base URL where your Uvicorn server is currently running
BASE_URL = "http://127.0.0.1:8005/refinery/v1"
TEST_DOCUMENT_ID = "test-doc-hypertension-lisinopril-001"

def test_ingestion():
    print("--- Testing Document Ingestion ---")
    url = f"{BASE_URL}/ingest"
    
    # A mock payload that satisfies the ExtractionOutput schema
    payload = {
        "content": (
            "Hypertension clinical guidance: patients taking lisinopril should monitor blood pressure, "
            "kidney function, potassium levels, dizziness, cough, angioedema symptoms, and cardiovascular "
            "risk factors such as smoking. Persistent uncontrolled hypertension increases risk of stroke, "
            "coronary artery disease, heart failure, and chronic kidney disease."
        ),
        "source": "clinical_notes",
        "document_id": TEST_DOCUMENT_ID,
        "metadata": {
            "title": {"value": "Sample Clinical Note", "confidence": 1.0},
            "published_at": {"value": datetime.now(timezone.utc).isoformat(), "confidence": 1.0},
            "tags": ["test", "clinical"]
        },
        "quality": {
            "overall_score": 0.95,
            "ocr_mean_confidence": 0.98,
            "issues": []
        },
        "audit": {
            "document_id": TEST_DOCUMENT_ID,
            "source": {
                "uri": "file://local/test-doc-hypertension-lisinopril-001.pdf",
                "provider": "local-test-provider"
            },
            "extraction": {
                "engine": "test-engine",
                "engine_version": "1.0.0",
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
        },
        "layout_graph": {},
        "section_hierarchy": {"id": "root", "type": "document"},
        "assets": [],
        "tables": [],
        "medical_patterns": {}
    }

    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}\n")


def wait_for_vectors(timeout_seconds=90):
    print("--- Waiting for Vectorization ---")
    url = f"{BASE_URL}/maintenance/vector-status/{TEST_DOCUMENT_ID}"
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        response = requests.get(url)
        data = response.json()
        print(f"Vector status: {json.dumps(data, indent=2)}")
        if data.get("ready"):
            return
        time.sleep(3)

    raise TimeoutError("Timed out waiting for document vectors to be created.")

def test_chat():
    print("--- Testing Diagnostic Chat ---")
    url = f"{BASE_URL}/chat/diagnostic"
    
    payload = {
      "question": "What are common complications for my condition and medication?",
      "user_profile": {
        "age": 45,
        "conditions": ["hypertension"],
        "allergies": ["penicillin"],
        "current_medications": ["lisinopril"],
        "habits": ["smoker"]
      }
    }

    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:\n{json.dumps(response.json(), indent=2)}\n")

if __name__ == "__main__":
    test_ingestion()
    wait_for_vectors()
    test_chat()
