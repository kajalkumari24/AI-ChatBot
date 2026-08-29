from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.schemas.history import ChatListResponse, ChatSummary, ChatDetailResponse, MessageOut
from src.services import history_service

router = APIRouter(prefix="/history")


@router.post("/create")
def create_chat(db: Session = Depends(get_db)):
    convo = history_service.create_conversation(db)
    return {"session_id": convo.id, "title": convo.title}


@router.get("", response_model=ChatListResponse)
def list_chats(db: Session = Depends(get_db)):
    conversations = history_service.list_conversations(db)
    return ChatListResponse(
        chats=[
            ChatSummary(
                session_id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    )


@router.get("/{session_id}", response_model=ChatDetailResponse)
def get_chat(session_id: str, db: Session = Depends(get_db)):
    convo = history_service.get_conversation(db, session_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ChatDetailResponse(
        session_id=convo.id,
        title=convo.title,
        messages=[MessageOut(role=m.role, content=m.content) for m in convo.messages],
    )


@router.patch("/{session_id}/rename")
def rename_chat(session_id: str, title: str = Form(...), db: Session = Depends(get_db)):
    convo = history_service.rename_conversation(db, session_id, title)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"session_id": convo.id, "title": convo.title}


@router.delete("/{session_id}")
def delete_chat(session_id: str, db: Session = Depends(get_db)):
    deleted = history_service.delete_conversation(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}
