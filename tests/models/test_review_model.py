# tests/models/test_review_model.py
import pytest
from sqlalchemy.exc import IntegrityError
import datetime

# Adjust imports based on your project structure
from librorecomienda.models.user import User
from librorecomienda.models.book import Book
from librorecomienda.models.review import Review
from librorecomienda.core.security import get_password_hash

# Helper fixture to create a user (can be moved to conftest.py if used widely)
@pytest.fixture
def test_user(db_session):
    user = User(email="review_user@example.com", hashed_password=get_password_hash("password"))
    db_session.add(user)
    db_session.flush() # Flush to assign ID without committing
    db_session.refresh(user)
    return user

# Helper fixture to create a book (can be moved to conftest.py if used widely)
@pytest.fixture
def test_book(db_session):
    book = Book(title="Review Test Book", author="Test Author", isbn="1112223334445")
    db_session.add(book)
    db_session.flush() # Flush to assign ID without committing
    db_session.refresh(book)
    return book

def test_create_review(db_session, test_user, test_book):
    """Test creating a valid Review instance."""
    rating = 4
    comment = "This is a test review."

    review = Review(
        rating=rating,
        comment=comment,
        user_id=test_user.id,
        book_id=test_book.id
    )
    db_session.add(review)
    db_session.commit()

    # Query the review back
    retrieved_review = db_session.query(Review).filter(
        Review.user_id == test_user.id, Review.book_id == test_book.id
    ).first()

    assert retrieved_review is not None
    assert retrieved_review.rating == rating
    assert retrieved_review.comment == comment
    assert retrieved_review.user_id == test_user.id
    assert retrieved_review.book_id == test_book.id
    assert retrieved_review.is_deleted is False # Check default
    assert retrieved_review.id is not None
    assert retrieved_review.created_at is not None
    # assert retrieved_review.updated_at is not None # updated_at might be same as created_at initially

    # Test relationship access
    assert retrieved_review.user == test_user
    assert retrieved_review.book == test_book
    assert retrieved_review in test_user.reviews
    assert retrieved_review in test_book.reviews

def test_create_review_invalid_rating_high(db_session, test_user, test_book):
    """Test that creating a review with rating > 5 raises IntegrityError."""
    review = Review(rating=6, user_id=test_user.id, book_id=test_book.id)
    db_session.add(review)

    # Expect IntegrityError due to the CheckConstraint
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_create_review_invalid_rating_low(db_session, test_user, test_book):
    """Test that creating a review with rating < 1 raises IntegrityError."""
    review = Review(rating=0, user_id=test_user.id, book_id=test_book.id)
    db_session.add(review)

    # Expect IntegrityError due to the CheckConstraint
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_create_review_duplicate(db_session, test_user, test_book):
    """Test that creating a duplicate review (same user, same book) raises IntegrityError."""
    # Create the first review
    review1 = Review(rating=3, user_id=test_user.id, book_id=test_book.id)
    db_session.add(review1)
    db_session.commit()

    # Attempt to create the second review
    review2 = Review(rating=5, user_id=test_user.id, book_id=test_book.id)
    db_session.add(review2)

    # Expect IntegrityError due to the UniqueConstraint('user_id', 'book_id')
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_review_repr(db_session, test_user, test_book):
    """Test the __repr__ method of the Review model."""
    review = Review(rating=5, user_id=test_user.id, book_id=test_book.id, is_deleted=False)
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)

    expected_repr = f"<Review(id={review.id}, book_id={test_book.id}, user_id={test_user.id}, rating=5)>"
    # Note: The __repr__ in the model has a trailing space if not deleted, adjust if needed
    assert repr(review) == expected_repr

    # Test repr when deleted
    review.is_deleted = True
    db_session.commit()
    db_session.refresh(review)
    # Adjust expected string to match the actual __repr__ output
    expected_repr_deleted = f"<Review(id={review.id}, book_id={test_book.id}, user_id={test_user.id}, rating=5) [DELETED]>"
    assert repr(review) == expected_repr_deleted

# Add tests for nullable fields (user_id, book_id, rating) if needed
# (They are currently set to nullable=False in the model refinement)
