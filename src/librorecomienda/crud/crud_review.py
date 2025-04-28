from sqlalchemy.orm import Session
from sqlalchemy import desc, func # Import func
import logging

from ..models.review import Review
from ..models.user import User
from ..models.book import Book # Import Book
from ..schemas.review import ReviewCreate

logger = logging.getLogger(__name__)

# --- NEW HELPER FUNCTION ---
def _update_book_average_rating(db: Session, book_id: int):
    """
    Calculates the average rating for a book based on non-deleted reviews
    and updates the book's average_rating field.
    """
    # Calculate the average rating using the database aggregate function
    # Filter only active (non-deleted) reviews for the specific book
    avg_rating_result = db.query(func.avg(Review.rating))\
                          .filter(Review.book_id == book_id, Review.is_deleted == False)\
                          .scalar() # Use scalar() to get a single value or None

    # Get the book object
    book = db.query(Book).filter(Book.id == book_id).first()

    if book:
        # Update the average_rating. If avg_rating_result is None (no reviews), set it to None
        book.average_rating = avg_rating_result if avg_rating_result is not None else None
        db.add(book) # Add the updated book instance to the session
        # No commit here, the caller handles it.
        # No flush needed here as the caller flushes before calling this.


def create_review(db: Session, review: ReviewCreate, user_id: int, book_id: int) -> Review:
    db_review = Review(
        **review.model_dump(),
        user_id=user_id,
        book_id=book_id,
        is_deleted=False # Explicitly set is_deleted to False
    )
    db.add(db_review)
    db.flush() # Ensure db_review gets an ID and is pending insertion

    # --- Update average rating within the SAME transaction ---
    _update_book_average_rating(db=db, book_id=book_id)

    try:
        db.commit() # Commit both review and rating update together
        db.refresh(db_review)
        logger.info(f"Review {db_review.id} created for book {book_id} by user {user_id}. Average rating updated.")
    except Exception as e:
        logger.exception(f"Error committing review creation/rating update for book {book_id}: {e}")
        db.rollback()
        raise # Re-raise the exception after rollback

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
    Marks a review as deleted (soft delete) and updates the book's average rating.
    Returns True if marked as deleted, False if not found or not authorized.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Attempted soft delete of non-existent review ID: {review_id}")
        return False # Review not found

    # --- Permission Check ---
    if db_review.user_id != requesting_user_id:
        logger.error(f"Unauthorized attempt: User {requesting_user_id} tried to delete review {review_id} owned by {db_review.user_id}")
        # In a real API, you might raise an HTTPException 403 Forbidden here
        return False # Not the owner

    if db_review.is_deleted:
        logger.info(f"Review {review_id} was already marked as deleted.")
        return True # Already deleted, operation "successful"

    book_id = db_review.book_id # Get book_id BEFORE marking as deleted

    # Mark as deleted
    db_review.is_deleted = True
    db.add(db_review)
    db.flush() # Ensure the change is pending

    # --- Update average rating within the SAME transaction ---
    _update_book_average_rating(db=db, book_id=book_id)

    try:
        db.commit() # Commit both flag change and rating update together
        logger.info(f"Review {review_id} marked as deleted by user {requesting_user_id}. Average rating for book {book_id} updated.")
        return True
    except Exception as e:
        logger.exception(f"Error committing soft delete/rating update for review ID {review_id}: {e}")
        db.rollback()
        return False # Indicate failure


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


# --- NEW ADMIN ACTIONS ---

def restore_review(db: Session, review_id: int) -> bool:
    """
    Restores a logically deleted review (sets is_deleted=False)
    and updates the book's average rating.
    Returns True if restored, False if not found or already active.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Attempted to restore non-existent review ID: {review_id}")
        return False # Review not found

    if not db_review.is_deleted:
        logger.info(f"Review {review_id} is already active. No action taken.")
        return False # Already active

    book_id = db_review.book_id # Get book_id for rating update

    # Mark as active (not deleted)
    db_review.is_deleted = False
    db.add(db_review)
    db.flush() # Ensure the change is pending

    # --- Update average rating within the SAME transaction ---
    _update_book_average_rating(db=db, book_id=book_id)

    try:
        db.commit() # Commit both flag change and rating update together
        logger.info(f"Review {review_id} restored. Average rating for book {book_id} updated.")
        return True
    except Exception as e:
        logger.exception(f"Error committing restore/rating update for review ID {review_id}: {e}")
        db.rollback()
        return False # Indicate failure


def permanently_delete_review(db: Session, review_id: int) -> bool:
    """
    Permanently deletes a review from the database
    and updates the book's average rating.
    Returns True if deleted, False if not found.
    """
    db_review = get_review_by_id(db, review_id)

    if not db_review:
        logger.warning(f"Attempted to permanently delete non-existent review ID: {review_id}")
        return False # Review not found

    book_id = db_review.book_id # Get book_id BEFORE deleting

    try:
        db.delete(db_review)
        db.flush() # Ensure the deletion is pending

        # --- Update average rating within the SAME transaction ---
        # Important: Call this *after* flush ensures the review is gone for the calculation
        _update_book_average_rating(db=db, book_id=book_id)

        db.commit() # Commit both deletion and rating update together
        logger.info(f"Review {review_id} permanently deleted. Average rating for book {book_id} updated.")
        return True
    except Exception as e:
        logger.exception(f"Error committing permanent delete/rating update for review ID {review_id}: {e}")
        db.rollback()
        return False # Indicate failure
