from sqlalchemy.orm import Session
from src.models.user import User
from src.core.security import hash_password, verify_password, create_access_token


def signup(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("A user with this email already exists")

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(db: Session, email: str, password: str) -> str:
    """Returns a JWT access token if credentials are valid, raises ValueError otherwise."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid email or password")

    return create_access_token(user.id)
