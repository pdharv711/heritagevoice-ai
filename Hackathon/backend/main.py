import base64
import json
import logging
import re
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image

import config
import database

try:
    from google import genai
    from google.genai import types as genai_types
    NEW_SDK = True
except ImportError:
    NEW_SDK = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HeritageVoice AI API",
    description="Multilingual AI Tour Guide — Worldwide Monument Recognition",
    version="4.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_MODEL = "gemini-3.7-flash"
gemini_client = None
gemini_available = False

if config.GEMINI_API_KEY and NEW_SDK:
    try:
        gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
        gemini_available = True
        logger.info("Gemini client ready (model: %s)", GEMINI_MODEL)
    except Exception:
        logger.exception("Gemini initialization failed")
elif not NEW_SDK:
    logger.error("google-genai is not installed. Run: pip install -U google-genai")
else:
    logger.warning("GEMINI_API_KEY is not set — Demo Mode.")

SUPPORTED_LANGUAGES = [
    "English", "Hindi", "Tamil", "Telugu", "Bengali", "Marathi",
    "Gujarati", "Kannada", "Punjabi", "French", "Spanish", "German",
    "Arabic", "Japanese", "Korean", "Portuguese", "Russian", "Italian",
]

MOCK_NARRATIONS: Dict[str, str] = {
    "English": "Welcome to {name}! Located in {location}, this historical monument was built by {built_by} around {construction}. A key highlight is {key_fact}",
    "Hindi": "{name} में आपका स्वागत है! यह ऐतिहासिक स्मारक {location} में स्थित है और {built_by} द्वारा {construction} के आसपास बनाया गया था। इसकी एक प्रमुख विशेषता है: {key_fact}",
    "Gujarati": "{name} માં આપનું સ્વાગત છે! આ ઐતિહાસિક સ્મારક {location} માં આવેલું છે અને {built_by} દ્વારા {construction} ની આસપાસ બનાવવામાં આવ્યું હતું. તેની એક મહત્વપૂર્ણ વિશેષતા છે: {key_fact}",
    "Tamil": "{name}-க்கு வரவேற்கிறோம்! இந்த வரலாற்றுச் சின்னம் {location}-ல் அமைந்துள்ளது. இது {built_by} அவர்களால் {construction} காலத்தில் கட்டப்பட்டது. முக்கிய அம்சம்: {key_fact}",
    "Telugu": "{name} కు స్వాగతం! ఈ చారిత్రక కట్టడం {location}లో ఉంది. దీనిని {built_by} వారు {construction} కాలంలో నిర్మించారు. ముఖ్యమైన విషయం: {key_fact}",
    "Bengali": "{name}-এ স্বাগত! এই ঐতিহাসিক স্থাপনাটি {location}-এ অবস্থিত এবং {built_by} দ্বারা {construction} সময়ে নির্মিত হয়েছিল। গুরুত্বপূর্ণ তথ্য: {key_fact}",
    "Marathi": "{name} मध्ये आपले स्वागत आहे! हे ऐतिहासिक स्मारक {location} येथे आहे आणि {built_by} यांनी {construction} च्या सुमारास बांधले. महत्त्वाची माहिती: {key_fact}",
    "Kannada": "{name} ಗೆ ಸ್ವಾಗತ! ಈ ಐತಿಹಾಸಿಕ ಸ್ಮಾರಕವು {location} ನಲ್ಲಿ ಇದೆ ಮತ್ತು {built_by} ಅವರು {construction} ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು. ಪ್ರಮುಖ ಮಾಹಿತಿ: {key_fact}",
    "Punjabi": "{name} ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ! ਇਹ ਇਤਿਹਾਸਕ ਸਮਾਰਕ {location} ਵਿੱਚ ਸਥਿਤ ਹੈ ਅਤੇ {built_by} ਦੁਆਰਾ {construction} ਦੇ ਆਸ-ਪਾਸ ਬਣਾਇਆ ਗਿਆ ਸੀ। ਮੁੱਖ ਤੱਥ: {key_fact}",
    "French": "Bienvenue à {name}! Situé à {location}, ce monument historique a été construit par {built_by} vers {construction}. Fait important: {key_fact}",
    "Spanish": "¡Bienvenido a {name}! Situado en {location}, este monumento histórico fue construido por {built_by} alrededor de {construction}. Dato importante: {key_fact}",
    "German": "Willkommen bei {name}! Dieses historische Monument befindet sich in {location} und wurde von {built_by} um {construction} errichtet. Interessante Tatsache: {key_fact}",
    "Arabic": "مرحباً بكم في {name}! يقع هذا المعلم التاريخي في {location} وقد بناه {built_by} حوالي {construction}. حقيقة مهمة: {key_fact}",
    "Japanese": "{name}へようこそ！この歴史的建造物は{location}にあり、{built_by}によって{construction}頃に建設されました。重要な特徴は、{key_fact}です。",
    "Korean": "{name}에 오신 것을 환영합니다! 이 역사적인 기념물은 {location}에 있으며 {built_by}가 {construction}경에 건설했습니다. 중요한 사실은 {key_fact}입니다.",
    "Portuguese": "Bem-vindo a {name}! Localizado em {location}, este monumento histórico foi construído por {built_by} por volta de {construction}. Fato importante: {key_fact}",
    "Russian": "Добро пожаловать в {name}! Этот исторический памятник находится в {location} и был построен {built_by} примерно в {construction}. Важный факт: {key_fact}",
    "Italian": "Benvenuti a {name}! Situato a {location}, questo monumento storico fu costruito da {built_by} intorno a {construction}. Fatto importante: {key_fact}",
}


