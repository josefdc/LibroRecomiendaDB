# src/librorecomienda/crud/crud_user.py
from sqlalchemy.orm import Session
from ..models.user import User
from ..schemas.user import UserCreate
from ..core.security import get_password_hash

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100) -> list:
    """
    Obtiene una lista de usuarios, opcionalmente con paginación.
    Devuelve una lista de tuplas (o Rows) con las columnas seleccionadas.
    NO devuelve la contraseña hasheada por seguridad al mostrar.
    """
    # Correct chaining of methods
    return db.query(
        User.id,
        User.email,
        User.is_active,
        User.created_at,
        User.updated_at
    ).order_by(User.id).offset(skip).limit(limit).all()
