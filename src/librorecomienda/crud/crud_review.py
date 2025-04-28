"""
Operaciones CRUD para reseñas (Review) en la base de datos del sistema LibroRecomienda.
Incluye creación, borrado lógico y permanente, restauración, consulta de reseñas y actualización
del rating promedio del libro asociado. Pensado para uso por la API y el agente conversacional.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import logging
from typing import List, Optional, Tuple, Any

from ..models.review import Review
from ..models.user import User
from ..models.book import Book
from ..schemas.review import ReviewCreate

logger = logging.getLogger(__name__)

def _update_book_average_rating(db: Session, book_id: int) -> None:
    """
    Calcula el rating promedio de un libro basado en reseñas no borradas
    y actualiza el campo average_rating del libro.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        book_id (int): ID del libro a actualizar.
    """
    avg_rating_result: Optional[float] = db.query(func.avg(Review.rating))\
        .filter(Review.book_id == book_id, Review.is_deleted == False)\
        .scalar()

    book: Optional[Book] = db.query(Book).filter(Book.id == book_id).first()

    if book:
        book.average_rating = avg_rating_result if avg_rating_result is not None else None
        db.add(book)
        # No commit aquí, lo maneja el llamador.

def create_review(db: Session, review: ReviewCreate, user_id: int, book_id: int) -> Review:
    """
    Crea una nueva reseña para un libro y actualiza el rating promedio del libro.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        review (ReviewCreate): Datos de la reseña.
        user_id (int): ID del usuario que crea la reseña.
        book_id (int): ID del libro reseñado.

    Returns:
        Review: La reseña creada.

    Raises:
        Exception: Si ocurre un error al guardar en la base de datos.
    """
    db_review = Review(
        **review.model_dump(),
        user_id=user_id,
        book_id=book_id,
        is_deleted=False
    )
    db.add(db_review)
    db.flush()

    _update_book_average_rating(db=db, book_id=book_id)

    try:
        db.commit()
        db.refresh(db_review)
        logger.info(f"Review {db_review.id} created for book {book_id} by user {user_id}. Average rating updated.")
    except Exception as e:
        logger.exception(f"Error committing review creation/rating update for book {book_id}: {e}")
        db.rollback()
        raise

    return db_review

def get_reviews_for_book(db: Session, book_id: int, limit: int = 20) -> List[Review]:
    """
    Obtiene las últimas reseñas NO BORRADAS para un libro.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        book_id (int): ID del libro.
        limit (int): Número máximo de reseñas a devolver.

    Returns:
        List[Review]: Lista de reseñas.
    """
    return db.query(Review)\
        .filter(Review.book_id == book_id, Review.is_deleted == False)\
        .order_by(desc(Review.created_at))\
        .limit(limit).all()

def get_reviews_for_book_with_user(db: Session, book_id: int, limit: int = 20) -> List[Tuple[Review, str]]:
    """
    Obtiene reseñas NO BORRADAS y el email del usuario que la hizo.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        book_id (int): ID del libro.
        limit (int): Número máximo de reseñas a devolver.

    Returns:
        List[Tuple[Review, str]]: Lista de tuplas (Review, User.email).
    """
    return db.query(Review, User.email)\
        .join(User, Review.user_id == User.id)\
        .filter(Review.book_id == book_id, Review.is_deleted == False)\
        .order_by(desc(Review.created_at))\
        .limit(limit).all()

def get_review_by_id(db: Session, review_id: int) -> Optional[Review]:
    """
    Obtiene una reseña específica por su ID (incluyendo borradas lógicamente).

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        review_id (int): ID de la reseña.

    Returns:
        Optional[Review]: La reseña si existe, None si no.
    """
    return db.get(Review, review_id)

def soft_delete_review(db: Session, review_id: int, requesting_user_id: int) -> bool:
    """
    Marca una reseña como borrada (soft delete) y actualiza el rating promedio del libro.
    Solo el usuario propietario puede borrar su reseña.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        review_id (int): ID de la reseña a borrar.
        requesting_user_id (int): ID del usuario que solicita el borrado.

    Returns:
        bool: True si se marcó como borrada, False si no se encontró o no autorizado.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Attempted soft delete of non-existent review ID: {review_id}")
        return False

    if db_review.user_id != requesting_user_id:
        logger.error(f"Unauthorized attempt: User {requesting_user_id} tried to delete review {review_id} owned by {db_review.user_id}")
        return False

    if db_review.is_deleted:
        logger.info(f"Review {review_id} was already marked as deleted.")
        return True

    book_id = db_review.book_id

    db_review.is_deleted = True
    db.add(db_review)
    db.flush()

    _update_book_average_rating(db=db, book_id=book_id)

    try:
        db.commit()
        logger.info(f"Review {review_id} marked as deleted by user {requesting_user_id}. Average rating for book {book_id} updated.")
        return True
    except Exception as e:
        logger.exception(f"Error committing soft delete/rating update for review ID {review_id}: {e}")
        db.rollback()
        return False

def get_all_reviews_admin(db: Session, skip: int = 0, limit: int = 100) -> List[Any]:
    """
    Obtiene todas las reseñas (incluyendo borradas lógicamente) con información del usuario y del libro.
    Ideal para vistas de administrador.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        skip (int): Número de registros a omitir (paginación).
        limit (int): Número máximo de registros a devolver.

    Returns:
        List[Any]: Lista de Rows/Tuplas con (Review, User.email, Book.title).
    """
    return db.query(Review, User.email, Book.title)\
        .join(User, Review.user_id == User.id)\
        .join(Book, Review.book_id == Book.id)\
        .order_by(desc(Review.created_at))\
        .offset(skip)\
        .limit(limit).all()

def restore_review(db: Session, review_id: int) -> bool:
    """
    Restaura una reseña borrada lógicamente (is_deleted=False) y actualiza el rating promedio del libro.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        review_id (int): ID de la reseña a restaurar.

    Returns:
        bool: True si se restauró, False si no se encontró o ya estaba activa.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Attempted to restore non-existent review ID: {review_id}")
        return False

    if not db_review.is_deleted:
        logger.info(f"Review {review_id} is already active. No action taken.")
        return False

    book_id = db_review.book_id

    db_review.is_deleted = False
    db.add(db_review)
    db.flush()

    _update_book_average_rating(db=db, book_id=book_id)

    try:
        db.commit()
        logger.info(f"Review {review_id} restored. Average rating for book {book_id} updated.")
        return True
    except Exception as e:
        logger.exception(f"Error committing restore/rating update for review ID {review_id}: {e}")
        db.rollback()
        return False

def permanently_delete_review(db: Session, review_id: int) -> bool:
    """
    Elimina permanentemente una reseña de la base de datos y actualiza el rating promedio del libro.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        review_id (int): ID de la reseña a eliminar.

    Returns:
        bool: True si se eliminó, False si no se encontró.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Attempted to permanently delete non-existent review ID: {review_id}")
        return False

    book_id = db_review.book_id

    try:
        db.delete(db_review)
        db.flush()
        _update_book_average_rating(db=db, book_id=book_id)
        db.commit()
        logger.info(f"Review {review_id} permanently deleted. Average rating for book {book_id} updated.")
        return True
    except Exception as e:
        logger.exception(f"Error committing permanent delete/rating update for review ID {review_id}: {e}")
        db.rollback()
        return False
