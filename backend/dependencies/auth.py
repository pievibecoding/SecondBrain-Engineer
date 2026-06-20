from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services import auth_service
from backend.schemas.auth import UserResponse

bearer_scheme = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> UserResponse:
    claims = auth_service.verify_token(credentials.credentials)
    return UserResponse(
        id=claims["sub"],
        email=claims["email"],
        role=claims["role"],
        username=claims.get("username",""),
        created_at=claims.get("created_at"),
    )


async def require_admin(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
