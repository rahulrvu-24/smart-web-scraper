from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core import audit
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: DbSession, request: Request) -> User:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    user = User(email=email, hashed_password=hash_password(body.password), full_name=body.full_name)
    db.add(user)
    db.flush()  # assigns user.id so the audit row can point at it
    audit.record(db, request, "auth.register", user_id=user.id, target_type="user", target_id=user.id)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession, request: Request) -> Token:
    # OAuth2's form calls the field "username"; we use it for the email.
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if user is None or not verify_password(form.password, user.hashed_password):
        # Failed logins are saved even though the request fails: they're how you spot
        # someone guessing passwords.
        audit.record(
            db, request, "auth.login_failed", user_id=user.id if user else None, details={"email": form.username.lower()[:320]}
        )
        db.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="This account is disabled")
    audit.record(db, request, "auth.login", user_id=user.id)
    db.commit()
    return Token(access_token=create_access_token(str(user.id)))

@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user