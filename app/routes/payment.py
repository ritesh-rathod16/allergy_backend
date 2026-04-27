from fastapi import APIRouter, Depends, HTTPException, Body
import razorpay
import os
from app.core.security import get_current_user
from app.core.database import db
from app.models.payment import Plan, PromoCode, Subscription
from datetime import datetime, timedelta
from typing import List

router = APIRouter()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# --- 1. FETCH PLANS ---
@router.get("/plans", response_model=List[dict])
async def get_active_plans():
    plans = await db.plans.find({"active": True}).to_list(10)
    return plans

# --- 2. APPLY PROMO CODE ---
@router.post("/apply-promo")
async def apply_promo(data: dict):
    plan_id = data.get("plan_id")
    code = data.get("promo_code")
    
    plan = await db.plans.find_one({"plan_id": plan_id})
    promo = await db.promo_codes.find_one({"code": code, "active": True})
    
    if not plan or not promo:
        raise HTTPException(status_code=400, detail="Invalid plan or promo code")
    
    if promo.get("expiry_date") and promo["expiry_date"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Promo code expired")
        
    final_price = plan["price"]
    if promo["discount_type"] == "percentage":
        final_price = plan["price"] * (1 - promo["discount_value"] / 100)
        
    return {
        "original_price": plan["price"],
        "discount": plan["price"] - final_price,
        "final_price": int(final_price)
    }

# --- 3. CREATE ORDER ---
@router.post("/create-order")
async def create_order(data: dict, user: dict = Depends(get_current_user)):
    plan_id = data.get("plan_id")
    promo_code = data.get("promo_code")
    
    plan = await db.plans.find_one({"plan_id": plan_id})
    if not plan: raise HTTPException(404, "Plan not found")
    
    final_amount = plan["price"]
    if promo_code:
        promo_res = await apply_promo({"plan_id": plan_id, "promo_code": promo_code})
        final_amount = promo_res["final_price"]

    order_data = {
        "amount": int(final_amount * 100), # to paise
        "currency": "INR",
        "receipt": f"rcpt_{user['sub']}_{int(datetime.utcnow().timestamp())}",
    }
    
    try:
        razorpay_order = client.order.create(data=order_data)
        return {
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key": RAZORPAY_KEY_ID
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- 4. VERIFY PAYMENT ---
@router.post("/verify")
async def verify_payment(data: dict, user: dict = Depends(get_current_user)):
    try:
        client.utility.verify_payment_signature({
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_signature": data["razorpay_signature"]
        })
        
        # Provisioning
        plan = await db.plans.find_one({"plan_id": data.get("plan_id", "monthly")})
        days = plan["duration_days"] if plan else 30
        expiry = datetime.utcnow() + timedelta(days=days)
        
        await db.users.update_one(
            {"email": user["sub"]},
            {"$set": {"premium_status": True, "subscription_expiry": expiry}}
        )
        
        # Log Transaction
        await db.subscriptions.insert_one({
            "user_id": user["sub"],
            "plan_id": data.get("plan_id"),
            "amount_paid": data.get("amount", 0),
            "razorpay_payment_id": data["razorpay_payment_id"],
            "status": "success",
            "expiry_date": expiry,
            "created_at": datetime.utcnow()
        })
        return {"message": "Success"}
    except:
        raise HTTPException(400, "Verification failed")

# --- 5. STATUS ---
@router.get("/status")
async def get_status(user: dict = Depends(get_current_user)):
    user_data = await db.users.find_one({"email": user["sub"]})
    return {
        "premium_status": user_data.get("premium_status", False),
        "expiry": user_data.get("subscription_expiry")
    }
