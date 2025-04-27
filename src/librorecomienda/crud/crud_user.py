# src/librorecomienda/crud/crud_user.py
from sqlalchemy.orm import Session
# Asegúrate que User esté bien definido en models.user
from librorecomienda.models.user import User
from librorecomienda.schemas.user import UserCreate
from librorecomienda.core.security import get_password_hash

def get_user_by_email(db: Session, email: str) -> User | None:
    """Busca un usuario por su dirección de email."""
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate) -> User:
    """Crea un nuevo registro de usuario en la BD."""
    hashed_password = get_password_hash(user.password)
    # Crea la instancia del modelo SQLAlchemy
    db_user = User(
        email=user.email,
        hashed_password=hashed_password
        # is_active tiene valor por defecto True en el modelo
    )
    db.add(db_user) # Añade a la sesión
    db.commit()      # Guarda en la BD
    db.refresh(db_user) # Refresca para obtener el ID asignado
    return db_user
