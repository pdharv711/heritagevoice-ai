import base64
import json
import logging
import os
import re
from io import BytesIO
from typing import List, Dict, Any, Optional

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

logger = logging.getLogger("heritagevoice")


# =============================================================================
# FASTAPI
# =============================================================================

app = FastAPI(
    title="HeritageVoice AI API",
    description="Multilingual AI-powered Tour Guide",
    version="4.0.0",
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

gemini_client = None
gemini_available = False

# Current Gemini Flash model.
# Can be overridden using Render environment variable GEMINI_MODEL.
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash",
)


if config.GEMINI_API_KEY and NEW_SDK:

    try:

        gemini_client = genai.Client(
            api_key=config.GEMINI_API_KEY
        )

        gemini_available = True

        logger.info(
            "Gemini client initialized successfully. "
            f"Model: {GEMINI_MODEL}"
        )

    except Exception as e:

        logger.exception(
            f"Gemini initialization failed: {e}"
        )

else:

    if not NEW_SDK:

        logger.error(
            "google-genai package is not installed."
        )

    if not config.GEMINI_API_KEY:

        logger.warning(
            "GEMINI_API_KEY is missing."
        )


# =============================================================================
# SUPPORTED LANGUAGES
# =============================================================================

SUPPORTED_LANGUAGES = {
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
}


def normalize_language(language: str) -> str:
    """
    Normalize the language selected by the frontend.
    """

    if not language:
        return "English"

    language = str(language).strip()

    for supported in SUPPORTED_LANGUAGES:

        if supported.lower() == language.lower():
            return supported

    logger.warning(
        f"Unsupported language '{language}'. "
        "Falling back to English."
    )

    return "English"


# =============================================================================
# LANGUAGE INSTRUCTIONS
# =============================================================================

LANGUAGE_NATIVE_NAMES = {
    "English": "English",
    "Hindi": "Hindi (हिन्दी)",
    "Tamil": "Tamil (தமிழ்)",
    "Telugu": "Telugu (తెలుగు)",
    "Bengali": "Bengali (বাংলা)",
    "Marathi": "Marathi (मराठी)",
    "Gujarati": "Gujarati (ગુજરાતી)",
    "Kannada": "Kannada (ಕನ್ನಡ)",
    "Punjabi": "Punjabi (ਪੰਜਾਬੀ)",
    "French": "French (Français)",
    "Spanish": "Spanish (Español)",
    "German": "German (Deutsch)",
    "Arabic": "Arabic (العربية)",
    "Japanese": "Japanese (日本語)",
    "Korean": "Korean (한국어)",
    "Portuguese": "Portuguese (Português)",
    "Russian": "Russian (Русский)",
    "Italian": "Italian (Italiano)",
}


def language_instruction(language: str) -> str:
    """
    Strong language instruction used in every Gemini request.
    """

    language = normalize_language(language)

    native_name = LANGUAGE_NATIVE_NAMES.get(
        language,
        language,
    )

    return f"""
LANGUAGE REQUIREMENT - VERY IMPORTANT

The visitor selected: {native_name}

Your response MUST be written entirely in {language}.

Do NOT answer in English unless the selected language is English.

Do NOT translate only part of the answer.

Do NOT mix English sentences into the response.

Proper names of monuments, people and places may remain in
their internationally recognized form when necessary, but all
explanatory sentences MUST be in {language}.

Selected language: {language}
"""


# =============================================================================
# PYDANTIC REQUEST MODELS
# =============================================================================

class IdentifyRequest(BaseModel):

    image: str = Field(
        ...,
        description="Base64 encoded image or data URI",
    )

    language: str = Field(
        default="English",
        description="Language for AI narration",
    )


class ChatMessage(BaseModel):

    role: str = Field(
        default="user"
    )

    content: str = Field(
        ...
    )


class ChatRequest(BaseModel):

    monument_id: str

    question: str

    language: str = Field(
        default="English"
    )

    history: List[ChatMessage] = Field(
        default_factory=list
    )

    details: Optional[Dict[str, Any]] = None


class NarrationRequest(BaseModel):

    monument_name: str

    language: str = Field(
        default="English"
    )

    details: Dict[str, Any]


# =============================================================================
# MOCK NARRATION
# =============================================================================

