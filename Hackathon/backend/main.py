import base64
import json
import logging
import re
from io import BytesIO
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image

import config
import database

# ──────────────────────────────────────────────────────────────────────────────
# New Google Gen AI SDK  (google-genai >= 0.8)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    NEW_SDK = True
except ImportError:
    NEW_SDK = False

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="HeritageVoice AI API",
    description="Multilingual AI-powered Tour Guide — Any Monument Recognition",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Initialise Gemini client
# ──────────────────────────────────────────────────────────────────────────────
gemini_client = None
gemini_available = False
GEMINI_MODEL = "gemini-3.6-flash"   # Current supported model with vision

if config.GEMINI_API_KEY and NEW_SDK:
    try:
        gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        gemini_available = True
        logger.info(f"Gemini client ready (model: {GEMINI_MODEL})")
    except Exception as e:
        logger.error(f"Gemini init error: {e}")
elif not NEW_SDK:
    logger.error("google-genai package not installed. Run: pip install google-genai")
else:
    logger.warning("GEMINI_API_KEY not set — Demo Mode.")

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────────────────────────────────
class IdentifyRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image (data URI or raw base64)")
    language: str = Field("English", description="Target language for narration")

class ChatMessage(BaseModel):
    role: str = Field("user")
    content: str = Field(...)

class ChatRequest(BaseModel):
    monument_id: str
    question: str
    language: str = Field("English")
    history: List[ChatMessage] = Field(default=[])

# ──────────────────────────────────────────────────────────────────────────────
# Mock narrations (Demo Mode / fallback)
# ──────────────────────────────────────────────────────────────────────────────
MOCK_NARRATIONS: Dict[str, str] = {
    "English":    "Welcome to {name}! Located in {location}, built by {built_by} around {construction}. Key fact: {key_fact}",
    "Hindi":      "{name} में आपका स्वागत है! {location} में स्थित यह स्मारक {built_by} ने {construction} में बनवाया। मुख्य तथ्य: {key_fact}",
    "Tamil":      "{name}-க்கு வரவேற்கிறோம்! {location}-ல் {built_by} கட்டினார், {construction}. {key_fact}",
    "Telugu":     "{name} కు స్వాగతం! {location}లో {built_by} నిర్మించారు, {construction}. {key_fact}",
    "Bengali":    "{name}-এ স্বাগত! {location}-এ {built_by} নির্মিত, {construction}. {key_fact}",
    "Marathi":    "{name} मध्ये स्वागत! {location} येथे {built_by} यांनी {construction} मध्ये बांधले. {key_fact}",
    "Gujarati":   "{name} માં સ્વાગત! {location} માં {built_by} દ્વારા {construction} માં બનાવ્યું. {key_fact}",
    "Kannada":    "{name} ಗೆ ಸ್ವಾಗತ! {location} ನಲ್ಲಿ {built_by} {construction} ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು. {key_fact}",
    "Punjabi":    "{name} ਵਿੱਚ ਸੁਆਗਤ! {location} ਵਿੱਚ {built_by} ਨੇ {construction} ਵਿੱਚ ਬਣਾਇਆ. {key_fact}",
    "French":     "Bienvenue à {name}! Situé à {location}, construit par {built_by} en {construction}. Fait: {key_fact}",
    "Spanish":    "¡Bienvenido a {name}! En {location}, construido por {built_by} en {construction}. Hecho: {key_fact}",
    "German":     "Willkommen bei {name}! In {location}, erbaut von {built_by} um {construction}. Fakt: {key_fact}",
    "Arabic":     "مرحباً بكم في {name}! يقع في {location}، بناه {built_by} عام {construction}. الحقيقة: {key_fact}",
    "Japanese":   "{name}へようこそ！{location}に位置し、{built_by}が{construction}に建設。特徴：{key_fact}",
    "Korean":     "{name}에 오신 것을 환영합니다! {location}에 위치, {built_by}가 {construction}에 건설. {key_fact}",
    "Portuguese": "Bem-vindo a {name}! Em {location}, construído por {built_by} em {construction}. Fato: {key_fact}",
    "Russian":    "Добро пожаловать в {name}! В {location}, построен {built_by} в {construction}. Факт: {key_fact}",
    "Italian":    "Benvenuti a {name}! A {location}, costruito da {built_by} nel {construction}. Fatto: {key_fact}",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def clean_base64_image(b64: str) -> bytes:
    if "," in b64:
        b64 = b64.split(",")[1]
    # Fix padding
    b64 += "=" * (-len(b64) % 4)
    return base64.b64decode(b64)


def extract_json(text: str) -> Optional[Dict]:
    """Try multiple strategies to extract a JSON object from text."""
    text = text.strip()
    # 1. Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # 2. Strip markdown fences ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 3. Find first {...} block (greedy)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


def gemini_text(prompt: str) -> str:
    """Send a text-only prompt and return the response text."""
    resp = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return resp.text.strip()


def gemini_vision(pil_image: Image.Image, prompt: str) -> str:
    """Send an image + text prompt and return the response text."""
    # Convert PIL to bytes for the new SDK
    buf = BytesIO()
    fmt = pil_image.format or "JPEG"
    if fmt not in ("JPEG", "PNG", "WEBP", "GIF"):
        fmt = "JPEG"
    pil_image.save(buf, format=fmt)
    img_bytes = buf.getvalue()
    mime = f"image/{fmt.lower()}"

    image_part = genai_types.Part.from_bytes(data=img_bytes, mime_type=mime)
    text_part  = genai_types.Part.from_text(text=prompt)

    resp = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[genai_types.Content(parts=[image_part, text_part], role="user")],
    )
    return resp.text.strip()


