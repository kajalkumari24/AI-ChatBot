from fastapi import APIRouter
from src.api.routes import chat, auth, convert, history, files

api_router = APIRouter(prefix="/api")
api_router.include_router(chat.router)
api_router.include_router(auth.router)
api_router.include_router(convert.router)
api_router.include_router(history.router)
api_router.include_router(files.router)