MOCK_NARRATIONS = {

    "English":
        "Welcome to {name}! Located in {location}, "
        "this historic monument was built by {built_by} "
        "around {construction}. One important fact is: {key_fact}",

    "Hindi":
        "{name} में आपका स्वागत है! यह ऐतिहासिक स्मारक "
        "{location} में स्थित है। इसे {built_by} ने "
        "{construction} के आसपास बनवाया था। "
        "एक महत्वपूर्ण तथ्य है: {key_fact}",

    "Gujarati":
        "{name} માં આપનું સ્વાગત છે! આ ઐતિહાસિક સ્મારક "
        "{location} માં આવેલું છે. તેને {built_by} એ "
        "{construction} દરમિયાન બનાવ્યું હતું. "
        "મહત્વપૂર્ણ માહિતી: {key_fact}",

    "Marathi":
        "{name} मध्ये आपले स्वागत आहे! हे ऐतिहासिक स्मारक "
        "{location} येथे आहे. हे {built_by} यांनी "
        "{construction} च्या सुमारास बांधले. "
        "महत्त्वाची माहिती: {key_fact}",

    "Tamil":
        "{name}-க்கு வரவேற்கிறோம்! இந்த வரலாற்றுச் சின்னம் "
        "{location}-ல் அமைந்துள்ளது. இதை {built_by} "
        "{construction} காலப்பகுதியில் கட்டினார். "
        "முக்கியமான தகவல்: {key_fact}",

    "Telugu":
        "{name} కు స్వాగతం! ఈ చారిత్రక కట్టడం "
        "{location}లో ఉంది. దీనిని {built_by} "
        "{construction} కాలంలో నిర్మించారు. "
        "ముఖ్యమైన విషయం: {key_fact}",

    "Bengali":
        "{name}-এ স্বাগতম! এই ঐতিহাসিক স্থাপনাটি "
        "{location}-এ অবস্থিত। এটি {built_by} "
        "{construction} সময়ে নির্মাণ করেছিলেন। "
        "গুরুত্বপূর্ণ তথ্য: {key_fact}",

    "Kannada":
        "{name} ಗೆ ಸ್ವಾಗತ! ಈ ಐತಿಹಾಸಿಕ ಸ್ಮಾರಕವು "
        "{location} ನಲ್ಲಿ ಇದೆ. ಇದನ್ನು {built_by} "
        "{construction} ರಲ್ಲಿ ನಿರ್ಮಿಸಿದರು. "
        "ಪ್ರಮುಖ ಮಾಹಿತಿ: {key_fact}",

    "Punjabi":
        "{name} ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ! ਇਹ ਇਤਿਹਾਸਕ ਸਮਾਰਕ "
        "{location} ਵਿੱਚ ਸਥਿਤ ਹੈ। ਇਸਨੂੰ {built_by} "
        "{construction} ਦੇ ਆਸ-ਪਾਸ ਬਣਾਇਆ ਸੀ। "
        "ਮਹੱਤਵਪੂਰਨ ਤੱਥ: {key_fact}",

    "French":
        "Bienvenue à {name} ! Ce monument historique se trouve "
        "à {location}. Il a été construit par {built_by} "
        "vers {construction}. Fait important : {key_fact}",

    "Spanish":
        "¡Bienvenido à {name}! Este monumento histórico está "
        "en {location}. Fue construido por {built_by} "
        "alrededor de {construction}. Dato importante: {key_fact}",

    "German":
        "Willkommen bei {name}! Dieses historische Monument "
        "befindet sich in {location}. Es wurde von {built_by} "
        "um {construction} erbaut. Eine wichtige Tatsache: {key_fact}",

    "Arabic":
        "مرحباً بكم في {name}! يقع هذا النصب التاريخي "
        "في {location}. بناه {built_by} حوالي {construction}. "
        "ومن الحقائق المهمة: {key_fact}",

    "Japanese":
        "{name}へようこそ！この歴史的な建造物は"
        "{location}にあります。{built_by}によって"
        "{construction}頃に建設されました。"
        "重要な情報：{key_fact}",

    "Korean":
        "{name}에 오신 것을 환영합니다! 이 역사적인 기념물은 "
        "{location}에 있습니다. {built_by}가 "
        "{construction} 무렵에 건설했습니다. "
        "중요한 사실: {key_fact}",

    "Portuguese":
        "Bem-vindo a {name}! Este monumento histórico está "
        "localizado em {location}. Foi construído por {built_by} "
        "por volta de {construction}. Fato importante: {key_fact}",

    "Russian":
        "Добро пожаловать в {name}! Этот исторический памятник "
        "находится в {location}. Он был построен {built_by} "
        "примерно в {construction}. Важный факт: {key_fact}",

    "Italian":
        "Benvenuti a {name}! Questo monumento storico si trova "
        "a {location}. Fu costruito da {built_by} "
        "intorno al {construction}. Un fatto importante: {key_fact}",
}


