import asyncio
import logging
from datetime import datetime
from pymongo.errors import ServerSelectionTimeoutError, AutoReconnect

from app.core.database import db

logger = logging.getLogger(__name__)

class SubscriptionService:
    @staticmethod
    async def expire_subscriptions():
        """Finds and deactivates expired premium subscriptions with retry logic."""
        now = datetime.utcnow()
        query = {"premium_status": True, "subscription_expiry": {"$lt": now}}
        update = {"$set": {"premium_status": False}}
        retries = 3
        
        for attempt in range(retries):
            try:
                result = await db.users.update_many(query, update)
                if result.modified_count > 0:
                    logger.info(f"Successfully expired {result.modified_count} subscriptions.")
                else:
                    logger.info("No subscriptions to expire.")
                return # Success
            except (ServerSelectionTimeoutError, AutoReconnect) as e:
                logger.warning(f"MongoDB connection error on attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Subscription expiry job failed after all retries.")
                    break # Failed all retries
            except Exception as e:
                logger.error(f"An unexpected error occurred in expiry job: {e}")
                break
