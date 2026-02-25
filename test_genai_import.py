"""
Check if google.generativeai module can be imported and configured
"""

import os
import sys

print("1. Checking if google.generativeai can be imported...")
try:
    import google.generativeai as genai
    print(f"   ✓ genai imported successfully: {genai}")
except Exception as e:
    print(f"   ✗ Failed to import genai: {e}")
    genai = None

print(f"\n2. Checking if genai is not None: {genai is not None}")

if genai:
    print(f"\n3. Trying to configure genai with API key...")
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"   API Key available: {bool(api_key)}")
    print(f"   API Key preview: {api_key[:10] if api_key else 'None'}...")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            print(f"   ✓ genai.configure() succeeded")
            
            print(f"\n4. Trying to create GenerativeModel...")
            model = genai.GenerativeModel('gemini-2.5-pro')
            print(f"   ✓ Model created: {model}")
            
        except Exception as e:
            print(f"   ✗ genai configuration failed: {e}")
    else:
        print(f"   ✗ No API key available")
else:
    print(f"\n✗ genai module not available - this is the root cause!")
    print(f"   Install with: pip install google-generativeai")

print(f"\n[PYTHON PATH]")
for p in sys.path[:5]:
    print(f"  - {p}")