# =============================================================================
# IMAGE HELPERS
# =============================================================================

def clean_base64_image(b64: str) -> bytes:
    """
    Convert data URI or raw base64 to bytes.
    """

    if not b64:
        raise ValueError("Image data is empty.")

    if "," in b64:

        b64 = b64.split(
            ",",
            1
        )[1]

    b64 = b64.strip()

    b64 = re.sub(
        r"\s+",
        "",
        b64
    )

    b64 += "=" * (-len(b64) % 4)

    try:

        return base64.b64decode(
            b64,
            validate=False
        )

    except Exception as e:

        raise ValueError(
            f"Invalid base64 image: {e}"
        )


# =============================================================================
# JSON HELPER
# =============================================================================

def extract_json(text: str) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    text = text.strip()

    try:

        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except Exception:
        pass

    match = re.search(
        r"```json\s*(.*?)\s*```",
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

    match = re.search(
        r"```\s*(.*?)\s*```",
        text,
        re.DOTALL,
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

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:

        try:

            result = json.loads(
                text[start:end + 1]
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    return None


# =============================================================================
# MONUMENT ID
# =============================================================================

def make_dynamic_monument_id(name: str) -> str:

    monument_id = re.sub(
        r"[^a-z0-9]+",
        "_",
        name.lower(),
    ).strip("_")

    return monument_id[:60] or "unknown_monument"


# =============================================================================
# MOCK NARRATION
# =============================================================================

def mock_narration(
    info: Dict[str, Any],
    language: str,
) -> str:

    language = normalize_language(language)

    template = MOCK_NARRATIONS.get(
        language,
        MOCK_NARRATIONS["English"],
    )

    facts = info.get(
        "key_facts",
        [],
    )

    if not isinstance(facts, list):
        facts = [str(facts)]

    fact = (
        str(facts[0])
        if facts
        else "This is an important historical heritage site."
    )

    try:

        return template.format(

            name=info.get(
                "canonical_name",
                info.get(
                    "name",
                    "this monument",
                ),
            ),

            location=info.get(
                "location",
                "an unknown location",
            ),

            built_by=info.get(
                "built_by",
                "unknown builders",
            ),

            construction=info.get(
                "construction_year",
                info.get(
                    "year",
                    "an unknown period",
                ),
            ),

            key_fact=fact,
        )

    except Exception:

        return (
            f"Welcome to "
            f"{info.get('canonical_name', 'this monument')}."
        )


# =============================================================================
# GEMINI HELPERS
# =============================================================================

def ensure_gemini_available():

    if not NEW_SDK:

        raise RuntimeError(
            "google-genai package is not installed."
        )

    if not gemini_client:

        raise RuntimeError(
            "Gemini client is not initialized. "
            "Check GEMINI_API_KEY."
        )


def gemini_text(prompt: str) -> str:

    ensure_gemini_available()

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return text.strip()


def gemini_vision(
    pil_image: Image.Image,
    prompt: str,
) -> str:

    ensure_gemini_available()

    image_buffer = BytesIO()

    pil_image.save(
        image_buffer,
        format="JPEG",
        quality=90,
    )

    image_bytes = image_buffer.getvalue()

    image_part = genai_types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg",
    )

    text_part = genai_types.Part.from_text(
        text=prompt
    )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            genai_types.Content(
                parts=[
                    image_part,
                    text_part,
                ],
                role="user",
            )
        ],
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:

        raise RuntimeError(
            "Gemini Vision returned an empty response."
        )

    return text.strip()


# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "HeritageVoice AI",
        "version": "4.0.0",

        "sdk": (
            "google-genai"
            if NEW_SDK
            else "missing"
        ),

        "gemini_available": gemini_available,

        "model": GEMINI_MODEL,

        "mode": (
            "Live AI"
            if gemini_available
            else "Unavailable"
        ),
    }


