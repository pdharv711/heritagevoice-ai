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
    Fast monument identification.
    One Gemini Vision call identifies the monument AND generates
    narration in the requested language.
    """

    # ─────────────────────────────────────────────
    # Decode image
    # ─────────────────────────────────────────────
    try:
        img_bytes = clean_base64_image(request.image)
        pil_image = Image.open(BytesIO(img_bytes))

        # Convert to RGB for reliable processing
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        # Resize large images to reduce upload/processing time
        max_size = 1280
        if max(pil_image.size) > max_size:
            pil_image.thumbnail((max_size, max_size))

    except Exception as e:
        logger.error(f"Image decode error: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid image. Please upload a valid JPEG/PNG."
        )

    # ─────────────────────────────────────────────
    # Gemini Vision
    # ─────────────────────────────────────────────
    if not gemini_available:
        return {
            "monument_id": "unknown",
            "canonical_name": "AI unavailable",
            "narration": "The AI service is currently unavailable.",
            "details": None,
        }

    try:
        logger.info(
            f"Identifying monument and generating {request.language} narration..."
        )

        prompt = f"""
You are HeritageVoice AI, an expert worldwide monument and landmark
recognition system.

Analyze the image VERY CAREFULLY.

Your goal is to identify the SPECIFIC monument, landmark, historical
building, archaeological site, temple, mosque, church, fort, palace,
memorial, statue, tower, gate, stepwell, cave, bridge, or other
recognizable heritage structure shown in the image.

IMPORTANT:
- Do NOT limit yourself to famous monuments.
- Try to identify regional and lesser-known monuments too.
- Use architecture, carvings, columns, domes, towers, sculptures,
  inscriptions, landscape, colors, structure layout and visual clues.
- Consider monuments from India AND the rest of the world.
- If the exact monument cannot be determined, give the most likely
  identification and set confidence to "low".
- Do NOT simply answer "unknown" unless the image contains no useful
  architectural/landmark information.
- Never invent a completely unrelated monument.

Return ONLY valid JSON.

Use exactly this structure:

{{
  "name": "specific monument name",
  "location": "city/state/country if known",
  "built_by": "ruler, dynasty, kingdom, architect or organization if known",
  "year": "construction date or period",
  "architectural_style": "architectural style",
  "key_facts": [
    "important fact 1",
    "important fact 2",
    "important fact 3"
  ],
  "description": "Short accurate description of the monument.",
  "confidence": "high/medium/low",
  "narration": "A short engaging tour-guide narration written entirely in {request.language}"
}}

Narration requirements:
- Entirely in {request.language}
- 70-110 words
- Natural and easy to listen to
- Interesting for tourists
- Mention the monument's name and location
- Include important historical information
- Do not use markdown
- Do not include headings
- Do not mention that you are an AI
"""

        raw = gemini_vision(pil_image, prompt)

        logger.info(f"Gemini response: {raw[:500]}")

        parsed = extract_json(raw)

        if not parsed:
            logger.error("Could not parse Gemini JSON.")
            raise Exception("Invalid Gemini response")

        name = str(parsed.get("name", "")).strip()

        if not name:
            raise Exception("Gemini did not return a monument name")

        # ─────────────────────────────────────────
        # Match local catalog if possible
        # ─────────────────────────────────────────
        catalog_key = database.search_monument(name.lower())

        if catalog_key:
            monument_id = catalog_key
            catalog_info = database.get_monument_by_id(catalog_key)

            effective = {
                "canonical_name": catalog_info["canonical_name"],
                "location": catalog_info["location"],
                "built_by": catalog_info["built_by"],
                "construction_year": catalog_info["construction_year"],
                "theme": catalog_info["theme"],
                "key_facts": catalog_info["key_facts"],
                "detailed_context": catalog_info["detailed_context"],
            }

        else:
            # Dynamic monument — not in database
            monument_id = re.sub(
                r"[^a-z0-9]+",
                "_",
                name.lower()
            )[:40]

            effective = {
                "canonical_name": name,
                "location": parsed.get("location", "Unknown"),
                "built_by": parsed.get("built_by", "Unknown"),
                "construction_year": parsed.get("year", "Unknown"),
                "theme": parsed.get(
                    "architectural_style",
                    "Unknown"
                ),
                "key_facts": parsed.get(
                    "key_facts",
                    []
                ),
                "detailed_context": parsed.get(
                    "description",
                    ""
                ),
            }

        # ─────────────────────────────────────────
        # Narration already generated by same call
        # ─────────────────────────────────────────
        narration = parsed.get("narration", "").strip()

        if not narration:
            narration = mock_narration(
                effective,
                request.language
            )

        logger.info(
            f"Identified: {effective['canonical_name']} "
            f"(confidence: {parsed.get('confidence', 'unknown')})"
        )

        return {
            "monument_id": monument_id,
            "canonical_name": effective["canonical_name"],
            "narration": narration,

            "details": {
                "location": effective["location"],
                "built_by": effective["built_by"],
                "construction_year": effective["construction_year"],
                "theme": effective["theme"],
                "key_facts": effective["key_facts"],
                "description": effective["detailed_context"],
                "confidence": parsed.get(
                    "confidence",
                    "medium"
                ),
            },
        }

    except Exception as e:
        logger.error(
            f"Monument identification failed: {e}",
            exc_info=True
        )

        return {
            "monument_id": "unknown",
            "canonical_name": "Monument Not Recognized",
            "narration": (
                "I could not confidently identify this monument. "
                "Please try another photo where the monument is "
                "clearly visible."
            ),
            "details": None,
        }
class NarrationRequest(BaseModel):
    monument_name: str
    language: str = Field("English")
    details: Dict[str, Any]


@app.post("/api/narrate")
def generate_narration(request: NarrationRequest):

    if not gemini_available:
        return {
            "narration": (
                f"{request.monument_name} is a remarkable "
                f"historical monument."
            )
        }

    try:

        details = request.details

        prompt = f"""
You are HeritageVoice AI, an expert multilingual tour guide.

Create an engaging narration about:

Monument:
{request.monument_name}

Location:
{details.get("location", "Unknown")}

Built by:
{details.get("built_by", "Unknown")}

Construction:
{details.get("construction_year", "Unknown")}

Architectural style:
{details.get("theme", "Unknown")}

Important facts:
{details.get("key_facts", [])}

Description:
{details.get("description", "")}

Write the narration entirely in:
{request.language}

Rules:
- 70-110 words
- Natural tour-guide style
- Easy to listen to
- Historically accurate
- Mention the monument name
- Do not use markdown
- Do not add headings
- Return ONLY the narration
"""

        narration = gemini_text(prompt)

        return {
            "narration": narration
        }

    except Exception as e:

        logger.error(
            f"Narration generation failed: {e}",
            exc_info=True
        )

        return {
            "narration": (
                f"Welcome to {request.monument_name}."
            )
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
