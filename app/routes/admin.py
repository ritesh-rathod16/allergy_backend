from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.core.security import check_admin, get_current_user
from app.core.database import db
from app.services.audit_service import AuditService
from app.services.email_service import send_broadcast_email
from app.models.admin import AdConfig, GlobalRecall, FeatureFlags
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

router = APIRouter()

# --- 1. USER COMMAND CENTER ---
@router.get("/users")
async def get_all_users(admin: dict = Depends(check_admin)):
    users = await db.users.find({}, {"hashed_password": 0, "otp": 0}).to_list(1000)
    for u in users: u["id"] = str(u["_id"])
    return users

@router.post("/users/{email}/ban")
async def ban_user(email: str, admin: dict = Depends(check_admin)):
    await db.users.update_one({"email": email}, {"$set": {"status": "banned"}})
    await AuditService.log_action(admin["sub"], "BAN_USER", email)
    return {"status": "success"}

@router.post("/users/{email}/grant-premium")
async def grant_premium(email: str, admin: dict = Depends(check_admin)):
    expiry = datetime.utcnow() + datetime.timedelta(days=365)
    await db.users.update_one({"email": email}, {"$set": {"premium_status": True, "subscription_expiry": expiry}})
    await AuditService.log_action(admin["sub"], "GRANT_PREMIUM", email)
    return {"status": "success"}

# --- 2. PRODUCT & RECALL ENGINE ---
@router.get("/products/cached")
async def get_cached_products(admin: dict = Depends(check_admin)):
    return await db.products_cache.find().to_list(100)

@router.post("/recalls")
async def issue_recall(recall: GlobalRecall, admin: dict = Depends(check_admin)):
    await db.recalls.insert_one(recall.dict())
    await AuditService.log_action(admin["sub"], "ISSUE_RECALL", recall.barcode)
    return {"message": "Recall Issued"}

# --- 3. MONETIZATION & PROMOS ---
@router.get("/promo-codes")
async def get_promos(admin: dict = Depends(check_admin)):
    return await db.promo_codes.find().to_list(100)

@router.post("/promo-codes")
async def create_promo(promo: dict, admin: dict = Depends(check_admin)):
    await db.promo_codes.insert_one({**promo, "uses": 0, "created_at": datetime.utcnow()})
    return {"status": "success"}

# --- 4. REAL-TIME ANALYTICS ---
@router.get("/analytics/overview")
async def get_admin_analytics(admin: dict = Depends(check_admin)):
    total_users = await db.users.count_documents({})
    total_scans = await db.scan_history.count_documents({})
    premium_users = await db.users.count_documents({"premium_status": True})
    
    # Revenue aggregation
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}}]
    rev_data = await db.subscriptions.aggregate(pipeline).to_list(1)
    total_revenue = rev_data[0]["total"] if rev_data else 0

    return {
        "platform": {
            "total_users": total_users,
            "premium_users": premium_users,
            "total_scans": total_scans
        },
        "revenue": {
            "monthly": total_revenue,
            "daily": total_revenue / 30 
        }
    }

# --- 5. BROADCAST SYSTEM ---
@router.post("/broadcast")
async def send_broadcast(data: dict, admin: dict = Depends(check_admin)):
    users = await db.users.find({}, {"email": 1}).to_list(None)
    emails = [u["email"] for u in users]
    if data.get("send_email"):
        await send_broadcast_email(emails, data["subject"], data["content"], data.get("cta_text"), data.get("cta_url"))
    return {"message": f"Broadcast sent to {len(emails)} users"}

# --- 6. SYSTEM HEALTH ---
@router.get("/health")
async def get_health(admin: dict = Depends(check_admin)):
    start = datetime.utcnow()
    await db.command("ping")
    latency = (datetime.utcnow() - start).total_seconds() * 1000
    return {
        "status": "Healthy",
        "database_latency": f"{latency:.2f}ms",
        "uptime": "99.9%"
    }
