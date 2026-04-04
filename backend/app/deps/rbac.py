from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.deps.auth import get_current_user
from app.models.enums import UserRole
from app.models.user import User


def require_inventory_mutator(user: Annotated[User, Depends(get_current_user)]) -> User:
    """ADMIN and INVENTORY_CONTROLLER may create products, batches, and change stock."""
    if user.role not in (UserRole.ADMIN, UserRole.INVENTORY_CONTROLLER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def require_inventory_reader(user: Annotated[User, Depends(get_current_user)]) -> User:
    """All authenticated platform roles may view inventory and alerts."""
    if user.role not in (
        UserRole.ADMIN,
        UserRole.BRANCH_MANAGER,
        UserRole.INVENTORY_CONTROLLER,
        UserRole.STAFF,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user
