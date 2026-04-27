import secrets
from datetime import datetime, timedelta
from app.core.database import db
from app.core.security import hash_password, verify_password
from fastapi import HTTPException, status

class OTPService:
    @staticmethod
    def generate_otp() -> str:
        """Generates a cryptographically secure 6-digit OTP."""
        return str(secrets.randbelow(900000) + 100000)

    @staticmethod
    async def check_rate_limit(email: str):
        """Checks if the user has exceeded the OTP request rate limit."""
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        record = await db.otp_codes.find_one({"email": email})
        
        if record:
            if record["last_request_time"] > ten_minutes_ago:
                if record["request_count"] >= 3:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many OTP requests. Try again later."
                    )
                return record["request_count"] + 1
        return 1

    @staticmethod
    async def create_otp(email: str):
        """Generates, hashes, and stores a new OTP record."""
        request_count = await OTPService.check_rate_limit(email)
        otp = OTPService.generate_otp()
        otp_hash = hash_password(otp)
        
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        await db.otp_codes.update_one(
            {"email": email},
            {
                "$set": {
                    "otp_hash": otp_hash,
                    "attempts": 0,
                    "expires_at": expires_at,
                    "last_request_time": datetime.utcnow(),
                    "request_count": request_count
                },
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        return otp

    @staticmethod
    async def verify_otp(email: str, otp: str):
        """Verifies the provided OTP against the stored hash."""
        record = await db.otp_codes.find_one({"email": email})
        
        if not record:
            raise HTTPException(status_code=404, detail="No OTP request found")
        
        if datetime.utcnow() > record["expires_at"]:
            await db.otp_codes.delete_one({"email": email})
            raise HTTPException(status_code=400, detail="OTP expired")
        
        if record["attempts"] >= 5:
            await db.otp_codes.delete_one({"email": email})
            raise HTTPException(status_code=400, detail="Max attempts reached. Request a new OTP.")

        if not verify_password(otp, record["otp_hash"]):
            await db.otp_codes.update_one({"email": email}, {"$inc": {"attempts": 1}})
            raise HTTPException(status_code=400, detail="Invalid OTP")

        # Success: Clean up and return true
        await db.otp_codes.delete_one({"email": email})
        return True
