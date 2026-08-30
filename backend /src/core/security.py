from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = settings.JWT_SECRET
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


if __name__ == "__main__":
    print("Testing security functions...")
    hashed = hash_password("test123")
    print("Password hashed OK:", verify_password("test123", hashed))
    token = create_access_token("user-abc-123")
    print("Token created:", token[:30] + "...")
    user_id = decode_access_token(token)
    print("Token decoded OK:", user_id == "user-abc-123")
    print("security.py OK")