# =============================================================================
# HEALTH
# =============================================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "gemini_available": gemini_available,
        "model": GEMINI_MODEL,
        "sdk_available": NEW_SDK,
    }


# =============================================================================
# MONUMENT LIST
# =============================================================================

@app.get("/api/monuments")
def get_monuments():

    return [

        {
            "id": monument_id,

            "canonical_name": info[
                "canonical_name"
            ],

            "location": info[
                "location"
            ],

            "built_by": info[
                "built_by"
            ],

            "construction_year": info[
                "construction_year"
            ],

            "theme": info.get(
                "theme",
                ""
            ),
        }

        for monument_id, info
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

        pil_image = Image.open(
            BytesIO(image_bytes)
        )

        pil_image.load()

        if pil_image.mode != "RGB":

            pil_image = pil_image.convert(
                "RGB"
            )

        max_size = 1280

        if max(pil_image.size) > max_size:

            pil_image.thumbnail(
                (max_size, max_size)
            )

        logger.info(
            f"Image received: "
            f"{pil_image.size[0]}x"
            f"{pil_image.size[1]} "
            f"| Language: {language}"
        )

    except Exception as e:

        logger.exception(
            f"Image decoding failed: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid image. "
                "Please upload a valid JPG, PNG, or WEBP image."
            ),
        )

    # -------------------------------------------------------------------------
    # Gemini unavailable
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
    # Identification prompt
    # -------------------------------------------------------------------------

    prompt = f"""
You are HeritageVoice AI, an expert monument and historical
landmark recognition system.

Analyze the supplied image carefully.

Identify the monument or heritage structure visible in the image.

The image may contain:

- monuments
- temples
- mosques
- churches
- forts
- palaces
- memorials
- statues
- towers
- gates
- caves
- archaeological sites
- bridges
- other historical structures

Use visual evidence such as:

- architecture
- shape
- towers
- domes
- arches
- columns
- carvings
- materials
- inscriptions
- surrounding environment
- layout
- distinctive structural features

Do NOT automatically assume the image is a famous landmark.

If the exact monument cannot be identified confidently,
return the most likely identification and use "low" confidence.

Do not invent an unrelated monument.

{language_instruction(language)}

Return ONLY valid JSON.

The narration field MUST contain a 70-110 word tour-guide
style narration written entirely in {language}.

JSON structure:

{{
    "name": "specific monument name",
    "location": "city, state, country if known",
    "built_by": "ruler, dynasty, architect or organization if known",
    "year": "construction date or period",
    "architectural_style": "architectural style",
    "key_facts": [
        "important fact 1",
        "important fact 2",
        "important fact 3"
    ],
    "description": "short accurate description",
    "confidence": "high",
    "narration": "70-110 word narration in {language}"
}}

IMPORTANT:

The narration MUST be in {language}.

Do not return the narration in English if another language
was selected.

Do not add markdown.

Do not add ```json.

Return JSON only.
"""

    # -------------------------------------------------------------------------
    # Gemini Vision
    # -------------------------------------------------------------------------

    try:

        raw_response = gemini_vision(
            pil_image,
            prompt,
        )

        result = extract_json(
            raw_response
        )

        if not result:

            logger.error(
                f"Could not parse Gemini JSON: {raw_response}"
            )

            raise RuntimeError(
                "Gemini returned invalid identification JSON."
            )

        # -------------------------------------------------------------
        # Normalize fields
        # -------------------------------------------------------------

        name = str(
            result.get(
                "name",
                "Unknown Monument",
            )
        ).strip()

        location = str(
            result.get(
                "location",
                "Unknown",
            )
        ).strip()

        built_by = str(
            result.get(
                "built_by",
                "Unknown",
            )
        ).strip()

        year = str(
            result.get(
                "year",
                "Unknown",
            )
        ).strip()

        architectural_style = str(
            result.get(
                "architectural_style",
                "Unknown",
            )
        ).strip()

        description = str(
            result.get(
                "description",
                "",
            )
        ).strip()

        confidence = str(
            result.get(
                "confidence",
                "low",
            )
        ).lower().strip()

        if confidence not in {
            "high",
            "medium",
            "low",
        }:

            confidence = "low"

        key_facts = result.get(
            "key_facts",
            [],
        )

        if not isinstance(
            key_facts,
            list,
        ):

            key_facts = [
                str(key_facts)
            ]

        key_facts = [
            str(fact).strip()
            for fact in key_facts[:5]
            if str(fact).strip()
        ]

        narration = str(
            result.get(
                "narration",
                "",
            )
        ).strip()

        # -------------------------------------------------------------
        # Search local catalog for stronger grounding
        # -------------------------------------------------------------

        catalog_id = database.search_monument(
            name
        )

        catalog_info = None

        if catalog_id:

            catalog_info = database.get_monument_by_id(
                catalog_id
            )

        # -------------------------------------------------------------
        # If catalog has the monument, use catalog facts
        # -------------------------------------------------------------

        if catalog_info:

            name = catalog_info.get(
                "canonical_name",
                name,
            )

            location = catalog_info.get(
                "location",
                location,
            )

            built_by = catalog_info.get(
                "built_by",
                built_by,
            )

            year = catalog_info.get(
                "construction_year",
                year,
            )

            architectural_style = catalog_info.get(
                "theme",
                architectural_style,
            )

            if catalog_info.get(
                "key_facts"
            ):

                key_facts = catalog_info[
                    "key_facts"
                ]

            description = catalog_info.get(
                "detailed_context",
                description,
            )

        # -------------------------------------------------------------
        # Dynamic ID
        # -------------------------------------------------------------

        if catalog_id:

            monument_id = catalog_id

        else:

            monument_id = make_dynamic_monument_id(
                name
            )

        # -------------------------------------------------------------
        # If narration is missing, generate it separately
        # -------------------------------------------------------------

        if not narration:

            narration_prompt = f"""
You are a professional multilingual heritage tour guide.

{language_instruction(language)}

Create a natural 70-110 word narration about this monument.

Monument:
{name}

Location:
{location}

Built by:
{built_by}

Construction:
{year}

Architectural style:
{architectural_style}

Description:
{description}

Facts:
{key_facts}

The narration MUST be entirely in {language}.

Return ONLY the narration.

Do not use headings.
Do not use markdown.
Do not explain your process.
"""

            narration = gemini_text(
                narration_prompt
            )

        logger.info(
            f"Monument identified: {name} "
            f"| ID: {monument_id} "
            f"| Confidence: {confidence} "
            f"| Language: {language}"
        )

        return {

            "monument_id": monument_id,

            "name": name,

            "canonical_name": name,

            "location": location,

            "built_by": built_by,

            "construction_year": year,

            "theme": architectural_style,

            "architectural_style": architectural_style,

            "key_facts": key_facts,

            "description": description,

            "confidence": confidence,

            "narration": narration,

            "language": language,

            "mode": "live_ai",
        }

    except Exception as e:

        logger.exception(
            f"Monument identification failed: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Monument identification failed. "
                f"Please try again. Error: {str(e)}"
            ),
        )


