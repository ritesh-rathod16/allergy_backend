from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.services.ai_service import AIService
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ProductSearchRequest(BaseModel):
    product_name: str

class OrganicRemediesRequest(BaseModel):
    symptoms: List[str]

@router.post("/product-analyze")
async def analyze_product_by_name(request: ProductSearchRequest, user: dict = Depends(get_current_user)):
    try:
        # Let the AIService handle the logic
        analysis = await AIService.analyze_product_by_name(request.product_name, user)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/organic-remedies")
async def get_organic_remedies(request: OrganicRemediesRequest, user: dict = Depends(get_current_user)):
    try:
        remedies = await AIService.get_organic_remedies(request.symptoms)
        return remedies
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
