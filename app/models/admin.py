from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class AdConfig(BaseModel):
    enabled: bool = True
    show_to_premium: bool = False
    frequency: int = 5  # Every X scans
    ad_type: str = "image" # image, video
    media_url: str
    target_url: Optional[str] = None

class GlobalRecall(BaseModel):
    barcode: str
    product_name: str
    reason: str
    severity: str = "CRITICAL"
    issued_at: datetime = Field(default_factory=datetime.utcnow)

class FeatureFlags(BaseModel):
    ai_analysis: bool = True
    chatbot: bool = True
    community_alerts: bool = True
    premium_features: bool = True

class AdminActionLog(BaseModel):
    admin_id: str
    action: str # ban_user, edit_product, issue_recall
    target_id: str
    details: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
