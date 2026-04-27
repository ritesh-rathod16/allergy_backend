from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Set logging levels to reduce spam
logging.getLogger("pymongo").setLevel(logging.WARNING)

# Load configuration from environment
MONGO_URI = os.getenv("MONGO_URI")
MAX_POOL_SIZE = int(os.getenv("MONGO_MAX_POOL_SIZE", "50"))
TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT", "30000"))

# Production-grade Async MongoDB Client with Resiliency Parameters
client = AsyncIOMotorClient(
    MONGO_URI,
    serverSelectionTimeoutMS=TIMEOUT_MS,
    connectTimeoutMS=TIMEOUT_MS,
    socketTimeoutMS=TIMEOUT_MS,
    maxPoolSize=MAX_POOL_SIZE,
    minPoolSize=10,
    retryWrites=True,
    retryReads=True,
    tls=True,
    w="majority"
)

db = client["allergy_detector"]

async def init_db():
    """Initializes the database with required collections and indexes."""
    try:
        # Step 4: MongoDB Connection Health Check (Startup Ping)
        await client.admin.command('ping')
        logging.info("MongoDB: Connection verified successfully.")
        
        # Create Core Indexes
        await db.users.create_index("email", unique=True)
        await db.products_cache.create_index("barcode", unique=True)
        await db.scan_history.create_index("user_id")
        await db.chat_history.create_index("timestamp", expireAfterSeconds=86400)
        
        logging.info("MongoDB: Database indexes verified.")
    except Exception as e:
        logging.critical(f"MongoDB: Initialization failed: {e}")
        raise e
