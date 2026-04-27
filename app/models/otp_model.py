from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class OTPRecord(BaseModel):
    email: EmailStr
    otp_hash: str
    attempts: int = 0
    expires_at: datetime
    created_at: datetime
    request_count: int = 1
    last_request_time: datetime
