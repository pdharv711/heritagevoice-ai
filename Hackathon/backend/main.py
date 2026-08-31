
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
# Google Gen AI SDK
# =============================================================================

try:
    from google import genai
    from google.genai import types as genai_types

    NEW_SDK = True

except ImportError:
    NEW_SDK = False


# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="HeritageVoice AI API",
    description="Multilingual AI-powered Tour Guide — Any Monument Recognition",
    version="3.0.0"
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
# Gemini Configuration
# =============================================================================

gemini_client = None
gemini_available = False

# Stable Gemini model with multimodal/vision support.
GEMINI_MODEL = "gemini-3.6-flash"


if config.GEMINI_API_KEY and NEW_SDK:

    try:

        gemini_client = genai.Client(
            api_key=config.GEMINI_API_KEY
        )

        gemini_available = True

        logger.info(
            f"Gemini client ready "
            f"(model: {GEMINI_MODEL})"
        )

    except Exception as e:

        logger.error(
            f"Gemini initialization error: {e}"
        )

elif not NEW_SDK:

    logger.error(
        "google-genai package not installed. "
        "Run: pip install google-genai"
    )

else:

    logger.warning(
        "GEMINI_API_KEY not set — Demo Mode."
    )


# =============================================================================
# Pydantic Schemas
# =============================================================================

class IdentifyRequest(BaseModel):

    image: str = Field(
        ...,
        description="Base64 encoded image (data URI or raw base64)"
    )

    language: str = Field(
        "English",
        description="Target language for narration"
    )


class ChatMessage(BaseModel):

    role: str = Field(
        "user"
    )

    content: str = Field(
        ...
    )


class ChatRequest(BaseModel):

    monument_id: str

    question: str

    language: str = Field(
        "English"
    )

    history: List[ChatMessage] = Field(
        default_factory=list
    )

    # Important for monuments that are NOT in database.py
    monument_details: Optional[Dict[str, Any]] = None


class NarrationRequest(BaseModel):

    monument_name: str

    language: str = Field(
        "English"
    )

    details: Dict[str, Any]


# =============================================================================
# Supported Languages
# =============================================================================

