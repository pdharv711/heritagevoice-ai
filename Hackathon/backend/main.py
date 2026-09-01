import base64
import json
import logging
import re
import wave
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image

import config
import database


# =============================================================================
# GOOGLE GEMINI SDK
# =============================================================================

try:
    from google import genai
    from google.genai import types as genai_types

    NEW_SDK = True
except ImportError:
    NEW_SDK = False


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="HeritageVoice AI API",
    description="Multilingual AI Tour Guide — Monument Recognition",
    version="5.0.0",
)


# =============================================================================
# CORS
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# GEMINI CONFIGURATION
# =============================================================================

# Current stable Gemini Flash model.
GEMINI_MODEL = "gemini-3.6-flash"

# Gemini TTS model.
GEMINI_TTS_MODEL = "gemini-3.1-flash-tts-preview"

gemini_client = None
gemini_available = False


if config.GEMINI_API_KEY and NEW_SDK:
    try:
        gemini_client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=genai_types.HttpOptions(
                timeout=30000
            ),
        )

        gemini_available = True

        logger.info(
            "Gemini client ready. Model=%s",
            GEMINI_MODEL,
        )

    except Exception:
        logger.exception("Gemini initialization failed")

elif not NEW_SDK:
    logger.error(
        "google-genai is not installed. "
        "Add google-genai to requirements.txt."
    )

else:
    logger.warning(
        "GEMINI_API_KEY is not configured. "
        "Backend will run without Gemini."
    )


# =============================================================================
# SUPPORTED LANGUAGES
# =============================================================================

SUPPORTED_LANGUAGES = [
    "English",
    "Hindi",
    "Tamil",
    "Telugu",
    "Bengali",
    "Marathi",
    "Gujarati",
    "Kannada",
    "Punjabi",
    "French",
    "Spanish",
    "German",
    "Arabic",
    "Japanese",
    "Korean",
    "Portuguese",
    "Russian",
    "Italian",
]


# =============================================================================
# LANGUAGE CODES
# =============================================================================

LANGUAGE_CODES = {
    "English": "en-US",
    "Hindi": "hi-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Bengali": "bn-IN",
    "Marathi": "mr-IN",
    "Gujarati": "gu-IN",
    "Kannada": "kn-IN",
    "Punjabi": "pa-IN",
    "French": "fr-FR",
    "Spanish": "es-ES",
    "German": "de-DE",
    "Arabic": "ar-SA",
    "Japanese": "ja-JP",
    "Korean": "ko-KR",
    "Portuguese": "pt-BR",
    "Russian": "ru-RU",
    "Italian": "it-IT",
}


# =============================================================================
# FALLBACK NARRATIONS
# =============================================================================

