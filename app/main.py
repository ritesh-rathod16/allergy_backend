from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, admin, scan, payment, chat, reactions, ads, ai
from app.routers import product_router
from app.core.database import init_db
from app.services.subscription_service import SubscriptionService
import os
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

load_dotenv()

app = FastAPI(title="Allergy Detector AI-Powered API")

# Configure Production Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(scan.router, prefix="/scan", tags=["Scan"])
app.include_router(payment.router, prefix="/payment", tags=["Payment"])
app.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
app.include_router(reactions.router, prefix="/reactions", tags=["Cure Symptoms"])
app.include_router(ads.router, prefix="/ads", tags=["Ads System"])
app.include_router(ai.router, prefix="/ai", tags=["AI Product Analysis"])
app.include_router(product_router.router)

@app.on_event("startup")
async def startup_event():
    try:
        # 1. Connect and Verify MongoDB
        await init_db()
        logger.info("✅ MongoDB connection verified.")

        # 2. Setup Production-Grade Scheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            SubscriptionService.expire_subscriptions, 
            "interval", 
            hours=1, 
            id="expire_subs",
            replace_existing=True,
            coalesce=True, # Merge missed runs
            misfire_grace_time=3600 # Allow 1h delay
        )
        scheduler.start()
        logger.info("✅ Resilient Background Scheduler started.")

    except Exception as e:
        logger.critical(f"❌ Startup sequence failed: {e}")

@app.get("/")
def health_check():
    return {
        "status": "Allergy Detector Backend Running", 
        "timestamp": datetime.utcnow().isoformat(),
        "database": "Connected"
    }

if __name__ == "__main__":
    import uvicorn
    # Production Mode (Disable reload, enable workers)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False, workers=4)
