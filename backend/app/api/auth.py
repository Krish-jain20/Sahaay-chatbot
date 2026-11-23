"""Verify the Supabase access token (JWT) on every protected route.

Supabase signs tokens with an asymmetric key; we fetch the public keys from the project's JWKS
endpoint, so no JWT secret is needed. The user id comes only from the verified token.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer = HTTPBearer(auto_error=False)
ALGORITHMS = ["ES256", "RS256"]


@dataclass(frozen=True)
class User:
    id: str
    is_anonymous: bool
    email: str | None = None


class TokenVerifier:
    def __init__(self, supabase_url: str) -> None:
        self.issuer = f"{supabase_url.rstrip('/')}/auth/v1"
        self._jwks = jwt.PyJWKClient(f"{self.issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600)

    def verify(self, token: str) -> User:
        try:
            key = self._jwks.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt.decode(
                token, key.key, algorithms=ALGORITHMS, audience="authenticated", issuer=self.issuer
            )
        except jwt.PyJWTError as e:
            raise HTTPException(401, "Invalid or expired sign-in") from e
        return User(
            id=claims["sub"], is_anonymous=bool(claims.get("is_anonymous")), email=claims.get("email")
        )


def current_user(
    request: Request, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    verifier: TokenVerifier | None = getattr(request.app.state, "verifier", None)
    if verifier is None:
        if get_settings().auth_required:
            raise HTTPException(503, "Sign-in is not configured")
        return User(id="dev-user", is_anonymous=True)
    if creds is None:
        raise HTTPException(401, "Sign in required")
    return verifier.verify(creds.credentials)


CurrentUser = Annotated[User, Depends(current_user)]