MOCK_NARRATIONS: Dict[str, str] = {

    "English":
        "Welcome to {name}! Located in {location}, "
        "this historical monument was built by {built_by} "
        "around {construction}. A key highlight is {key_fact}.",

    "Hindi":
        "{name} में आपका स्वागत है। यह ऐतिहासिक स्मारक "
        "{location} में स्थित है। इसे {built_by} द्वारा "
        "{construction} के आसपास बनाया गया था। "
        "इसकी एक प्रमुख विशेषता है: {key_fact}.",

    "Gujarati":
        "{name} માં આપનું સ્વાગત છે. આ ઐતિહાસિક સ્મારક "
        "{location} માં આવેલું છે. તેનું નિર્માણ {built_by} "
        "દ્વારા {construction} ની આસપાસ કરવામાં આવ્યું હતું. "
        "તેની એક મહત્વપૂર્ણ વિશેષતા છે: {key_fact}.",

    "Tamil":
        "{name}-க்கு வரவேற்கிறோம். இந்த வரலாற்றுச் சின்னம் "
        "{location}-ல் அமைந்துள்ளது. இது {built_by} அவர்களால் "
        "{construction} காலத்தில் கட்டப்பட்டது. "
        "இதன் முக்கிய அம்சம்: {key_fact}.",

    "Telugu":
        "{name} కు స్వాగతం. ఈ చారిత్రక కట్టడం "
        "{location}లో ఉంది. దీనిని {built_by} వారు "
        "{construction} కాలంలో నిర్మించారు. "
        "ముఖ్యమైన విషయం: {key_fact}.",

    "Bengali":
        "{name}-এ আপনাকে স্বাগত। এই ঐতিহাসিক স্থাপনাটি "
        "{location}-এ অবস্থিত। এটি {built_by} দ্বারা "
        "{construction} সময়ে নির্মিত হয়েছিল। "
        "গুরুত্বপূর্ণ তথ্য হলো: {key_fact}.",

    "Marathi":
        "{name} मध्ये आपले स्वागत आहे. हे ऐतिहासिक स्मारक "
        "{location} येथे आहे. हे {built_by} यांनी "
        "{construction} च्या सुमारास बांधले. "
        "महत्त्वाची माहिती: {key_fact}.",

    "Kannada":
        "{name} ಗೆ ಸ್ವಾಗತ. ಈ ಐತಿಹಾಸಿಕ ಸ್ಮಾರಕವು "
        "{location} ನಲ್ಲಿ ಇದೆ. ಇದನ್ನು {built_by} ಅವರು "
        "{construction} ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು. "
        "ಪ್ರಮುಖ ಮಾಹಿತಿ: {key_fact}.",

    "Punjabi":
        "{name} ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ। ਇਹ ਇਤਿਹਾਸਕ ਸਮਾਰਕ "
        "{location} ਵਿੱਚ ਸਥਿਤ ਹੈ। ਇਸਨੂੰ {built_by} ਦੁਆਰਾ "
        "{construction} ਦੇ ਆਸ-ਪਾਸ ਬਣਾਇਆ ਗਿਆ ਸੀ। "
        "ਮੁੱਖ ਤੱਥ: {key_fact}.",

    "French":
        "Bienvenue à {name}! Situé à {location}, "
        "ce monument historique a été construit par "
        "{built_by} vers {construction}. "
        "Un fait important est : {key_fact}.",

    "Spanish":
        "¡Bienvenido a {name}! Situado en {location}, "
        "este monumento histórico fue construido por "
        "{built_by} alrededor de {construction}. "
        "Un dato importante es: {key_fact}.",

    "German":
        "Willkommen bei {name}! Dieses historische Monument "
        "befindet sich in {location} und wurde von "
        "{built_by} um {construction} errichtet. "
        "Eine wichtige Tatsache ist: {key_fact}.",

    "Arabic":
        "مرحباً بكم في {name}! يقع هذا المعلم التاريخي في "
        "{location} وقد بناه {built_by} حوالي {construction}. "
        "ومن أهم الحقائق عنه: {key_fact}.",

    "Japanese":
        "{name}へようこそ。この歴史的建造物は{location}にあり、"
        "{built_by}によって{construction}頃に建設されました。"
        "重要な特徴は{key_fact}です。",

    "Korean":
        "{name}에 오신 것을 환영합니다. 이 역사적인 기념물은 "
        "{location}에 있으며 {built_by}가 {construction}경에 "
        "건설했습니다. 중요한 사실은 {key_fact}입니다.",

    "Portuguese":
        "Bem-vindo a {name}! Localizado em {location}, "
        "este monumento histórico foi construído por "
        "{built_by} por volta de {construction}. "
        "Um fato importante é: {key_fact}.",

    "Russian":
        "Добро пожаловать в {name}! Этот исторический памятник "
        "находится в {location} и был построен {built_by} "
        "примерно в {construction}. Важный факт: {key_fact}.",

    "Italian":
        "Benvenuti a {name}! Situato a {location}, "
        "questo monumento storico fu costruito da "
        "{built_by} intorno a {construction}. "
        "Un fatto importante è: {key_fact}.",
}


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class IdentifyRequest(BaseModel):
    image: str = Field(
        ...,
        description="Base64 encoded image or data URI",
    )

    language: str = Field(
        "English",
        description="Requested narration language",
    )


class NarrationRequest(BaseModel):
    monument_name: str

    language: str = Field(
        "English"
    )

    details: Dict[str, Any] = Field(
        default_factory=dict
    )


class TTSRequest(BaseModel):
    text: str

    language: str = Field(
        "English"
    )


class ChatMessage(BaseModel):
    role: str = Field(
        "user"
    )

    content: str


class ChatRequest(BaseModel):
    monument_id: str

    monument_name: Optional[str] = None

    monument_details: Optional[Dict[str, Any]] = None

    question: str

    language: str = Field(
        "English"
    )

    history: List[ChatMessage] = Field(
        default_factory=list
    )


