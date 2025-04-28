"""
Operaciones CRUD para el modelo User en la base de datos del sistema LibroRecomienda.
Incluye funciones para crear usuarios, obtener usuarios por email y listar usuarios.
Pensado para ser utilizado por la capa de servicios y autenticación.
"""

from sqlalchemy.orm import Session
from ..models.user import User
from ..schemas.user import UserCreate
from ..core.security import get_password_hash
from typing import Optional, List, Any

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Obtiene un usuario por su email.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        email (str): Email del usuario a buscar.

    Returns:
        Optional[User]: El usuario si existe, None si no.
    """
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    """
    Crea un nuevo usuario en la base de datos.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        user (UserCreate): Objeto con los datos del usuario a crear.

    Returns:
        User: El usuario creado.
    """
    hashed_password: str = get_password_hash(user.password)
    db_user: User = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[Any]:
    """
    Obtiene una lista de usuarios, opcionalmente con paginación.
    Devuelve una lista de tuplas (o Rows) con las columnas seleccionadas.
    NO devuelve la contraseña hasheada por seguridad al mostrar.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        skip (int): Número de registros a omitir (paginación).
        limit (int): Número máximo de registros a devolver.

    Returns:
        List[Any]: Lista de Rows/Tuplas con los campos seleccionados del usuario.
    """
    return db.query(
        User.id,
        User.email,
        User.is_active,
        User.created_at,
        User.updated_at
    ).order_by(User.id).offset(skip).limit(limit).all()
