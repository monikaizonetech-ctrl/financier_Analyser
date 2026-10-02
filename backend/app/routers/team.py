from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserOut, UserCreateByAdmin, UserUpdate, PaginatedUsers

router = APIRouter(prefix="/team", tags=["Team Management"])


@router.get("/users", response_model=PaginatedUsers)
def list_users(
    role: UserRole | None = Query(default=None),
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org_owner_id = current_user.org_id
    query = db.query(User).filter(or_(User.id == org_owner_id, User.added_by_id == org_owner_id))
    if role:
        query = query.filter(User.role == role)
    query = query.order_by(User.created_at.asc())

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedUsers(items=items, total=total, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_owner_id = current_user.org_id
    user = db.query(User).filter(
        User.id == user_id, or_(User.id == org_owner_id, User.added_by_id == org_owner_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def add_user(
    payload: UserCreateByAdmin,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        added_by_id=current_user.org_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db),
):
    org_owner_id = current_user.org_id
    user = db.query(User).filter(
        User.id == user_id, or_(User.id == org_owner_id, User.added_by_id == org_owner_id)
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(
    user_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    user = db.query(User).filter(User.id == user_id, User.added_by_id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None