# =============================================================================
# GEMINI STRUCTURED OUTPUT SCHEMA
# =============================================================================

IDENTIFICATION_SCHEMA = {
    "type": "object",

    "properties": {

        "name": {
            "type": "string"
        },

        "location": {
            "type": "string"
        },

        "built_by": {
            "type": "string"
        },

        "year": {
            "type": "string"
        },

        "architectural_style": {
            "type": "string"
        },

        "key_facts": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },

        "description": {
            "type": "string"
        },

        "confidence": {
            "type": "string",
            "enum": [
                "high",
                "medium",
                "low"
            ]
        },

        "narration": {
            "type": "string"
        },
    },

    "required": [
        "name",
        "location",
        "built_by",
        "year",
        "architectural_style",
        "key_facts",
        "description",
        "confidence",
        "narration",
    ],
}


# =============================================================================
# HELPERS
# =============================================================================

def normalize_language(language: str) -> str:
    """
    Make sure only supported languages are used.
    """

    if language in SUPPORTED_LANGUAGES:
        return language

    return "English"


def clean_base64_image(value: str) -> bytes:
    """
    Decode Base64 image data.
    Supports:
      data:image/jpeg;base64,...
      data:image/png;base64,...
      raw Base64
    """

    if not value:
        raise ValueError("Empty image")

    value = value.strip()

    if "," in value:
        value = value.split(",", 1)[1]

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    value += "=" * (
        -len(value) % 4
    )

    try:
        return base64.b64decode(
            value,
            validate=False,
        )

    except Exception as exc:

        raise ValueError(
            "Invalid Base64 image"
        ) from exc


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely extract JSON from Gemini response.
    """

    if not text:
        return None

    text = text.strip()

    # Direct JSON
    try:

        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except Exception:
        pass

    # Markdown JSON
    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:

        try:

            result = json.loads(
                match.group(1)
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    # First { to last }
    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:

        try:

            result = json.loads(
                text[start:end + 1]
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    return None


def gemini_text(prompt: str) -> str:

    if not gemini_client:

        raise RuntimeError(
            "Gemini client unavailable"
        )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return (
        response.text or ""
    ).strip()


def gemini_vision_json(
    image: Image.Image,
    prompt: str,
) -> Dict[str, Any]:

    if not gemini_client:

        raise RuntimeError(
            "Gemini client unavailable"
        )

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=88,
        optimize=True,
    )

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
                    genai_types.Part.from_text(
                        text=prompt
                    ),
                ],
            )
        ],

        config=genai_types.GenerateContentConfig(

            response_mime_type="application/json",

            response_schema=IDENTIFICATION_SCHEMA,
        ),
    )

    parsed = extract_json(
        response.text or ""
    )

    if not parsed:

        raise ValueError(
            "Gemini returned invalid identification JSON"
        )

    return parsed


def mock_narration(
    info: Dict[str, Any],
    language: str,
) -> str:

    language = normalize_language(
        language
    )

    template = MOCK_NARRATIONS.get(
        language,
        MOCK_NARRATIONS["English"],
    )

    facts = info.get(
        "key_facts"
    ) or [
        "a remarkable historical site."
    ]

    if not isinstance(
        facts,
        list,
    ):

        facts = [
            str(facts)
        ]

    return template.format(

        name=(
            info.get("canonical_name")
            or info.get("name")
            or "this monument"
        ),

        location=(
            info.get("location")
            or "an unknown location"
        ),

        built_by=(
            info.get("built_by")
            or "unknown builders"
        ),

        construction=(
            info.get("construction_year")
            or info.get("year")
            or "an unknown period"
        ),

        key_fact=str(
            facts[0]
        ),
    )


def normalize_details(
    name: str,
    parsed: Dict[str, Any],
) -> Dict[str, Any]:

    facts = (
        parsed.get("key_facts")
        or []
    )

    if not isinstance(
        facts,
        list,
    ):

        facts = [
            str(facts)
        ]

    return {

        "canonical_name":
            name,

        "location":
            str(
                parsed.get("location")
                or "Unknown"
            ),

        "built_by":
            str(
                parsed.get("built_by")
                or "Unknown"
            ),

        "construction_year":
            str(
                parsed.get("year")
                or "Unknown"
            ),

        "theme":
            str(
                parsed.get("architectural_style")
                or "Unknown"
            ),

        "key_facts":
            [
                str(x)
                for x in facts[:8]
            ],

        "description":
            str(
                parsed.get("description")
                or ""
            ),

        "confidence":
            str(
                parsed.get("confidence")
                or "medium"
            ).lower(),
    }


# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
def root():

    return {

        "status": "online",

        "service":
            "HeritageVoice AI",

        "gemini_available":
            gemini_available,

        "vision_model":
            GEMINI_MODEL,

        "tts_model":
            GEMINI_TTS_MODEL,

        "version":
            "5.0.0",
    }


# =============================================================================
# HEALTH
# =============================================================================

@app.get("/health")
def health():

    return {

        "status": "healthy",

        "gemini_available":
            gemini_available,

        "model":
            GEMINI_MODEL,
    }


# =============================================================================
# MONUMENT LIST
# =============================================================================

@app.get("/api/monuments")
def get_monuments():

    return [

        {
            "id": key,

            "canonical_name":
                value.get(
                    "canonical_name",
                    key.replace(
                        "_",
                        " "
                    ).title(),
                ),

            "location":
                value.get(
                    "location",
                    "Unknown",
                ),

            "built_by":
                value.get(
                    "built_by",
                    "Unknown",
                ),

            "construction_year":
                value.get(
                    "construction_year",
                    "Unknown",
                ),
        }

        for key, value
        in database.MONUMENT_CATALOG.items()
    ]


# =============================================================================
# IDENTIFY MONUMENT
# =============================================================================

@app.post("/api/identify")
def identify_monument(
    request: IdentifyRequest,
):

    language = normalize_language(
        request.language
    )

    # -------------------------------------------------------------------------
    # Decode image
    # -------------------------------------------------------------------------

    try:

        image_bytes = clean_base64_image(
            request.image
        )

        image = Image.open(
            BytesIO(image_bytes)
        ).convert("RGB")

        max_size = 1280

        if max(image.size) > max_size:

            image.thumbnail(
                (
                    max_size,
                    max_size,
                ),
                Image.Resampling.LANCZOS,
            )

        logger.info(
            "Image received: %s | language=%s",
            image.size,
            language,
        )

    except Exception as exc:

        logger.exception(
            "Image decode failed"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid image. "
                "Please upload a valid JPEG or PNG."
            ),
        ) from exc

    # -------------------------------------------------------------------------
    # Gemini availability
    # -------------------------------------------------------------------------

    if not gemini_available:

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini AI is unavailable. "
                "Check GEMINI_API_KEY and google-genai."
            ),
        )

    # -------------------------------------------------------------------------
    # Vision prompt
    # -------------------------------------------------------------------------

    prompt = f"""
