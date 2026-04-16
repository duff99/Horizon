import time

import pytest

from app.security import (
    MIN_PASSWORD_LENGTH,
    SessionTokenError,
    decode_session_token,
    encode_session_token,
    hash_password,
    validate_password_policy,
    verify_password,
)


def test_hash_verify_roundtrip() -> None:
    raw = "correct horse battery staple"
    h = hash_password(raw)
    assert h != raw
    assert verify_password(raw, h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_unique_per_call() -> None:
    raw = "same_password"
    assert hash_password(raw) != hash_password(raw)


def test_policy_accepts_long_password() -> None:
    validate_password_policy("Un_MotDePasse_Solide_2026!")


def test_policy_rejects_too_short() -> None:
    with pytest.raises(ValueError, match=f"{MIN_PASSWORD_LENGTH} caractères"):
        validate_password_policy("trop_court")


def test_policy_accepts_minimum_length() -> None:
    validate_password_policy("a" * MIN_PASSWORD_LENGTH)


def test_session_token_roundtrip() -> None:
    secret = "x" * 32
    token = encode_session_token(user_id=42, secret=secret)
    assert decode_session_token(token, secret=secret, max_age_seconds=3600) == 42


def test_session_token_expired() -> None:
    secret = "x" * 32
    token = encode_session_token(user_id=7, secret=secret)
    time.sleep(2)
    with pytest.raises(SessionTokenError, match="expirée"):
        decode_session_token(token, secret=secret, max_age_seconds=1)


def test_session_token_tampered() -> None:
    secret = "x" * 32
    token = encode_session_token(user_id=7, secret=secret)
    with pytest.raises(SessionTokenError):
        decode_session_token(token + "tamper", secret=secret, max_age_seconds=3600)


def test_session_token_wrong_secret() -> None:
    token = encode_session_token(user_id=7, secret="a" * 32)
    with pytest.raises(SessionTokenError):
        decode_session_token(token, secret="b" * 32, max_age_seconds=3600)
