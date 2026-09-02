from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    email: str

    class Config:
        from_attributes = True  # allows creating this from an ORM User object