from app.core.database import db
from datetime import datetime

class AuditService:
    @staticmethod
    async def log_action(admin_email: str, action: str, details: str):
        await db.audit_logs.insert_one({
            "admin_email": admin_email,
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow()
        })
