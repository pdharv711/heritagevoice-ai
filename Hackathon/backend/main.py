import base64
import json
import logging
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
# GOOGLE GENAI
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
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =============================================================================
# FASTAPI
# =============================================================================

app = FastAPI(
    title="HeritageVoice AI API",
    description="Multilingual AI-powered Tour Guide — Any Monument Recognition",
    version="3.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# GEMINI
# =============================================================================

gemini_client = None
gemini_available = False

GEMINI_MODEL = "gemini-3.6-flash"


if config.GEMINI_API_KEY and NEW_SDK:
    try:
        gemini_client = genai.Client(
            api_key=config.GEMINI_API_KEY
        )

        gemini_available = True

        logger.info(
            f"Gemini client ready: {GEMINI_MODEL}"
        )

    except Exception as e:
        logger.error(
            f"Gemini initialization error: {e}"
        )

elif not NEW_SDK:
    logger.error(
        "google-genai is not installed."
    )

else:
    logger.warning(
        "GEMINI_API_KEY not configured."
    )


# =============================================================================
# REQUEST MODELS
# =============================================================================

class IdentifyRequest(BaseModel):

    image: str = Field(
        ...,
        description="Base64 encoded image"
    )

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

    question: str

    language: str = Field(
        "English"
    )

    history: List[ChatMessage] = Field(
        default_factory=list
    )

    # Important for monuments not present in database.py
    monument_details: Optional[Dict[str, Any]] = None


class NarrationRequest(BaseModel):

    monument_name: str

    language: str = Field(
        "English"
    )

    details: Dict[str, Any]


# =============================================================================
# LANGUAGES
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
# BASE64 IMAGE
# =============================================================================

def clean_base64_image(value: str) -> bytes:

    if "," in value:
        value = value.split(",", 1)[1]

    value = value.strip()

    value += "=" * (-len(value) % 4)

    try:
        return base64.b64decode(value)

    except Exception as e:
        raise ValueError(
            f"Invalid base64 image: {e}"
        )


# =============================================================================
# JSON EXTRACTION
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

    # Markdown JSON
    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL
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

    # Find object
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


# =============================================================================
# GEMINI TEXT
# =============================================================================

def gemini_text(prompt: str) -> str:

    if not gemini_client:
        raise RuntimeError(
            "Gemini client unavailable."
        )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return (
        response.text or ""
    ).strip()


# =============================================================================
# GEMINI VISION
# =============================================================================

def gemini_vision(
    image: Image.Image,
    prompt: str
) -> str:

    if not gemini_client:
        raise RuntimeError(
            "Gemini client unavailable."
        )

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=82,
        optimize=True
    )

    image_bytes = buffer.getvalue()

    image_part = genai_types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg"
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
                    text_part
                ]
            )
        ]
    )

    return (
        response.text or ""
    ).strip()


# =============================================================================
# FALLBACK NARRATION
# =============================================================================

def fallback_narration(
    name: str,
    language: str
) -> str:

    translations = {

        "English":
            f"Welcome to {name}. "
            "This remarkable heritage monument reflects "
            "the history and architectural traditions of its region.",

        "Hindi":
            f"{name} में आपका स्वागत है। "
            "यह शानदार ऐतिहासिक स्मारक अपने क्षेत्र के इतिहास "
            "और वास्तुकला की समृद्ध परंपरा को दर्शाता है।",

        "Gujarati":
            f"{name} માં આપનું સ્વાગત છે. "
            "આ અદ્ભુત ઐતિહાસિક સ્મારક તેના પ્રદેશના ઇતિહાસ "
            "અને સ્થાપત્ય પરંપરાને દર્શાવે છે।",

        "Tamil":
            f"{name}-க்கு வரவேற்கிறோம். "
            "இந்த அற்புதமான வரலாற்றுச் சின்னம் அதன் பகுதியின் "
            "வரலாறு மற்றும் கட்டிடக்கலை மரபுகளை பிரதிபலிக்கிறது.",

        "Telugu":
            f"{name} కు స్వాగతం. "
            "ఈ అద్భుతమైన చారిత్రక కట్టడం తన ప్రాంత చరిత్ర "
            "మరియు వాస్తుశిల్ప సంప్రదాయాలను ప్రతిబింబిస్తుంది.",

    }

    return translations.get(
        language,
        translations["English"]
    )


# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "gemini_available": gemini_available,
        "model": GEMINI_MODEL,
        "mode":
            "Live AI"
            if gemini_available
            else "Demo"
    }


# =============================================================================
# HEALTH
# =============================================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "gemini_available": gemini_available,
        "model": GEMINI_MODEL
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
                value["canonical_name"],
            "location":
                value["location"],
            "built_by":
                value["built_by"],
            "construction_year":
                value["construction_year"]
        }

        for key, value
        in database.MONUMENT_CATALOG.items()
    ]


# =============================================================================
# IDENTIFY MONUMENT
# =============================================================================