class IdentifyRequest(BaseModel):
    image: str = Field(..., description="Base64 image data URI or raw Base64")
    language: str = Field("English")


class NarrationRequest(BaseModel):
    monument_name: str
    language: str = Field("English")
    details: Dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str = Field("user")
    content: str


class ChatRequest(BaseModel):
    monument_id: str
    monument_name: Optional[str] = None
    monument_details: Optional[Dict[str, Any]] = None
    question: str
    language: str = Field("English")
    history: List[ChatMessage] = Field(default_factory=list)


IDENTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "location": {"type": "string"},
        "built_by": {"type": "string"},
        "year": {"type": "string"},
        "architectural_style": {"type": "string"},
        "key_facts": {"type": "array", "items": {"type": "string"}},
        "description": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "narration": {"type": "string"},
    },
    "required": [
        "name", "location", "built_by", "year",
        "architectural_style", "key_facts",
        "description", "confidence", "narration",
    ],
}


def clean_base64_image(value: str) -> bytes:
    if "," in value:
        value = value.split(",", 1)[1]
    value = re.sub(r"\s+", "", value.strip())
    value += "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value, validate=False)
    except Exception as exc:
        raise ValueError("Invalid Base64 image") from exc


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()

    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            result = json.loads(match.group(1))
            return result if isinstance(result, dict) else None
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            result = json.loads(text[start:end + 1])
            return result if isinstance(result, dict) else None
        except Exception:
            pass

    return None


def gemini_text(prompt: str) -> str:
    if not gemini_client:
        raise RuntimeError("Gemini client is unavailable")

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return (response.text or "").strip()


def gemini_vision_json(image: Image.Image, prompt: str) -> Dict[str, Any]:
    if not gemini_client:
        raise RuntimeError("Gemini client is unavailable")

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)

    image_part = genai_types.Part.from_bytes(
        data=buffer.getvalue(),
        mime_type="image/jpeg",
    )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            genai_types.Content(
                role="user",
                parts=[
                    image_part,
                    genai_types.Part.from_text(text=prompt),
                ],
            )
        ],
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=IDENTIFICATION_SCHEMA,
        ),
    )

    parsed = extract_json(response.text or "")
    if not parsed:
        raise ValueError("Gemini returned no valid structured identification")
    return parsed


def mock_narration(info: Dict[str, Any], language: str) -> str:
    template = MOCK_NARRATIONS.get(language, MOCK_NARRATIONS["English"])
    facts = info.get("key_facts") or ["a remarkable historical site."]
    if not isinstance(facts, list):
        facts = [str(facts)]

    return template.format(
        name=info.get("canonical_name") or info.get("name") or "this monument",
        location=info.get("location") or "an unknown location",
        built_by=info.get("built_by") or "unknown builders",
        construction=info.get("construction_year") or info.get("year") or "an unknown period",
        key_fact=str(facts[0]),
    )


