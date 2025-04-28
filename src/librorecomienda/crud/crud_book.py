"""
Operaciones CRUD para el modelo Book en la base de datos.
Incluye funciones para buscar libros por distintos criterios, obtener por ID o ISBN, etc.
Pensado para ser utilizado por la capa de servicios y herramientas del agente conversacional.
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import List, Optional

from ..models.book import Book

def search_books(
    db: Session,
    title: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 10
) -> List[Book]:
    """
    Busca libros en la base de datos según título, autor, género o un término general.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        title (Optional[str]): Filtra por título del libro (coincidencia parcial, sin distinción de mayúsculas).
        author (Optional[str]): Filtra por autor (coincidencia parcial, sin distinción de mayúsculas).
        genre (Optional[str]): Filtra por género (coincidencia parcial, sin distinción de mayúsculas).
        query (Optional[str]): Término general para buscar en título, autor o género.
        limit (int): Número máximo de resultados a devolver.

    Returns:
        List[Book]: Lista de objetos Book que cumplen los criterios.
    """
    stmt = select(Book)
    filters = []

    if query:
        # Búsqueda general en título, autor y género
        query_filter = or_(
            Book.title.ilike(f"%{query}%"),
            Book.author.ilike(f"%{query}%"),
            Book.genre.ilike(f"%{query}%")
        )
        filters.append(query_filter)
    else:
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
    Recupera un libro por su ID primario.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        book_id (int): ID del libro a recuperar.

    Returns:
        Optional[Book]: El objeto Book si se encuentra, None si no existe.
    """
    return db.get(Book, book_id)

def get_book_by_isbn(db: Session, isbn: str) -> Optional[Book]:
    """
    Recupera un libro por su ISBN.

    Args:
        db (Session): Sesión de base de datos SQLAlchemy.
        isbn (str): ISBN del libro a recuperar.

    Returns:
        Optional[Book]: El objeto Book si se encuentra, None si no existe.
    """
    stmt = select(Book).where(Book.isbn == isbn)
    result = db.execute(stmt)
    return result.scalars().first()
