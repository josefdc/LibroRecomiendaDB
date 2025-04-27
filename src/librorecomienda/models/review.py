# src/librorecomienda/models/review.py
import datetime
from sqlalchemy import (Column, Integer, String, Text, ForeignKey, DateTime,
                      func, CheckConstraint, Index, UniqueConstraint)
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    # Rating obligatorio
    rating = Column(Integer, nullable=False)
    # Comentario opcional (puede ser nulo)
    comment = Column(Text, nullable=True)
    # Fecha de creación automática
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # --- Foreign Keys ---
    # Clave foránea hacia la tabla users. Obligatoria. Indexada para eficiencia.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Clave foránea hacia la tabla books. Obligatoria. Indexada para eficiencia.
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)

    # --- Relaciones ---
    # Define la relación inversa hacia User y Book
    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")

    # --- Restricciones y Índices Adicionales ---
    __table_args__ = (
        # Asegura que el rating esté entre 1 y 5 (ajusta si tu escala es diferente)
        CheckConstraint('rating >= 1 AND rating <= 5', name='review_rating_check'),
        # Opcional: ¿Permitir solo una reseña por usuario por libro?
        # UniqueConstraint('user_id', 'book_id', name='uix_user_book_review'),
    )

    def __repr__(self):
        return f"<Review(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, rating={self.rating})>"