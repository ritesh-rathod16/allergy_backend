from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.core.database import db
from datetime import datetime

router = APIRouter()

@router.post("/log")
async def log_reaction(reaction_data: dict, user: dict = Depends(get_current_user)):
    # reaction_data: { symptoms: ["Rash", "Swelling"], severity: 5, notes: "After eating X" }
    reaction_data.update({
        "user_id": user["sub"],
        "timestamp": datetime.utcnow()
    })
    
    await db.reactions.insert_one(reaction_data)
    
    # Simple pattern detection (Mock ML clustering)
    recent_reactions = await db.reactions.find({"user_id": user["sub"]}).to_list(10)
    
    return {"message": "Reaction logged successfully.", "history_count": len(recent_reactions)}

@router.get("/history")
async def get_reaction_history(user: dict = Depends(get_current_user)):
    history = await db.reactions.find({"user_id": user["sub"]}).sort("timestamp", -1).to_list(50)
    for item in history:
        item["_id"] = str(item["_id"])
    return history
