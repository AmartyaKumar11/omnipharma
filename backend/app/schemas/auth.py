from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRoleSchema(str, Enum):
    ADMIN = "ADMIN"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    INVENTORY_CONTROLLER = "INVENTORY_CONTROLLER"
    STAFF = "STAFF"


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRoleSchema


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: UUID
    email: str
    role: UserRoleSchema
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