You are HeritageVoice AI, an expert monument recognition
and historical tour-guide system.

Analyze the supplied image carefully.

IDENTIFICATION:
Identify the specific monument, landmark, fort, palace,
temple, mosque, cave, memorial, tower, gate, stepwell,
archaeological site or other heritage structure.

OPEN-WORLD RECOGNITION:
- Consider India and other countries.
- Consider famous and lesser-known monuments.
- Use architecture, materials, carvings, domes, towers,
  proportions, landscape and visual evidence.
- Do not invent an unrelated monument.
- If uncertain, give the most likely monument with low
  or medium confidence.
- If there is genuinely no recognizable monument,
  return "Unknown Monument".

DATABASE GROUNDING:
If the identified monument is a known Indian monument,
use historically accurate information.
Do not invent dates, builders or facts.

LANGUAGE:
The selected guide language is:

{language}

The narration MUST be entirely in {language}.

IMPORTANT FOR INDIAN LANGUAGES:
Write the narration using the correct native script.

Hindi -> Devanagari
Gujarati -> Gujarati script
Tamil -> Tamil script
Telugu -> Telugu script
Bengali -> Bengali script
Marathi -> Devanagari
Kannada -> Kannada script
Punjabi -> Gurmukhi

Do NOT write Indian-language narration using English
transliteration.