SUPPORTED_LANGUAGES = [
    "English",
    "Hindi",
    "Gujarati",
    "Tamil",
    "Telugu",
    "Bengali",
    "Marathi",
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
# Mock Narrations
# =============================================================================

MOCK_NARRATIONS: Dict[str, str] = {

    "English":
        "Welcome to {name}! Located in {location}, "
        "this remarkable monument was built by {built_by} "
        "around {construction}. Key fact: {key_fact}",

    "Hindi":
        "{name} में आपका स्वागत है! {location} में स्थित "
        "यह ऐतिहासिक स्मारक {built_by} द्वारा {construction} "
        "के आसपास बनाया गया था। मुख्य तथ्य: {key_fact}",

    "Gujarati":
        "{name} માં આપનું સ્વાગત છે! {location} માં આવેલું "
        "આ ઐતિહાસિક સ્મારક {built_by} દ્વારા {construction} "
        "ની આસપાસ બનાવવામાં આવ્યું હતું. મુખ્ય હકીકત: {key_fact}",

    "Tamil":
        "{name}-க்கு வரவேற்கிறோம்! {location}-ல் அமைந்துள்ள "
        "இந்த வரலாற்றுச் சின்னம் {built_by} அவர்களால் "
        "{construction} காலத்தில் கட்டப்பட்டது. முக்கிய தகவல்: {key_fact}",

    "Telugu":
        "{name} కు స్వాగతం! {location}లో ఉన్న ఈ చారిత్రక "
        "కట్టడం {built_by} చేత {construction} కాలంలో నిర్మించబడింది. "
        "ముఖ్య విషయం: {key_fact}",

    "Bengali":
        "{name}-এ স্বাগত! {location}-এ অবস্থিত এই ঐতিহাসিক "
        "স্থাপনাটি {built_by} দ্বারা {construction} সময়ে নির্মিত। "
        "গুরুত্বপূর্ণ তথ্য: {key_fact}",

    "Marathi":
        "{name} मध्ये आपले स्वागत आहे! {location} येथे असलेले "
        "हे ऐतिहासिक स्मारक {built_by} यांनी {construction} "
        "च्या सुमारास बांधले. महत्त्वाची माहिती: {key_fact}",

    "Kannada":
        "{name} ಗೆ ಸ್ವಾಗತ! {location} ನಲ್ಲಿ ಇರುವ ಈ ಐತಿಹಾಸಿಕ "
        "ಸ್ಮಾರಕವನ್ನು {built_by} ಅವರು {construction} ರಲ್ಲಿ "
        "ನಿರ್ಮಿಸಿದರು. ಪ್ರಮುಖ ಮಾಹಿತಿ: {key_fact}",

    "Punjabi":
        "{name} ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ! {location} ਵਿੱਚ ਸਥਿਤ "
        "ਇਹ ਇਤਿਹਾਸਕ ਸਮਾਰਕ {built_by} ਦੁਆਰਾ {construction} "
        "ਦੇ ਆਸ-ਪਾਸ ਬਣਾਇਆ ਗਿਆ ਸੀ। ਮੁੱਖ ਤੱਥ: {key_fact}",

    "French":
        "Bienvenue à {name}! Situé à {location}, "
        "ce monument historique a été construit par {built_by} "
        "vers {construction}. Fait important: {key_fact}",

    "Spanish":
        "¡Bienvenido a {name}! Situado en {location}, "
        "este monumento histórico fue construido por {built_by} "
        "alrededor de {construction}. Dato importante: {key_fact}",

    "German":
        "Willkommen bei {name}! Dieses historische Monument "
        "befindet sich in {location} und wurde von {built_by} "
        "um {construction} errichtet. Interessante Tatsache: {key_fact}",

    "Arabic":
        "مرحباً بكم في {name}! يقع هذا المعلم التاريخي في "
        "{location} وقد بناه {built_by} حوالي {construction}. "
        "حقيقة مهمة: {key_fact}",

    "Japanese":
        "{name}へようこそ！{location}に位置するこの歴史的建造物は、"
        "{built_by}によって{construction}頃に建設されました。"
        "重要な事実：{key_fact}",

    "Korean":
        "{name}에 오신 것을 환영합니다! {location}에 위치한 "
        "이 역사적인 기념물은 {built_by}가 {construction}경에 "
        "건설했습니다. 중요한 사실: {key_fact}",

    "Portuguese":
        "Bem-vindo a {name}! Localizado em {location}, "
        "este monumento histórico foi construído por {built_by} "
        "por volta de {construction}. Fato importante: {key_fact}",

    "Russian":
        "Добро пожаловать в {name}! Этот исторический памятник "
        "находится в {location} и был построен {built_by} "
        "примерно в {construction}. Важный факт: {key_fact}",

    "Italian":
        "Benvenuti a {name}! Situato a {location}, "
        "questo monumento storico fu costruito da {built_by} "
        "intorno a {construction}. Fatto importante: {key_fact}",
}


# =============================================================================
# Helper: Clean Base64 Image
# =============================================================================

def clean_base64_image(b64: str) -> bytes:

    if "," in b64:

        b64 = b64.split(",", 1)[1]

    b64 = b64.strip()

    # Fix missing Base64 padding
    b64 += "=" * (-len(b64) % 4)

    return base64.b64decode(b64)


# =============================================================================
# Helper: Extract JSON from Gemini Response
# =============================================================================

def extract_json(text: str) -> Optional[Dict]:

    if not text:
        return None

    text = text.strip()

    # Strategy 1: Direct JSON
    try:

        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except Exception:
        pass

    # Strategy 2: Markdown JSON block
    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL
    )

    if match:

        try:

            result = json.loads(match.group(1))

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    # Strategy 3: Find JSON object
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
# Gemini Text Request
# =============================================================================

