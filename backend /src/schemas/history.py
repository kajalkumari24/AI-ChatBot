from pydantic import BaseModel
from datetime import datetime


class ChatSummary(BaseModel):
    session_id: str
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    chats: list[ChatSummary]


class MessageOut(BaseModel):
    role: str
    content: str

    class Config:
        from_attributes = True


class ChatDetailResponse(BaseModel):
    session_id: str
    title: str
    messages: list[MessageOut]
