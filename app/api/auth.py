from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
import httpx
from app.models.user import UserCreate
logger = logging.getLogger(__name__)
import asyncio
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    async with httpx.AsyncClient() as client:
        # Check if user exists
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{user_data.email}",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {SUPABASE_ANON_KEY}"}
        )
        if response.status_code == 200 and response.json():
            raise HTTPException(400, "User already exists")

        # Hash password (blocking, so run in thread pool)
        loop = asyncio.get_event_loop()
        hashed = await loop.run_in_executor(None, get_password_hash, user_data.password)

        # Insert user
        user_record = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed,
            "is_active": True
        }
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/users",
            json=user_record,
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
        )

        if response.status_code not in (200, 201):
            raise HTTPException(500, "Failed to create user")

        created = response.json()[0]
        return User(**created)
