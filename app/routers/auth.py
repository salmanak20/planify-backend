"""
Authentication router.
POST /auth/register — create a new user
POST /auth/login    — return JWT token
GET  /auth/me       — return current user profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User
from app.schemas.auth import UserCreate, UserLogin, UserFirebaseLogin, UserResponse, Token
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.firebase_auth import verify_firebase_id_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user. Returns JWT immediately so the app can log in."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        occupation=payload.occupation
    )
    db.add(user)
    await db.flush()  # get ID before commit

    token = create_access_token({"sub": str(user.id)})
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email + password. Returns JWT on success."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    token = create_access_token({"sub": str(user.id)})
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login/firebase", response_model=Token)
async def login_firebase(payload: UserFirebaseLogin, db: AsyncSession = Depends(get_db)):
    """Login or register via Firebase Google Sign-In."""
    try:
        claims = verify_firebase_id_token(payload.id_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase credentials"
        )

    firebase_uid = claims.get("uid")
    email = claims.get("email")
    if not firebase_uid or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token payload"
        )

    full_name = payload.full_name or claims.get("name") or "User"

    # 1. Try to find user by firebase_uid
    result = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    user = result.scalar_one_or_none()
    
    if not user:
        # 2. Try by email
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            # Update user with firebase uid
            user.firebase_uid = firebase_uid
            await db.flush()
        else:
            # 3. Create new user
            user = User(
                email=email,
                full_name=full_name,
                firebase_uid=firebase_uid,
                occupation=payload.occupation,
                hashed_password=None
            )
            db.add(user)
            await db.flush()

    token = create_access_token({"sub": str(user.id)})
    return Token(
        access_token=token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
