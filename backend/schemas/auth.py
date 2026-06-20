from pydantic import BaseModel, EmailStr, field_validator
from pydantic import ConfigDict
from datetime import datetime
from uuid import UUID


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email", "password")
    @classmethod
    def field_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | str
    username: str
    email: str
    role: str
    created_at: datetime | str | None = None

    def model_post_init(self, __context):
        # normalize id to str for consistent serialization
        object.__setattr__(self, 'id', str(self.id))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
