from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Plan(BaseModel):
    plan_id: str
    name: str
    description: str
    price: int  # in base currency (e.g. INR)
    currency: str = "INR"
    duration_days: int
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PromoCode(BaseModel):
    code: str
    discount_type: str  # "percentage", "free_trial"
    discount_value: int
    max_uses: int
    uses: int = 0
    expiry_date: Optional[datetime] = None
    active: bool = True

class Subscription(BaseModel):
    user_id: str
    plan_id: str
    amount_paid: float
    razorpay_payment_id: str
    razorpay_order_id: str
    promo_code: Optional[str] = None
    start_date: datetime = Field(default_factory=datetime.utcnow)
    expiry_date: datetime
    status: str = "active" # "active", "expired", "cancelled"
