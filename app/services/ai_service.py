import os
import json
import asyncio
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# 🔑 API KEYS
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Safety Settings
SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
]


class AIService:

    # ---------------- GEMINI ---------------- #
    @staticmethod
    async def _call_gemini(prompt: str):
        if not GEMINI_API_KEY:
            return None

        try:
            response = await client.aio.models.generate_content(
                model="gemini-1.5-flash",  # ✅ safer model
                contents=prompt,
                config=types.GenerateContentConfig(
                    safety_settings=SAFETY_SETTINGS,
                    temperature=0.7,
                    max_output_tokens=800,
                )
            )

            if response and response.text:
                return response.text

        except Exception as e:
            print(f"❌ Gemini Error: {e}")

        return None


    # ---------------- GROQ ---------------- #
    @staticmethod
    def _call_groq(prompt: str):
        if not GROQ_API_KEY:
            print("❌ GROQ KEY missing")
            return None

        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",  # ✅ FIXED MODEL
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=20
            )

            print("Groq Status:", res.status_code)

            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]

            print("❌ Groq Error:", res.text)

        except Exception as e:
            print("❌ Groq Exception:", e)

        return None


    # ---------------- OPENROUTER ---------------- #
    @staticmethod
    def _call_openrouter(prompt: str):
        if not OPENROUTER_API_KEY:
            print("❌ OPENROUTER KEY missing")
            return None

        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-3-8b-instruct",  # ✅ FIXED MODEL
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=20
            )

            print("OpenRouter Status:", res.status_code)

            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]

            print("❌ OpenRouter Error:", res.text)

        except Exception as e:
            print("❌ OpenRouter Exception:", e)

        return None


    # ---------------- MAIN AI CALL ---------------- #
    @staticmethod
    async def ask_ai(prompt: str):

        # 🔥 1️⃣ TRY GROQ FIRST (fast + reliable)
        print("🚀 Trying Groq...")
        groq_result = AIService._call_groq(prompt)
        if groq_result:
            return groq_result

        # 🔄 2️⃣ TRY OPENROUTER
        print("🔄 Groq failed → trying OpenRouter")
        openrouter_result = AIService._call_openrouter(prompt)
        if openrouter_result:
            return openrouter_result

        # 🔄 3️⃣ LAST TRY GEMINI
        print("🔄 OpenRouter failed → trying Gemini")
        gemini_result = await AIService._call_gemini(prompt)
        if gemini_result:
            return gemini_result

        return "⚠️ AI services unavailable. Please try again later."


    # ---------------- CLEAN JSON ---------------- #
    @staticmethod
    def _clean_json(text: str):
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)
        except:
            return None


    # ---------------- FEATURES ---------------- #

    @staticmethod
    async def analyze_product_by_name(product_name: str, user_profile: dict):
        raw_allergies = user_profile.get("allergies", []) if isinstance(user_profile, dict) else []
        allergy_names = []
        for a in raw_allergies:
            if isinstance(a, dict):
                n = str(a.get("name") or "").strip()
            else:
                n = str(a).strip()
            if n:
                allergy_names.append(n)
        allergies = ", ".join(allergy_names)

        prompt = f"""
        Product: {product_name}
        User Allergies: {allergies}

        Return JSON:
        {{
          "product_name": "",
          "category": "",
          "risk": "SAFE | CAUTION | DANGEROUS",
          "explanation": "",
          "detected_allergens": [],
          "ai_insights": [
            {{ "type": "warning | success | danger | info", "text": "" }}
          ]
        }}
        """

        result = await AIService.ask_ai(prompt)
        parsed = AIService._clean_json(result)

        if isinstance(parsed, dict):
            parsed.setdefault("product_name", product_name)
            parsed.setdefault("category", "")
            parsed.setdefault("risk", "CAUTION")
            parsed.setdefault("explanation", "")
            parsed.setdefault("detected_allergens", [])
            parsed.setdefault("ai_insights", [])
            return parsed

        return {
            "product_name": product_name,
            "category": "",
            "risk": "CAUTION",
            "explanation": "AI unavailable",
            "detected_allergens": [],
            "ai_insights": [],
        }


    @staticmethod
    async def analyze_ingredients(ingredients: str, user_context: str = ""):
        prompt = f"""
        Ingredients: {ingredients}
        Context: {user_context}

        Return JSON:
        {{
          "risk_level": "SAFE | WARNING | DANGER",
          "detected_allergens": []
        }}
        """

        result = await AIService.ask_ai(prompt)
        parsed = AIService._clean_json(result)

        return parsed or {"risk_level": "UNKNOWN"}


    @staticmethod
    async def chatbot_response(query: str, chat_history: list):
        history = "\n".join([
            f"{'User' if m['role']=='user' else 'AI'}: {m['content']}"
            for m in chat_history[-5:]
        ])

        prompt = f"""
        You are an Allergy Assistant. Be helpful and short.

        {history}

        User: {query}
        AI:
        """

        return await AIService.ask_ai(prompt)


    @staticmethod
    async def get_organic_remedies(symptoms: list):
        prompt = f"""
        Symptoms: {', '.join(symptoms)}

        Return JSON:
        {{
          "remedies": []
        }}
        """

        result = await AIService.ask_ai(prompt)
        parsed = AIService._clean_json(result)

        return parsed or {"remedies": []}
