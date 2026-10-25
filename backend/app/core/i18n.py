"""Indian-language text helpers: detection, normalization, query expansion, UI strings.

Detection is script-based and deliberately conservative: Latin-script input is treated
as English, even when it is romanized Hindi or Tamil. That limitation is reported in
the assistant response and documented; no fabricated confidence is claimed.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

SUPPORTED_LANGUAGES: Final = ("en", "hi", "ta")
LANGUAGE_NAMES: Final = {"en": "English", "hi": "हिन्दी", "ta": "தமிழ்"}

SCRIPT_RANGES: Final = {
    "hi": ((0x0900, 0x097F),),  # Devanagari
    "ta": ((0x0B80, 0x0BFF),),  # Tamil
}

# Canonical expansion used for retrieval. Indic terms are mapped onto the English
# vocabulary present in scheme records so one index serves all three languages.
QUERY_SYNONYMS: Final = {
    "किसान": "farmer kisan",
    "kisan": "farmer",
    "farmer": "farmer kisan krishi",
    "खेती": "farmer agriculture",
    "விவசாயி": "farmer",
    "வேளாண்": "farmer agriculture",
    "pension": "pension",
    "पेंशन": "pension",
    "ஓய்வூதியம்": "pension",
    "scholarship": "scholarship education student",
    "छात्रवृत्ति": "scholarship education student",
    "உதவித்தொகை": "scholarship education student",
    "शिक्षा": "education scholarship",
    "கல்வி": "education scholarship",
    "housing": "housing awas house",
    "आवास": "housing awas house",
    "घर": "housing house",
    "வீடு": "housing house",
    "health": "health hospital insurance",
    "स्वास्थ्य": "health hospital insurance",
    "स्वास्थ": "health hospital insurance",
    "சுகாதாரம்": "health hospital insurance",
    "मजदूरी": "employment wage job",
    "रोजगार": "employment wage job",
    "வேலை": "employment wage job",
    "बुजुर्ग": "old age pension senior",
    "वृद्ध": "old age pension senior",
    "முதியோர்": "old age pension senior",
    "girl": "girl child daughter",
    "बालिका": "girl child daughter",
    "பெண்": "girl child daughter",
    "schlor": "scholarship",
    "scholership": "scholarship",
    "pensoin": "pension",
    "awas": "housing awas",
    "yojana": "scheme yojana",
    "योजना": "scheme yojana",
    "திட்டம்": "scheme yojana",
}

# Generic words that appear in almost every record. Matching on them would return the
# whole catalogue for an unrelated question, so they are dropped before retrieval.
QUERY_STOPWORDS: Final = frozenset(
    {
        "scheme",
        "schemes",
        "yojana",
        "yojna",
        "government",
        "sarkari",
        "सरकार",
        "सरकारी",
        "योजना",
        "योजनाएँ",
        "योजनाओं",
        "அரசு",
        "அரசின்",
        "திட்டம்",
        "திட்டங்கள்",
    }
)

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_TAMIL_DIGITS = str.maketrans("௦௧௨௩௪௫௬௭௮௯", "0123456789")
_WS = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^\w\u0900-\u097F\u0B80-\u0BFF]+", re.UNICODE)


def detect_language(text: str) -> tuple[str, str]:
    """Return (language, detection method). Script-based, no fabricated confidence."""
    counts = {"hi": 0, "ta": 0}
    for char in text:
        code = ord(char)
        for language, ranges in SCRIPT_RANGES.items():
            for start, end in ranges:
                if start <= code <= end:
                    counts[language] += 1
    winner = max(counts, key=counts.get)
    if counts[winner] >= 2:
        return winner, "unicode_script"
    return "en", "default_latin"


def normalize_digits(text: str) -> str:
    return text.translate(_DEVANAGARI_DIGITS).translate(_TAMIL_DIGITS)


def normalize_query(text: str) -> str:
    """Lowercase, strip punctuation, normalize digits and expand known synonyms."""
    cleaned = normalize_digits(unicodedata.normalize("NFKC", text or "")).lower()
    cleaned = _NON_WORD.sub(" ", cleaned)
    cleaned = _WS.sub(" ", cleaned).strip()
    if not cleaned:
        return ""
    tokens = cleaned.split(" ")
    expanded = list(tokens)
    for token in tokens:
        mapped = QUERY_SYNONYMS.get(token)
        if mapped:
            expanded.extend(mapped.split())
    seen: set[str] = set()
    result: list[str] = []
    for token in expanded:
        if token and token not in seen and token not in QUERY_STOPWORDS:
            seen.add(token)
            result.append(token)
    if not result:
        # The query is only generic words; fall back to sending a single meaningful
        # token rather than silently matching the whole catalogue. If nothing remains
        # the caller treats it as an empty query.
        return " ".join(token for token in tokens if token not in QUERY_STOPWORDS) or ""
    return " ".join(result)


def extract_numbers(text: str) -> set[str]:
    """Numeric tokens (digits and Indian grouping) for grounding checks."""
    normalized = normalize_digits(text or "")
    found = re.findall(r"\d[\d,]*(?:\.\d+)?", normalized)
    return {item.replace(",", "") for item in found if item.replace(",", "")}


def normalize_for_grounding(text: str) -> str:
    return _WS.sub(" ", normalize_digits(unicodedata.normalize("NFKC", text or "")).lower()).strip()


# Assistant response templates. {placeholders} are filled from evidence only.
STRINGS: Final[dict[str, dict[str, str]]] = {
    "en": {
        "found_one": "I found {count} scheme in the reviewed catalogue that matches your question.",
        "found_many": "I found {count} schemes in the reviewed catalogue that match your question.",
        "no_match": "No scheme in the reviewed catalogue matched your question. Try a different word, or browse the scheme list. This assistant only answers from the reviewed catalogue.",
        "benefit": "Benefit",
        "eligibility": "Who can apply",
        "documents": "Documents",
        "steps": "How to apply",
        "deadline": "Deadline",
        "official_link": "Official page",
        "source_status": "Source status",
        "missing_info": "Information still needed",
        "uncertainty": "This is general information from the cited source, not an official decision. Verify details on the official portal.",
        "translation_unavailable": "A reviewed translation is not available for this language, so the original English text is shown.",
        "eligibility_result": "Preliminary eligibility result",
        "eligibility_note": "This is a preliminary check against documented criteria. It is not an official determination and does not guarantee benefits.",
        "next_steps": "Next steps",
        "no_profile": "Sign in and complete your profile to prepare an application draft.",
        "unsupported_language": "This language is not yet supported by the assistant.",
    },
    "hi": {
        "found_one": "समीक्षित सूची में आपके प्रश्न से मेल खाती {count} योजना मिली।",
        "found_many": "समीक्षित सूची में आपके प्रश्न से मेल खाती {count} योजनाएँ मिलीं।",
        "no_match": "समीक्षित सूची में आपके प्रश्न से मेल खाती कोई योजना नहीं मिली। कृपया दूसरा शब्द आज़माएँ या योजना सूची देखें। यह सहायक केवल समीक्षित सूची से उत्तर देता है।",
        "benefit": "लाभ",
        "eligibility": "कौन आवेदन कर सकता है",
        "documents": "दस्तावेज़",
        "steps": "आवेदन कैसे करें",
        "deadline": "अंतिम तिथि",
        "official_link": "आधिकारिक पृष्ठ",
        "source_status": "स्रोत की स्थिति",
        "missing_info": "अभी आवश्यक जानकारी",
        "uncertainty": "यह उद्धृत स्रोत से सामान्य जानकारी है, कोई आधिकारिक निर्णय नहीं। विवरण आधिकारिक पोर्टल पर जाँचें।",
        "translation_unavailable": "इस भाषा में समीक्षित अनुवाद उपलब्ध नहीं है, इसलिए मूल अंग्रेज़ी पाठ दिखाया गया है।",
        "eligibility_result": "प्रारंभिक पात्रता परिणाम",
        "eligibility_note": "यह प्रलेखित मानदंडों के आधार पर प्रारंभिक जाँच है। यह आधिकारिक निर्णय नहीं है और लाभ की गारंटी नहीं देती।",
        "next_steps": "अगले कदम",
        "no_profile": "आवेदन का मसौदा तैयार करने के लिए साइन इन करें और प्रोफ़ाइल पूरी करें।",
        "unsupported_language": "यह भाषा अभी सहायक में समर्थित नहीं है।",
    },
    "ta": {
        "found_one": "மதிப்பாய்வு செய்யப்பட்ட பட்டியலில் உங்கள் கேள்விக்கு பொருந்தும் {count} திட்டம் கிடைத்தது.",
        "found_many": "மதிப்பாய்வு செய்யப்பட்ட பட்டியலில் உங்கள் கேள்விக்கு பொருந்தும் {count} திட்டங்கள் கிடைத்தன.",
        "no_match": "மதிப்பாய்வு செய்யப்பட்ட பட்டியலில் உங்கள் கேள்விக்கு பொருந்தும் திட்டம் இல்லை. வேறு சொல்லை முயற்சிக்கவும் அல்லது திட்டப் பட்டியலைப் பார்க்கவும். இந்த உதவியாளர் மதிப்பாய்வு செய்யப்பட்ட பட்டியலில் இருந்து மட்டுமே பதிலளிக்கிறார்.",
        "benefit": "பயன்",
        "eligibility": "யார் விண்ணப்பிக்கலாம்",
        "documents": "ஆவணங்கள்",
        "steps": "எப்படி விண்ணப்பிப்பது",
        "deadline": "கடைசி தேதி",
        "official_link": "அதிகாரப்பூர்வ பக்கம்",
        "source_status": "மூல நிலை",
        "missing_info": "இன்னும் தேவையான தகவல்",
        "uncertainty": "இது மேற்கோள் காட்டப்பட்ட மூலத்திலிருந்து பொதுத் தகவல், அதிகாரப்பூர்வ முடிவு அல்ல. விவரங்களை அதிகாரப்பூர்வ இணையதளத்தில் சரிபார்க்கவும்.",
        "translation_unavailable": "இந்த மொழிக்கு மதிப்பாய்வு செய்யப்பட்ட மொழிபெயர்ப்பு இல்லை, எனவே அசல் ஆங்கில உரை காட்டப்படுகிறது.",
        "eligibility_result": "பூர்வாங்க தகுதி முடிவு",
        "eligibility_note": "இது ஆவணப்படுத்தப்பட்ட நிபந்தனைகளின் அடிப்படையில் பூர்வாங்க சரிபார்ப்பு. இது அதிகாரப்பூர்வ முடிவு அல்ல, பயன்களுக்கு உத்தரவாதம் அளிக்காது.",
        "next_steps": "அடுத்த படிகள்",
        "no_profile": "விண்ணப்ப வரைவைத் தயாரிக்க உள்நுழைந்து சுயவிவரத்தை நிரப்பவும்.",
        "unsupported_language": "இந்த மொழி இன்னும் உதவியாளரில் ஆதரிக்கப்படவில்லை.",
    },
}


def t(language: str, key: str, **kwargs: object) -> str:
    catalog = STRINGS.get(language, STRINGS["en"])
    template = catalog.get(key, STRINGS["en"].get(key, ""))
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):  # pragma: no cover - defensive
        return template
