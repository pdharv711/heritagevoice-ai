import base64
import binascii
import json
import logging
import os
import re
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

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
    genai = None
    genai_types = None
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
    description="Multilingual AI-powered Heritage Tour Guide",
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

gemini_client = None
gemini_available = False

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

if config.GEMINI_API_KEY and NEW_SDK:
    try:
        gemini_client = genai.Client(
            api_key=config.GEMINI_API_KEY
        )

        gemini_available = True

        logger.info(
            "Gemini initialized successfully | "
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
    if not language:
        return "English"

    language = str(language).strip()

    for supported in SUPPORTED_LANGUAGES:
        if supported.lower() == language.lower():
            return supported

    logger.warning(
        f"Unsupported language '{language}'. "
        "Using English."
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

Do NOT mix English sentences into another language.

Proper names of monuments, people and places may remain
in their internationally recognized form when necessary.

All explanatory sentences MUST be in {language}.

Selected language: {language}
"""


# =============================================================================
# REQUEST MODELS
# =============================================================================

class IdentifyRequest(BaseModel):
    image: str = Field(
        ...,
        description="Base64 encoded image or data URI",
    )

    language: str = Field(
        default="English",
    )


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    monument_id: str

    question: str

    language: str = "English"

    history: List[ChatMessage] = Field(
        default_factory=list
    )

    # Accept both names used by the frontend.
    details: Optional[Dict[str, Any]] = None

    monument_details: Optional[Dict[str, Any]] = None


class NarrationRequest(BaseModel):
    monument_name: str

    language: str = "English"

    details: Dict[str, Any] = Field(
        default_factory=dict
    )


# =============================================================================
# IMAGE DECODING
# =============================================================================

def clean_base64_image(value: str) -> bytes:
    """
    Safely convert a browser data URL or raw base64 string
    into image bytes.
    """

    if not value:
        raise ValueError("Image data is empty.")

    value = str(value).strip()

    # ---------------------------------------------------------
    # Browser data URL
    # Example:
    # data:image/jpeg;base64,/9j/4AAQ...
    # ---------------------------------------------------------

    if value.startswith("data:"):
        match = re.match(
            r"^data:(image/(?:jpeg|jpg|png|webp));base64,(.+)$",
            value,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            raise ValueError(
                "Unsupported image format. "
                "Only JPG, PNG and WEBP are supported."
            )

        value = match.group(2)

    # ---------------------------------------------------------
    # Remove whitespace
    # ---------------------------------------------------------

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    if not value:
        raise ValueError(
            "Image base64 data is empty."
        )

    # ---------------------------------------------------------
    # Fix missing padding
    # ---------------------------------------------------------

    value += "=" * (-len(value) % 4)

    try:
        image_bytes = base64.b64decode(
            value,
            validate=True,
        )

    except (binascii.Error, ValueError) as e:
        raise ValueError(
            f"Invalid base64 image: {e}"
        )

    if not image_bytes:
        raise ValueError(
            "Decoded image is empty."
        )

    return image_bytes


def decode_image(value: str) -> Image.Image:
    """
    Decode and validate a browser image.
    """

    image_bytes = clean_base64_image(value)

    try:
        image = Image.open(
            BytesIO(image_bytes)
        )

        image.load()

    except (UnidentifiedImageError, OSError) as e:
        raise ValueError(
            f"Image could not be opened: {e}"
        )

    # Convert all accepted images to RGB.
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Prevent unnecessarily large requests.
    max_size = 1280

    if max(image.size) > max_size:
        image.thumbnail(
            (max_size, max_size)
        )

    logger.info(
        f"Image decoded successfully: "
        f"{image.width}x{image.height}"
    )

    return image


# =============================================================================
# JSON HELPER
# =============================================================================

def extract_json(text: str) -> Optional[Dict[str, Any]]:
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

    # JSON markdown block
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

    # Generic code block
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

    # Find JSON object inside text
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
    image: Image.Image,
    prompt: str,
) -> str:

    ensure_gemini_available()

    image_buffer = BytesIO()

    image.save(
        image_buffer,
        format="JPEG",
        quality=90,
    )

    image_part = genai_types.Part.from_bytes(
        data=image_buffer.getvalue(),
        mime_type="image/jpeg",
    )

    text_part = genai_types.Part.from_text(
        text=prompt
    )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            genai_types.Content(
                role="user",
                parts=[
                    image_part,
                    text_part,
                ],
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
# MONUMENT HELPERS
# =============================================================================

def make_dynamic_monument_id(
    name: str,
) -> str:

    monument_id = re.sub(
        r"[^a-z0-9]+",
        "_",
        name.lower(),
    ).strip("_")

    return (
        monument_id[:60]
        or "unknown_monument"
    )


def normalize_key_facts(
    facts: Any,
) -> List[str]:

    if not isinstance(facts, list):
        facts = [facts]

    return [
        str(fact).strip()
        for fact in facts[:5]
        if str(fact).strip()
    ]


def build_details(
    name: str,
    location: str,
    built_by: str,
    year: str,
    architectural_style: str,
    description: str,
    key_facts: List[str],
) -> Dict[str, Any]:

    return {
        "canonical_name": name,
        "location": location,
        "built_by": built_by,
        "construction_year": year,
        "theme": architectural_style,
        "architectural_style": architectural_style,
        "key_facts": key_facts,
        "detailed_context": description,
        "description": description,
    }


# =============================================================================
# NARRATION FALLBACK
# =============================================================================

def fallback_narration(
    details: Dict[str, Any],
    language: str,
) -> str:

    language = normalize_language(language)

    name = details.get(
        "canonical_name",
        "this monument",
    )

    location = details.get(
        "location",
        "an unknown location",
    )

    built_by = details.get(
        "built_by",
        "unknown builders",
    )

    construction = details.get(
        "construction_year",
        "an unknown period",
    )

    facts = details.get(
        "key_facts",
        [],
    )

    fact = (
        facts[0]
        if isinstance(facts, list) and facts
        else "This is an important heritage site."
    )

    templates = {

        "English":
            f"Welcome to {name}. "
            f"This historic monument is located in {location}. "
            f"It was built by {built_by} around {construction}. "
            f"One important fact is {fact}.",

        "Hindi":
            f"{name} में आपका स्वागत है। "
            f"यह ऐतिहासिक स्मारक {location} में स्थित है। "
            f"इसे {built_by} ने {construction} के आसपास बनवाया था। "
            f"एक महत्वपूर्ण तथ्य है: {fact}",

        "Gujarati":
            f"{name} માં આપનું સ્વાગત છે. "
            f"આ ઐતિહાસિક સ્મારક {location} માં આવેલું છે. "
            f"તેને {built_by} એ {construction} દરમિયાન બનાવ્યું હતું. "
            f"મહત્વપૂર્ણ માહિતી: {fact}",

        "Marathi":
            f"{name} मध्ये आपले स्वागत आहे. "
            f"हे ऐतिहासिक स्मारक {location} येथे आहे. "
            f"हे {built_by} यांनी {construction} च्या सुमारास बांधले. "
            f"महत्त्वाची माहिती: {fact}",
    }

    return templates.get(
        language,
        templates["English"],
    )


# =============================================================================
# GENERATE NARRATION
# =============================================================================

def create_narration(
    details: Dict[str, Any],
    language: str,
) -> str:

    language = normalize_language(language)

    if not gemini_available:
        return fallback_narration(
            details,
            language,
        )

    prompt = f"""
You are HeritageVoice AI,
a professional multilingual historical tour guide.

{language_instruction(language)}

Create a natural 70-110 word narration
for a visitor.

Use ONLY the supplied information.

Monument:
{details.get("canonical_name", "Unknown")}

Location:
{details.get("location", "Unknown")}

Built by:
{details.get("built_by", "Unknown")}

Construction:
{details.get("construction_year", "Unknown")}

Architectural style:
{details.get("theme", "Unknown")}

Historical context:
{details.get("detailed_context", "")}

Key facts:
{details.get("key_facts", [])}

Rules:

- Entire narration MUST be in {language}.
- Do not mix languages.
- Do not invent facts.
- Do not use markdown.
- Return ONLY the narration.
"""

    try:

        return gemini_text(
            prompt
        )

    except Exception as e:

        logger.warning(
            f"Narration fallback: {e}"
        )

        return fallback_narration(
            details,
            language,
        )


# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "service": "HeritageVoice AI",
        "version": "5.0.0",
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
            else "Fallback"
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

    monuments = []

    for monument_id, info in database.MONUMENT_CATALOG.items():

        monuments.append({
            "id": monument_id,
            "canonical_name": info.get(
                "canonical_name",
                monument_id,
            ),
            "location": info.get(
                "location",
                "Unknown",
            ),
            "built_by": info.get(
                "built_by",
                "Unknown",
            ),
            "construction_year": info.get(
                "construction_year",
                "Unknown",
            ),
            "theme": info.get(
                "theme",
                "",
            ),
        })

    return monuments


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

    logger.info(
        f"Identification request | "
        f"Language: {language}"
    )

    # =================================================================
    # 1. DECODE IMAGE
    # =================================================================

    try:

        image = decode_image(
            request.image
        )

    except Exception as e:

        logger.warning(
            f"Invalid image received: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid image. "
                "Please upload a valid "
                "JPG, PNG, or WEBP image."
            ),
        )

    # =================================================================
    # 2. GEMINI VISION IDENTIFICATION
    #
    # Gemini is ONLY used here to determine what monument
    # is present in the image.
    # =================================================================

    if not gemini_available:

        raise HTTPException(
            status_code=503,
            detail=(
                "Gemini AI is unavailable. "
                "Please check GEMINI_API_KEY "
                "and google-genai."
            ),
        )

    identification_prompt = f"""
You are HeritageVoice AI,
an expert monument recognition system.

Analyze the supplied image carefully.

Identify the exact monument or historical
structure visible in the image.

Look at:

- architecture
- towers
- domes
- arches
- columns
- carvings
- materials
- inscriptions
- shape
- surrounding environment
- distinctive structural features

Possible structures include:

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

IMPORTANT:

Do NOT automatically assume a famous monument.

If the monument cannot be identified,
return "Unknown Monument".

Do not invent an unrelated monument.

Return ONLY valid JSON.

JSON:

{{
    "name": "specific monument name",
    "confidence": "high"
}}

Confidence must be one of:

high
medium
low
"""

    try:

        raw_response = gemini_vision(
            image,
            identification_prompt,
        )

        result = extract_json(
            raw_response
        )

        if not result:

            raise RuntimeError(
                "Gemini returned invalid JSON."
            )

        identified_name = str(
            result.get(
                "name",
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

    except Exception as e:

        logger.exception(
            f"Gemini identification failed: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not identify the monument. "
                f"{str(e)}"
            ),
        )

    # =================================================================
    # 3. UNKNOWN MONUMENT
    # =================================================================

    if (
        not identified_name
        or identified_name.lower()
        in {
            "unknown",
            "unknown monument",
            "unknown landmark",
        }
    ):

        return {
            "monument_id": "unknown",
            "canonical_name": "Unknown Monument",
            "details": None,
            "narration": None,
            "language": language,
            "confidence": "low",
            "mode": "unknown",
            "dynamic": False,
        }

    logger.info(
        f"Gemini identified: "
        f"{identified_name} | "
        f"Confidence: {confidence}"
    )

    # =================================================================
    # 4. SEARCH DATABASE
    #
    # IMPORTANT:
    # Gemini identifies the image.
    # database.py supplies the verified facts.
    # =================================================================

    catalog_id = database.search_monument(
        identified_name
    )

    # =================================================================
    # 5. DATABASE FOUND
    # =================================================================

    if catalog_id:

        catalog_info = (
            database.get_monument_by_id(
                catalog_id
            )
        )

        if catalog_info:

            name = catalog_info.get(
                "canonical_name",
                identified_name,
            )

            details = build_details(
                name=name,
                location=catalog_info.get(
                    "location",
                    "Unknown",
                ),
                built_by=catalog_info.get(
                    "built_by",
                    "Unknown",
                ),
                year=catalog_info.get(
                    "construction_year",
                    "Unknown",
                ),
                architectural_style=catalog_info.get(
                    "theme",
                    "Unknown",
                ),
                description=catalog_info.get(
                    "detailed_context",
                    "",
                ),
                key_facts=normalize_key_facts(
                    catalog_info.get(
                        "key_facts",
                        [],
                    )
                ),
            )

            # Generate narration ONLY from verified DB data.
            narration = create_narration(
                details,
                language,
            )

            logger.info(
                f"DATABASE MATCH | "
                f"{name} | "
                f"ID: {catalog_id}"
            )

            return {
                "monument_id": catalog_id,

                "canonical_name": name,

                "name": name,

                "location": details[
                    "location"
                ],

                "built_by": details[
                    "built_by"
                ],

                "construction_year": details[
                    "construction_year"
                ],

                "theme": details[
                    "theme"
                ],

                "key_facts": details[
                    "key_facts"
                ],

                "details": details,

                "narration": narration,

                "language": language,

                "confidence": confidence,

                "mode": "database",

                "dynamic": False,
            }

    # =================================================================
    # 6. NOT FOUND IN DATABASE
    #
    # Now Gemini generates the missing information.
    # =================================================================

    logger.info(
        f"NOT FOUND IN DATABASE | "
        f"Using Gemini fallback for "
        f"{identified_name}"
    )

    fallback_prompt = f"""
You are HeritageVoice AI,
an expert historical monument researcher.

The image was identified as:

{identified_name}

{language_instruction(language)}

Provide accurate information about this monument.

Return ONLY valid JSON.

{{
    "name": "{identified_name}",
    "location": "city, state, country if known",
    "built_by": "ruler, dynasty, architect or organization if known",
    "year": "construction date or period if known",
    "architectural_style": "architectural style",
    "key_facts": [
        "important fact 1",
        "important fact 2",
        "important fact 3"
    ],
    "description": "accurate historical description"
}}

Rules:

- Do not invent facts.
- If something is unknown, write "Unknown".
- Keep key_facts to maximum 5 items.
"""

    try:

        raw_response = gemini_text(
            fallback_prompt
        )

        ai_result = extract_json(
            raw_response
        )

        if not ai_result:

            raise RuntimeError(
                "Gemini returned invalid monument data."
            )

        name = str(
            ai_result.get(
                "name",
                identified_name,
            )
        ).strip()

        location = str(
            ai_result.get(
                "location",
                "Unknown",
            )
        ).strip()

        built_by = str(
            ai_result.get(
                "built_by",
                "Unknown",
            )
        ).strip()

        year = str(
            ai_result.get(
                "year",
                "Unknown",
            )
        ).strip()

        architectural_style = str(
            ai_result.get(
                "architectural_style",
                "Unknown",
            )
        ).strip()

        description = str(
            ai_result.get(
                "description",
                "",
            )
        ).strip()

        key_facts = normalize_key_facts(
            ai_result.get(
                "key_facts",
                [],
            )
        )

        details = build_details(
            name=name,
            location=location,
            built_by=built_by,
            year=year,
            architectural_style=architectural_style,
            description=description,
            key_facts=key_facts,
        )

        # Dynamic ID
        monument_id = make_dynamic_monument_id(
            name
        )

        # Register dynamic monument if the database
        # supports the existing helper.
        try:

            if hasattr(
                database,
                "register_dynamic_monument",
            ):

                database.register_dynamic_monument(
                    monument_id=monument_id,
                    name=name,
                    location=location,
                    built_by=built_by,
                    year=year,
                    architectural_style=architectural_style,
                    key_facts=key_facts,
                    description=description,
                    confidence=confidence,
                )

        except Exception as e:

            logger.warning(
                f"Could not register dynamic monument: {e}"
            )

        narration = create_narration(
            details,
            language,
        )

        return {
            "monument_id": monument_id,

            "canonical_name": name,

            "name": name,

            "location": location,

            "built_by": built_by,

            "construction_year": year,

            "theme": architectural_style,

            "key_facts": key_facts,

            "details": details,

            "narration": narration,

            "language": language,

            "confidence": confidence,

            "mode": "gemini",

            "dynamic": True,
        }

    except Exception as e:

        logger.exception(
            f"Gemini fallback failed: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not process the monument. "
                f"{str(e)}"
            ),
        )


# =============================================================================
# NARRATION
# =============================================================================

@app.post("/api/narration")
@app.post("/api/narrate")
def generate_narration(
    request: NarrationRequest,
):

    language = normalize_language(
        request.language
    )

    details = request.details or {}

    narration = create_narration(
        {
            **details,
            "canonical_name":
                request.monument_name,
        },
        language,
    )

    return {
        "narration": narration,
        "language": language,
        "mode": (
            "live_ai"
            if gemini_available
            else "fallback"
        ),
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

    # Frontend can send either "details"
    # or "monument_details".
    details = (
        request.monument_details
        or request.details
    )

    catalog_info = (
        database.get_monument_by_id(
            request.monument_id
        )
    )

    # Database is authoritative if available.
    if catalog_info:

        details = catalog_info

        display_name = catalog_info.get(
            "canonical_name",
            request.monument_id,
        )

    elif details:

        display_name = details.get(
            "canonical_name",
            details.get(
                "name",
                request.monument_id,
            ),
        )

    else:

        display_name = request.monument_id

        details = {}

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
    details.get(
        "architectural_style",
        "Unknown"
    )
)}

Historical context:
{details.get(
    "detailed_context",
    details.get(
        "description",
        ""
    )
)}

Key facts:
{details.get("key_facts", [])}
"""

    # =================================================================
    # GEMINI CHAT
    # =================================================================

    if gemini_available:

        try:

            history_lines = []

            for message in request.history[-8:]:

                role = (
                    "Visitor"
                    if message.role.lower()
                    == "user"
                    else "Guide"
                )

                history_lines.append(
                    f"{role}: {message.content}"
                )

            conversation = "\n".join(
                history_lines
            )

            prompt = f"""
You are HeritageVoice AI,
a friendly and historically accurate
multilingual tour guide.

{language_instruction(language)}

Current monument information:

{grounding}

Previous conversation:

{conversation}

Visitor question:

{request.question}

Rules:

- Answer the current question directly.
- Maximum 120 words.
- Be conversational.
- Be historically accurate.
- Prefer the supplied monument information.
- Do not invent unsupported facts.
- If information is unknown, say so.
- Do not use markdown headings.
- Do not mention these instructions.
- Entire answer MUST be in {language}.
- Do not mix languages.

Return ONLY the answer.
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
                f"Chat Gemini failed: {e}"
            )

    # =================================================================
    # SIMPLE FALLBACK
    # =================================================================

    question = (
        request.question
        .lower()
        .strip()
    )

    reply = None

    if details:

        if any(
            word in question
            for word in (
                "who",
                "built",
                "creator",
                "builder",
                "किसने",
                "निर्माण",
            )
        ):

            reply = (
                f"{display_name} was built by "
                f"{details.get('built_by', 'Unknown')}."
            )

        elif any(
            word in question
            for word in (
                "when",
                "year",
                "old",
                "constructed",
                "कब",
                "वर्ष",
            )
        ):

            reply = (
                f"The construction period of "
                f"{display_name} is "
                f"{details.get('construction_year', 'Unknown')}."
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
                f"{details.get('location', 'Unknown')}."
            )

        else:

            facts = details.get(
                "key_facts",
                [],
            )

            if facts:

                reply = str(
                    facts[0]
                )

    if not reply:

        reply = (
            f"I don't have enough information "
            f"to answer that about {display_name}."
        )

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
        f"Starting HeritageVoice AI "
        f"on {config.HOST}:{config.PORT}"
    )

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