def mock_narration(info: Dict, language: str) -> str:
    tmpl = MOCK_NARRATIONS.get(language, MOCK_NARRATIONS["English"])
    facts = info.get("key_facts", ["a remarkable historical site."])
    fact0 = facts[0] if facts else "a remarkable historical site."
    return tmpl.format(
        name=info.get("canonical_name", info.get("name", "this monument")),
        location=info.get("location", "unknown location"),
        built_by=info.get("built_by", "unknown builders"),
        construction=info.get("construction_year", info.get("year", "an unknown era")),
        key_fact=fact0,
    )

# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "online",
        "sdk": "google-genai (new)" if NEW_SDK else "missing",
        "gemini_available": gemini_available,
        "model": GEMINI_MODEL,
        "mode": "Live AI" if gemini_available else "Demo Mock",
    }


@app.get("/api/monuments")
def get_monuments():
    return [
        {"id": k, "canonical_name": v["canonical_name"], "location": v["location"],
         "built_by": v["built_by"], "construction_year": v["construction_year"]}
        for k, v in database.MONUMENT_CATALOG.items()
    ]


@app.post("/api/identify")
def identify_monument(request: IdentifyRequest):
    """
    Identify ANY world monument from an image using Gemini Vision,
    then generate a narration in the requested language.
    """
    # ── Decode image ──────────────────────────────────────────────────────────
    try:
        img_bytes = clean_base64_image(request.image)
        pil_image = Image.open(BytesIO(img_bytes))
        # Ensure format is set
        if not pil_image.format:
            pil_image.format = "JPEG"
    except Exception as e:
        logger.error(f"Image decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid image. Please upload a valid JPEG/PNG.")

    monument_id = "unknown"
    catalog_info = None
    dynamic_info: Optional[Dict] = None

    # ── STEP 1: Open-ended Gemini Vision identification ───────────────────────
    if gemini_available:
        try:
            logger.info("Calling Gemini Vision for monument identification...")

            id_prompt = (
                "You are an expert monument recognition AI. "
                "Look at this image and identify the monument, landmark or historical structure shown.\n\n"
                "Respond with ONLY a JSON object (no markdown, no explanation) using exactly these keys:\n"
                "{\n"
                '  "name": "full official name",\n'
                '  "location": "city, country",\n'
                '  "built_by": "who commissioned or built it",\n'
                '  "year": "construction period",\n'
                '  "architectural_style": "style",\n'
                '  "key_facts": ["fact1", "fact2", "fact3"],\n'
                '  "description": "2-3 sentence history",\n'
                '  "confidence": "high or medium or low"\n'
                "}\n\n"
                "If no monument is visible, respond: {\"name\": \"unknown\", \"confidence\": \"low\"}"
            )

            raw = gemini_vision(pil_image, id_prompt)
            logger.info(f"Gemini vision raw response (first 400 chars): {raw[:400]}")

            parsed = extract_json(raw)
            logger.info(f"Parsed JSON: {parsed}")

            if parsed and str(parsed.get("name", "")).strip().lower() not in ("", "unknown"):
                dynamic_info = parsed
                name_lower = parsed["name"].lower()

                # Check if it matches local catalog
                catalog_key = database.search_monument(name_lower)
                if catalog_key:
                    monument_id = catalog_key
                    catalog_info = database.get_monument_by_id(catalog_key)
                    logger.info(f"Matched local catalog: {catalog_key}")
                else:
                    monument_id = re.sub(r"[^a-z0-9]+", "_", name_lower)[:40]
                    logger.info(f"Dynamic monument (not in catalog): {parsed['name']}")
            else:
                logger.warning(f"Gemini returned unrecognized or unparseable response: {raw[:200]}")

        except Exception as e:
            logger.error(f"Gemini vision call failed: {e}", exc_info=True)

    # ── STEP 2: Build effective info ──────────────────────────────────────────
    effective: Optional[Dict] = None

    if catalog_info:
        effective = {
            "canonical_name": catalog_info["canonical_name"],
            "location":        catalog_info["location"],
            "built_by":        catalog_info["built_by"],
            "construction_year": catalog_info["construction_year"],
            "theme":           catalog_info["theme"],
            "key_facts":       catalog_info["key_facts"],
            "detailed_context": catalog_info["detailed_context"],
        }
    elif dynamic_info:
        kf = dynamic_info.get("key_facts", [])
        if not kf:
            kf = [dynamic_info.get("description", "A remarkable historical structure.")]
        effective = {
            "canonical_name": dynamic_info.get("name", "Unknown Monument"),
            "location":        dynamic_info.get("location", "Unknown Location"),
            "built_by":        dynamic_info.get("built_by", "Unknown"),
            "construction_year": dynamic_info.get("year", "Unknown Period"),
            "theme":           dynamic_info.get("architectural_style", "Unknown Style"),
            "key_facts":       kf,
            "detailed_context": dynamic_info.get("description", ""),
        }

    if not effective:
        return {
            "monument_id": "unknown",
            "canonical_name": "Monument Not Recognized",
            "narration": (
                "We could not identify the monument in this image. "
                "Please try a clearer photo with the monument prominently visible."
            ),
            "details": None,
        }

    # ── STEP 3: Generate narration ─────────────────────────────────────────────
    narration_text = ""
    if gemini_available:
        try:
            logger.info(f"Generating narration in '{request.language}' for '{effective['canonical_name']}'...")
            narration_prompt = (
                f"You are an engaging local tour guide. "
                f"Write a captivating audio narration about '{effective['canonical_name']}' ({effective['location']}) "
                f"entirely in the language: '{request.language}'.\n\n"
                f"Facts to include:\n"
                f"- Built by: {effective['built_by']}\n"
                f"- Period: {effective['construction_year']}\n"
                f"- Style: {effective['theme']}\n"
                f"- Key facts: {'; '.join(effective['key_facts'])}\n"
                f"- Context: {effective['detailed_context']}\n\n"
                f"Rules: 120-180 words, warm storytelling tone, suitable for listening aloud. "
                f"Return ONLY the narration — no titles, no labels, no markdown."
            )
            narration_text = gemini_text(narration_prompt)
        except Exception as e:
            logger.error(f"Narration generation failed: {e}")

    if not narration_text:
        narration_text = mock_narration(effective, request.language)

    return {
        "monument_id": monument_id,
        "canonical_name": effective["canonical_name"],
        "narration": narration_text,
        "details": {
            "location":          effective["location"],
            "built_by":          effective["built_by"],
            "construction_year": effective["construction_year"],
            "theme":             effective["theme"],
            "key_facts":         effective["key_facts"],
        },
    }


