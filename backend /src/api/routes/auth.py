"""
api/routes/auth.py — POST /api/auth/signup, POST /api/auth/login
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.schemas.auth import SignupRequest, LoginRequest, TokenResponse
from src.services import auth_service
from src.core.security import create_access_token

router = APIRouter()


@router.post("/auth/signup", response_model=TokenResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.signup(db, request.email, request.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        token = auth_service.login(db, request.email, request.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    return TokenResponse(access_token=token)
