"""Authentication: API key and JWT-based access control."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt  # type: ignore

from db.models import DatabaseManager

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages API key and JWT authentication."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        secret = os.getenv("JWT_SECRET_KEY", "").strip()
        if len(secret) < 32 or secret in {"change-this-jwt-secret", "changeme"}:
            raise RuntimeError(
                "JWT_SECRET_KEY must be set to a random value of at least 32 characters"
            )
        self.secret_key = secret
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        self.api_key_header = os.getenv("API_KEY_HEADER", "X-API-Key")

    async def authenticate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user by API key."""
        if not api_key:
            return None
        try:
            user = await self.db.get_user_by_api_key(api_key)
            if user and user.get("is_active"):
                return user
        except Exception as exc:
            logger.warning("API key authentication failed: %s", exc)
        return None

    def create_access_token(self, user_id: str, role: str) -> str:
        """Create a JWT access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "role": role,
            "iat": now,
            "exp": expire,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.warning("Invalid JWT token: %s", exc)
            return None

    def extract_api_key(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract API key from request headers."""
        return headers.get(self.api_key_header) or headers.get(
            self.api_key_header.lower()
        )

    def extract_bearer_token(self, authorization: Optional[str]) -> Optional[str]:
        """Extract bearer token from Authorization header."""
        if not authorization:
            return None
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None
