"""SQLAdmin authentication backend using JWT sessions."""
from __future__ import annotations

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.core.security import (
    RateLimiter,
    create_access_token,
    verify_password,
    verify_token,
)
from app.core.settings import settings


class AdminAuth(AuthenticationBackend):
    def __init__(self, secret_key: str) -> None:
        super().__init__(
            secret_key=secret_key,
            https_only=settings.environment == "production",
            same_site="lax",
        )
        self._ip_login_limiter = RateLimiter(
            limit=settings.admin_login_rate_limit,
            window_seconds=settings.admin_login_window_seconds,
        )
        self._credential_login_limiter = RateLimiter(
            limit=settings.admin_login_rate_limit,
            window_seconds=settings.admin_login_window_seconds,
        )

    def _login_allowed(self, client_ip: str, email: str) -> bool:
        """Apply both an IP-wide and an IP/email credential limit."""
        return self._ip_login_limiter.allow(client_ip) and self._credential_login_limiter.allow(
            f"{client_ip}:{email}"
        )

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")  # sqladmin uses "username" field for email
        password = form.get("password")

        if not email or not password:
            return False
        email = str(email).strip().lower()
        client_ip = request.client.host if request.client else "unknown"
        if not self._login_allowed(client_ip, email):
            return False

        from app.core.database import get_session
        from app.models.users import User

        async for db in get_session():
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user and verify_password(password, user.password):
                token = create_access_token(
                    {"sub": str(user.id)},
                    secret=settings.effective_admin_secret,
                    algorithm=settings.admin_jwt_algorithm,
                    expires_minutes=settings.admin_jwt_expiration_minutes,
                )
                request.session.clear()
                request.session["token"] = token
                return True

        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        try:
            verify_token(
                token,
                secret=settings.effective_admin_secret,
                algorithm=settings.admin_jwt_algorithm,
            )
            return True
        except ValueError:
            return False


def get_authentication_backend() -> AdminAuth:
    return AdminAuth(secret_key=settings.effective_admin_secret)
