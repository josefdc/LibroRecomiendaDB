from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.review import Review
from ..models.user import User
from ..models.book import Book
from ..schemas.review import ReviewCreate

import logging  # Añade logging para mensajes

logger = logging.getLogger(__name__)


def create_review(db: Session, review: ReviewCreate, user_id: int, book_id: int) -> Review:
    db_review = Review(**review.model_dump(), user_id=user_id, book_id=book_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_reviews_for_book(db: Session, book_id: int, limit: int = 20) -> list[Review]:
    """Obtiene las últimas 'limit' reseñas NO BORRADAS para un libro."""
    return db.query(Review).\
            filter(Review.book_id == book_id, Review.is_deleted == False).\
            order_by(desc(Review.created_at)).\
            limit(limit).all()


def get_reviews_for_book_with_user(db: Session, book_id: int, limit: int = 20) -> list:
    """Obtiene reseñas NO BORRADAS y el email del usuario que la hizo.
       Devuelve una lista de tuplas (o Rows) con (Review, User.email).
    """
    return db.query(Review, User.email).\
            join(User, Review.user_id == User.id).\
            filter(Review.book_id == book_id, Review.is_deleted == False).\
            order_by(desc(Review.created_at)).\
            limit(limit).all()


def get_review_by_id(db: Session, review_id: int) -> Review | None:
     """Obtiene una reseña específica por su ID (incluyendo borradas lógicamente)."""
     return db.get(Review, review_id)


def soft_delete_review(db: Session, review_id: int, requesting_user_id: int) -> bool:
    """
    Marca una reseña como borrada (soft delete).
    Retorna True si se marcó como borrada, False si no se encontró o no se tenía permiso.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Intento de borrado de reseña no encontrada ID: {review_id}")
        return False # Reseña no encontrada

    # --- Verificación de Permiso ---
    if db_review.user_id != requesting_user_id:
        logger.error(f"Intento no autorizado: Usuario {requesting_user_id} intentó borrar reseña {review_id} del usuario {db_review.user_id}")
        # En una API real, aquí lanzarías una excepción HTTP 403 Forbidden
        return False # No es el dueño

    if db_review.is_deleted:
        logger.info(f"Reseña {review_id} ya estaba marcada como borrada.")
        return True # Ya estaba borrada, operación "exitosa" en el sentido de que el estado deseado se cumple

    # Marcar como borrada y guardar
    try:
        db_review.is_deleted = True
        db.add(db_review) # Marcar el objeto como modificado para la sesión
        db.commit()
        logger.info(f"Reseña {review_id} marcada como borrada por usuario {requesting_user_id}.")
        return True
    except Exception as e:
        logger.exception(f"Error al hacer commit en soft_delete_review para review ID {review_id}: {e}")
        db.rollback() # Deshacer cambios si el commit falla
        return False


def get_all_reviews_admin(db: Session, skip: int = 0, limit: int = 100) -> list:
    """
    Obtiene todas las reseñas (incluyendo borradas lógicamente)
    con información del usuario y del libro.
    Ideal para vistas de administrador.
    Devuelve una lista de Rows/Tuples con (Review, User.email, Book.title).
    """
    return db.query(Review, User.email, Book.title).\
            join(User, Review.user_id == User.id).\
            join(Book, Review.book_id == Book.id).\
            order_by(desc(Review.created_at)).\
            offset(skip).\
            limit(limit).all() # Sin filtro por is_deleted
