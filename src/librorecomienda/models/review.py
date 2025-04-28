# src/librorecomienda/models/review.py
import datetime
# Asegúrate de importar Boolean
from sqlalchemy import (Column, Integer, String, Text, ForeignKey, DateTime,
                      func, CheckConstraint, Index, UniqueConstraint, Boolean) # Añadir Boolean
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)

    # --- Nueva Columna ---
    # default=False: Nuevas reseñas no están borradas.
    # nullable=False: Siempre debe tener un valor (True o False).
    # server_default='false': Ayuda a la BD a poner un valor por defecto explícito.
    # index=True: Útil para filtrar rápidamente las borradas/no borradas.
    is_deleted = Column(Boolean, default=False, nullable=False, server_default='false', index=True)
    # --------------------

    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")

    __table_args__ = (
        # Ensure rating is between 1 and 5
        CheckConstraint('rating >= 1 AND rating <= 5', name='review_rating_check'),
        # Ensure a user can review a specific book only once
        UniqueConstraint('user_id', 'book_id', name='uq_user_book_review'),
        # Add other table-level constraints here if needed
    )

    def __repr__(self):
        # Actualizar si quieres indicar si está borrada
        deleted_status = " [DELETED]" if self.is_deleted else ""
        return f"<Review(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, rating={self.rating}){deleted_status}>"