from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Any

from app.services.product_service import product_service
from app.services.allergy_engine import analyze_risk
from app.services.ai_service import AIService
from app.core.security import get_current_user
from app.core.database import db

router = APIRouter(prefix="/api", tags=["Product Analysis"])

class OCRRequest(BaseModel):
    text: str

def normalize_barcode(barcode: str) -> str:
    barcode = barcode.strip()
    if len(barcode) == 12:
        return "0" + barcode
    return barcode

def _is_digits(s: str) -> bool:
    return bool(s) and s.isdigit()

def _ean13_check_digit(d12: str) -> int:
    total = 0
    for i, ch in enumerate(d12):
        n = int(ch)
        total += n if (i % 2 == 0) else (n * 3)
    return (10 - (total % 10)) % 10

def validate_barcode(raw: str) -> str:
    if raw is None:
        raise HTTPException(status_code=422, detail="Barcode is required.")

    barcode = raw.strip()
    if not _is_digits(barcode):
        raise HTTPException(status_code=422, detail="Barcode must contain only digits.")

    if len(barcode) not in (12, 13):
        raise HTTPException(status_code=422, detail="Barcode must be 12 (UPC-A) or 13 (EAN-13) digits long.")

    normalized = normalize_barcode(barcode)
    if len(normalized) != 13:
        raise HTTPException(status_code=422, detail="Invalid barcode length after normalization.")

    expected = _ean13_check_digit(normalized[:12])
    actual = int(normalized[12])
    if expected != actual:
        raise HTTPException(status_code=422, detail="Invalid barcode check digit.")

    return normalized

@router.get("/product/{barcode}")
async def get_product(barcode: str, user_token: dict = Depends(get_current_user)):
    user = await db.users.find_one({"email": user_token["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    barcode = validate_barcode(barcode)

    # 1. Check for Global Recalls
    recall = await db.recalls.find_one({"barcode": barcode})
    
    # 2. Get Product Data from OpenFoodFacts & others
    product_data = await product_service.get_product_by_barcode(barcode)
    if not product_data:
        raise HTTPException(status_code=404, detail="Product not found in any global database.")
    
    # 3. Personalized Allergy Analysis
    ingredients = product_data.get("ingredientsText") or product_data.get('ingredientsList', [])
    user_allergies = user.get("allergies", [])
    analysis = analyze_risk(user_allergies, ingredients)
    
    # 4. Final Result Assembly
    result = {
        "status": analysis["status"],
        "message": analysis["message"],
        "color": analysis["color"],
    }
    
    # Override if recall exists
    if recall:
        result = {
            "status": "DANGEROUS",
            "message": f"RECALLED: {recall.get('reason')}",
            "color": "red"
        }

    return {
        **product_data,
        "result": result,
        "detectedAllergens": analysis.get("detected_allergens", []),
        "detectedAllergenDetails": analysis.get("detected_allergen_details", []),
        "userHits": analysis.get("user_hits", []),
        "userSpecificWarning": analysis["message"] if analysis["status"] != "SAFE" else "--",
    }

@router.post("/ingredient-analyze")
async def analyze_ocr(request: OCRRequest, user_token: dict = Depends(get_current_user)):
    user = await db.users.find_one({"email": user_token["sub"]})
    user_allergies = user.get("allergies", [])
    
    text = (request.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="ingredients text is required.")

    local = analyze_risk(user_allergies, text)

    ai = await AIService.analyze_ingredients(text, user_context=f"User allergies: {', '.join(local.get('user_hits', []))}")
    ai_detected_raw = ai.get("detected_allergens") if isinstance(ai, dict) else None
    ai_detected = []
    if isinstance(ai_detected_raw, list):
        ai_detected = [str(x).strip() for x in ai_detected_raw if str(x).strip()]

    detected = sorted(set(local.get("detected_allergens", []) + ai_detected))
    status = local.get("status", "SAFE")
    message = local.get("message", "No major allergens detected.")
    color = local.get("color", "green")

    if not detected:
        status, message, color = "SAFE", "No major allergens detected.", "green"
    elif len(detected) >= 2:
        status, message, color = "DANGEROUS", "Multiple allergens detected. Avoid if sensitive.", "red"
    else:
        status, message, color = "CAUTION", "Allergen detected. Check before consuming.", "yellow"

    ingredients_list = []
    for part in [p.strip() for p in text.replace("\n", ",").split(",")]:
        if not part:
            continue
        lower = part.lower()
        risk = "SAFE"
        reason = "No known allergen signal"
        for a in detected:
            if a.lower() in lower:
                risk = "DANGEROUS"
                reason = f"Contains {a}"
                break
        ingredients_list.append({"name": part[:1].upper() + part[1:], "risk": risk, "reason": reason})

    ai_insights = []
    if detected:
        ai_insights.append({"type": "warning", "text": f"Detected allergens: {', '.join(detected)}", "icon": "warning"})

    return {
        "barcode": "OCR_SCAN",
        "name": "Label Scan",
        "brand": "--",
        "quantity": "--",
        "imageUrl": "--",
        "ingredientsText": text,
        "ingredientsList": ingredients_list,
        "nutritionFacts": {},
        "nutriScore": "--",
        "ecoScore": "--",
        "novaGroup": 0,
        "healthScore": 0,
        "additives": [],
        "aiInsights": ai_insights,
        "packaging": "--",
        "manufacturingCountry": "--",
        "stores": "--",
        "countriesSold": "--",
        "result": {"status": status, "message": message, "color": color},
        "detectedAllergens": detected,
        "detectedAllergenDetails": local.get("detected_allergen_details", []),
        "userHits": local.get("user_hits", []),
    }
