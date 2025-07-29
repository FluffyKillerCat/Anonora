from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.models.user import TokenData
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")

        if email is None:
            return None

        token_data = TokenData(email=email, user_id=user_id)
        return token_data

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        return None


def get_current_user_id(token: str) -> Optional[str]:
    token_data = verify_token(token)
    if token_data:
        return token_data.user_id
    return None


def get_current_user_email(token: str) -> Optional[str]:
    token_data = verify_token(token)
    if token_data:
        return token_data.email
    return None