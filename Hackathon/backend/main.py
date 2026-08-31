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
    version="3.0.0",
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

# Current stable Gemini model with multimodal/image support.
# Can also be overridden from Render Environment Variables.
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
            f"Gemini client initialized successfully. "
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

    elif not config.GEMINI_API_KEY:
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
    Make sure the requested language is one of our supported languages.
    """

    if not language:
        return "English"

    language = language.strip()

    for supported in SUPPORTED_LANGUAGES:
        if supported.lower() == language.lower():
            return supported

    return "English"


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

    # Important:
    # Allows ChatWindow to send dynamically identified monument details.
    details: Optional[Dict[str, Any]] = None


class NarrationRequest(BaseModel):
    monument_name: str

    language: str = Field(
        default="English"
    )

    details: Dict[str, Any]


# =============================================================================
# MOCK / OFFLINE NARRATION
# =============================================================================

MOCK_NARRATIONS: Dict[str, str] = {

    "English":
        "Welcome to {name}! Located in {location}, "
        "this remarkable monument was built by {built_by} "
        "around {construction}. One important fact is: {key_fact}",

    "Hindi":
        "{name} में आपका स्वागत है! यह ऐतिहासिक स्मारक "
        "{location} में स्थित है। इसे {built_by} ने "
        "{construction} के आसपास बनवाया था। "
        "एक महत्वपूर्ण तथ्य है: {key_fact}",

    "Tamil":
        "{name}-க்கு வரவேற்கிறோம்! இந்த வரலாற்றுச் சின்னம் "
        "{location}-ல் அமைந்துள்ளது. இதை {built_by}, "
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

    "Marathi":
        "{name} मध्ये आपले स्वागत आहे! हे ऐतिहासिक स्मारक "
        "{location} येथे आहे. हे {built_by} यांनी "
        "{construction} च्या सुमारास बांधले. "
        "महत्त्वाची माहिती: {key_fact}",

    "Gujarati":
        "{name} માં આપનું સ્વાગત છે! આ ઐતિહાસિક સ્મારક "
        "{location} માં આવેલું છે. તેને {built_by} એ "
        "{construction} દરમિયાન બનાવ્યું હતું. "
        "મહત્વપૂર્ણ માહિતી: {key_fact}",

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
        "¡Bienvenido a {name}! Este monumento histórico está "
        "en {location}. Fue construido por {built_by} "
        "alrededor de {construction}. Dato importante: {key_fact}",

    "German":
        "Willkommen bei {name}! Dieses historische Monument "
        "befindet sich in {location}. Es wurde von {built_by} "
        "um {construction} erbaut. Eine wichtige Tatsache: {key_fact}",

    "Arabic":
        "مرحباً بكم في {name}! يقع هذا النصب التاريخي "
        "في {location}. بناه {built_by} حوالي عام {construction}. "
        "ومن الحقائق المهمة: {key_fact}",

    "Japanese":
        "{name}へようこそ！この歴史的な monument は "
        "{location}にあります。{built_by}によって "
        "{construction}頃に建設されました。 "
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
# HELPER FUNCTIONS
# =============================================================================

def clean_base64_image(b64: str) -> bytes:
    """
    Convert data URI / raw base64 into image bytes.
    """

    if not b64:
        raise ValueError("Image data is empty.")

    # Example:
    # data:image/jpeg;base64,/9j/4AAQ...
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    b64 = b64.strip()

    # Remove accidental whitespace/newlines.
    b64 = re.sub(r"\s+", "", b64)

    # Fix base64 padding.
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


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON safely from Gemini response.
    """

    if not text:
        return None

    text = text.strip()

    # -------------------------------------------------
    # 1. Direct JSON
    # -------------------------------------------------

    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except Exception:
        pass

    # -------------------------------------------------
    # 2. Markdown JSON block
    # -------------------------------------------------

    match = re.search(
        r"```json\s*(\{.*?\})\s*```",
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

    # -------------------------------------------------
    # 3. Generic code block
    # -------------------------------------------------

    match = re.search(
        r"```\s*(\{.*?\})\s*```",
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

    # -------------------------------------------------
    # 4. Find JSON object
    # -------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:

        candidate = text[start:end + 1]

        try:
            result = json.loads(candidate)

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    return None


def make_dynamic_monument_id(name: str) -> str:
    """
    Generate a stable ID for monuments not present
    in the local catalog.
    """

    monument_id = re.sub(
        r"[^a-z0-9]+",
        "_",
        name.lower(),
    ).strip("_")

    return monument_id[:60] or "unknown_monument"


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
        else "it is an important historical heritage site."
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
# GEMINI FUNCTIONS
# =============================================================================

def ensure_gemini_available():

    if not NEW_SDK:
        raise RuntimeError(
            "google-genai package is not installed."
        )

    if not gemini_client:
        raise RuntimeError(
            "Gemini client is not initialized. "
            "Check GEMINI_API_KEY on Render."
        )


def gemini_text(prompt: str) -> str:
    """
    Text-only Gemini request.
    """

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
    """
    Gemini Vision request.
    """

    ensure_gemini_available()

    # Always convert to JPEG for reliable MIME handling.
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
# ROOT / HEALTH
# =============================================================================

@app.get("/")
def root():

    return {
        "status": "online",

        "service": "HeritageVoice AI",

        "version": "3.0.0",

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


@app.get("/api/health")
def health():

    return {
        "status": "healthy",

        "gemini_available": gemini_available,

        "model": GEMINI_MODEL,

        "sdk_available": NEW_SDK,
    }


# =============================================================================
# MONUMENT CATALOG
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
    """
    Identify a monument from an image and generate
    narration in the selected language.
    """

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

        # Limit image size.
        max_size = 1280

        if max(pil_image.size) > max_size:

            pil_image.thumbnail(
                (max_size, max_size)
            )

        logger.info(
            f"Image received: "
            f"{pil_image.size[0]}x"
            f"{pil_image.size[1]}"
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
                "Check GEMINI_API_KEY and the google-genai package "
                "on the backend."
            ),
        )

    # -------------------------------------------------------------------------
    # Gemini prompt
    # -------------------------------------------------------------------------

    prompt = f"""
You are HeritageVoice AI, an expert multilingual monument
and historical landmark recognition system.

Analyze the supplied image carefully.

Identify the specific monument, landmark, historical building,
archaeological site, temple, mosque, church, fort, palace,
memorial, statue, tower, gate, stepwell, cave, bridge,
or other heritage structure visible in the image.

IMPORTANT:

1. Use visual evidence from the image.
2. Consider monuments from India and around the world.
3. Do not automatically assume the monument is a famous landmark.
4. Use architecture, structure, carvings, towers, domes,
   columns, inscriptions, colors, surroundings and layout.
5. If the exact monument cannot be determined, give the
   most likely identification and set confidence to "low".
6. Do not invent an unrelated monument.
7. Do not answer "unknown" when the image contains useful
   architectural information.

The visitor selected this language:

{language}

The narration MUST be written entirely in:

{language}

Return ONLY a JSON object.

Use exactly this structure:

{{
    "name": "specific monument name",
    "location": "city, state, country if known",
    "built_by": "ruler, dynasty, kingdom, architect or organization if known",
    "year": "construction date or period",
    "architectural_style": "architectural style",
    "key_facts": [
        "important fact 1",
        "important fact 2",
        "important fact 3"
    ],
    "description": "Short accurate description.",
    "confidence": "high/medium/low",
    "narration": "70-110 word tour-guide narration entirely in {language}"
}}

Narration requirements:

- Entirely in {language}
- 70-110 words
- Natural tour-guide style
- Easy to listen to
- Interesting for tourists
- Mention the monument name
- Mention the location when known
- Include important historical information
- No markdown
- No headings
- Do not mention that you are an AI
"""


    # -------------------------------------------------------------------------
    # Call Gemini
    # -------------------------------------------------------------------------

    try:

        logger.info(
            f"Starting monument identification "
            f"in language: {language}"
        )

        raw_response = gemini_vision(
            pil_image,
            prompt,
        )

        logger.info(
            f"Gemini response received: "
            f"{raw_response[:800]}"
        )

    except Exception as e:

        logger.exception(
            f"Gemini Vision request failed: {e}"
        )

        # IMPORTANT:
        # Do NOT convert a Gemini/API error into
        # "Monument Not Recognized".
        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini Vision request failed. "
                f"Model: {GEMINI_MODEL}. "
                f"Reason: {str(e)}"
            ),
        )


    # -------------------------------------------------------------------------
    # Parse JSON
    # -------------------------------------------------------------------------

    parsed = extract_json(
        raw_response
    )

    if not parsed:

        logger.error(
            "Gemini returned non-JSON response."
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini returned an invalid recognition response. "
                "Please try the image again."
            ),
        )


    # -------------------------------------------------------------------------
    # Validate monument name
    # -------------------------------------------------------------------------

    name = str(
        parsed.get(
            "name",
            "",
        )
    ).strip()

    if not name:

        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini did not return a monument name."
            ),
        )


    # -------------------------------------------------------------------------
    # Match local catalog
    # -------------------------------------------------------------------------

    catalog_key = None

    try:

        catalog_key = database.search_monument(
            name.lower()
        )

    except Exception as e:

        logger.warning(
            f"Database monument search failed: {e}"
        )


    if catalog_key:

        catalog_info = (
            database.get_monument_by_id(
                catalog_key
            )
        )

        effective = {

            "canonical_name":
                catalog_info[
                    "canonical_name"
                ],

            "location":
                catalog_info[
                    "location"
                ],

            "built_by":
                catalog_info[
                    "built_by"
                ],

            "construction_year":
                catalog_info[
                    "construction_year"
                ],

            "theme":
                catalog_info.get(
                    "theme",
                    "Unknown",
                ),

            "key_facts":
                catalog_info.get(
                    "key_facts",
                    [],
                ),

            "detailed_context":
                catalog_info.get(
                    "detailed_context",
                    "",
                ),
        }

        monument_id = catalog_key

    else:

        # Dynamic monument.
        monument_id = make_dynamic_monument_id(
            name
        )

        effective = {

            "canonical_name":
                name,

            "location":
                parsed.get(
                    "location",
                    "Unknown",
                ),

            "built_by":
                parsed.get(
                    "built_by",
                    "Unknown",
                ),

            "construction_year":
                parsed.get(
                    "year",
                    "Unknown",
                ),

            "theme":
                parsed.get(
                    "architectural_style",
                    "Unknown",
                ),

            "key_facts":
                parsed.get(
                    "key_facts",
                    [],
                ),

            "detailed_context":
                parsed.get(
                    "description",
                    "",
                ),
        }


    # -------------------------------------------------------------------------
    # Narration
    # -------------------------------------------------------------------------

    narration = str(
        parsed.get(
            "narration",
            "",
        )
    ).strip()


    if not narration:

        logger.warning(
            "Gemini did not provide narration. "
            "Using local fallback."
        )

        narration = mock_narration(
            effective,
            language,
        )


    confidence = str(
        parsed.get(
            "confidence",
            "medium",
        )
    ).lower()


    logger.info(
        f"Monument identified: "
        f"{effective['canonical_name']} "
        f"(confidence={confidence}, "
        f"language={language})"
    )


    # -------------------------------------------------------------------------
    # Final response
    # -------------------------------------------------------------------------

    return {

        "monument_id":
            monument_id,

        "canonical_name":
            effective[
                "canonical_name"
            ],

        "narration":
            narration,

        "language":
            language,

        "details": {

            "location":
                effective[
                    "location"
                ],

            "built_by":
                effective[
                    "built_by"
                ],

            "construction_year":
                effective[
                    "construction_year"
                ],

            "theme":
                effective[
                    "theme"
                ],

            "key_facts":
                effective[
                    "key_facts"
                ],

            "description":
                effective[
                    "detailed_context"
                ],

            "confidence":
                confidence,
        },
    }