NARRATION:
- 70 to 110 words.
- Natural spoken tour-guide style.
- Mention monument and location.
- Include useful historical/architectural information.
- Use database facts when available.
- Avoid unsupported claims.
- Do not mention AI, Gemini, prompts or databases.

Return ONLY the required JSON structure.
"""

    # -------------------------------------------------------------------------
    # Gemini Vision
    # -------------------------------------------------------------------------

    try:

        parsed = gemini_vision_json(
            image,
            prompt,
        )

    except Exception as exc:

        logger.exception(
            "Gemini vision failed"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "AI identification failed. "
                f"{str(exc)}"
            ),
        ) from exc

    # -------------------------------------------------------------------------
    # Extract name
    # -------------------------------------------------------------------------

    name = str(
        parsed.get("name")
        or ""
    ).strip()

    if (
        not name
        or name.lower()
        in {
            "unknown",
            "unknown monument",
            "unidentified",
        }
    ):

        return {

            "monument_id":
                "unknown",

            "canonical_name":
                "Monument Not Recognized",

            "narration":
                "I could not confidently identify this monument from the image. Please try a clearer photo where the structure is larger and more visible.",

            "language":
                language,

            "details":
                None,
        }

    # -------------------------------------------------------------------------
    # Match database
    # -------------------------------------------------------------------------

    catalog_key = database.search_monument(
        name
    )

    if catalog_key:

        catalog = database.get_monument_by_id(
            catalog_key
        )

        if not catalog:

            catalog_key = None

    # -------------------------------------------------------------------------
    # Database monument
    # -------------------------------------------------------------------------

    if catalog_key:

        details = {

            "canonical_name":
                catalog.get(
                    "canonical_name",
                    name,
                ),

            "location":
                catalog.get(
                    "location",
                    "Unknown",
                ),

            "built_by":
                catalog.get(
                    "built_by",
                    "Unknown",
                ),

            "construction_year":
                catalog.get(
                    "construction_year",
                    "Unknown",
                ),

            "theme":
                catalog.get(
                    "theme",
                    "Unknown",
                ),

            "key_facts":
                catalog.get(
                    "key_facts",
                    [],
                ),

            "description":
                catalog.get(
                    "detailed_context",
                    "",
                ),

            "confidence":
                str(
                    parsed.get(
                        "confidence",
                        "medium",
                    )
                ).lower(),
        }

        monument_id = catalog_key

    # -------------------------------------------------------------------------
    # Gemini-only monument
    # -------------------------------------------------------------------------

    else:

        details = normalize_details(
            name,
            parsed,
        )

        monument_id = re.sub(
            r"[^a-z0-9]+",
            "_",
            name.lower(),
        ).strip("_")[:60]

        if not monument_id:

            monument_id = "dynamic_monument"

    # -------------------------------------------------------------------------
    # Narration
    # -------------------------------------------------------------------------

    narration = str(
        parsed.get("narration")
        or ""
    ).strip()

    if not narration:

        narration = mock_narration(
            details,
            language,
        )

    logger.info(
        "Identified monument=%s | id=%s | language=%s",
        details["canonical_name"],
        monument_id,
        language,
    )

    return {

        "monument_id":
            monument_id,

        "canonical_name":
            details["canonical_name"],

        "narration":
            narration,

        "language":
            language,

        "language_code":
            LANGUAGE_CODES.get(
                language,
                "en-US",
            ),

        "details":
            details,
    }


# =============================================================================
# GENERATE NARRATION
# =============================================================================

@app.post("/api/narrate")
def generate_narration(
    request: NarrationRequest,
):

    language = normalize_language(
        request.language
    )

    details = request.details or {}

    if not gemini_available:

        return {

            "narration":
                mock_narration(
                    {
                        "canonical_name":
                            request.monument_name,
                        **details,
                    },
                    language,
                ),

            "language":
                language,

            "language_code":
                LANGUAGE_CODES.get(
                    language,
                    "en-US",
                ),
        }

    prompt = f"""
You are HeritageVoice AI, a multilingual historical
tour guide.

Generate a natural spoken narration for this monument.

MONUMENT:
{request.monument_name}

LOCATION:
{details.get("location", "Unknown")}

BUILT BY:
{details.get("built_by", "Unknown")}

CONSTRUCTION:
{details.get("construction_year", "Unknown")}

