"""
Modelo ORM para la entidad User en la base de datos de LibroRecomienda.
Define los campos principales de un usuario y su relación con las reseñas.
"""

import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class User(Base):
    """
    Representa un usuario registrado en el sistema.

    Atributos:
        id (int): Identificador primario del usuario.
        email (str): Correo electrónico único del usuario.
        hashed_password (str): Contraseña almacenada de forma segura (hash).
        is_active (bool): Indica si el usuario está activo.
        created_at (datetime): Fecha de creación del usuario.
        updated_at (datetime): Fecha de última actualización del usuario.
        reviews (List[Review]): Lista de reseñas realizadas por el usuario.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """
        Representación legible del objeto User para depuración.

        Returns:
            str: Cadena representando el usuario.
        """
        return f"<User(id={self.id}, email='{self.email}')>"