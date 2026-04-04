from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.deps.auth import get_current_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        role=UserRole(body.role.value),
        full_name=None,
        is_active=True,
        last_login_at=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(
        str(user.id),
        extra={"email": user.email, "role": user.role.value},
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
def me(current: Annotated[User, Depends(get_current_user)]) -> User:
    return current


@router.get("/admin/ping")
def admin_ping(_user: Annotated[User, Depends(require_role(UserRole.ADMIN))]) -> dict[str, str]:
    return {"message": "admin OK"}
