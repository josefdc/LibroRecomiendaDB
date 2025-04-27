# src/librorecomienda/models/user.py
import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    # Email como identificador único y obligatorio
    email = Column(String(255), unique=True, index=True, nullable=False)
    # IMPORTANTE: Aquí guardaremos el HASH de la contraseña, no la contraseña real.
    hashed_password = Column(String(255), nullable=False)
    # Para poder activar/desactivar usuarios
    is_active = Column(Boolean, default=True, nullable=False)
    # Fecha de creación automática en la BD (con zona horaria)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Fecha de actualización automática en la BD (opcional, pero útil)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relación con Review ---
    # Un usuario puede tener muchas reseñas.
    # back_populates crea la relación bidireccional con el modelo Review.
    # cascade="all, delete-orphan": Si se borra un usuario, se borran sus reseñas.
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"