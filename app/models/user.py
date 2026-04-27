from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class Allergy(BaseModel):
    name: str
    severity: str  # low, medium, high

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class User(UserBase):
    id: Optional[str] = Field(None, alias="_id")
    role: str = "user"
    is_verified: bool = False
    premium_status: bool = False
    
    # Medical Profile Fields
    blood_group: Optional[str] = ""
    weight: Optional[float] = 0.0
    age: Optional[int] = 0
    gender: Optional[str] = ""
    allergies: List[Allergy] = []
    emergency_contact: Optional[str] = ""
    medical_notes: Optional[str] = ""

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    blood_group: Optional[str] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    allergies: Optional[List[Allergy]] = None
    emergency_contact: Optional[str] = None
    medical_notes: Optional[str] = None

class UserInDB(User):
    hashed_password: str
    otp: Optional[str] = None
    otp_expiry: Optional[datetime] = None
    last_otp_sent: Optional[datetime] = None
    otp_attempts: int = 0