def gemini_text(prompt: str) -> str:

    if not gemini_client:

        raise RuntimeError(
            "Gemini client is not available."
        )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return (response.text or "").strip()


# =============================================================================
# Gemini Vision Request
# =============================================================================

def gemini_vision(
    pil_image: Image.Image,
    prompt: str
) -> str:

    if not gemini_client:

        raise RuntimeError(
            "Gemini client is not available."
        )

    # Always send JPEG for predictable size and MIME type.
    buffer = BytesIO()

    pil_image.save(
        buffer,
        format="JPEG",
        quality=85,
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
                parts=[
                    image_part,
                    text_part
                ],
                role="user"
            )
        ],
    )

    return (response.text or "").strip()


# =============================================================================
# Mock Narration
# =============================================================================

def mock_narration(
    info: Dict,
    language: str
) -> str:

    template = MOCK_NARRATIONS.get(
        language,
        MOCK_NARRATIONS["English"]
    )

    facts = info.get(
        "key_facts",
        []
    )

    if not facts:

        facts = [
            "a remarkable historical site."
        ]

    fact = facts[0]

    return template.format(
        name=info.get(
            "canonical_name",
            info.get(
                "name",
                "this monument"
            )
        ),

        location=info.get(
            "location",
            "an unknown location"
        ),

        built_by=info.get(
            "built_by",
            "unknown builders"
        ),

        construction=info.get(
            "construction_year",
            info.get(
                "year",
                "an unknown era"
            )
        ),

        key_fact=fact
    )


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/")
def root():

    return {
        "status": "online",

        "sdk":
            "google-genai (new)"
            if NEW_SDK
            else "missing",

        "gemini_available":
            gemini_available,

        "model":
            GEMINI_MODEL,

        "mode":
            "Live AI"
            if gemini_available
            else "Demo Mock",

        "version":
            "3.0.0"
    }