ARCHITECTURAL STYLE:
{details.get("theme", "Unknown")}

KEY FACTS:
{details.get("key_facts", [])}

DESCRIPTION:
{details.get("description", "")}

TARGET LANGUAGE:
{language}

IMPORTANT:
- Entire response MUST be in {language}.
- Use the correct native script.
- Do not use transliteration for Indian languages.
- Do not change the monument.
- Do not invent facts.
- 70-110 words.
- Natural tour-guide style.
- Return ONLY narration.
"""

    try:

        narration = gemini_text(
            prompt
        )

        if not narration:

            raise ValueError(
                "Empty narration"
            )

        return {

            "narration":
                narration,

            "language":
                language,

            "language_code":
                LANGUAGE_CODES.get(
                    language,
                    "en-US",
                ),
        }

    except Exception:

        logger.exception(
            "Narration generation failed"
        )

        return {

            "narration":
                mock_narration(
                    {
                        "canonical_name":
                            request.monument_name,
                        **details,
                    },
                    language,
                ),

            "language":
                language,

            "language_code":
                LANGUAGE_CODES.get(
                    language,
                    "en-US",
                ),
        }


# =============================================================================
# GEMINI TTS
# =============================================================================

@app.post("/api/tts")
def generate_tts(
    request: TTSRequest,
):

    language = normalize_language(
        request.language
    )

    text = (
        request.text
        or ""
    ).strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="TTS text cannot be empty.",
        )

    if not gemini_available:

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini TTS is unavailable."
            ),
        )

    language_code = LANGUAGE_CODES.get(
        language,
        "en-US",
    )

    logger.info(
        "Generating TTS | language=%s | code=%s",
        language,
        language_code,
    )

    # Explicitly tell Gemini which language to speak.
    tts_prompt = f"""
Speak the following tour-guide narration naturally.

LANGUAGE:
{language}

LANGUAGE CODE:
{language_code}

IMPORTANT:
- Speak ONLY in {language}.
- For Indian languages, pronounce the native script
  naturally.
- Do not translate the text into English.
- Do not read the language instructions aloud.
- Use a clear, friendly museum-tour-guide voice.

