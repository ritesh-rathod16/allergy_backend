from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import UserRegister, UserLogin, Token, OTPVerify, User, ProfileUpdate
from app.core.database import db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.services.email_service import send_otp_email
from datetime import datetime, timedelta
import secrets
import logging
from app.utils.mongo_serializer import serialize_mongo

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    """Register a new user and send an email OTP."""
    email = user.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    otp = str(secrets.randbelow(900000) + 100000)
    
    user_dict = {
        "name": user.name.strip(),
        "email": email,
        "hashed_password": hash_password(user.password),
        "role": "user",
        "is_verified": False,
        "premium_status": False,
        "created_at": datetime.utcnow(),
        "otp": otp,
        "otp_expiry": datetime.utcnow() + timedelta(minutes=5),
        "allergies": [],
        "blood_group": "",
        "weight": 0.0
    }
    
    await db.users.insert_one(user_dict)
    await send_otp_email(email, otp)
    return {"message": "Registration successful. Please check your email for the OTP."}

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password to receive JWT."""
    email = credentials.email.lower().strip()
    user = await db.users.find_one({"email": email})
    
    if not user:
        logger.warning(f"Login failed: User {email} not found.")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user.get("hashed_password")):
        logger.warning(f"Login failed: Incorrect password for {email}.")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if not user.get("is_verified"):
        logger.warning(f"Login failed: User {email} is not verified.")
        raise HTTPException(status_code=400, detail="Email not verified")
    
    # Generate token
    access_token = create_access_token(data={"sub": user["email"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.post("/verify-otp", response_model=Token)
async def verify_otp(data: OTPVerify):
    """Verify email OTP and return JWT."""
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})

    if not user or user.get("otp") != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user.get("otp_expiry") < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired")

    await db.users.update_one(
        {"email": email},
        {"$set": {"is_verified": True, "otp": None, "otp_expiry": None}}
    )
    
    access_token = create_access_token(data={"sub": user["email"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.get("/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Fetch current user profile."""
    user = await db.users.find_one({"email": current_user["sub"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_mongo(user)

@router.put("/update-profile", response_model=User)
async def update_profile(data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    """Update user profile details."""
    update_data = data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    updated_user = await db.users.find_one_and_update(
        {"email": current_user["sub"]},
        {"$set": update_data},
        return_document=True
    )
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_mongo(updated_user)

@router.post("/resend-otp")
async def resend_otp(email: str):
    """Generate and send a new OTP."""
    email = email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    otp = str(secrets.randbelow(900000) + 100000)
    await db.users.update_one(
        {"email": email},
        {"$set": {"otp": otp, "otp_expiry": datetime.utcnow() + timedelta(minutes=5), "last_otp_sent": datetime.utcnow()}}
    )
    await send_otp_email(email, otp)
    return {"message": "OTP resent successfully"}
