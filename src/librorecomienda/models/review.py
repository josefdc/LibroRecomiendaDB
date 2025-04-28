"""
Modelo ORM para la entidad Review en la base de datos de LibroRecomienda.
Define los campos principales de una reseña, sus restricciones y relaciones con usuario y libro.
"""

import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime,
    func, CheckConstraint, UniqueConstraint, Boolean
)
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class Review(Base):
    """
    Representa una reseña de un libro realizada por un usuario.

    Atributos:
        id (int): Identificador primario de la reseña.
        rating (int): Calificación otorgada (1 a 5).
        comment (str): Comentario textual de la reseña.
        created_at (datetime): Fecha y hora de creación.
        user_id (int): ID del usuario que realizó la reseña.
        book_id (int): ID del libro reseñado.
        is_deleted (bool): Indica si la reseña está borrada lógicamente.
        user (User): Relación con el usuario autor de la reseña.
        book (Book): Relación con el libro reseñado.
    """
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false', index=True)

    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='review_rating_check'),
        UniqueConstraint('user_id', 'book_id', name='uq_user_book_review'),
    )

    def __repr__(self) -> str:
        """
        Representación legible del objeto Review para depuración.

        Returns:
            str: Cadena representando la reseña, indicando si está borrada.
        """
        deleted_status = " [DELETED]" if self.is_deleted else ""
        return f"<Review(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, rating={self.rating}){deleted_status}>"