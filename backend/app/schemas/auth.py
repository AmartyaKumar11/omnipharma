import re
from datetime import datetime
from enum import Enum
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator


class UserRoleSchema(str, Enum):
    ADMIN = "ADMIN"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    INVENTORY_CONTROLLER = "INVENTORY_CONTROLLER"
    STAFF = "STAFF"


def _normalize_username(v: str) -> str:
    return v.strip().lower()


class SignupRequest(BaseModel):
    """email is optional; do not use EmailStr here — Pydantic/OpenAPI can treat it as required."""

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    role: UserRoleSchema
    email: str | None = Field(default=None, max_length=320)
    store_id: UUID | None = Field(default=None)

    @field_validator("email", mode="before")
    @classmethod
    def email_optional_validated(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        if isinstance(v, str):
            try:
                return validate_email(v.strip(), check_deliverability=False).normalized
            except EmailNotValidError:
                raise ValueError("Invalid email address (or leave the field empty)") from None
        return v

    @field_validator("username", mode="before")
    @classmethod
    def username_normalize(cls, v: object) -> object:
        if isinstance(v, str):
            s = _normalize_username(v)
            if not re.fullmatch(r"[a-z0-9_]{3,32}", s):
                raise ValueError("Username: 3–32 characters, lowercase letters, digits, underscore only")
            return s
        return v


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def username_lower(cls, v: object) -> object:
        if isinstance(v, str):
            return _normalize_username(v)
        return v


class UserPublic(BaseModel):
    id: UUID
    username: str
    email: str | None
    role: UserRoleSchema
    store_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
