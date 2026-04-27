from fastapi import APIRouter
from app.core.database import db

router = APIRouter()

@router.get("/config")
async def get_ads_config():
    settings = await db.ads_settings.find_one({}, {"_id": 0})
    if not settings:
        return {
            "all_ads_on": True,
            "banner_ads": True,
            "interstitial_ads": True,
            "interstitial_frequency": 5,
            "campaigns": []
        }
    return settings

@router.get("/campaigns")
async def get_active_campaigns():
    # Filter for active campaigns
    campaigns = await db.ads_campaigns.find({"active": True}, {"_id": 0}).to_list(10)
    return campaigns
