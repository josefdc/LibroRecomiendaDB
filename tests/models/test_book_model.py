# tests/models/test_book_model.py
import pytest
from sqlalchemy.exc import IntegrityError

# Adjust imports based on your project structure
from librorecomienda.models.book import Book

def test_create_book(db_session):
    """Test creating a valid Book instance."""
    title = "The Hitchhiker's Guide to the Galaxy"
    author = "Douglas Adams"
    isbn = "9780345391803"

    book = Book(title=title, author=author, isbn=isbn)
    db_session.add(book)
    db_session.commit()

    # Query the book back
    retrieved_book = db_session.query(Book).filter(Book.isbn == isbn).first()

    assert retrieved_book is not None
    assert retrieved_book.title == title
    assert retrieved_book.author == author
    assert retrieved_book.isbn == isbn
    assert retrieved_book.id is not None
    assert retrieved_book.average_rating is None # Check default
    # Add checks for other fields if needed (genre, description, cover_image_url)

def test_create_book_no_title(db_session):
    """Test that creating a book without a title raises IntegrityError."""
    # Attempt to create a book with title=None
    book = Book(author="Some Author", isbn="1234567890123")
    db_session.add(book)

    # Expect an IntegrityError due to the nullable=False constraint on title
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_create_book_duplicate_isbn(db_session):
    """Test that creating a book with a duplicate ISBN raises IntegrityError."""
    title = "Duplicate ISBN Test"
    isbn = "9999999999999"

    # Create the first book
    book1 = Book(title=title + " 1", isbn=isbn)
    db_session.add(book1)
    db_session.commit()

    # Attempt to create the second book with the same ISBN
    book2 = Book(title=title + " 2", isbn=isbn)
    db_session.add(book2)

    # Expect an IntegrityError due to the unique constraint on isbn
    # Note: SQLite might not enforce unique constraints on NULL values by default.
    # This test assumes ISBN is not NULL.
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_book_repr(db_session):
    """Test the __repr__ method of the Book model."""
    title = "Representation Test Book Title That Is Quite Long"
    isbn = "1122334455667"

    book = Book(title=title, isbn=isbn)
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    # Check against the format defined in the Book model's __repr__
    expected_repr = f"<Book(id={book.id}, title='{title[:30]}...', isbn='{isbn}'>"
    assert repr(book) == expected_repr

# Add more tests here for:
# - Relationships (e.g., book.reviews) once Review model/tests exist
# - Other constraints or default values