# =============================================================================
# GENERATE / TRANSLATE NARRATION
# =============================================================================

@app.post("/api/narrate")
def generate_narration(
    request: NarrationRequest,
):
    """
    Generate narration for an already identified monument
    in a newly selected language.
    """

    language = normalize_language(
        request.language
    )

    if not gemini_available:

        # Offline fallback.
        narration = mock_narration(
            {
                "canonical_name":
                    request.monument_name,

                **request.details,
            },
            language,
        )

        return {
            "narration": narration,
            "language": language,
            "mode": "fallback",
        }


    details = request.details


    prompt = f"""
You are HeritageVoice AI, a professional multilingual
historical tour guide.

Create a natural audio-guide narration for this monument.

Monument:
{request.monument_name}

Location:
{details.get("location", "Unknown")}

Built by:
{details.get("built_by", "Unknown")}

Construction period:
{details.get("construction_year", "Unknown")}

Architectural style:
{details.get("theme", "Unknown")}

Important facts:
{details.get("key_facts", [])}

Description:
{details.get("description", "")}

Write the narration entirely in:

{language}

Rules:

- 70-110 words
- Natural tour-guide style
- Easy to listen to
- Historically accurate
- Mention the monument name
- Mention the location when useful
- Include important historical information
- No markdown
- No headings
- Do not mention AI
- Return ONLY the narration
"""


    try:

        narration = gemini_text(
            prompt
        )

        return {
            "narration": narration,
            "language": language,
            "mode": "live",
        }

    except Exception as e:

        logger.exception(
            f"Narration generation failed: {e}"
        )

        # Do not fail the entire application.
        fallback = mock_narration(
            {
                "canonical_name":
                    request.monument_name,

                **details,
            },
            language,
        )

        return {
            "narration": fallback,
            "language": language,
            "mode": "fallback",
            "warning": (
                "Gemini narration failed; "
                "fallback narration was used."
            ),
        }


