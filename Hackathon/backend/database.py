from typing import Dict, Any, Optional

# Curated monument database for factual grounding (RAG-style)
MONUMENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "taj_mahal": {
        "canonical_name": "Taj Mahal",
        "location": "Agra, Uttar Pradesh, India",
        "built_by": "Mughal Emperor Shah Jahan",
        "construction_year": "Completed around 1648 AD (started in 1631 AD)",
        "theme": "Mughal Architecture (mixture of Persian, Islamic, and Indian styles)",
        "key_facts": [
            "It was built as a mausoleum for Shah Jahan's favorite wife, Mumtaz Mahal.",
            "It is made of white marble inlaid with semi-precious stones (pietra dura technique).",
            "It is recognized as a UNESCO World Heritage Site and one of the New Seven Wonders of the World.",
            "Architect Ustad Ahmad Lahori is widely considered the principal designer."
        ],
        "detailed_context": (
            "The Taj Mahal is an ivory-white marble mausoleum on the south bank of the Yamuna river "
            "in the Indian city of Agra. It was commissioned in 1631 by the Mughal emperor Shah Jahan "
            "(reigned from 1628 to 1658) to house the tomb of his favourite wife, Mumtaz Mahal; it also "
            "houses the tomb of Shah Jahan himself. The tomb is the centrepiece of a 17-hectare (42-acre) "
            "complex, which includes a mosque and a guest house, and is set in formal gardens bounded on "
            "three sides by a crenellated wall. Construction of the mausoleum was essentially completed in "
            "1643, but work continued on other phases of the project for another ten years."
        )
    },
    "red_fort": {
        "canonical_name": "Red Fort",
        "location": "Delhi, India",
        "built_by": "Mughal Emperor Shah Jahan",
        "construction_year": "Completed in 1648 AD (started in 1638 AD)",
        "theme": "Mughal Architecture",
        "key_facts": [
            "It served as the main residence of the Mughal emperors for nearly 200 years.",
            "It is constructed using red sandstone, which gives it its name.",
            "Every year on India's Independence Day (August 15), the Prime Minister hoists the national flag here.",
            "Designed by architect Ustad Ahmad Lahori, who also designed the Taj Mahal."
        ],
        "detailed_context": (
            "The Red Fort, Lal Qila, is a historic fort in Old Delhi, India, that served as the main "
            "residence of the Mughal Emperors. Emperor Shah Jahan commissioned construction of the Red Fort "
            "on 12 May 1638, when he decided to shift his capital from Agra to Delhi. Originally red and "
            "white, its design is credited to architect Ustad Ahmad Lahori. The fort represents the zenith "
            "of Mughal creativity under Shah Jahan and synthesizes Persianate palace architecture with Indian "
            "traditions."
        )
    },
    "sun_temple": {
        "canonical_name": "Konark Sun Temple",
        "location": "Konark, Odisha, India",
        "built_by": "King Narasimhadeva I of the Eastern Ganga Dynasty",
        "construction_year": "Around 1250 AD",
        "theme": "Kalinga Architecture",
        "key_facts": [
            "It is designed as a colossal chariot drawn by seven horses with 24 ornately carved stone wheels.",
            "The temple was originally built at the mouth of the Chandrabhaga river, but the waterline has since receded.",
            "It is also known as the 'Black Pagoda' due to its dark color and magnetic properties that once drew ships ashore according to legends.",
            "It is a UNESCO World Heritage Site."
        ],
        "detailed_context": (
            "Konark Sun Temple is a 13th-century CE Sun temple at Konark about 35 kilometres northeast "
            "from Puri city on the coastline in Odisha, India. The temple is attributed to king Narasimhadeva I "
            "of the Eastern Ganga dynasty about 1250 CE. Dedicated to the Hindu Sun God Surya, what remains of "
            "the temple complex has the appearance of a 100-foot (30 m) high chariot with immense wheels and horses, "
            "all carved from stone. Once over 200 feet (61 m) high, much of the temple is now in ruins."
        )
    },
    "hampi": {
        "canonical_name": "Virupaksha Temple (Hampi)",
        "location": "Hampi, Vijayanagara District, Karnataka, India",
        "built_by": "Lakkana Dandesha, a chieftain under King Deva Raya II of the Vijayanagara Empire",
        "construction_year": "7th Century AD (expanded in 14th-16th Century)",
        "theme": "Vijayanagara Style / Dravidian Architecture",
        "key_facts": [
            "It is dedicated to Lord Shiva, known here as Virupaksha, the consort of local goddess Pampa.",
            "It is the main center of pilgrimage at Hampi, having survived the destruction of the city in 1565.",
            "Features a 50-meter-tall nine-tiered gateway (Gopuram).",
            "Part of the Group of Monuments at Hampi, a UNESCO World Heritage Site."
        ],
        "detailed_context": (
            "Virupaksha Temple is located in Hampi in the Vijayanagara district of Karnataka, India. It is "
            "part of the Group of Monuments at Hampi, designated as a UNESCO World Heritage Site. The temple is "
            "dedicated to Lord Virupaksha, a form of Shiva. The temple was built by Lakkana Dandesha, a "
            "nayaka (chieftain) under the ruler Deva Raya II of the Vijayanagara Empire. Hampi was the grand "
            "capital of the Vijayanagara Empire, and this temple was one of its most sacred and highly patronized "
            "complexes, remaining active even after the empire's fall in 1565."
        )
    },
    "qutub_minar": {
        "canonical_name": "Qutub Minar",
        "location": "New Delhi, India",
        "built_by": "Qutb-ud-din Aibak (started) and completed by Iltutmish and Firoz Shah Tughlaq",
        "construction_year": "Started in 1199 AD",
        "theme": "Indo-Islamic Architecture",
        "key_facts": [
            "It is a 73-meter tall tapering tower of five distinct storeys.",
            "It is surrounded by several significant historic monuments, collectively known as the Qutb complex (including the Iron Pillar).",
            "The tower has 379 spiral steps leading to the top, which are now closed to the public.",
            "It is a UNESCO World Heritage Site."
        ],
        "detailed_context": (
            "The Qutb Minar is a minaret and 'victory tower' that forms part of the Qutb complex, which lies "
            "at the site of Delhi's oldest fortified city, Lal Kot, founded by the Tomar Rajputs. It is a UNESCO "
            "World Heritage Site in the Mehrauli area of South Delhi, India. It is 72.5 metres (238 feet) tall, "
            "making it the tallest minaret in the world built of bricks. It has a spiral staircase of 379 steps."
        )
    }
}

def get_monument_by_id(monument_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve monument details by its ID keys."""
    return MONUMENT_CATALOG.get(monument_id.lower())

def search_monument(query: str) -> Optional[str]:
    """Find closest monument key based on string query."""
    query = query.lower()
    for key, data in MONUMENT_CATALOG.items():
        if key in query or data["canonical_name"].lower() in query:
            return key
        for fact in data["key_facts"]:
            if any(word in fact.lower() for word in query.split() if len(word) > 4):
                return key
    return None
