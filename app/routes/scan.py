from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.core.database import db
from app.services.allergy_engine import analyze_risk
from app.services.ai_service import AIService
from app.services.product_service import product_service
from typing import List, Optional
import re

router = APIRouter()

def validate_barcode(barcode: str):
    """Validates EAN-8, EAN-12 (UPC-A), and EAN-13 barcodes."""
    if not barcode:
        raise HTTPException(status_code=400, detail="Barcode is required")
    
    # Remove any spaces or dashes
    clean_barcode = re.sub(r'[\s-]', '', barcode)
    
    if not clean_barcode.isdigit():
        raise HTTPException(status_code=400, detail="Barcode must contain only digits")
    
    if len(clean_barcode) not in [8, 12, 13]:
        raise HTTPException(status_code=400, detail="Invalid barcode length. Expected 8, 12, or 13 digits.")
    
    return clean_barcode

@router.get("/barcode/{barcode}")
async def get_product_by_barcode(barcode: str, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"email": current_user["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 1. Validate Barcode
    valid_barcode = validate_barcode(barcode)
    
    # 2. Fetch Product Data
    product_data = await product_service.get_product_by_barcode(valid_barcode)
    if not product_data:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 3. Analyze Risk for User
    user_allergies = user.get("allergies", [])
    analysis = analyze_risk(user_allergies, product_data.get("ingredientsList", []))
    
    # 4. Merge analysis into product data
    product_data["result"] = {
        "status": analysis["risk"],
        "message": analysis["message"],
        "color": analysis["color"]
    }
    product_data["detectedAllergens"] = [a['name'] for a in analysis["detected_allergens"]]
    
    # 5. Generate AI Explanation if risky
    if analysis["risk"] != "SAFE" and not product_data.get("aiInsights"):
        detected_names = [a['name'] for a in analysis["detected_allergens"]]
        prompt = f"Product: {product_data['name']}. Detected Allergens: {', '.join(detected_names)}. Explain the health risk for this user in 2 concise sentences."
        ai_warning = await AIService.chatbot_response(prompt, [])
        product_data["aiInsights"].append({
            "type": "warning",
            "text": ai_warning,
            "icon": "warning"
        })

    return product_data

@router.post("/analyze")
async def analyze_ingredients(ingredients: List[str], current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"email": current_user["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_allergies = user.get("allergies", [])
    
    # 1. Run Allergy Risk Engine
    analysis = analyze_risk(user_allergies, ingredients)
    
    # 2. If risk detected, generate AI explanation
    ai_warning = ""
    if analysis["risk"] != "SAFE":
        detected_names = [a['name'] for a in analysis["detected_allergens"]]
        prompt = f"User: {user['name']}. Detected Allergens: {', '.join(detected_names)}. Explain the health risk in 2 sentences."
        ai_warning = await AIService.chatbot_response(prompt, []) # Using chatbot for simplicity

    return {
        "risk": analysis["risk"],
        "detected_allergens": [a['name'] for a in analysis["detected_allergens"]],
        "ai_warning": ai_warning
    }