@app.post("/api/identify")
def identify_monument(
    request: IdentifyRequest
):

    try:

        image_bytes = clean_base64_image(
            request.image
        )

        image = Image.open(
            BytesIO(image_bytes)
        )

        if image.mode != "RGB":
            image = image.convert("RGB")

        # Reduce very large phone images.
        max_dimension = 1280

        if max(image.size) > max_dimension:

            image.thumbnail(
                (max_dimension, max_dimension),
                Image.Resampling.LANCZOS
            )

        logger.info(
            f"Image received: {image.size}"
        )

    except Exception as e:

        logger.error(
            f"Image processing error: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid image."
        )


    if not gemini_available:

        raise HTTPException(
            status_code=503,
            detail="Gemini AI is not available."
        )


    # -------------------------------------------------------------------------
    # ONE AI CALL:
    # Identify monument + create narration in requested language
    # -------------------------------------------------------------------------

    prompt = f"""
You are HeritageVoice AI.

You are an expert worldwide monument and landmark
recognition system.

Analyze the image carefully.

The monument may be ANYWHERE IN THE WORLD.

Do NOT restrict recognition to a database or a predefined
list of monuments.

Look at:

- architecture
- shape
- towers
- domes
- arches
- columns
- carvings
- sculptures
- inscriptions
- materials
- surrounding environment
- historical architectural style
- unique visual characteristics

Try to identify the EXACT monument.

The requested narration language is:

{request.language}

Return ONLY valid JSON.

Use exactly this structure:

{{
  "name": "official monument name",
  "location": "city, state/region, country",
  "built_by": "person, ruler, dynasty, kingdom, architect or organization",
  "year": "construction year or historical period",
  "architectural_style": "style",
  "key_facts": [
    "fact 1",
    "fact 2",
    "fact 3"
  ],
  "description": "short historical description",
  "confidence": "high",
  "narration": "70-110 word narration entirely in {request.language}"
}}

IMPORTANT:

- "confidence" must be high, medium, or low.
- Do not invent a monument.
- If exact identification is uncertain, use medium or low.
- If there is no recognizable monument, use:
  "Unknown Monument"
- Keep the narration entirely in {request.language}.
- Do not include markdown.
- Do not mention AI.
"""

    try:

        raw = gemini_vision(
            image,
            prompt
        )

        logger.info(
            f"Gemini response: {raw[:500]}"
        )

        data = extract_json(raw)

        if not data:

            raise ValueError(
                "Invalid JSON returned by Gemini."
            )

        name = str(
            data.get(
                "name",
                ""
            )
        ).strip()

        if not name or name.lower() == "unknown monument":

            return {
                "monument_id": "unknown",
                "canonical_name":
                    "Monument Not Recognized",
                "narration":
                    "I could not confidently identify this monument. Please try a clearer photograph.",
                "details": None
            }


        # ---------------------------------------------------------------------
        # DATABASE MATCH
        # ---------------------------------------------------------------------

        catalog_key = database.search_monument(
            name.lower()
        )


        if catalog_key:

            catalog = database.get_monument_by_id(
                catalog_key
            )

            monument_id = catalog_key

            details = {

                "canonical_name":
                    catalog["canonical_name"],

                "location":
                    catalog["location"],

                "built_by":
                    catalog["built_by"],

                "construction_year":
                    catalog["construction_year"],

                "theme":
                    catalog.get(
                        "theme",
                        data.get(
                            "architectural_style",
                            "Unknown"
                        )
                    ),

                "key_facts":
                    catalog.get(
                        "key_facts",
                        data.get(
                            "key_facts",
                            []
                        )
                    ),

                "description":
                    catalog.get(
                        "detailed_context",
                        data.get(
                            "description",
                            ""
                        )
                    ),

                "confidence":
                    data.get(
                        "confidence",
                        "high"
                    )
            }

            logger.info(
                f"Database match: {details['canonical_name']}"
            )


        else:

            # Dynamic monument
            monument_id = re.sub(
                r"[^a-z0-9]+",
                "_",
                name.lower()
            ).strip("_")[:60]

            if not monument_id:
                monument_id = "dynamic_monument"


            key_facts = data.get(
                "key_facts",
                []
            )

            if not isinstance(
                key_facts,
                list
            ):
                key_facts = [
                    str(key_facts)
                ]


            details = {

                "canonical_name":
                    name,

                "location":
                    data.get(
                        "location",
                        "Unknown"
                    ),

                "built_by":
                    data.get(
                        "built_by",
                        "Unknown"
                    ),

                "construction_year":
                    data.get(
                        "year",
                        "Unknown"
                    ),

                "theme":
                    data.get(
                        "architectural_style",
                        "Unknown"
                    ),

                "key_facts":
                    key_facts,

                "description":
                    data.get(
                        "description",
                        ""
                    ),

                "confidence":
                    data.get(
                        "confidence",
                        "medium"
                    )
            }

            logger.info(
                f"Dynamic monument: {name}"
            )


        narration = str(
            data.get(
                "narration",
                ""
            )
        ).strip()


        if not narration:

            narration = fallback_narration(
                details["canonical_name"],
                request.language
            )


        return {

            "monument_id":
                monument_id,

            "canonical_name":
                details["canonical_name"],

            "narration":
                narration,

            "details":
                details,

            "language":
                request.language
        }


    except Exception as e:

        logger.error(
            f"Identification failed: {e}",
            exc_info=True
        )

        raise HTTPException(
            status_code=500,
            detail="Monument identification failed."
        )