@app.post("/api/chat")
def chat_with_guide(request: ChatRequest):
    """Multilingual follow-up Q&A about an identified monument."""
    catalog_info = database.get_monument_by_id(request.monument_id)
    display_name = catalog_info["canonical_name"] if catalog_info else request.monument_id.replace("_", " ").title()

    reply = ""
    if gemini_available:
        try:
            history_lines = []
            for msg in request.history[-6:]:
                role = "Visitor" if msg.role == "user" else "Guide"
                history_lines.append(f"{role}: {msg.content}")

            if catalog_info:
                grounding = (
                    f"Facts — {catalog_info['canonical_name']} ({catalog_info['location']}):\n"
                    f"Built by: {catalog_info['built_by']}\n"
                    f"Period: {catalog_info['construction_year']}\n"
                    f"Context: {catalog_info['detailed_context']}\n"
                    f"Key facts: {'; '.join(catalog_info['key_facts'])}"
                )
            else:
                grounding = f"The visitor is asking about: {display_name}. Use your historical knowledge."

            prompt = (
                f"You are HeritageVoice AI — a multilingual tour guide. Language: '{request.language}'.\n"
                f"{grounding}\n\n"
                f"Conversation:\n{chr(10).join(history_lines)}\n\n"
                f"Visitor: {request.question}\n\n"
                f"Reply in '{request.language}', under 100 words, conversational and accurate. "
                f"Return ONLY the guide's answer."
            )
            reply = gemini_text(prompt)
        except Exception as e:
            logger.error(f"Chat failed: {e}")

    if not reply:
        q = request.question.lower()
        if catalog_info:
            if any(w in q for w in ("who", "built", "creator")):
                reply = f"Built by {catalog_info['built_by']}."
            elif any(w in q for w in ("when", "year", "old", "age")):
                reply = f"Construction: {catalog_info['construction_year']}."
            elif any(w in q for w in ("where", "location", "city")):
                reply = f"Located at {catalog_info['location']}."
            else:
                reply = f"Key highlight: {catalog_info['key_facts'][0]}"
        else:
            reply = f"I don't have offline data for {display_name}. Please ensure the AI backend is running."
        if request.language != "English":
            reply = f"[Demo — {request.language}]: {reply}"

    return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting HeritageVoice AI v2.1 on {config.HOST}:{config.PORT}")
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
