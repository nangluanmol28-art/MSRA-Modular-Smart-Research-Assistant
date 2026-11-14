"""
MSRA Gemini Model Availability Diagnostic
==========================================
Lists all available Gemini models and their supported generation methods.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")

if not API_KEY:
    print("No GEMINI_API_KEY found in environment or .env")
    exit(0)

url = "https://generativelanguage.googleapis.com/v1beta/models"
headers = {"x-goog-api-key": API_KEY}

try:
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        models = response.json().get("models", [])
        print("\nAVAILABLE TEXT GENERATION MODELS:\n")
        for model in models:
            methods = model.get("supportedGenerationMethods", [])
            if "generateContent" in methods:
                print(f"Model: {model.get('name')} | Display: {model.get('displayName')}")
    else:
        print(f"STATUS CODE: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Connection error: {e}")
