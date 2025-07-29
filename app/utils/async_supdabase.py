import httpx
from app.core.config import settings

SUPABASE_URL = settings.supabase_url.rstrip("/")
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
        return resp.json()