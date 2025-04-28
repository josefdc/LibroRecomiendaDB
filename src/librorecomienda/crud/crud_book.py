# src/librorecomienda/crud/crud_book.py
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import List, Optional

from ..models.book import Book  # Assuming your model is in models/book.py

def search_books(
    db: Session,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    query: Optional[str] = None, # General query term
    limit: int = 10
) -> List[Book]:
    """
    Searches for books in the database based on title, author, genre, or a general query term.

    Args:
        db: The database session.
        title: Filter by book title (case-insensitive partial match).
        author: Filter by author name (case-insensitive partial match).
        genre: Filter by genre (case-insensitive partial match).
        query: A general search term to match against title, author, or genre.
        limit: The maximum number of results to return.

    Returns:
        A list of matching Book objects.
    """
    stmt = select(Book)
    filters = []

    if query:
        # General query searches across title, author, and genre
        query_filter = or_(
            Book.title.ilike(f"%{query}%"),
            Book.author.ilike(f"%{query}%"),
            Book.genre.ilike(f"%{query}%")
        )
        filters.append(query_filter)
    else:
        # Specific field filters
        if title:
            filters.append(Book.title.ilike(f"%{title}%"))
        if author:
            filters.append(Book.author.ilike(f"%{author}%"))
        if genre:
            filters.append(Book.genre.ilike(f"%{genre}%"))

    if filters:
        stmt = stmt.where(*filters)

    stmt = stmt.limit(limit)
    result = db.execute(stmt)
    return result.scalars().all()

def get_book_by_id(db: Session, book_id: int) -> Optional[Book]:
    """
    Retrieves a single book by its primary key ID.

    Args:
        db: The database session.
        book_id: The ID of the book to retrieve.

    Returns:
        The Book object if found, otherwise None.
    """
    return db.get(Book, book_id)

def get_book_by_isbn(db: Session, isbn: str) -> Optional[Book]:
    """
    Retrieves a single book by its ISBN.

    Args:
        db: The database session.
        isbn: The ISBN of the book to retrieve.

    Returns:
        The Book object if found, otherwise None.
    """
    stmt = select(Book).where(Book.isbn == isbn)
    result = db.execute(stmt)
    return result.scalars().first()

# You might add more functions as needed, e.g., create_book, update_book, etc.
# def create_book(db: Session, book_data: schemas.BookCreate) -> Book:
#     ...
