from sqlalchemy.orm import Session
from sqlalchemy import desc
from librorecomienda.models.review import Review
from librorecomienda.models.user import User
from librorecomienda.schemas.review import ReviewCreate

def create_review(db: Session, review: ReviewCreate, user_id: int, book_id: int) -> Review:
    """Crea una nueva reseña para un usuario y libro."""
    db_review = Review(
        rating=review.rating,
        comment=review.comment,
        user_id=user_id,
        book_id=book_id
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

def get_reviews_for_book(db: Session, book_id: int, limit: int = 20) -> list[Review]:
    """Obtiene las últimas 'limit' reseñas para un libro específico."""
    return db.query(Review).\
            filter(Review.book_id == book_id).\
            order_by(desc(Review.created_at)).\
            limit(limit).all()

def get_reviews_for_book_with_user(db: Session, book_id: int, limit: int = 20) -> list[tuple[Review, str | None]]:
    """Obtiene reseñas y el email del usuario que la hizo."""
    return db.query(Review, User.email).\
            join(User, Review.user_id == User.id).\
            filter(Review.book_id == book_id).\
            order_by(desc(Review.created_at)).\
            limit(limit).all()
