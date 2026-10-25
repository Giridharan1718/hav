"""Deterministic eligibility evaluation.

Rule evaluation never calls a language model and never infers sensitive attributes.
Only fields referenced by the scheme version's rules are accepted, so a request cannot
smuggle unrelated personal data into the evaluation.

Outcome precedence (deterministic):
1. ``cannot_evaluate`` when a rule or its source is unusable (unsupported operator,
   unknown field, rule not validated).
2. ``not_eligible`` when at least one evaluated rule is not met.
3. ``insufficient_information`` when rules are usable but required answers are absent.
4. ``eligible`` when every usable rule is met.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.core.errors import ApiError
from app.core.i18n import SUPPORTED_LANGUAGES
from app.models import EligibilityRule, SchemeVersion

OUTCOME_ELIGIBLE = "eligible"
OUTCOME_NOT_ELIGIBLE = "not_eligible"
OUTCOME_INSUFFICIENT = "insufficient_information"
OUTCOME_CANNOT = "cannot_evaluate"

OPERATORS = {"gte", "lte", "eq", "neq", "in", "not_in", "is_true", "is_false"}

DISCLAIMER = (
    "This is a preliminary check against the criteria documented for this scheme version. "
    "It is not an official determination, does not verify your documents, and does not "
    "guarantee any benefit. The administering department makes the final decision."
)


@dataclass(frozen=True)
class FieldSpec:
    key: str
    kind: str  # int | number | bool | str
    label: dict[str, str]
    purpose: dict[str, str]
    choices: tuple[str, ...] | None = None
    minimum: float | None = None
    maximum: float | None = None
    sensitive: bool = False

    def serialize(self, language: str) -> dict[str, Any]:
        return {
            "key": self.key,
            "type": self.kind,
            "label": self.label.get(language) or self.label["en"],
            "purpose": self.purpose.get(language) or self.purpose["en"],
            "choices": list(self.choices) if self.choices else None,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "sensitive": self.sensitive,
        }


INDIAN_STATES = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands",
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
)

FIELD_SPECS: dict[str, FieldSpec] = {
    "age": FieldSpec(
        "age", "int",
        {"en": "Age", "hi": "आयु", "ta": "வயது"},
        {
            "en": "Some schemes have age limits. Only your age in years is used, and it is not saved.",
            "hi": "कुछ योजनाओं में आयु सीमा होती है। केवल आपकी आयु वर्षों में उपयोग होती है और सहेजी नहीं जाती।",
            "ta": "சில திட்டங்களுக்கு வயது வரம்பு உள்ளது. உங்கள் வயது மட்டும் பயன்படுத்தப்படும், சேமிக்கப்படாது.",
        },
        minimum=0, maximum=120,
    ),
    "state": FieldSpec(
        "state", "str",
        {"en": "State or UT", "hi": "राज्य या केंद्रशासित प्रदेश", "ta": "மாநிலம் அல்லது யூனியன் பிரதேசம்"},
        {
            "en": "Used to match schemes limited to particular states or union territories.",
            "hi": "कुछ राज्यों तक सीमित योजनाओं से मिलान के लिए उपयोग होता है।",
            "ta": "குறிப்பிட்ட மாநிலங்களுக்கு மட்டும் உள்ள திட்டங்களைப் பொருத்த பயன்படுகிறது.",
        },
        choices=INDIAN_STATES,
    ),
    "district": FieldSpec(
        "district", "str",
        {"en": "District", "hi": "ज़िला", "ta": "மாவட்டம்"},
        {"en": "Only used when a scheme is limited to specific districts.",
         "hi": "जब योजना कुछ ज़िलों तक सीमित हो तभी उपयोग होता है।",
         "ta": "சில மாவட்டங்களுக்கு மட்டும் எனும் போது மட்டுமே பயன்படும்."},
        maximum=120,
    ),
    "gender": FieldSpec(
        "gender", "str",
        {"en": "Gender", "hi": "लिंग", "ta": "பாலினம்"},
        {"en": "Some schemes are restricted by gender. Used only for this check and not saved.",
         "hi": "कुछ योजनाएँ लिंग के आधार पर सीमित हैं। केवल इस जाँच के लिए उपयोग, सहेजा नहीं जाता।",
         "ta": "சில திட்டங்கள் பாலின அடிப்படையில் உள்ளன. இந்த சரிபார்ப்புக்கு மட்டுமே, சேமிக்கப்படாது."},
        choices=("female", "male", "other", "prefer_not_to_say"), sensitive=True,
    ),
    "annual_income_inr": FieldSpec(
        "annual_income_inr", "int",
        {"en": "Annual family income (₹)", "hi": "वार्षिक पारिवारिक आय (₹)", "ta": "ஆண்டு குடும்ப வருமானம் (₹)"},
        {"en": "Some schemes have income limits. Used only for this check and not saved.",
         "hi": "कुछ योजनाओं में आय सीमा है। केवल इस जाँच के लिए उपयोग, सहेजी नहीं जाती।",
         "ta": "சில திட்டங்களுக்கு வருமான வரம்பு உள்ளது. இந்த சரிபார்ப்புக்கு மட்டுமே, சேமிக்கப்படாது."},
        minimum=0, maximum=100_000_000, sensitive=True,
    ),
    "social_category": FieldSpec(
        "social_category", "str",
        {"en": "Social category", "hi": "सामाजिक श्रेणी", "ta": "சமூகப் பிரிவு"},
        {"en": "Some schemes are meant for specific categories. Used only for this check and not saved.",
         "hi": "कुछ योजनाएँ विशेष श्रेणियों के लिए हैं। केवल इस जाँच के लिए उपयोग, सहेजी नहीं जाती।",
         "ta": "சில திட்டங்கள் குறிப்பிட்ட பிரிவுகளுக்கானவை. இந்த சரிபார்ப்புக்கு மட்டுமே, சேமிக்கப்படாது."},
        choices=("general", "obc", "sc", "st", "ews"), sensitive=True,
    ),
    "occupation": FieldSpec(
        "occupation", "str",
        {"en": "Occupation", "hi": "व्यवसाय", "ta": "தொழில்"},
        {"en": "Some schemes apply to farmers, students or other groups.",
         "hi": "कुछ योजनाएँ किसानों, छात्रों या अन्य समूहों के लिए हैं।",
         "ta": "சில திட்டங்கள் விவசாயிகள், மாணவர்கள் அல்லது பிற குழுக்களுக்கானவை."},
        choices=("farmer", "agricultural_labourer", "student", "salaried", "self_employed",
                 "unemployed", "retired", "other"),
    ),
    "education_level": FieldSpec(
        "education_level", "str",
        {"en": "Education level", "hi": "शिक्षा स्तर", "ta": "கல்வி நிலை"},
        {"en": "Used for scholarship checks only.",
         "hi": "केवल छात्रवृत्ति जाँच के लिए।",
         "ta": "கல்வி உதவித்தொகை சரிபார்ப்புக்கு மட்டும்."},
        choices=("below_class_10", "class_10", "class_11", "class_12", "undergraduate",
                 "postgraduate", "other"),
    ),
    "is_student": FieldSpec(
        "is_student", "bool",
        {"en": "Currently studying", "hi": "वर्तमान में अध्ययनरत", "ta": "தற்போது படிக்கிறீர்களா"},
        {"en": "Used for education-related schemes.", "hi": "शिक्षा संबंधी योजनाओं के लिए।",
         "ta": "கல்வி தொடர்பான திட்டங்களுக்கு."},
    ),
    "residence_area": FieldSpec(
        "residence_area", "str",
        {"en": "Rural or urban", "hi": "ग्रामीण या शहरी", "ta": "கிராமப்புறம் அல்லது நகர்ப்புறம்"},
        {"en": "Some schemes are limited to rural or urban areas.",
         "hi": "कुछ योजनाएँ ग्रामीण या शहरी क्षेत्रों तक सीमित हैं।",
         "ta": "சில திட்டங்கள் கிராமப்புற அல்லது நகர்ப்புற பகுதிகளுக்கு மட்டும்."},
        choices=("rural", "urban"),
    ),
    "landholding_acres": FieldSpec(
        "landholding_acres", "number",
        {"en": "Land holding (acres)", "hi": "भूमि (एकड़)", "ta": "நிலம் (ஏக்கர்)"},
        {"en": "Used for farm-related schemes. Used only for this check and not saved.",
         "hi": "कृषि संबंधी योजनाओं के लिए। केवल इस जाँच के लिए उपयोग, सहेजा नहीं जाता।",
         "ta": "வேளாண் திட்டங்களுக்கு. இந்த சரிபார்ப்புக்கு மட்டுமே, சேமிக்கப்படாது."},
        minimum=0, maximum=1000, sensitive=True,
    ),
    "has_bank_account": FieldSpec(
        "has_bank_account", "bool",
        {"en": "Bank account", "hi": "बैंक खाता", "ta": "வங்கிக் கணக்கு"},
        {"en": "Some benefits are paid into a bank account.",
         "hi": "कुछ लाभ बैंक खाते में मिलते हैं।",
         "ta": "சில பயன்கள் வங்கிக் கணக்கில் வழங்கப்படும்."},
    ),
    "has_aadhaar": FieldSpec(
        "has_aadhaar", "bool",
        {"en": "Aadhaar number", "hi": "आधार संख्या", "ta": "ஆதார் எண்"},
        {"en": "Aadhaar is required for identity verification in several schemes. This check does not verify it.",
         "hi": "कई योजनाओं में पहचान सत्यापन के लिए आधार आवश्यक है। यह जाँच इसे सत्यापित नहीं करती।",
         "ta": "பல திட்டங்களில் அடையாள சரிபார்ப்புக்கு ஆதார் தேவை. இந்த சரிபார்ப்பு அதை உறுதிப்படுத்தாது."},
        sensitive=False,
    ),
    "is_income_tax_payer": FieldSpec(
        "is_income_tax_payer", "bool",
        {"en": "Pay income tax", "hi": "आयकर देते हैं", "ta": "வருமான வரி செலுத்துகிறீர்களா"},
        {"en": "Some schemes exclude income-tax payers. Not saved.",
         "hi": "कुछ योजनाएँ आयकर देने वालों को छूट देती हैं। सहेजा नहीं जाता।",
         "ta": "சில திட்டங்கள் வருமான வரி செலுத்துவோரை விலக்குகின்றன. சேமிக்கப்படாது."},
        sensitive=True,
    ),
    "is_bpl": FieldSpec(
        "is_bpl", "bool",
        {"en": "Below Poverty Line household", "hi": "गरीबी रेखा से नीचे परिवार", "ta": "வறுமைக் கோட்டுக்குக் கீழ் குடும்பம்"},
        {"en": "Some schemes require a BPL household. This check does not verify official lists.",
         "hi": "कुछ योजनाओं में बीपीएल परिवार आवश्यक है। यह जाँच आधिकारिक सूची सत्यापित नहीं करती।",
         "ta": "சில திட்டங்களுக்கு வறுமைக் கோட்டுக்குக் கீழ் குடும்பம் தேவை. இந்த சரிபார்ப்பு அதிகாரப்பூர்வ பட்டியலை உறுதிப்படுத்தாது."},
        sensitive=True,
    ),
    "has_pucca_house": FieldSpec(
        "has_pucca_house", "bool",
        {"en": "Own a pucca house", "hi": "पक्का घर है", "ta": "நிரந்தர வீடு உள்ளதா"},
        {"en": "Some housing schemes exclude households that already own a pucca house.",
         "hi": "कुछ आवास योजनाएँ उन परिवारों को छोड़ती हैं जिनके पास पक्का घर है।",
         "ta": "சில வீட்டுத் திட்டங்கள் ஏற்கனவே நிரந்தர வீடு உள்ள குடும்பங்களை விலக்குகின்றன."},
    ),
    "child_age": FieldSpec(
        "child_age", "int",
        {"en": "Child's age", "hi": "बच्चे की आयु", "ta": "குழந்தையின் வயது"},
        {"en": "Used only for child-focused schemes.", "hi": "केवल बच्चों से जुड़ी योजनाओं के लिए।",
         "ta": "குழந்தைகளுக்கான திட்டங்களுக்கு மட்டும்."},
        minimum=0, maximum=30,
    ),
    "child_gender": FieldSpec(
        "child_gender", "str",
        {"en": "Child's gender", "hi": "बच्चे का लिंग", "ta": "குழந்தையின் பாலினம்"},
        {"en": "Used only for child-focused schemes.", "hi": "केवल बच्चों से जुड़ी योजनाओं के लिए।",
         "ta": "குழந்தைகளுக்கான திட்டங்களுக்கு மட்டும்."},
        choices=("female", "male", "other"), sensitive=True,
    ),
    "family_size": FieldSpec(
        "family_size", "int",
        {"en": "Family size", "hi": "परिवार का आकार", "ta": "குடும்ப அளவு"},
        {"en": "Used only where a scheme defines a household size.",
         "hi": "केवल जहाँ योजना में परिवार का आकार परिभाषित है।",
         "ta": "குடும்ப அளவு வரையறுக்கப்பட்ட திட்டங்களுக்கு மட்டும்."},
        minimum=1, maximum=30,
    ),
}

_BOOL_OPS = {"is_true", "is_false"}


def _coerce(spec: FieldSpec, value: Any) -> Any:
    if spec.kind == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ValueError("expected true or false")
    if spec.kind in {"int", "number"}:
        if isinstance(value, bool):
            raise ValueError("expected a number")
        number = float(value) if spec.kind == "number" else int(value)
        if spec.kind == "int" and float(value) != int(value):
            raise ValueError("expected a whole number")
        if spec.minimum is not None and number < spec.minimum:
            raise ValueError("below the allowed minimum")
        if spec.maximum is not None and number > spec.maximum:
            raise ValueError("above the allowed maximum")
        return number
    if not isinstance(value, str):
        raise ValueError("expected text")
    cleaned = value.strip()
    if spec.choices and cleaned not in spec.choices:
        raise ValueError("not an allowed choice")
    if spec.maximum and len(cleaned) > int(spec.maximum):
        raise ValueError("too long")
    return cleaned


def validate_inputs(raw: dict[str, Any] | None, allowed_fields: set[str]) -> dict[str, Any]:
    """Validate and coerce answers; reject any field that is not required."""
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise ApiError(422, "validation_error", "Answers must be an object.")
    unknown = sorted(set(raw) - allowed_fields)
    if unknown:
        raise ApiError(
            422, "validation_error", "Only fields required by this scheme may be submitted.",
            details=[{"field": key, "issue": "not required for this scheme"} for key in unknown],
        )
    clean: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    for key, value in raw.items():
        spec = FIELD_SPECS.get(key)
        if spec is None:
            errors.append({"field": key, "issue": "unsupported field"})
            continue
        if value is None or value == "":
            continue
        try:
            clean[key] = _coerce(spec, value)
        except (ValueError, TypeError) as exc:
            errors.append({"field": key, "issue": str(exc)})
    if errors:
        raise ApiError(422, "validation_error", "Some answers are not valid.", details=errors)
    return clean


def _compare(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "gte":
        return actual >= expected
    if operator == "lte":
        return actual <= expected
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "is_true":
        return bool(actual) is True
    if operator == "is_false":
        return bool(actual) is False
    raise ValueError(f"unsupported operator: {operator}")


def _rule_active(rule: EligibilityRule, today: date) -> bool:
    if rule.effective_from and today < rule.effective_from:
        return False
    if rule.effective_to and today > rule.effective_to:
        return False
    return True


def required_fields(rules: list[EligibilityRule]) -> list[str]:
    seen: list[str] = []
    for rule in rules:
        if rule.validation_status == "valid" and rule.operator in OPERATORS and rule.field in FIELD_SPECS:
            if rule.field not in seen:
                seen.append(rule.field)
    return seen


def build_questions(version: SchemeVersion, language: str) -> dict[str, Any]:
    rules = [rule for rule in version.rules if rule.validation_status == "valid" and _rule_active(rule, date.today())]
    fields = required_fields(rules)
    return {
        "scheme": {
            "slug": version.scheme.slug if version.scheme else None,
            "name": version.scheme.official_name if version.scheme else None,
            "version_no": version.version_no,
            "review_status": version.review_status,
            "verified": version.review_status == "verified",
        },
        "fields": [FIELD_SPECS[key].serialize(language) for key in fields if key in FIELD_SPECS],
        "rules": [
            {
                "rule_key": rule.rule_key,
                "field": rule.field,
                "description": rule.description,
                "source_reference": rule.source_reference,
            }
            for rule in rules
        ],
        "disclaimer": DISCLAIMER,
    }


def _label(key: str, language: str) -> str:
    spec = FIELD_SPECS.get(key)
    if not spec:
        return key.replace("_", " ")
    return spec.label.get(language) or spec.label["en"]


def evaluate(
    version: SchemeVersion,
    inputs: dict[str, Any],
    *,
    language: str = "en",
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    language = language if language in SUPPORTED_LANGUAGES else "en"
    allowed = set(required_fields(version.rules))
    answers = validate_inputs(inputs, allowed)

    results: list[dict[str, Any]] = []
    reasons: list[dict[str, str]] = []
    missing: list[str] = []
    unsupported = False
    failed = False

    for rule in sorted(version.rules, key=lambda item: item.rule_key):
        if not _rule_active(rule, today):
            results.append({"rule_key": rule.rule_key, "status": "not_applicable"})
            continue
        if rule.validation_status != "valid":
            unsupported = True
            results.append({"rule_key": rule.rule_key, "status": "unsupported", "field": rule.field})
            reasons.append({"code": "rule_not_validated", "rule_key": rule.rule_key})
            continue
        spec = FIELD_SPECS.get(rule.field)
        if spec is None or rule.operator not in OPERATORS:
            unsupported = True
            results.append({"rule_key": rule.rule_key, "status": "unsupported", "field": rule.field})
            reasons.append({"code": "rule_unsupported", "rule_key": rule.rule_key})
            continue
        if rule.field not in answers:
            missing.append(rule.field)
            results.append({
                "rule_key": rule.rule_key,
                "status": "missing",
                "field": rule.field,
                "description": rule.description,
            })
            continue
        actual = answers[rule.field]
        if rule.operator in _BOOL_OPS and not isinstance(actual, bool):
            unsupported = True
            results.append({"rule_key": rule.rule_key, "status": "unsupported", "field": rule.field})
            reasons.append({"code": "rule_type_mismatch", "rule_key": rule.rule_key})
            continue
        met = _compare(rule.operator, actual, rule.value)
        if not met:
            failed = True
            reasons.append({
                "code": "criterion_not_met",
                "rule_key": rule.rule_key,
                "field": rule.field,
                "label": _label(rule.field, language),
            })
        results.append({
            "rule_key": rule.rule_key,
            "status": "met" if met else "not_met",
            "field": rule.field,
            "label": _label(rule.field, language),
            "description": rule.description,
            "source_reference": rule.source_reference,
        })

    if unsupported:
        outcome = OUTCOME_CANNOT
    elif failed:
        outcome = OUTCOME_NOT_ELIGIBLE
    elif missing:
        outcome = OUTCOME_INSUFFICIENT
    else:
        outcome = OUTCOME_ELIGIBLE

    unique_missing = [key for key in dict.fromkeys(missing)]
    return {
        "outcome": outcome,
        "scheme": {
            "slug": version.scheme.slug if version.scheme else None,
            "name": version.scheme.official_name if version.scheme else None,
            "version_no": version.version_no,
            "review_status": version.review_status,
            "verified": version.review_status == "verified",
            "official_url": version.scheme.official_url if version.scheme else None,
        },
        "rules": results,
        "missing_fields": [FIELD_SPECS[key].serialize(language) for key in unique_missing if key in FIELD_SPECS],
        "reasons": reasons,
        "disclaimer": DISCLAIMER,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "language": language,
    }
