"""
Authentication API endpoints
"""

import time
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.vault_service import VaultService

router = APIRouter()
logger = structlog.get_logger(__name__)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    username: str
    email: Optional[str] = None
    roles: list[str] = []


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    settings = get_settings()
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    vault_service: VaultService = Depends(lambda: None)  # Will be injected by dependency override
) -> UserInfo:
    """Get current authenticated user"""
    settings = get_settings()
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # In a real implementation, you would fetch user info from Vault or a database
    user = UserInfo(
        username=username,
        email=f"{username}@example.com",
        roles=["user"]
    )
    
    return user


async def authenticate_user(username: str, password: str, vault_service: VaultService) -> Optional[UserInfo]:
    """Authenticate user against Vault or other auth backend"""
    try:
        # In a real implementation, this would authenticate against Vault's userpass auth method
        # For demo purposes, we'll use a simple check
        if username == "admin" and password == "admin123":
            return UserInfo(
                username=username,
                email=f"{username}@intellistore.local",
                roles=["admin", "user"]
            )
        elif username == "user" and password == "user123":
            return UserInfo(
                username=username,
                email=f"{username}@intellistore.local",
                roles=["user"]
            )
        
        # Try to authenticate with Vault
        if vault_service:
            # This would use Vault's userpass auth method
            # vault_response = await vault_service.authenticate_user(username, password)
            # if vault_response:
            #     return UserInfo(username=username, roles=vault_response.get("roles", []))
            pass
        
        return None
        
    except Exception as e:
        logger.error("Authentication error", username=username, error=str(e))
        return None


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    vault_service: VaultService = Depends(lambda: None)
):
    """Authenticate user and return access token"""
    logger.info("Login attempt", username=request.username)
    
    user = await authenticate_user(request.username, request.password, vault_service)
    if not user:
        logger.warning("Failed login attempt", username=request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "roles": user.roles},
        expires_delta=access_token_expires
    )
    
    logger.info("Successful login", username=user.username)
    
    return LoginResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/logout")
async def logout(current_user: UserInfo = Depends(get_current_user)):
    """Logout user (invalidate token)"""
    # In a real implementation, you would add the token to a blacklist
    logger.info("User logout", username=current_user.username)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.post("/refresh")
async def refresh_token(current_user: UserInfo = Depends(get_current_user)):
    """Refresh access token"""
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": current_user.username, "roles": current_user.roles},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: UserInfo = Depends(get_current_user),
    vault_service: VaultService = Depends(lambda: None)
):
    """Change user password"""
    # Verify current password
    user = await authenticate_user(current_user.username, current_password, vault_service)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # In a real implementation, you would update the password in Vault
    # await vault_service.update_user_password(current_user.username, new_password)
    
    logger.info("Password changed", username=current_user.username)
    return {"message": "Password changed successfully"}