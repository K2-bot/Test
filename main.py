# list_models.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
genai.configure(api_key=GEMINI_KEY)

# List available models
models = genai.list_models()
print("✅ Available Gemini Models:\n")
for m in models:
    name = m.get("name", "Unknown")
    desc = m.get("description", "")
    methods = m.get("capabilities", {}).get("methods", [])
    print(f"Model Name: {name}")
    print(f"Description: {desc}")
    print(f"Supported Methods: {methods}")
    print("-" * 50)