def normalize_details(name: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    facts = parsed.get("key_facts") or []
    if not isinstance(facts, list):
        facts = [str(facts)]

    return {
        "canonical_name": name,
        "location": str(parsed.get("location") or "Unknown"),
        "built_by": str(parsed.get("built_by") or "Unknown"),
        "construction_year": str(parsed.get("year") or "Unknown"),
        "theme": str(parsed.get("architectural_style") or "Unknown"),
        "key_facts": [str(x) for x in facts[:8]],
        "description": str(parsed.get("description") or ""),
        "confidence": str(parsed.get("confidence") or "medium").lower(),
    }


@app.get("/")
def root():
    return {
        "status": "online",
        "sdk": "google-genai" if NEW_SDK else "missing",
        "gemini_available": gemini_available,
        "model": GEMINI_MODEL,
        "mode": "Live AI" if gemini_available else "Demo Mock",
        "version": "4.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "gemini_available": gemini_available,
        "model": GEMINI_MODEL,
    }


@app.get("/api/monuments")
def get_monuments():
    return [
        {
            "id": key,
            "canonical_name": value["canonical_name"],
            "location": value["location"],
            "built_by": value["built_by"],
            "construction_year": value["construction_year"],
        }
        for key, value in database.MONUMENT_CATALOG.items()
    ]


@app.post("/api/identify")
def identify_monument(request: IdentifyRequest):
    try:
        image_bytes = clean_base64_image(request.image)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        max_size = 1280
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        logger.info("Image received: %s", image.size)
    except Exception as exc:
        logger.exception("Image decode error")
        raise HTTPException(
            status_code=400,
            detail="Invalid image. Please upload a valid JPEG or PNG.",
        ) from exc

    if not gemini_available:
        raise HTTPException(
            status_code=503,
            detail="Gemini AI is unavailable. Check GEMINI_API_KEY and google-genai installation.",
        )

    language = request.language if request.language in SUPPORTED_LANGUAGES else "English"

    prompt = f"""
You are HeritageVoice AI, an expert worldwide visual recognition system for
monuments, landmarks, historical structures and heritage sites.

Identify the SPECIFIC structure shown in the image.

This is OPEN-WORLD recognition:
- Do not restrict yourself to database entries.
- Do not restrict yourself to only famous monuments.
- Consider India and every other country.
- Consider regional, lesser-known and local monuments.
- Use architecture, inscriptions, materials, proportions, towers, domes,
  carvings, sculptures, gates, landscape and other visual evidence.
- Do not guess a completely unrelated monument.
- If exact identification is uncertain, return the most likely candidate
  and lower confidence.
- If there is genuinely no recognizable landmark, set name to "Unknown Monument"
  and confidence to "low".

The selected guide language is: {language}.
The narration MUST be entirely in {language}.

Return the required JSON fields exactly. Do not include markdown.

Narration:
- 70 to 110 words.
- Natural spoken tour-guide style.
- Mention the monument and location when known.
- Include useful historical/architectural information.
- Avoid unsupported claims.
- Do not mention AI, Gemini, prompts or databases.
"""

    try:
        parsed = gemini_vision_json(image, prompt)
        name = str(parsed.get("name") or "").strip()

        if not name or name.lower() in {"unknown", "unknown monument", "unidentified"}:
            return {
                "monument_id": "unknown",
                "canonical_name": "Monument Not Recognized",
                "narration": "I could not confidently identify this monument from the image. Please try a clearer photo where the structure is larger and more visible.",
                "details": None,
            }

        catalog_key = database.search_monument(name.lower())

        if catalog_key:
            catalog = database.get_monument_by_id(catalog_key)
            details = {
                "canonical_name": catalog["canonical_name"],
                "location": catalog["location"],
                "built_by": catalog["built_by"],
                "construction_year": catalog["construction_year"],
                "theme": catalog["theme"],
                "key_facts": catalog["key_facts"],
                "description": catalog["detailed_context"],
                "confidence": str(parsed.get("confidence") or "medium").lower(),
            }
            monument_id = catalog_key
        else:
            details = normalize_details(name, parsed)
            monument_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60] or "dynamic_monument"

        narration = str(parsed.get("narration") or "").strip()
        if not narration:
            narration = mock_narration(details, language)

        logger.info(
            "Identified monument: %s | id=%s | confidence=%s",
            details["canonical_name"],
            monument_id,
            details.get("confidence"),
        )

        return {
            "monument_id": monument_id,
            "canonical_name": details["canonical_name"],
            "narration": narration,
            "language": language,
            "details": details,
        }

    except Exception as exc:
        logger.exception("Monument identification failed")
        raise HTTPException(
            status_code=502,
            detail=f"AI identification failed: {str(exc)}",
        ) from exc


