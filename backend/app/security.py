from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

_hasher = PasswordHasher()

MIN_PASSWORD_LENGTH = 12


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, raw)
        return True
    except VerifyMismatchError:
        return False


def validate_password_policy(raw: str) -> None:
    """Valide un mot de passe en clair selon la politique MVP.

    NOTE (Plan 6) : la vérification contre la base HIBP locale (fichier de
    hashes Pwned Passwords) est ajoutée au Plan 6, pas ici.
    """
    if len(raw) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères"
        )


class SessionTokenError(Exception):
    """Token de session invalide ou expiré."""


def encode_session_token(*, user_id: int, secret: str) -> str:
    """Encode un token horodaté (l'expiration est vérifiée au décodage)."""
    signer = TimestampSigner(secret)
    return signer.sign(str(user_id)).decode("utf-8")


def decode_session_token(token: str, *, secret: str, max_age_seconds: int) -> int:
    """Décode un token ; lève SessionTokenError s'il est invalide ou trop vieux."""
    signer = TimestampSigner(secret)
    try:
        raw = signer.unsign(token, max_age=max_age_seconds).decode("utf-8")
    except SignatureExpired as exc:
        raise SessionTokenError("Session expirée") from exc
    except BadSignature as exc:
        raise SessionTokenError("Token invalide") from exc
    try:
        return int(raw)
    except ValueError as exc:
        raise SessionTokenError("Format de token invalide") from exc