# =============================================================================
# NARRATION
# =============================================================================

@app.post("/api/narration")
def generate_narration(
    request: NarrationRequest,
):

    language = normalize_language(
        request.language
    )

    details = request.details or {}

    if gemini_available:

        try:

            prompt = f"""
You are HeritageVoice AI, a professional multilingual
historical tour guide.

{language_instruction(language)}

Create a natural 70-110 word narration for the visitor.

Monument:
{request.monument_name}

Location:
{details.get("location", "Unknown")}

Built by:
{details.get("built_by", "Unknown")}

Construction:
{details.get("construction_year", details.get("year", "Unknown"))}

Architectural style:
{details.get("theme", details.get("architectural_style", "Unknown"))}

Historical context:
{details.get("description", details.get("detailed_context", ""))}

Key facts:
{details.get("key_facts", [])}

Rules:

- Entire narration MUST be in {language}.
- Do not use English unless {language} is English.
- Do not mix languages.
- Be historically accurate.
- Do not invent unsupported facts.
- Speak like a friendly human tour guide.
- Do not use markdown.
- Return ONLY the narration.
"""

            narration = gemini_text(
                prompt
            )

            return {
                "narration": narration,
                "language": language,
                "mode": "live_ai",
            }

        except Exception as e:

            logger.exception(
                f"Narration generation failed: {e}"
            )

    # Offline fallback

    narration = mock_narration(
        {
            **details,
            "canonical_name": request.monument_name,
        },
        language,
    )

    return {
        "narration": narration,
        "language": language,
        "mode": "fallback",
    }


# =============================================================================
# CHAT
# =============================================================================