# =============================================================================
# CHAT / DISCUSS
# =============================================================================

@app.post("/api/chat")
def chat_with_guide(
    request: ChatRequest,
):
    """
    Multilingual follow-up questions about the identified monument.
    """

    language = normalize_language(
        request.language
    )

    # -------------------------------------------------------------------------
    # Get monument information
    # -------------------------------------------------------------------------

    catalog_info = None

    try:

        catalog_info = (
            database.get_monument_by_id(
                request.monument_id
            )
        )

    except Exception as e:

        logger.warning(
            f"Catalog lookup failed: {e}"
        )


    # -------------------------------------------------------------------------
    # Use frontend details for dynamically identified monuments.
    # -------------------------------------------------------------------------

    if catalog_info:

        display_name = (
            catalog_info[
                "canonical_name"
            ]
        )

        grounding = f"""
Monument:
{catalog_info["canonical_name"]}

Location:
{catalog_info.get("location", "Unknown")}

Built by:
{catalog_info.get("built_by", "Unknown")}

Construction:
{catalog_info.get("construction_year", "Unknown")}

Architectural style:
{catalog_info.get("theme", "Unknown")}

Historical context:
{catalog_info.get("detailed_context", "")}

Key facts:
{catalog_info.get("key_facts", [])}
"""

    else:

        details = (
            request.details
            or {}
        )

        display_name = (
            details.get(
                "canonical_name"
            )
            or request.monument_id
                .replace("_", " ")
                .title()
        )

        grounding = f"""
Monument:
{display_name}

Location:
{details.get("location", "Unknown")}

Built by:
{details.get("built_by", "Unknown")}

Construction:
{details.get("construction_year", "Unknown")}

Architectural style:
{details.get("theme", "Unknown")}

Historical context:
{details.get("description", "")}

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
                    if message.role == "user"
                    else "Guide"
                )

                history_lines.append(
                    f"{role}: {message.content}"
                )

            conversation = "\n".join(
                history_lines
            )

            prompt = f"""
