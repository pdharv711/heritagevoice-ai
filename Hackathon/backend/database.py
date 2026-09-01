from typing import Dict, Any, Optional


# =============================================================================
# CURATED MONUMENT DATABASE
# =============================================================================
# This database is used for factual grounding (RAG-style).
# Gemini may identify monuments that are not present here, but when a monument
# exists in this catalog, its information is supplied to Gemini to reduce
# hallucination.


MONUMENT_CATALOG: Dict[str, Dict[str, Any]] = {

    # =========================================================================
    # TAJ MAHAL
    # =========================================================================

    "taj_mahal": {
        "canonical_name": "Taj Mahal",
        "location": "Agra, Uttar Pradesh, India",
        "built_by": "Mughal Emperor Shah Jahan",
        "construction_year": "Completed around 1648 AD (started in 1631 AD)",
        "theme": "Mughal Architecture with Persian, Islamic and Indian influences",

        "key_facts": [
            "It was commissioned by Shah Jahan as a mausoleum for Mumtaz Mahal.",
            "It is primarily constructed from white Makrana marble.",
            "The complex is a UNESCO World Heritage Site.",
            "The principal designer is widely associated with Ustad Ahmad Lahori."
        ],

        "detailed_context": (
            "The Taj Mahal is an ivory-white marble mausoleum on the south bank "
            "of the Yamuna River in Agra. Mughal Emperor Shah Jahan commissioned "
            "it in memory of his wife Mumtaz Mahal. The monument forms the "
            "centre of a large complex containing gardens, a mosque and a "
            "guest house. Its architecture combines Persian, Islamic and "
            "Indian traditions."
        )
    },


    # =========================================================================
    # RED FORT
    # =========================================================================

    "red_fort": {
        "canonical_name": "Red Fort",
        "location": "Delhi, India",
        "built_by": "Mughal Emperor Shah Jahan",
        "construction_year": "Completed around 1648 AD (started in 1638 AD)",
        "theme": "Mughal Architecture",

        "key_facts": [
            "It served as an important residence of the Mughal emperors.",
            "The fort is famous for its red sandstone walls.",
            "The Prime Minister of India traditionally addresses the nation from the Red Fort on Independence Day.",
            "It is part of the UNESCO World Heritage Site designation."
        ],

        "detailed_context": (
            "The Red Fort, also known as Lal Qila, is a historic fort complex "
            "in Old Delhi. Emperor Shah Jahan commissioned its construction "
            "when he moved his capital from Agra to Delhi. The fort represents "
            "the height of Mughal architectural development under Shah Jahan."
        )
    },


    # =========================================================================
    # KONARK SUN TEMPLE
    # =========================================================================

    "sun_temple": {
        "canonical_name": "Konark Sun Temple",
        "location": "Konark, Odisha, India",
        "built_by": "King Narasimhadeva I of the Eastern Ganga Dynasty",
        "construction_year": "Around 1250 AD",
        "theme": "Kalinga Architecture",

        "key_facts": [
            "The temple is designed as a colossal chariot dedicated to Surya, the Sun God.",
            "Its design includes 24 richly carved stone wheels.",
            "The monument is a UNESCO World Heritage Site.",
            "The temple is an important example of medieval Kalinga architecture."
        ],

        "detailed_context": (
            "The Konark Sun Temple is a 13th-century temple dedicated to the "
            "Hindu Sun God Surya. It was built during the reign of King "
            "Narasimhadeva I of the Eastern Ganga dynasty. The surviving "
            "structure resembles a monumental stone chariot with carved wheels "
            "and horses."
        )
    },


    # =========================================================================
    # VIRUPAKSHA TEMPLE
    # =========================================================================

    "hampi": {
        "canonical_name": "Virupaksha Temple, Hampi",
        "location": "Hampi, Karnataka, India",
        "built_by": "Vijayanagara rulers, with earlier foundations and later expansions",
        "construction_year": "Early medieval origins; greatly expanded during the Vijayanagara period",
        "theme": "Vijayanagara / Dravidian Architecture",

        "key_facts": [
            "The temple is dedicated to Virupaksha, a form of Lord Shiva.",
            "It is one of the most important surviving monuments of Hampi.",
            "The temple complex contains a large gopuram and richly decorated halls.",
            "Hampi is a UNESCO World Heritage Site."
        ],

        "detailed_context": (
            "Virupaksha Temple is an active Hindu temple in Hampi, Karnataka. "
            "It is dedicated to Virupaksha, a form of Shiva, and is closely "
            "associated with the Vijayanagara Empire. The temple survived the "
            "destruction of Hampi in the 16th century and continues to function "
            "as a place of worship."
        )
    },


    # =========================================================================
    # QUTUB MINAR
    # =========================================================================

    "qutub_minar": {
        "canonical_name": "Qutub Minar",
        "location": "New Delhi, India",
        "built_by": "Qutb-ud-din Aibak and later rulers including Iltutmish",
        "construction_year": "Construction began around 1199 AD",
        "theme": "Indo-Islamic Architecture",

        "key_facts": [
            "The Qutub Minar is approximately 72.5 metres tall.",
            "It has five main storeys.",
            "It is part of the Qutb complex.",
            "The Qutb complex is a UNESCO World Heritage Site."
        ],

        "detailed_context": (
            "The Qutub Minar is a monumental minaret in the Qutb complex of "
            "Delhi. Construction was initiated by Qutb-ud-din Aibak and the "
            "tower was later completed and modified by subsequent rulers. "
            "Its architecture combines Indo-Islamic decorative elements."
        )
    },


    # =========================================================================
    # GATEWAY OF INDIA
    # =========================================================================

    "gateway_of_india": {
        "canonical_name": "Gateway of India",
        "location": "Mumbai, Maharashtra, India",
        "built_by": "British colonial government; designed by architect George Wittet",
        "construction_year": "Completed in 1924",
        "theme": "Indo-Saracenic Architecture",

        "key_facts": [
            "It stands on the waterfront at Apollo Bunder in Mumbai.",
            "It was designed by architect George Wittet.",
            "The monument commemorates the 1911 visit of King George V and Queen Mary to India.",
            "It later became associated with the departure of the last British troops from India."
        ],

        "detailed_context": (
            "The Gateway of India is a monumental arch on Mumbai's waterfront. "
            "It was designed by George Wittet in an Indo-Saracenic architectural "
            "style and completed in 1924. It became one of Mumbai's most "
            "recognizable landmarks."
        )
    },


    # =========================================================================
    # INDIA GATE
    # =========================================================================

    "india_gate": {
        "canonical_name": "India Gate",
        "location": "New Delhi, India",
        "built_by": "Designed by Sir Edwin Lutyens",
        "construction_year": "Completed in 1931",
        "theme": "Neoclassical / War Memorial Architecture",

        "key_facts": [
            "It is a war memorial in central New Delhi.",
            "It commemorates Indian soldiers who died in the First World War and other conflicts.",
            "The names of many soldiers are inscribed on the monument.",
            "The Amar Jawan Jyoti was established here in 1972."
        ],

        "detailed_context": (
            "India Gate is a large war memorial located in the heart of New "
            "Delhi. It was designed by Sir Edwin Lutyens and completed in 1931. "
            "The monument commemorates Indian soldiers who served and died "
            "during the First World War and related campaigns."
        )
    },


    # =========================================================================
    # SANCHI STUPA
    # =========================================================================

    "sanchi_stupa": {
        "canonical_name": "Great Stupa at Sanchi",
        "location": "Sanchi, Madhya Pradesh, India",
        "built_by": "Commissioned by Emperor Ashoka",
        "construction_year": "Originally constructed in the 3rd century BCE; later enlarged",
        "theme": "Buddhist Architecture",

        "key_facts": [
            "The Great Stupa is one of India's oldest surviving stone structures.",
            "It is associated with Emperor Ashoka and the spread of Buddhism.",
            "The gateways are richly decorated with Buddhist narrative carvings.",
            "The Buddhist Monuments at Sanchi are a UNESCO World Heritage Site."
        ],

        "detailed_context": (
            "The Great Stupa at Sanchi is one of the most important surviving "
            "Buddhist monuments in India. Its earliest core dates to the reign "
            "of Emperor Ashoka in the 3rd century BCE. The monument was later "
            "expanded and surrounded by elaborately carved gateways."
        )
    },


    # =========================================================================
    # AJANTA CAVES
    # =========================================================================

    "ajanta_caves": {
        "canonical_name": "Ajanta Caves",
        "location": "Aurangabad district, Maharashtra, India",
        "built_by": "Buddhist monastic communities under various patronage",
        "construction_year": "Developed mainly from the 2nd century BCE to about the 5th century CE",
        "theme": "Buddhist Rock-Cut Architecture",

        "key_facts": [
            "The caves contain important Buddhist paintings and sculptures.",
            "Many paintings depict stories associated with the Jataka tales.",
            "The caves were carved into a horseshoe-shaped cliff.",
            "The Ajanta Caves are a UNESCO World Heritage Site."
        ],

        "detailed_context": (
            "The Ajanta Caves are a group of Buddhist rock-cut caves in "
            "Maharashtra. They contain monasteries, prayer halls, sculptures "
            "and famous ancient paintings. The surviving artworks provide "
            "important evidence about Buddhist culture and Indian artistic "
            "traditions."
        )
    },


    # =========================================================================
    # ELLORA CAVES
    # =========================================================================

    "ellora_caves": {
        "canonical_name": "Ellora Caves",
        "location": "Verul, Maharashtra, India",
        "built_by": "Various Buddhist, Hindu and Jain patrons",
        "construction_year": "Developed mainly between the 6th and 10th centuries CE",
        "theme": "Rock-Cut Buddhist, Hindu and Jain Architecture",

        "key_facts": [
            "The complex contains Buddhist, Hindu and Jain monuments.",
            "The Kailasa Temple is one of the most remarkable structures at Ellora.",
            "The Kailasa Temple was carved directly from the surrounding rock.",
            "Ellora is a UNESCO World Heritage Site."
        ],

        "detailed_context": (
            "The Ellora Caves form a major rock-cut architectural complex in "
            "Maharashtra. The site includes Buddhist, Hindu and Jain monuments. "
            "The Kailasa Temple is particularly famous for being carved from "
            "a single mass of rock."
        )
    },


    # =========================================================================
    # MYSORE PALACE
    # =========================================================================

    "mysore_palace": {
        "canonical_name": "Mysore Palace",
        "location": "Mysuru, Karnataka, India",
        "built_by": "Wadiyar dynasty; current palace designed by Henry Irwin",
        "construction_year": "Current structure completed in 1912",
        "theme": "Indo-Saracenic Architecture",

        "key_facts": [
            "It was the principal palace of the Wadiyar dynasty.",
            "The current structure was designed by British architect Henry Irwin.",
            "The palace combines Indo-Saracenic, Hindu, Islamic and Gothic elements.",
            "It is one of India's most visited heritage attractions."
        ],

        "detailed_context": (
            "Mysore Palace is the former royal residence of the Wadiyar dynasty "
            "in Mysuru. The current building was designed by Henry Irwin and "
            "completed in the early 20th century. Its architecture combines "
            "several Indian and European architectural traditions."
        )
    },


    # =========================================================================
    # CHARMINAR
    # =========================================================================

    "charminar": {
        "canonical_name": "Charminar",
        "location": "Hyderabad, Telangana, India",
        "built_by": "Muhammad Quli Qutb Shah",
        "construction_year": "Completed around 1591 AD",
        "theme": "Indo-Islamic Architecture",

        "key_facts": [
            "The monument has four grand minarets, giving it the name Charminar.",
            "It was commissioned by Muhammad Quli Qutb Shah.",
            "It is one of the most recognizable landmarks of Hyderabad.",
            "The structure combines Islamic architectural traditions with local influences."
        ],

        "detailed_context": (
            "Charminar is a historic monument and mosque in Hyderabad. It was "
            "commissioned by Muhammad Quli Qutb Shah in the late 16th century. "
            "Its four prominent minarets and monumental arches have made it "
            "an enduring symbol of Hyderabad."
        )
    },


    # =========================================================================
    # GOL GUMBAZ
    # =========================================================================

    "gol_gumbaz": {
        "canonical_name": "Gol Gumbaz",
        "location": "Vijayapura, Karnataka, India",
        "built_by": "Sultan Mohammed Adil Shah of the Adil Shahi dynasty",
        "construction_year": "17th century; completed around 1656 AD",
        "theme": "Indo-Islamic / Deccan Architecture",

        "key_facts": [
            "It is the mausoleum of Sultan Mohammed Adil Shah.",
            "Its enormous dome is one of the largest masonry domes in the world.",
            "The structure is famous for its acoustic gallery.",
            "It is an important example of Deccan Sultanate architecture."
        ],

        "detailed_context": (
            "Gol Gumbaz is the mausoleum of Mohammed Adil Shah in Vijayapura, "
            "Karnataka. The monument is famous for its huge dome and the "
            "whispering gallery around the inner circumference of the structure."
        )
    },


    # =========================================================================
    # VICTORIA MEMORIAL
    # =========================================================================

    "victoria_memorial": {
        "canonical_name": "Victoria Memorial",
        "location": "Kolkata, West Bengal, India",
        "built_by": "British Indian government; designed by William Emerson",
        "construction_year": "Completed in 1921",
        "theme": "Indo-Saracenic / Revival Architecture",

        "key_facts": [
            "It was built in memory of Queen Victoria.",
            "The building is made largely from white Makrana marble.",
            "It was designed by architect William Emerson.",
            "The memorial contains a museum and extensive collections."
        ],

        "detailed_context": (
            "Victoria Memorial is a large marble monument in Kolkata built "
            "in memory of Queen Victoria. Designed by William Emerson, the "
            "building incorporates Indo-Saracenic and European architectural "
            "features and now functions as a museum and cultural institution."
        )
    },


    # =========================================================================
    # PRATAPGAD FORT
    # =========================================================================

    "pratapgad_fort": {
        "canonical_name": "Pratapgad Fort",
        "location": "Satara district, Maharashtra, India",
        "built_by": "Maratha ruler Chhatrapati Shivaji Maharaj",
        "construction_year": "Completed around 1658 AD",
        "theme": "Maratha Fort Architecture",

        "key_facts": [
            "The fort was built during the reign of Chhatrapati Shivaji Maharaj.",
            "It is associated with the Battle of Pratapgad in 1659.",
            "The fort occupies a strategically important hill location.",
            "It is an important example of Maratha military architecture."
        ],

        "detailed_context": (
            "Pratapgad is a hill fort in Maharashtra associated with the rise "
            "of the Maratha kingdom. It was constructed under Chhatrapati "
            "Shivaji Maharaj and became famous for the Battle of Pratapgad "
            "in 1659."
        )
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_monument_by_id(monument_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve monument details by ID."""
    if not monument_id:
        return None

    return MONUMENT_CATALOG.get(
        monument_id.strip().lower()
    )


def search_monument(query: str) -> Optional[str]:
    """
    Find a monument ID from a user query or monument name.
    """

    if not query:
        return None

    query = query.lower().strip()

    # Exact ID / canonical name first
    for key, data in MONUMENT_CATALOG.items():

        canonical_name = data.get(
            "canonical_name",
            ""
        ).lower()

        if key == query:
            return key

        if canonical_name == query:
            return key

        if canonical_name in query:
            return key

    # Keyword matching
    query_words = {
        word
        for word in query.split()
        if len(word) > 3
    }

    best_match = None
    best_score = 0

    for key, data in MONUMENT_CATALOG.items():

        searchable_text = " ".join([
            key,
            data.get("canonical_name", ""),
            data.get("location", ""),
            data.get("built_by", ""),
            data.get("theme", ""),
        ]).lower()

        score = sum(
            1
            for word in query_words
            if word in searchable_text
        )

        if score > best_score:
            best_score = score
            best_match = key

    return best_match if best_score > 0 else None
