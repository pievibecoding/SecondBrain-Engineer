from backend.services import auth_service
from datetime import timedelta


def test_bcrypt_round_trip():
    plain = "my_secret_password"
    hashed = auth_service.hash_password(plain)
    assert hashed != plain
    assert auth_service.verify_password(plain, hashed) is True
    assert auth_service.verify_password("wrong_pass", hashed) is False


def test_jwt_round_trip():
    claims = {"sub": "user-123", "email": "a@b.com", "role": "user", "username": "alice"}
    token = auth_service.create_access_token(claims)
    decoded = auth_service.verify_token(token)
    assert decoded["sub"] == claims["sub"]
    assert decoded["email"] == claims["email"]