You are HeritageVoice AI, a friendly and
historically accurate multilingual tour guide.

The visitor selected this language:

{language}

IMPORTANT:
Your answer MUST be entirely in {language}.

{grounding}

Previous conversation:

{conversation}

Current visitor question:

{request.question}

Answer rules:

- Answer directly.
- Keep the answer under 120 words.
- Be conversational.
- Be historically accurate.
- Use the supplied monument information when relevant.
- Do not invent unsupported facts.
- If something is unknown, say so clearly.
- Do not use markdown headings.
- Return ONLY the guide's answer.
"""

            reply = gemini_text(
                prompt
            )

            return {
                "reply": reply,
                "language": language,
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

    if catalog_info:

        if any(
            word in question
            for word in (
                "who",
                "built",
                "creator",
                "builder",
            )
        ):

            reply = (
                f"{catalog_info['canonical_name']} "
                f"was built by "
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
            )
        ):

            reply = (
                f"The construction period of "
                f"{catalog_info['canonical_name']} "
                f"is {catalog_info['construction_year']}."
            )

        elif any(
            word in question
            for word in (
                "where",
                "location",
                "city",
            )
        ):

            reply = (
                f"It is located in "
                f"{catalog_info['location']}."
            )

        else:

            facts = (
                catalog_info.get(
                    "key_facts",
                    [],
                )
            )

            if facts:

                reply = str(
                    facts[0]
                )

            else:

                reply = (
                    f"I don't have enough offline "
                    f"information about {display_name}."
                )

    else:

        reply = (
            f"I don't have enough offline information "
            f"about {display_name}. "
            f"Please try again when the AI service is available."
        )


    # NOTE:
    # Offline fallback may not be translated perfectly.
    # Live Gemini is responsible for proper multilingual responses.

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
        f"Starting HeritageVoice AI v3.0 "
        f"on {config.HOST}:{config.PORT}"
    )

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
