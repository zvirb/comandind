"""Simple password hashing utilities for create_admin script."""

from passlib.context import CryptContext

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)