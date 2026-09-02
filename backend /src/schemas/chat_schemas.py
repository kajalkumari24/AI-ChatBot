from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or message")
    conversation_id: Optional[str] = Field(default="default", description="Session ID for chat history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="LLM generated answer")
    sources: Optional[List[Dict[str, Any]]] = Field(default=[], description="Retrieved source documents")

class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int