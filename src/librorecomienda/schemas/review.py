#LibroRecomienda/src/librorecomienda/schemas/review.py
from pydantic import BaseModel, Field
import datetime

class ReviewBase(BaseModel):
    rating: int = Field(..., ge=1, le=5) # Rating entre 1 y 5
    comment: str | None = None

class ReviewCreate(ReviewBase):
    pass # No necesita más campos para la creación (user_id/book_id vienen aparte)

class ReviewSchema(ReviewBase):
    id: int
    user_id: int
    book_id: int
    created_at: datetime.datetime
    # Podrías añadir el email del usuario aquí si haces join en el CRUD
    # user_email: str | None = None

    class Config:
        from_attributes = True
