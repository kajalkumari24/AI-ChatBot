from typing import Optional
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from PIL import Image
import io

from src.core.rag_engine import ask
from src.services import memory, history_service
from src.db.database import get_db

router = APIRouter()


@router.post("/chat")
async def chat(
    message: str = Form(...),
    session_id: str = Form("default_session"),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    image_obj = None
    if file:
        try:
            contents = await file.read()
            image_obj = Image.open(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")

    reply = ask(session_id=session_id, user_message=message, image=image_obj)

    history_service.get_or_create_conversation(db, session_id)
    history_service.add_message(db, session_id, "user", message)
    history_service.add_message(db, session_id, "assistant", reply)

    return {"reply": reply, "session_id": session_id}


@router.post("/clear")
async def clear_chat_history(session_id: str = Form("default_session"), db: Session = Depends(get_db)):
    memory.clear_session(session_id)
    history_service.clear_messages(db, session_id)
    return {"status": "success", "message": "Memory cleared"}


@router.get("/health")
def health():
    return {"status": "ok"}
