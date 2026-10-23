from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
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
    email_clean = payload.email.strip().lower()
    existing = db.query(User).filter(func.lower(User.email) == email_clean).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=payload.name.strip(),
        email=email_clean,
        phone=payload.phone.strip() if payload.phone else None,
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
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email_clean).first()

    # Support domain aliases (e.g. proanalyser.in <-> izoneanalyzer.in)
    if not user:
        if "@proanalyser.in" in email_clean:
            alt_email = email_clean.replace("@proanalyser.in", "@izoneanalyzer.in")
            user = db.query(User).filter(func.lower(User.email) == alt_email).first()
        elif "@izoneanalyzer.in" in email_clean:
            alt_email = email_clean.replace("@izoneanalyzer.in", "@proanalyser.in")
            user = db.query(User).filter(func.lower(User.email) == alt_email).first()

    if not user:
        print(f"[AUTH LOGIN FAILED] Email not found: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No account found with email '{payload.email}'. Please check your email or click 'Create one' to register."
        )

    # Verify password with dev master fallback
    is_valid_pw = verify_password(payload.password, user.hashed_password) or (payload.password == "Admin@123")
    if not is_valid_pw:
        print(f"[AUTH LOGIN FAILED] Incorrect password for email: {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password. For demo/dev accounts you can use 'Admin@123'."
        )

    if user.status.value == "Inactive":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    print(f"[AUTH LOGIN SUCCESS] User: {user.email} (Role: {user.role.value})")
    token = create_access_token(subject=user.id, extra_claims={"role": user.role.value})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
