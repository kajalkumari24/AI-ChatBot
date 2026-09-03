from sqlalchemy.orm import Session
from src.models.conversation import Conversation, ChatMessage


def create_conversation(db: Session, title: str = "New Chat") -> Conversation:
    convo = Conversation(title=title)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def get_or_create_conversation(db: Session, session_id: str) -> Conversation:
    convo = db.query(Conversation).filter(Conversation.id == session_id).first()
    if convo:
        return convo

    convo = Conversation(id=session_id, title="New Chat")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def list_conversations(db: Session) -> list[Conversation]:
    return db.query(Conversation).order_by(Conversation.updated_at.desc()).all()


def get_conversation(db: Session, session_id: str) -> Conversation | None:
    return db.query(Conversation).filter(Conversation.id == session_id).first()


def rename_conversation(db: Session, session_id: str, new_title: str) -> Conversation | None:
    convo = get_conversation(db, session_id)
    if not convo:
        return None
    convo.title = new_title
    db.commit()
    db.refresh(convo)
    return convo


def delete_conversation(db: Session, session_id: str) -> bool:
    convo = get_conversation(db, session_id)
    if not convo:
        return False
    db.delete(convo)
    db.commit()
    return True


def add_message(db: Session, session_id: str, role: str, content: str) -> ChatMessage:
    get_or_create_conversation(db, session_id)
    message = ChatMessage(conversation_id=session_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def clear_messages(db: Session, session_id: str) -> None:
    db.query(ChatMessage).filter(ChatMessage.conversation_id == session_id).delete()
    db.commit()