# =============================================================================
# Monument Catalog Endpoint
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

    """
    Identify ANY recognizable monument using Gemini Vision.

    The same Gemini request also generates narration in the
    requested language, reducing latency compared with making
    two separate AI calls.
    """

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

        # Convert to RGB
        if pil_image.mode != "RGB":

            pil_image = pil_image.convert(
                "RGB"
            )

        # Resize large images
        max_size = 1280

        if max(pil_image.size) > max_size:

            pil_image.thumbnail(
                (max_size, max_size),
                Image.Resampling.LANCZOS
            )

        logger.info(
            f"Image received: {pil_image.size}"
        )

    except Exception as e:

        logger.error(
            f"Image decode error: {e}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid image. "
                "Please upload a valid JPEG or PNG."
            )
        )


    # -------------------------------------------------------------------------
    # Gemini unavailable
    # -------------------------------------------------------------------------

    if not gemini_available:

        return {

            "monument_id":
                "unknown",

            "canonical_name":
                "AI unavailable",

            "narration":
                "The AI service is currently unavailable.",

            "details":
                None
        }


    # -------------------------------------------------------------------------
    # Open-ended worldwide monument recognition
    # -------------------------------------------------------------------------

    try:

        logger.info(
            "Calling Gemini Vision..."
        )

        language = request.language

        prompt = f"""
You are HeritageVoice AI, an expert worldwide monument
and historical landmark recognition system.

Analyze the image carefully and identify the SPECIFIC
monument, landmark, historical structure, archaeological
site, temple, mosque, church, fort, palace, memorial,
statue, tower, gate, stepwell, cave, bridge, or other
heritage structure shown.

IMPORTANT IDENTIFICATION RULES:

1. Do NOT restrict yourself to a predefined database.
2. Do NOT restrict yourself to famous monuments.
3. Consider monuments from India and every other country.
4. Try to recognize regional and lesser-known monuments.
5. Examine:
   - architecture
   - carvings
   - columns
   - domes
   - towers
   - sculptures
   - inscriptions
   - materials
   - surrounding landscape
   - colors
   - structure layout
   - visual landmarks
6. Use your historical knowledge to compare the visual evidence.
7. If you cannot determine the exact monument, provide the
   most likely identification and use a lower confidence.
8. Do NOT invent an unrelated monument.
9. If there is genuinely no recognizable landmark, return
   "Unknown Monument".

Return ONLY valid JSON.

Use EXACTLY this structure:

{{
    "name": "specific official monument name",
    "location": "city, state/region, country if known",
    "built_by": "ruler, dynasty, kingdom, architect,
organization or unknown",
    "year": "construction date or historical period",
    "architectural_style": "architectural style",
    "key_facts": [
        "important historical fact",
        "important architectural or cultural fact",
        "interesting visitor fact"
    ],
    "description": "Short accurate description of the monument.",
    "confidence": "high",
    "narration": "Tour guide narration entirely in {language}"
}}

CONFIDENCE:

Use "high" only when the visual evidence strongly supports
the identification.

Use "medium" when the identification is likely but not certain.

Use "low" when there is limited evidence.

NARRATION:

Write the narration entirely in {language}.

The narration must:

- Be approximately 70-110 words.
- Sound natural when spoken aloud.
- Be interesting for tourists.
- Mention the monument name.
- Mention its location when known.
- Include important historical information.
- Avoid unsupported claims.
- Use a warm tour-guide tone.
- Contain no markdown.
- Contain no headings.
- Not mention Gemini or AI.

If the exact monument cannot be identified confidently,
be honest about the uncertainty instead of inventing facts.
"""

        raw_response = gemini_vision(
            pil_image,
            prompt
        )

        logger.info(
            "Gemini response received."
        )

        logger.info(
            f"Response preview: "
            f"{raw_response[:500]}"
        )

        parsed = extract_json(
            raw_response
        )

        if not parsed:

            raise ValueError(
                "Gemini returned invalid JSON."
            )


        # ---------------------------------------------------------------------
        # Extract identification
        # ---------------------------------------------------------------------

        name = str(
            parsed.get(
                "name",
                ""
            )
        ).strip()

        if not name:

            raise ValueError(
                "Gemini did not return a monument name."
            )


        # ---------------------------------------------------------------------
        # Match database if possible
        # ---------------------------------------------------------------------

        catalog_key = database.search_monument(
            name.lower()
        )


        # ---------------------------------------------------------------------
        # Known monument
        # ---------------------------------------------------------------------

        if catalog_key:

            monument_id = catalog_key

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
                    catalog_info[
                        "theme"
                    ],

                "key_facts":
                    catalog_info[
                        "key_facts"
                    ],

                "detailed_context":
                    catalog_info[
                        "detailed_context"
                    ]
            }

            logger.info(
                f"Matched database monument: "
                f"{effective['canonical_name']}"
            )


        # ---------------------------------------------------------------------
        # Dynamic monument — NOT in database
        # ---------------------------------------------------------------------

        else:

            monument_id = re.sub(
                r"[^a-z0-9]+",
                "_",
                name.lower()
            ).strip("_")[:60]

            if not monument_id:

                monument_id = "dynamic_monument"

            effective = {

                "canonical_name":
                    name,

                "location":
                    parsed.get(
                        "location",
                        "Unknown"
                    ),

                "built_by":
                    parsed.get(
                        "built_by",
                        "Unknown"
                    ),

                "construction_year":
                    parsed.get(
                        "year",
                        "Unknown"
                    ),

                "theme":
                    parsed.get(
                        "architectural_style",
                        "Unknown"
                    ),

                "key_facts":
                    parsed.get(
                        "key_facts",
                        []
                    ),

                "detailed_context":
                    parsed.get(
                        "description",
                        ""
                    )
            }

            logger.info(
                f"Dynamic monument: "
                f"{effective['canonical_name']}"
            )


        # ---------------------------------------------------------------------
        # Narration from same Gemini call
        # ---------------------------------------------------------------------

        narration = str(
            parsed.get(
                "narration",
                ""
            )
        ).strip()

        if not narration:

            narration = mock_narration(
                effective,
                language
            )


        confidence = str(
            parsed.get(
                "confidence",
                "medium"
            )
        ).lower()

        if confidence not in (
            "high",
            "medium",
            "low"
        ):

            confidence = "medium"


        # ---------------------------------------------------------------------
        # Return result
        # ---------------------------------------------------------------------

        return {

            "monument_id":
                monument_id,

            "canonical_name":
                effective[
                    "canonical_name"
                ],

            "narration":
                narration,

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
                    confidence
            }
        }


    except Exception as e:

        logger.error(
            f"Monument identification failed: {e}",
            exc_info=True
        )

        return {

            "monument_id":
                "unknown",

            "canonical_name":
                "Monument Not Recognized",

            "narration":
                (
                    "I could not confidently identify this "
                    "monument. Please try a clearer photo "
                    "where the monument is prominently visible."
                ),

            "details":
                None
        }


