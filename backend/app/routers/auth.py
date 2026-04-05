from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.deps.auth import get_current_user, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.models.mapping import UserStoreMapping
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> User:
    existing_user = db.scalar(select(User).where(User.username == body.username))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    
    if body.role != UserRole.ADMIN and not body.store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="store_id is required for non-ADMIN users")

    if body.email is not None:
        existing_email = db.scalar(select(User).where(User.email == body.email.lower()))
        if existing_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    
    user = User(
        username=body.username,
        email=body.email.lower() if body.email else None,
        password_hash=hash_password(body.password),
        role=UserRole(body.role.value),
        full_name=None,
        is_active=True,
        last_login_at=None,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        
        if body.store_id and body.role != UserRole.ADMIN:
            mapping = UserStoreMapping(user_id=user.id, store_id=body.store_id)
            db.add(mapping)
            db.commit()
            
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database error while creating the user. "
                "Ensure PostgreSQL is running and apply migrations: "
                "`cd backend && alembic upgrade head`"
            ),
        ) from e
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = db.scalar(select(User).where(User.username == body.username))
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Check PostgreSQL and DATABASE_URL (see backend/.env).",
        ) from e
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
        
    mapping = db.scalar(select(UserStoreMapping).where(UserStoreMapping.user_id == user.id))
    
    if user.role != UserRole.ADMIN and not mapping:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No store mapped to this user session. Access restricted."
        )
        
    store_id_str = str(mapping.store_id) if mapping else None

    token = create_access_token(
        str(user.id),
        extra={"username": user.username, "email": user.email, "role": user.role.value, "store_id": store_id_str},
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
def me(current: Annotated[User, Depends(get_current_user)]) -> User:
    return current


@router.get("/admin/ping")
def admin_ping(_user: Annotated[User, Depends(require_role(UserRole.ADMIN))]) -> dict[str, str]:
    return {"message": "admin OK"}