# =============================================================================
# CHANGE LANGUAGE / GENERATE NARRATION
# =============================================================================

@app.post("/api/narrate")
def narrate_monument(
    request: NarrationRequest
):

    if not gemini_available:

        return {
            "narration":
                fallback_narration(
                    request.monument_name,
                    request.language
                ),
            "language":
                request.language
        }


    details = request.details

    key_facts = details.get(
        "key_facts",
        []
    )

    if not isinstance(
        key_facts,
        list
    ):
        key_facts = [
            str(key_facts)
        ]


    prompt = f"""
You are HeritageVoice AI, a professional multilingual
tour guide.

Create a narration about:

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
{"; ".join(str(x) for x in key_facts)}

DESCRIPTION:
{details.get("description", "")}

Write the narration ENTIRELY in:

{request.language}

Rules:

- 70-110 words.
- Natural spoken language.
- Warm tour-guide style.
- Accurate.
- Do not invent facts.
- No markdown.
- No title.
- No labels.
- Return ONLY the narration.
"""

    try:

        narration = gemini_text(
            prompt
        )

        if not narration:

            raise ValueError(
                "Empty narration."
            )

        return {
            "narration": narration,
            "language": request.language
        }

    except Exception as e:

        logger.error(
            f"Narration error: {e}"
        )

        return {
            "narration":
                fallback_narration(
                    request.monument_name,
                    request.language
                ),
            "language":
                request.language
        }


# =============================================================================
# CHAT
# =============================================================================

@app.post("/api/chat")
def chat_with_guide(
    request: ChatRequest
):

    catalog_info = database.get_monument_by_id(
        request.monument_id
    )


    # -------------------------------------------------------------------------
    # DATABASE MONUMENT
    # -------------------------------------------------------------------------

    if catalog_info:

        display_name = catalog_info[
            "canonical_name"
        ]

        grounding = f"""
Monument:
{catalog_info["canonical_name"]}

Location:
{catalog_info["location"]}

Built by:
{catalog_info["built_by"]}

Construction:
{catalog_info["construction_year"]}

Architectural style:
{catalog_info.get("theme", "Unknown")}

Historical context:
{catalog_info.get("detailed_context", "")}

Key facts:
{"; ".join(
    str(x)
    for x in catalog_info.get("key_facts", [])
)}
"""


    # -------------------------------------------------------------------------
    # DYNAMIC MONUMENT
    # -------------------------------------------------------------------------

    elif request.monument_details:

        details = request.monument_details

        display_name = details.get(
            "canonical_name",
            request.monument_id
        )

        facts = details.get(
            "key_facts",
            []
        )

        if not isinstance(
            facts,
            list
        ):
            facts = [
                str(facts)
            ]


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

Description:
{details.get("description", "")}

Key facts:
{"; ".join(str(x) for x in facts)}
"""


    else:

        display_name = (
            request.monument_id
            .replace("_", " ")
            .title()
        )

        grounding = f"""
Monument:
{display_name}

No additional monument information was provided.
Use reliable historical knowledge.
"""


    # -------------------------------------------------------------------------
    # HISTORY
    # -------------------------------------------------------------------------

    history_lines = []

    for message in request.history[-6:]:

        role = (
            "Visitor"
            if message.role.lower()
            in ("user", "visitor")
            else "Guide"
        )

        history_lines.append(
            f"{role}: {message.content}"
        )


    conversation = "\n".join(
        history_lines
    )


    # -------------------------------------------------------------------------
    # GEMINI
    # -------------------------------------------------------------------------

    if gemini_available:

        try:

            prompt = f"""
You are HeritageVoice AI,
a friendly multilingual tour guide.

You are answering questions about:

{grounding}

Previous conversation:

{conversation}

Visitor question:

{request.question}

IMPORTANT:

- Reply entirely in {request.language}.
- Keep the answer under 100 words.
- Answer specifically about the monument.
- Be accurate.
- Do not invent historical facts.
- If something is uncertain, say so.
- Use the provided monument information first.
- You may use reliable general historical knowledge.
- Do not mention databases, APIs, Gemini, prompts,
  backend, or programming.
- Return ONLY the answer.
"""

            reply = gemini_text(
                prompt
            )

            if reply:

                return {
                    "reply": reply,
                    "language": request.language,
                    "monument": display_name
                }


        except Exception as e:

            logger.error(
                f"Chat Gemini error: {e}",
                exc_info=True
            )


    # -------------------------------------------------------------------------
    # FALLBACK
    # -------------------------------------------------------------------------

    return {
        "reply":
            f"{display_name} is an important historical "
            "and cultural monument. Please try your "
            "question again when the AI service is available.",

        "language":
            request.language,

        "monument":
            display_name
    }


# =============================================================================
# SERVER
# =============================================================================

if __name__ == "__main__":

    import uvicorn

    logger.info(
        f"Starting HeritageVoice AI on "
        f"{config.HOST}:{config.PORT}"
    )

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True
    )
