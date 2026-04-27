from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user
from app.services.ai_service import AIService
from app.core.database import db
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    query: str

@router.post("/message")
async def chat_with_ai(request: ChatMessageRequest, user_token: dict = Depends(get_current_user)):
    try:
        # Fetch actual user from DB to ensure real-time premium status
        user = await db.users.find_one({"email": user_token["sub"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # --- 💎 PREMIUM LOGIC ---
        is_premium = user.get("premium_status", False)
        
        if not is_premium:
            # Check chat limits only for free users
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            chat_count = await db.chat_history.count_documents({
                "user_id": user_token["sub"],
                "role": "user",
                "timestamp": {"$gte": today}
            })
            
            if chat_count >= 5:
                raise HTTPException(
                    status_code=403, 
                    detail="Daily AI chat limit reached. Upgrade to Premium for unlimited chat!"
                )

        # Fetch recent chat history for context (last 10 messages)
        history = await db.chat_history.find({"user_id": user_token["sub"]}).sort("timestamp", -1).to_list(10)
        history.reverse()
        
        # Get AI response from Gemini
        ai_response = await AIService.chatbot_response(request.query, history)
        
        # Save interaction to persistent history
        now = datetime.utcnow()
        await db.chat_history.insert_many([
            {
                "user_id": user_token["sub"],
                "role": "user",
                "content": request.query,
                "timestamp": now
            },
            {
                "user_id": user_token["sub"],
                "role": "assistant",
                "content": ai_response,
                "timestamp": now
            }
        ])
        
        return {"reply": ai_response}
        
    except HTTPException:
        rethrow
    except Exception as e:
        logger.error(f"Chat Route Error: {e}")
        return {"reply": "I'm having trouble thinking right now. Please try again in a moment."}

@router.get("/history")
async def get_chat_history(user_token: dict = Depends(get_current_user)):
    # Return latest 50 messages for the UI
    history = await db.chat_history.find({"user_id": user_token["sub"]}).sort("timestamp", -1).to_list(50)
    for item in history:
        item["_id"] = str(item["_id"])
    return history

@router.delete("/clear")
async def clear_chat_history(user_token: dict = Depends(get_current_user)):
    await db.chat_history.delete_many({"user_id": user_token["sub"]})
    return {"message": "Chat history cleared"}
