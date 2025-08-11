#!/usr/bin/env python3
"""Test Gemini API integration."""

import sys
import re
import json
import requests

def test_gemini_api(api_key, word, translation_language="English"):
    """Test Gemini API with the exact same logic as the UI."""
    print(f"Testing Gemini API for word: '{word}' -> {translation_language}")
    
    GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = (
        f"You are a helpful German language assistant. For the word: **{word}**, provide the following structured information.\n"
        f"Translate ONLY into {translation_language}. Do NOT include English translations unless {translation_language} is English.\n"
        f"Your task is to return translations and example sentences ONLY in {translation_language}.\n"
        "Use consistent fields: base_e, s1e, s2e, s3e.\n"
        "If the word is not a valid German word, return this JSON exactly:\n"
        '{"error": "Not a valid German word"}\n\n'
        "1. **base_d**: The original German word\n"
        f"2. **base_e**: The {translation_language} translation(s)\n"
        "3. **artikel_d**: The definite article if the word is a noun (e.g., \"der\", \"die\", \"das\"). Leave empty if not a noun.\n"
        "4. **plural_d**: The plural form (for nouns). Leave empty if not a noun.\n"
        "5. **word_type**: The word type: \"noun\", \"verb\", \"adjective\", etc.\n"
        "6. **conjugation**: For verbs only, provide present tense conjugation as object: {\"ich\": \"form\", \"du\": \"form\", \"er_sie_es\": \"form\", \"wir\": \"form\", \"ihr\": \"form\", \"sie_Sie\": \"form\"}\n"
        "7. **praesens**: Present tense (3rd person singular), e.g., \"läuft\"\n"
        "8. **praeteritum**: Simple past tense (3rd person singular), e.g., \"lief\"\n"
        "9. **perfekt**: Present perfect form, e.g., \"ist gelaufen\"\n"
        "10. **full_d**: A combined string of the above three conjugation forms, e.g., \"läuft, lief, ist gelaufen\"\n"
        "11. **s1**: A natural German sentence using the word\n"
        "12. **s1e**: Translation of s1 sentence\n"
        "13. **s2** (optional): A second German sentence if the word has different context\n"
        "14. **s2e** (optional): Translation of s2 sentence\n"
        "15. **s3** (optional): A third German sentence for nuance\n"
        "16. **s3e** (optional): Translation of s3 sentence\n\n"
        "Example for verb:\n"
        "```json\n"
        "{\n"
        '  "base_d": "laufen",\n'
        f'  "base_e": "to run",\n'
        '  "artikel_d": "",\n'
        '  "plural_d": "",\n'
        '  "word_type": "verb",\n'
        '  "conjugation": {"ich": "laufe", "du": "läufst", "er_sie_es": "läuft", "wir": "laufen", "ihr": "lauft", "sie_Sie": "laufen"},\n'
        '  "praesens": "läuft",\n'
        '  "praeteritum": "lief",\n'
        '  "perfekt": "ist gelaufen",\n'
        '  "full_d": "läuft, lief, ist gelaufen",\n'
        '  "s1": "Ich laufe jeden Morgen im Park.",\n'
        '  "s1e": "I run every morning in the park.",\n'
        '  "s2": "Er läuft zur Arbeit.",\n'
        '  "s2e": "He runs to work."\n'
        "}\n"
        "```\n\n"
        "Example for noun:\n"
        "```json\n"
        "{\n"
        '  "base_d": "der Hund",\n'
        f'  "base_e": "the dog",\n'
        '  "artikel_d": "der",\n'
        '  "plural_d": "die Hunde",\n'
        '  "word_type": "noun",\n'
        '  "conjugation": {},\n'
        '  "praesens": "",\n'
        '  "praeteritum": "",\n'
        '  "perfekt": "",\n'
        '  "full_d": "der Hund",\n'
        '  "s1": "Der Hund läuft im Garten.",\n'
        '  "s1e": "The dog runs in the garden."\n'
        "}\n"
        "```"
    )

    headers = {'Content-Type': 'application/json'}
    body = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        print("Sending request to Gemini...")
        response = requests.post(GEMINI_ENDPOINT, headers=headers, json=body, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {"error": f"HTTP {response.status_code}: {response.text}"}
            
        result = response.json()
        
        if "candidates" not in result:
            print(f"API Error: {result}")
            return {"error": f"Gemini error: {result.get('error', 'No candidates returned')}"}
            
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        print(f"Raw Gemini response:\n{content}\n")
        
        # Extract JSON from response
        match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if not match:
            print("❌ No JSON block found in response")
            return {"error": "JSON block not found in Gemini response"}
            
        json_str = match.group(1)
        print(f"Extracted JSON:\n{json_str}\n")
        
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return {"error": f"JSON parsing failed: {str(e)}"}
        
        print("✅ Successfully parsed JSON!")
        print(f"Parsed structure:")
        for key, value in parsed.items():
            if isinstance(value, dict):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
        
        # Validate required fields
        required_fields = ["base_d", "base_e", "word_type"]
        missing = [field for field in required_fields if not parsed.get(field)]
        if missing:
            print(f"⚠️ Missing required fields: {missing}")
        else:
            print("✅ All required fields present")
            
        return parsed

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

if __name__ == "__main__":
    API_KEY = "AIzaSyDbSs1PM7jYzIuO4WroY_cMBGWlwYspO1Q"
    
    # Test with a verb
    print("=" * 50)
    print("TEST 1: German Verb")
    print("=" * 50)
    result1 = test_gemini_api(API_KEY, "laufen", "English")
    
    print("\n" + "=" * 50)
    print("TEST 2: German Noun")
    print("=" * 50)
    result2 = test_gemini_api(API_KEY, "der Hund", "English")
    
    print("\n" + "=" * 50)
    print("TEST 3: Invalid Word")
    print("=" * 50)
    result3 = test_gemini_api(API_KEY, "xyzabc", "English")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    tests = [("laufen", result1), ("der Hund", result2), ("xyzabc", result3)]
    
    for word, result in tests:
        if "error" in result:
            print(f"❌ {word}: {result['error']}")
        else:
            print(f"✅ {word}: {result.get('word_type', 'unknown')} - {result.get('base_e', 'no translation')}")