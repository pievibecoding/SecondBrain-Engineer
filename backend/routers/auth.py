from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_session
from backend.dependencies.auth import get_current_user
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.services import auth_service
from backend.models.user import User
from sqlalchemy import select

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_session)) -> TokenResponse:
    # check duplicate
    q = select(User).where(User.email == body.email)
    res = await db.execute(q)
    user = res.scalar_one_or_none()
    if user:
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = auth_service.hash_password(body.password)
    new = User(username=body.username, email=body.email, password_hash=hashed)
    db.add(new)
    await db.flush()
    await db.refresh(new)
    token = auth_service.create_access_token({"sub": str(new.id), "email": new.email, "role": new.role, "username": new.username, "created_at": new.created_at.isoformat() if new.created_at else ""})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(new))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_session)) -> TokenResponse:
    q = select(User).where(User.email == body.email)
    res = await db.execute(q)
    user = res.scalar_one_or_none()
    if not user or not auth_service.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth_service.create_access_token({"sub": str(user.id), "email": user.email, "role": user.role, "username": user.username, "created_at": user.created_at.isoformat() if user.created_at else ""})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