TEXT:
{text}
"""

    try:
        # Gemini 3.1 Flash TTS is officially supported through
        # the Interactions API. It returns raw PCM audio in
        # interaction.output_audio.data.
        interaction = gemini_client.interactions.create(
            model=GEMINI_TTS_MODEL,
            input=tts_prompt,
            response_format={
                "type": "audio"
            },
            generation_config={
                "speech_config": [
                    {
                        "voice": "Kore"
                    }
                ]
            },
        )

        output_audio = getattr(
            interaction,
            "output_audio",
            None,
        )

        audio_data = getattr(
            output_audio,
            "data",
            None,
        )

        if not audio_data:
            raise RuntimeError(
                "Gemini returned no output_audio data"
            )

        if isinstance(audio_data, str):
            audio_data = base64.b64decode(
                audio_data
            )
        elif not isinstance(audio_data, bytes):
            audio_data = bytes(audio_data)

        if not audio_data:
            raise RuntimeError(
                "Gemini returned empty audio data"
            )

        logger.info(
            "Gemini TTS generated %s bytes of PCM audio",
            len(audio_data),
        )

        # ---------------------------------------------------------------------
        # Convert PCM audio to WAV
        # ---------------------------------------------------------------------
        wav_buffer = BytesIO()
        with wave.open(
            wav_buffer,
            "wb",
        ) as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(audio_data)

        wav_bytes = wav_buffer.getvalue()
        encoded_audio = base64.b64encode(
            wav_bytes
        ).decode("utf-8")

        return {
            "success": True,
            "language": language,
            "language_code": language_code,
            "mime_type": "audio/wav",
            "sample_rate": 24000,
            "audio_base64": encoded_audio,
        }

    except Exception as exc:

        logger.exception(
            "Gemini TTS failed"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "TTS generation failed: "
                f"{str(exc)}"
            ),
        ) from exc


# =============================================================================
# CHAT
# =============================================================================

@app.post("/api/chat")
def chat_with_guide(
    request: ChatRequest,
):

    language = normalize_language(
        request.language
    )

    catalog = database.get_monument_by_id(
        request.monument_id
    )

    # -------------------------------------------------------------------------
    # Database monument
    # -------------------------------------------------------------------------

    if catalog:

        display_name = catalog.get(
            "canonical_name",
            request.monument_id,
        )

        grounding = (
            f"Monument: "
            f"{catalog.get('canonical_name', display_name)}\n"

            f"Location: "
            f"{catalog.get('location', 'Unknown')}\n"

            f"Built by: "
            f"{catalog.get('built_by', 'Unknown')}\n"

            f"Construction: "
            f"{catalog.get('construction_year', 'Unknown')}\n"

            f"Architectural style: "
            f"{catalog.get('theme', 'Unknown')}\n"

            f"Description: "
            f"{catalog.get('detailed_context', '')}\n"

            f"Key facts: "
            f"{'; '.join(str(x) for x in catalog.get('key_facts', []))}"
        )

    # -------------------------------------------------------------------------
    # Gemini-only monument
    # -------------------------------------------------------------------------

    elif request.monument_details:

        details = request.monument_details

        display_name = (
            request.monument_name
            or details.get(
                "canonical_name",
                request.monument_id.replace(
                    "_",
                    " "
                ).title(),
            )
        )

        facts = details.get(
            "key_facts",
            [],
        )

        if not isinstance(
            facts,
            list,
        ):

            facts = [
                str(facts)
            ]

        grounding = (
            f"Monument: {display_name}\n"

            f"Location: "
            f"{details.get('location', 'Unknown')}\n"

            f"Built by: "
            f"{details.get('built_by', 'Unknown')}\n"

            f"Construction: "
            f"{details.get('construction_year', 'Unknown')}\n"

            f"Architectural style: "
            f"{details.get('theme', 'Unknown')}\n"

            f"Description: "
            f"{details.get('description', '')}\n"

            f"Key facts: "
            f"{'; '.join(str(x) for x in facts)}"
        )

    else:

        display_name = (
            request.monument_name
            or request.monument_id.replace(
                "_",
                " "
            ).title()
        )

        grounding = (
            f"Monument: {display_name}\n"
            "No local details are available."
        )

    # -------------------------------------------------------------------------
    # Conversation history
    # -------------------------------------------------------------------------

    history = "\n".join(

        f"{'Visitor' if msg.role.lower() == 'user' else 'Guide'}: "
        f"{msg.content}"

        for msg in request.history[-8:]
    )

    reply = ""

    # -------------------------------------------------------------------------
    # Gemini chat
    # -------------------------------------------------------------------------

    if gemini_available:

        prompt = f"""
You are HeritageVoice AI, a friendly multilingual
tour guide.

CURRENT MONUMENT:
{grounding}

PREVIOUS CONVERSATION:
{history}

VISITOR QUESTION:
{request.question}

TARGET LANGUAGE:
{language}

RULES:
1. Reply entirely in {language}.
2. Use the correct native script.
3. For Indian languages, never use English transliteration.
4. Keep the answer under 100 words.
5. Answer specifically about this monument.
6. Use supplied facts when available.
7. Do not invent historical facts.
8. If uncertain, say so clearly.
9. Do not mention APIs, databases, Gemini,
   prompts or backend.
10. Return only the guide answer.
"""

        try:

            reply = gemini_text(
                prompt
            )

        except Exception:

            logger.exception(
                "Chat generation failed"
            )

    # -------------------------------------------------------------------------
    # Fallback
    # -------------------------------------------------------------------------

    if not reply:

        facts = []

        if catalog:

            facts = catalog.get(
                "key_facts",
                [],
            )

        elif request.monument_details:

            facts = request.monument_details.get(
                "key_facts",
                [],
            )

        if facts:

            reply = str(
                facts[0]
            )

        else:

            reply = (
                f"{display_name} is a notable "
                "historical monument."
            )

    return {

        "reply":
            reply,

        "language":
            language,

        "language_code":
            LANGUAGE_CODES.get(
                language,
                "en-US",
            ),

        "monument":
            display_name,
    }


# =============================================================================
# START SERVER
# =============================================================================

if __name__ == "__main__":

    import uvicorn

    logger.info(
        "Starting HeritageVoice AI v5.0"
    )

    logger.info(
        "Host: %s",
        config.HOST,
    )

    logger.info(
        "Port: %s",
        config.PORT,
    )

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