# =============================================================================
# CHANGE NARRATION LANGUAGE
# =============================================================================

@app.post("/api/narrate")
def generate_narration(
    request: NarrationRequest
):

    """
    Generate narration in a different language WITHOUT
    analyzing the image again.
    """

    if not gemini_available:

        return {

            "narration":
                mock_narration(
                    {
                        "canonical_name":
                            request.monument_name,

                        **request.details
                    },

                    request.language
                ),

            "language":
                request.language
        }


    try:

        details = request.details

        prompt = f"""
You are HeritageVoice AI, a multilingual historical
tour guide.

Create an engaging narration about this monument.

MONUMENT:
{request.monument_name}

LOCATION:
{details.get("location", "Unknown")}

BUILT BY:
{details.get("built_by", "Unknown")}

CONSTRUCTION PERIOD:
{details.get("construction_year", "Unknown")}

ARCHITECTURAL STYLE:
{details.get("theme", "Unknown")}

KEY FACTS:
{details.get("key_facts", [])}

DESCRIPTION:
{details.get("description", "")}

Write the narration ENTIRELY in:

{request.language}

Rules:

- 70-110 words.
- Natural spoken language.
- Warm tour-guide style.
- Interesting for visitors.
- Mention the monument name.
- Include historical information.
- Do not invent facts.
- Do not use markdown.
- Do not add headings.
- Return ONLY the narration.
"""

        narration = gemini_text(
            prompt
        )

        if not narration:

            raise ValueError(
                "Empty narration returned."
            )

        return {

            "narration":
                narration,

            "language":
                request.language
        }


    except Exception as e:

        logger.error(
            f"Language narration failed: {e}",
            exc_info=True
        )

        return {

            "narration":
                mock_narration(
                    {
                        "canonical_name":
                            request.monument_name,

                        **request.details
                    },

                    request.language
                ),

            "language":
                request.language
        }


# =============================================================================
# CHAT WITH GUIDE
# =============================================================================

