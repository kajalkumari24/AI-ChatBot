from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    filename: str
    content_type: str
    size_bytes: int