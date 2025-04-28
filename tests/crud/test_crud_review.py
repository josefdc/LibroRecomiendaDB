# tests/crud/test_crud_review.py
import pytest
from sqlalchemy.exc import IntegrityError

# Adjust imports based on your project structure
from librorecomienda.crud import (
    create_review,
    get_reviews_for_book_with_user,
    get_review_by_id,
    soft_delete_review,
    get_all_reviews_admin,
    create_user, # Need to create users
)
from librorecomienda.schemas.review import ReviewCreate
from librorecomienda.schemas.user import UserCreate
from librorecomienda.models.user import User
from librorecomienda.models.book import Book
from librorecomienda.models.review import Review

# --- Helper Fixtures ---
@pytest.fixture
def crud_test_user(db_session):
    user = create_user(db_session, UserCreate(email="crud_review_user@example.com", password="password"))
    return user

@pytest.fixture
def crud_test_user_2(db_session):
    user = create_user(db_session, UserCreate(email="crud_review_user2@example.com", password="password"))
    return user

@pytest.fixture
def crud_test_book(db_session):
    book = Book(title="CRUD Review Test Book", author="Test Author", isbn="5556667778889")
    db_session.add(book)
    db_session.commit() # Commit here as it's setup for multiple tests
    db_session.refresh(book)
    return book
# --------------------------------------------------------------------------------

def test_create_review_crud(db_session, crud_test_user, crud_test_book):
    """Test the create_review CRUD function."""
    rating = 5
    comment = "Excellent book!"
    review_in = ReviewCreate(rating=rating, comment=comment)

    created_review = create_review(
        db=db_session,
        review=review_in,
        user_id=crud_test_user.id,
        book_id=crud_test_book.id
    )

    assert created_review is not None
    assert created_review.rating == rating
    assert created_review.comment == comment
    assert created_review.user_id == crud_test_user.id
    assert created_review.book_id == crud_test_book.id
    assert created_review.is_deleted is False

    # Verify in DB - Use db_session.get()
    db_review = db_session.get(Review, created_review.id)
    assert db_review is not None
    assert db_review.rating == rating

def test_create_review_crud_duplicate_constraint(db_session, crud_test_user, crud_test_book):
    """Test create_review raises IntegrityError on duplicate (user, book)."""
    review_in = ReviewCreate(rating=4, comment="First review")
    create_review(db=db_session, review=review_in, user_id=crud_test_user.id, book_id=crud_test_book.id)

    # Attempt second review
    review_in_dup = ReviewCreate(rating=2, comment="Second attempt")
    with pytest.raises(IntegrityError):
        try:
            create_review(db=db_session, review=review_in_dup, user_id=crud_test_user.id, book_id=crud_test_book.id)
        finally:
            db_session.rollback() # Explicitly rollback after the expected error

def test_get_reviews_for_book_with_user(db_session, crud_test_user, crud_test_user_2, crud_test_book):
    """Test get_reviews_for_book_with_user, including is_deleted filtering."""
    # Review 1 (active) - User 1
    review1 = create_review(db=db_session, review=ReviewCreate(rating=5, comment="User 1 Active"), user_id=crud_test_user.id, book_id=crud_test_book.id)
    # Review 2 (active) - User 2
    review2 = create_review(db_session, review=ReviewCreate(rating=4, comment="User 2 Active"), user_id=crud_test_user_2.id, book_id=crud_test_book.id)
    # Review 3 (soft deleted) - User 1, Book 2
    # Create a second book for the deleted review to avoid the unique constraint
    book2 = Book(title="Another Book for Deletion Test", isbn="9998887776665")
    db_session.add(book2)
    db_session.commit() # Commit the new book
    db_session.refresh(book2)
    review3 = create_review(db=db_session, review=ReviewCreate(rating=3, comment="User 1 Deleted"), user_id=crud_test_user.id, book_id=book2.id) # Use book2

    # Manually mark as deleted for test setup
    # Use db_session.get() instead of query().get()
    review3_db = db_session.get(Review, review3.id)
    if review3_db:
        review3_db.is_deleted = True
        db_session.commit()
    else:
        pytest.fail("Failed to retrieve review3 from DB for marking as deleted.")


    # Get reviews for the FIRST book
    reviews_for_book = get_reviews_for_book_with_user(db=db_session, book_id=crud_test_book.id)

    # Assertions for the FIRST book
    assert len(reviews_for_book) == 2 # Should return 2 active reviews (review1 and review2) for crud_test_book
    review_ids = {r.Review.id for r in reviews_for_book}
    user_emails = {r.email for r in reviews_for_book}

    assert review1.id in review_ids
    assert review2.id in review_ids
    assert review3.id not in review_ids # review3 is for book2

    assert crud_test_user.email in user_emails # From review1
    assert crud_test_user_2.email in user_emails # From review2