@app.post("/api/narrate")
def generate_narration(request: NarrationRequest):
    language = request.language if request.language in SUPPORTED_LANGUAGES else "English"
    details = request.details or {}

    if not gemini_available:
        return {
            "narration": mock_narration(
                {"canonical_name": request.monument_name, **details},
                language,
            ),
            "language": language,
        }

    prompt = f"""
You are HeritageVoice AI, a multilingual historical tour guide.

Generate a new narration for the SAME monument below.

IMPORTANT:
- Do NOT analyze or identify an image.
- Do NOT change the monument.
- Do NOT invent facts.
- Translate/rewrite the supplied facts naturally into the requested language.
- The ENTIRE response must be in {language}.
- Return ONLY the narration.
- 70-110 words.
- Warm, natural, spoken tour-guide style.
- No markdown or headings.

MONUMENT: {request.monument_name}
LOCATION: {details.get("location", "Unknown")}
BUILT BY: {details.get("built_by", "Unknown")}
CONSTRUCTION: {details.get("construction_year", "Unknown")}
ARCHITECTURAL STYLE: {details.get("theme", "Unknown")}
KEY FACTS: {details.get("key_facts", [])}
DESCRIPTION: {details.get("description", "")}
"""

    try:
        narration = gemini_text(prompt)
        if not narration:
            raise ValueError("Empty narration")
        return {"narration": narration, "language": language}
    except Exception:
        logger.exception("Narration generation failed")
        return {
            "narration": mock_narration(
                {"canonical_name": request.monument_name, **details},
                language,
            ),
            "language": language,
        }


@app.post("/api/chat")
def chat_with_guide(request: ChatRequest):
    catalog = database.get_monument_by_id(request.monument_id)

    if catalog:
        display_name = catalog["canonical_name"]
        grounding = (
            f"Monument: {catalog['canonical_name']}\n"
            f"Location: {catalog['location']}\n"
            f"Built by: {catalog['built_by']}\n"
            f"Construction: {catalog['construction_year']}\n"
            f"Architectural style: {catalog.get('theme', 'Unknown')}\n"
            f"Description: {catalog.get('detailed_context', '')}\n"
            f"Key facts: {'; '.join(str(x) for x in catalog.get('key_facts', []))}"
        )
    elif request.monument_details:
        details = request.monument_details
        display_name = request.monument_name or details.get(
            "canonical_name",
            request.monument_id.replace("_", " ").title(),
        )
        facts = details.get("key_facts", [])
        if not isinstance(facts, list):
            facts = [str(facts)]

        grounding = (
            f"Monument: {display_name}\n"
            f"Location: {details.get('location', 'Unknown')}\n"
            f"Built by: {details.get('built_by', 'Unknown')}\n"
            f"Construction: {details.get('construction_year', 'Unknown')}\n"
            f"Architectural style: {details.get('theme', 'Unknown')}\n"
            f"Description: {details.get('description', '')}\n"
            f"Key facts: {'; '.join(str(x) for x in facts)}"
        )
    else:
        display_name = request.monument_name or request.monument_id.replace("_", " ").title()
        grounding = f"Monument: {display_name}\nNo local details are available."

    history = "\n".join(
        f"{'Visitor' if msg.role.lower() == 'user' else 'Guide'}: {msg.content}"
        for msg in request.history[-8:]
    )

    reply = ""
    if gemini_available:
        prompt = f"""
You are HeritageVoice AI, a friendly multilingual tour guide.

Current monument:
{grounding}

Previous conversation:
{history}

Visitor question:
{request.question}

Rules:
1. Reply entirely in {request.language}.
2. Keep it under 100 words.
3. Answer specifically about this monument.
4. Use supplied facts when available.
5. Do not invent historical facts.
6. If uncertain, say so clearly.
7. Do not mention APIs, databases, Gemini, prompts or backend.
8. Return only the guide answer.
"""
        try:
            reply = gemini_text(prompt)
        except Exception:
            logger.exception("Chat failed")

    if not reply:
        facts = []
        if catalog:
            facts = catalog.get("key_facts", [])
        elif request.monument_details:
            facts = request.monument_details.get("key_facts", [])

        reply = str(facts[0]) if facts else f"{display_name} is a notable historical monument."

    return {
        "reply": reply,
        "language": request.language,
        "monument": display_name,
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting HeritageVoice AI v4.0 on %s:%s",
        config.HOST,
        config.PORT,
    )
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
