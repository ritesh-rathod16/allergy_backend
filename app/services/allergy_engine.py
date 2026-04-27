from typing import List, Dict, Any, Union, Tuple

# Expanded keyword list for better detection
ALLERGEN_KEYWORDS = {
    "peanuts": ["peanut", "arachis", "groundnut", "goober"],
    "milk": ["milk", "dairy", "lactose", "whey", "casein", "caseinate", "curd", "yogurt", "cheese", "butter"],
    "soy": ["soy", "soya", "lecithin", "tofu", "edamame", "miso"],
    "gluten": ["wheat", "gluten", "barley", "rye", "malt", "spelt", "semolina", "durum", "triticale"],
    "egg": ["egg", "albumin", "globulin", "lysozyme", "ovalbumin", "ovomucoid"],
    "wheat": ["wheat", "durum", "semolina", "spelt", "triticale"],
    "fish": ["fish", "cod", "salmon", "tuna", "tilapia", "halibut", "haddock"],
    "shellfish": ["shrimp", "crab", "lobster", "prawn", "mussel", "oyster", "scallop"],
    "nuts": ["nut", "almond", "cashew", "walnut", "hazelnut", "pistachio", "pecan", "macadamia", "brazil nut"],
    "cosmetics": ["paraben", "sulfate", "fragrance", "silicone", "retinol", "phthalate"],
    "medicine": ["paracetamol", "ibuprofen", "aspirin", "penicillin"],
}

WHY_MAP: Dict[str, Tuple[str, str]] = {
    "milk": ("May trigger lactose intolerance or milk-protein allergy", "Avoid if sensitive"),
    "soy": ("Soy proteins can trigger allergic reactions", "Avoid if sensitive"),
    "gluten": ("Can trigger celiac disease or gluten sensitivity", "Avoid if sensitive"),
    "peanuts": ("Common trigger for severe allergic reactions", "Avoid if allergic"),
    "egg": ("Egg proteins can trigger allergic reactions", "Avoid if allergic"),
    "wheat": ("Wheat allergy can cause reactions; also linked with gluten sensitivity", "Avoid if sensitive"),
    "fish": ("Fish proteins can trigger allergic reactions", "Avoid if allergic"),
    "shellfish": ("Shellfish proteins can trigger allergic reactions", "Avoid if allergic"),
    "nuts": ("Tree nuts can trigger allergic reactions", "Avoid if allergic"),
}


def _normalize_input(ingredients_input: Union[str, List[str], None]) -> str:
    if ingredients_input is None:
        return ""
    if isinstance(ingredients_input, list):
        parts = []
        for i in ingredients_input:
            if isinstance(i, dict):
                parts.append(str(i.get("name") or i.get("text") or ""))
            else:
                parts.append(str(i))
        return " ".join(parts)
    return str(ingredients_input)


def _pretty(name: str) -> str:
    s = name.strip()
    if not s:
        return s
    return s[:1].upper() + s[1:]


def analyze_risk(user_allergies: List[Any], ingredients_input: Union[str, List[Dict], List[str], None]) -> Dict:
    """
    Analyzes ingredients for user-specific allergies and determines risk level.
    """
    ingredients_text = ""
    if isinstance(ingredients_input, list) and ingredients_input and isinstance(ingredients_input[0], dict):
        # Handle structured list of ingredients
        ingredients_text = ", ".join([str(i.get("name") or "") for i in ingredients_input])
    else:
        ingredients_text = _normalize_input(ingredients_input)

    text = ingredients_text.lower()

    detected_global = []
    detected_details = []

    # Map for standardized allergen detection
    ALLERGEN_MAP = {
        "milk": ["milk", "dairy", "lactose", "whey", "casein", "cheese", "butter", "cream", "yogurt"],
        "soy": ["soy", "soya", "lecithin"],
        "gluten": ["wheat", "gluten", "barley", "rye", "malt", "spelt"],
        "peanuts": ["peanut", "arachis", "groundnut"],
        "egg": ["egg", "albumin", "ovalbumin"],
        "wheat": ["wheat", "durum", "semolina", "spelt"],
    }

    for allergen, keywords in ALLERGEN_MAP.items():
        hits = [kw for kw in keywords if kw in text]
        if not hits:
            continue
        
        if allergen not in detected_global:
            detected_global.append(allergen)
            
        why, advice = WHY_MAP.get(allergen, ("May trigger an allergic reaction", "Avoid if sensitive"))
        detected_details.append({
            "name": _pretty(allergen),
            "matches": hits[:3],
            "why": why,
            "advice": advice,
        })

    # User-specific detection
    user_set = set()
    for allergy in user_allergies or []:
        if isinstance(allergy, dict):
            a = str(allergy.get("name") or "").strip().lower()
        else:
            a = str(allergy).strip().lower()
        if a: user_set.add(a)

    user_hits = [d for d in detected_details if d["name"].lower() in user_set]

    if not detected_global:
        status = "SAFE"
        color = "green"
        message = "This product is safe for general consumption."
    else:
        if user_hits:
            status = "DANGEROUS"
            color = "red"
            message = f"DANGEROUS: Contains {', '.join([h['name'] for h in user_hits])} which you are allergic to!"
        elif len(detected_global) > 2:
            status = "CAUTION"
            color = "yellow"
            message = "CAUTION: Contains multiple common allergens."
        else:
            status = "SAFE" # Or SAFE with warning if not in user allergies
            color = "green"
            message = "No allergens from your profile detected."

    return {
        "risk": status,
        "color": color,
        "message": message,
        "detected_allergens": detected_details
    }


class AllergyEngine:
    def analyze_risk(self, user_allergies: list, ingredients: Union[str, List[str]]):
        return analyze_risk(user_allergies, ingredients)

allergy_engine = AllergyEngine()