def test_get_review_by_id(db_session, crud_test_user, crud_test_book):
    """Test get_review_by_id."""
    review = create_review(db=db_session, review=ReviewCreate(rating=4), user_id=crud_test_user.id, book_id=crud_test_book.id)

    found_review = get_review_by_id(db=db_session, review_id=review.id)
    assert found_review is not None
    assert found_review.id == review.id

    not_found_review = get_review_by_id(db_session, review_id=99999)
    assert not_found_review is None

def test_soft_delete_review_owner(db_session, crud_test_user, crud_test_book):
    """Test soft_delete_review by the owner."""
    # Ensure the review exists before trying to delete
    review = create_review(db=db_session, review=ReviewCreate(rating=3), user_id=crud_test_user.id, book_id=crud_test_book.id)
    db_session.flush() # Ensure it gets an ID before potential commit/rollback
    assert review.is_deleted is False

    success = soft_delete_review(db=db_session, review_id=review.id, requesting_user_id=crud_test_user.id)
    assert success is True

    # Verify in DB
    db_session.expire(review) # Expire the object to force reload from DB
    # Use db_session.get() instead of query().get()
    db_review = db_session.get(Review, review.id)
    assert db_review is not None # Make sure it still exists
    assert db_review.is_deleted is True

def test_soft_delete_review_not_owner(db_session, crud_test_user, crud_test_user_2, crud_test_book):
    """Test soft_delete_review fails if not the owner."""
    # Ensure the review exists
    review = create_review(db=db_session, review=ReviewCreate(rating=3), user_id=crud_test_user.id, book_id=crud_test_book.id)
    db_session.flush() # Ensure it gets an ID
    assert review.is_deleted is False

    # Attempt delete by user 2
    success = soft_delete_review(db=db_session, review_id=review.id, requesting_user_id=crud_test_user_2.id)
    assert success is False

    # Verify in DB it wasn't deleted
    db_session.expire(review) # Expire the object to force reload from DB
    # Use db_session.get() instead of query().get()
    db_review = db_session.get(Review, review.id)
    assert db_review is not None
    assert db_review.is_deleted is False

def test_soft_delete_review_not_found(db_session, crud_test_user):
    """Test soft_delete_review for a non-existent review."""
    success = soft_delete_review(db=db_session, review_id=99999, requesting_user_id=crud_test_user.id)
    assert success is False

def test_get_all_reviews_admin(db_session, crud_test_user, crud_test_user_2, crud_test_book):
    """Test get_all_reviews_admin includes soft-deleted reviews."""
    # Review 1 (active) - User 1
    review1 = create_review(db=db_session, review=ReviewCreate(rating=5, comment="Admin Test 1"), user_id=crud_test_user.id, book_id=crud_test_book.id)
    # Review 2 (soft deleted) - User 2
    review2 = create_review(db_session, review=ReviewCreate(rating=3, comment="Admin Test 2 Deleted"), user_id=crud_test_user_2.id, book_id=crud_test_book.id)
    db_session.flush() # Ensure IDs are assigned before soft delete

    # Ensure review2 exists before trying to delete
    # Use db_session.get() instead of query().get()
    review2_db = db_session.get(Review, review2.id)
    assert review2_db is not None

    success_delete = soft_delete_review(db=db_session, review_id=review2.id, requesting_user_id=crud_test_user_2.id)
    assert success_delete is True # Ensure delete succeeded

    admin_reviews_result = get_all_reviews_admin(db=db_session)

    # Make the assertion more robust - check exact count if possible, or filter results
    found_active = False
    found_deleted = False
    for r, user_email, book_title in admin_reviews_result:
        if r.id == review1.id:
            found_active = True
            assert r.is_deleted is False
            assert user_email == crud_test_user.email
            assert book_title == crud_test_book.title
        elif r.id == review2.id:
            found_deleted = True
            assert r.is_deleted is True
            assert user_email == crud_test_user_2.email
            assert book_title == crud_test_book.title

    assert found_active, "Active review not found in admin list"
    assert found_deleted, "Deleted review not found in admin list"
