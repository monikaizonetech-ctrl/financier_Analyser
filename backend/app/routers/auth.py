from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.billing import Subscription
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        role=UserRole.ADMIN,  # first user of a new org is the Admin
    )
    db.add(user)
    db.flush()

    db.add(Subscription(user_id=user.id))
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if user.status.value == "Inactive":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    token = create_access_token(subject=user.id, extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
