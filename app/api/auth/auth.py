from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import UserCreate, User, Token, UserUpdate
from app.core.security import create_access_token, verify_password, get_password_hash, verify_token
from app.core.database import db_manager
from typing import Optional
import logging
import httpx
from app.core.config import settings

SUPABASE_URL = settings.supabase_url
SUPABASE_KEY = settings.supabase_key

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

async def fetch_user_by_email(email: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/users",
            params={"email": f"eq.{email}"},
            headers=get_headers()
        )
        resp.raise_for_status()
        return resp.json()

async def insert_user(user_data: dict):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/users",
            json=user_data,
            headers=get_headers()
        )
        resp.raise_for_status()

        if resp.content:
            return resp.json()
        else:
            print("Empty response from Supabase:", resp.status_code)
            return user_data


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    try:
        existing_users = await fetch_user_by_email(user_data.email)
        if existing_users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )


        hashed_password = get_password_hash(user_data.password)
        user_record = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "is_active": True
        }
        created_users = await insert_user(user_record)
        #created_user = created_users[0]
        return user_record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(email: str, password: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}",
                headers=get_headers()
            )
            resp.raise_for_status()
            users = resp.json()

            if not users:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            user = users[0]

            if not verify_password(password, user["hashed_password"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled"
                )

            token_data = {
                "sub": user["email"],
                "user_id": str(user["id"])
            }

            access_token = create_access_token(data=token_data)

            return Token(access_token=access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=User)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        token_data = verify_token(token)

        if not token_data or not token_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{token_data.user_id}",
                headers=get_headers()
            )
            resp.raise_for_status()
            users = resp.json()

            if not users:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            user = users[0]

            return User(
                id=user["id"],
                email=user["email"],
                full_name=user["full_name"],
                is_active=user["is_active"],
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        token = credentials.credentials
        token_data = verify_token(token)

        if not token_data or not token_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        async with httpx.AsyncClient() as client:
            update_data = {}
            if user_update.email is not None:
                update_data["email"] = user_update.email
            if user_update.full_name is not None:
                update_data["full_name"] = user_update.full_name
            if user_update.is_active is not None:
                update_data["is_active"] = user_update.is_active

            if not update_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )

            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{token_data.user_id}",
                json=update_data,
                headers=get_headers()
            )
            resp.raise_for_status()
            updated_user = resp.json()[0]

            return User(
                id=updated_user["id"],
                email=updated_user["email"],
                full_name=updated_user["full_name"],
                is_active=updated_user["is_active"],
                created_at=updated_user["created_at"],
                updated_at=updated_user["updated_at"]
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    user_id = verify_token(token)

    if not user_id or not user_id.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return user_id.user_id