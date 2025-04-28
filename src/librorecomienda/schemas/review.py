"""
Esquemas Pydantic para la entidad Review en la API de LibroRecomienda.
Define los modelos de entrada y salida para validación y serialización de reseñas.
"""

from pydantic import BaseModel, Field, ConfigDict
import datetime
from typing import Optional

class ReviewBase(BaseModel):
    """
    Esquema base para una reseña, usado como base para creación y visualización.

    Atributos:
        rating (int): Calificación entre 1 y 5.
        comment (Optional[str]): Comentario opcional de la reseña.
    """
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    """
    Esquema para la creación de una reseña.
    No requiere campos adicionales; user_id y book_id se gestionan aparte.
    """
    pass

class ReviewSchema(ReviewBase):
    """
    Esquema de salida para una reseña, incluyendo campos adicionales.

    Atributos:
        id (int): ID de la reseña.
        user_id (int): ID del usuario que hizo la reseña.
        book_id (int): ID del libro reseñado.
        created_at (datetime.datetime): Fecha de creación de la reseña.
    """
    id: int
    user_id: int
    book_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
