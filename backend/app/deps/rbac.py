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


def require_order_creator(user: Annotated[User, Depends(get_current_user)]) -> User:
    """STAFF, ADMIN, and INVENTORY_CONTROLLER may create sales orders."""
    if user.role not in (UserRole.STAFF, UserRole.ADMIN, UserRole.INVENTORY_CONTROLLER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def require_order_reader(user: Annotated[User, Depends(get_current_user)]) -> User:
    """BRANCH_MANAGER is read-only; all roles may list or view orders."""
    if user.role not in (
        UserRole.STAFF,
        UserRole.ADMIN,
        UserRole.INVENTORY_CONTROLLER,
        UserRole.BRANCH_MANAGER,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def require_dashboard_summary(user: Annotated[User, Depends(get_current_user)]) -> User:
    """All operational roles may view the summary strip (STAFF included)."""
    if user.role not in (
        UserRole.ADMIN,
        UserRole.BRANCH_MANAGER,
        UserRole.INVENTORY_CONTROLLER,
        UserRole.STAFF,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """ADMIN-only: audit logs and sensitive configuration."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


def require_dashboard_analytics(user: Annotated[User, Depends(get_current_user)]) -> User:
    """STAFF is summary-only; trend and store views require elevated roles."""
    if user.role not in (UserRole.ADMIN, UserRole.BRANCH_MANAGER, UserRole.INVENTORY_CONTROLLER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user
