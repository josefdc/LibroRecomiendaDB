# src/librorecomienda/core/security.py
from passlib.context import CryptContext

# Usa bcrypt, el estándar recomendado
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara una contraseña plana con su hash almacenado."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Genera un hash seguro para una contraseña."""
    return pwd_context.hash(password)
