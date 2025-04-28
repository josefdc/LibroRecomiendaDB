"""
Utilidades de seguridad para LibroRecomienda.

Este módulo proporciona funciones para el hasheo y verificación de contraseñas
utilizando bcrypt a través de passlib. Se utiliza para almacenar y comprobar
contraseñas de usuarios de forma segura.

Funciones:
    verify_password(plain_password: str, hashed_password: str) -> bool
    get_password_hash(password: str) -> str
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña en texto plano contra su versión hasheada.

    Args:
        plain_password (str): Contraseña en texto plano a verificar.
        hashed_password (str): Contraseña hasheada para comparar.

    Returns:
        bool: True si la contraseña coincide con el hash, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro para una contraseña dada.

    Args:
        password (str): Contraseña en texto plano a hashear.

    Returns:
        str: Contraseña hasheada.
    """
    return pwd_context.hash(password)