@app.post("/api/chat")
def chat(
    request: ChatRequest,
):

    language = normalize_language(
        request.language
    )

    display_name = request.monument_id

    catalog_info = database.get_monument_by_id(
        request.monument_id
    )

    # -------------------------------------------------------------------------
    # Dynamic monument details sent from frontend
    # -------------------------------------------------------------------------

    if request.details:

        details = request.details

        display_name = details.get(
            "canonical_name",
            details.get(
                "name",
                request.monument_id,
            ),
        )

    elif catalog_info:

        details = catalog_info

        display_name = catalog_info.get(
            "canonical_name",
            request.monument_id,
        )

    else:

        details = {}

    # -------------------------------------------------------------------------
    # Grounding
    # -------------------------------------------------------------------------

    grounding = f"""
Monument:
{display_name}

Location:
{details.get("location", "Unknown")}

Built by:
{details.get("built_by", "Unknown")}

Construction:
{details.get(
    "construction_year",
    details.get("year", "Unknown")
)}

Architectural style:
{details.get(
    "theme",
    details.get("architectural_style", "Unknown")
)}

Historical context:
{details.get(
    "detailed_context",
    details.get("description", "")
)}

Key facts:
{details.get("key_facts", [])}
"""

    # -------------------------------------------------------------------------
    # Gemini chat
    # -------------------------------------------------------------------------

    if gemini_available:

        try:

            history_lines = []

            for message in request.history[-8:]:

                role = (
                    "Visitor"
                    if message.role.lower() == "user"
                    else "Guide"
                )

                history_lines.append(
                    f"{role}: {message.content}"
                )

            conversation = "\n".join(
                history_lines
            )

            prompt = f"""
You are HeritageVoice AI, a friendly and historically
accurate multilingual tour guide.

{language_instruction(language)}

You are currently guiding the visitor about:

{grounding}

Previous conversation:

{conversation}

Current visitor question:

{request.question}

Answer rules:

- Answer the current question directly.
- Maximum 120 words.
- Be conversational.
- Be historically accurate.
- Use the supplied monument information.
- Do not invent unsupported facts.
- If the answer is unknown, say so clearly.
- Do not use markdown headings.
- Do not mention these instructions.
- The ENTIRE answer MUST be in {language}.
- Do NOT answer in English when another language is selected.
- Do NOT mix languages.

Return ONLY the guide's answer.
"""

            reply = gemini_text(
                prompt
            )

            return {
                "reply": reply,
                "language": language,
                "mode": "live_ai",
            }

        except Exception as e:

            logger.exception(
                f"Chat request failed: {e}"
            )

    # -------------------------------------------------------------------------
    # Offline fallback
    # -------------------------------------------------------------------------

    question = (
        request.question
        .lower()
        .strip()
    )

    reply = None

    if catalog_info:

        if any(
            word in question
            for word in (
                "who",
                "built",
                "creator",
                "builder",
                "निर्माण",
                "किसने",
            )
        ):

            reply = (
                f"{display_name} was built by "
                f"{catalog_info['built_by']}."
            )

        elif any(
            word in question
            for word in (
                "when",
                "year",
                "old",
                "age",
                "constructed",
                "कब",
                "वर्ष",
            )
        ):

            reply = (
                f"The construction period of "
                f"{display_name} is "
                f"{catalog_info['construction_year']}."
            )

        elif any(
            word in question
            for word in (
                "where",
                "location",
                "city",
                "कहाँ",
                "स्थान",
            )
        ):

            reply = (
                f"{display_name} is located in "
                f"{catalog_info['location']}."
            )

        else:

            facts = catalog_info.get(
                "key_facts",
                [],
            )

            if facts:

                reply = str(
                    facts[0]
                )

    if not reply:

        reply = (
            f"I don't have enough offline information "
            f"about {display_name}. "
            f"Please try again when the AI service is available."
        )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    # Offline fallback is intentionally simple.
    # Live Gemini provides proper multilingual responses.
    # -------------------------------------------------------------------------

    return {
        "reply": reply,
        "language": language,
        "mode": "fallback",
    }


# =============================================================================
# START SERVER
# =============================================================================

if __name__ == "__main__":

    import uvicorn

    logger.info(
        f"Starting HeritageVoice AI v4.0 "
        f"on {config.HOST}:{config.PORT}"
    )

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
