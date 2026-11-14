"""
MSRA Gemini Direct API Diagnostic
=================================
Performs a direct REST API connectivity probe to the Gemini endpoint.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
print("Gemini API key loaded:", API_KEY is not None)

if not API_KEY:
    print("No GEMINI_API_KEY found in environment or .env")
    exit(0)

url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": API_KEY
}

data = {
    "contents": [
        {
            "role": "user",
            "parts": [
                {
                    "text": "Explain Artificial Intelligence in 1 simple sentence."
                }
            ]
        }
    ]
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print("STATUS CODE:", response.status_code)
    if response.status_code == 200:
        result = response.json()
        answer = result["candidates"][0]["content"]["parts"][0]["text"]
        print("\nGEMINI RESPONSE:")
        print(answer)
    else:
        print("\nERROR RESPONSE:", response.text)
except Exception as e:
    print(f"Connection error: {e}")
