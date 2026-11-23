import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.api.auth import TokenVerifier
from app.main import app

ISS = "https://example.supabase.co/auth/v1"


@pytest.fixture(scope="module")
def key():
    return ec.generate_private_key(ec.SECP256R1())


def make_token(key, **over):
    claims = {
        "sub": "11111111-2222-3333-4444-555555555555",
        "aud": "authenticated",
        "iss": ISS,
        "exp": int(time.time()) + 300,
        "is_anonymous": True,
        **over,
    }
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "k1"})


@pytest.fixture
def authed(key, monkeypatch):
    verifier = TokenVerifier("https://example.supabase.co")
    monkeypatch.setattr(
        verifier._jwks,
        "get_signing_key_from_jwt",
        lambda token: type("K", (), {"key": key.public_key()})(),
    )
    with TestClient(app) as c:
        app.state.verifier = verifier
        yield c
        app.state.verifier = None


def test_me_requires_token(authed):
    assert authed.get("/me").status_code == 401
    assert authed.post("/chat", json={"message": "hi"}).status_code == 401


def test_me_with_valid_token(authed, key):
    r = authed.get("/me", headers={"Authorization": f"Bearer {make_token(key)}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "11111111-2222-3333-4444-555555555555", "is_anonymous": True}


@pytest.mark.parametrize(
    "over",
    [{"exp": int(time.time()) - 10}, {"aud": "other"}, {"iss": "https://evil.example/auth/v1"}],
)
def test_bad_tokens_rejected(authed, key, over):
    r = authed.get("/me", headers={"Authorization": f"Bearer {make_token(key, **over)}"})
    assert r.status_code == 401


def test_token_signed_by_other_key_rejected(authed):
    other = ec.generate_private_key(ec.SECP256R1())
    r = authed.get("/me", headers={"Authorization": f"Bearer {make_token(other)}"})
    assert r.status_code == 401