@app.post("/api/chat")
def chat_with_guide(
    request: ChatRequest
):

    """
    Multilingual follow-up Q&A about ANY identified monument.

    Supports both:
    1. Monuments stored in database.py
    2. Dynamically identified monuments
    """

    # -------------------------------------------------------------------------
    # Find database information
    # -------------------------------------------------------------------------

    catalog_info = (
        database.get_monument_by_id(
            request.monument_id
        )
    )


    # -------------------------------------------------------------------------
    # Build grounding information
    # -------------------------------------------------------------------------

    if catalog_info:

        display_name = (
            catalog_info[
                "canonical_name"
            ]
        )

        grounding = (
            f"Monument: "
            f"{catalog_info['canonical_name']}\n"

            f"Location: "
            f"{catalog_info['location']}\n"

            f"Built by: "
            f"{catalog_info['built_by']}\n"

            f"Construction: "
            f"{catalog_info['construction_year']}\n"

            f"Architectural context: "
            f"{catalog_info.get('theme', 'Unknown')}\n"

            f"Historical context: "
            f"{catalog_info['detailed_context']}\n"

            f"Key facts: "
            f"{'; '.join(catalog_info['key_facts'])}"
        )


    elif request.monument_details:

        # Dynamic monument not stored in database

        details = request.monument_details

        display_name = details.get(
            "canonical_name",
            request.monument_id
                .replace("_", " ")
                .title()
        )

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

        grounding = (

            f"Monument: "
            f"{display_name}\n"

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
            f"{'; '.join(str(x) for x in key_facts)}"
        )


    else:

        display_name = (
            request.monument_id
                .replace("_", " ")
                .title()
        )

        grounding = (
            f"Monument: {display_name}\n"
            f"No local information is available. "
            f"Use reliable historical knowledge."
        )


    # -------------------------------------------------------------------------
    # Conversation history
    # -------------------------------------------------------------------------

    history_lines = []

    for message in request.history[-6:]:

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


    # -------------------------------------------------------------------------
    # Gemini Chat
    # -------------------------------------------------------------------------

    reply = ""

    if gemini_available:

        try:

            prompt = f"""
You are HeritageVoice AI, a knowledgeable,
friendly multilingual tour guide.

The visitor is currently learning about:

{grounding}

Previous conversation:

{conversation}

New visitor question:

{request.question}

IMPORTANT RULES:

1. Reply entirely in {request.language}.
2. Keep the answer under 100 words.
3. Be conversational and easy to understand.
4. Answer specifically about the monument.
5. Use the supplied monument information when available.
6. Do not invent historical facts.
7. If information is uncertain, say so clearly.
8. You may use general historical knowledge when appropriate.
9. Do not mention databases, APIs, prompts, Gemini,
   backend systems, or internal implementation.
10. Return ONLY the guide's answer.
"""

            reply = gemini_text(
                prompt
            )


        except Exception as e:

            logger.error(
                f"Chat failed: {e}",
                exc_info=True
            )


    # -------------------------------------------------------------------------
    # Fallback
    # -------------------------------------------------------------------------

    if not reply:

        question_lower = (
            request.question.lower()
        )


        if catalog_info:

            if any(
                word in question_lower
                for word in (
                    "who",
                    "built",
                    "creator",
                    "builder"
                )
            ):

                reply = (
                    f"It was built by "
                    f"{catalog_info['built_by']}."
                )


            elif any(
                word in question_lower
                for word in (
                    "when",
                    "year",
                    "old",
                    "age"
                )
            ):

                reply = (
                    f"Its construction dates to "
                    f"{catalog_info['construction_year']}."
                )


            elif any(
                word in question_lower
                for word in (
                    "where",
                    "location",
                    "city"
                )
            ):

                reply = (
                    f"It is located in "
                    f"{catalog_info['location']}."
                )


            elif catalog_info.get(
                "key_facts"
            ):

                reply = (
                    "One important highlight is: "
                    f"{catalog_info['key_facts'][0]}"
                )


            else:

                reply = (
                    f"{display_name} is a significant "
                    "historical monument."
                )


        elif request.monument_details:

            facts = request.monument_details.get(
                "key_facts",
                []
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


        else:

            reply = (
                f"I don't have enough information about "
                f"{display_name} to answer that accurately."
            )


    return {

        "reply":
            reply,

        "language":
            request.language,

        "monument":
            display_name
    }


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
def health_check():

    return {

        "status":
            "healthy",

        "gemini_available":
            gemini_available,

        "model":
            GEMINI_MODEL
    }


# =============================================================================
# Start Server
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
        reload=True
    )
````

