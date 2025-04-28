"""
Herramientas (tools) para el agente conversacional de recomendaciones de libros.
Incluye funciones para buscar libros y obtener detalles de libros desde la base de datos,
expuestas como herramientas para LangChain/LangGraph.
"""

from langchain_core.tools import tool
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

try:
    from librorecomienda.db.session import SessionLocal
    from librorecomienda.crud.crud_book import (
        search_books as search_books_crud,
        get_book_by_id as get_book_crud
    )
    CRUD_AVAILABLE = True
except ImportError as e:
    logging.error(
        f"Error importing CRUD/DB modules in tools.py: {e}. "
        f"Ensure 'librorecomienda.crud.crud_book.py' exists and is importable. "
        f"Tool functions will return errors until this is fixed."
    )
    CRUD_AVAILABLE = False

    def search_books_crud(*args, **kwargs):
        raise NotImplementedError("CRUD function 'search_books_crud' not available due to import error.")

    def get_book_crud(*args, **kwargs):
        raise NotImplementedError("CRUD function 'get_book_by_id' not available due to import error.")

    def SessionLocal():
        raise NotImplementedError("DB Session 'SessionLocal' not available due to import error.")

logger = logging.getLogger(__name__)

@tool
def search_books(
    query: Optional[str] = None,
    genre: Optional[str] = None,
    author: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Busca libros en la base de datos según un query (palabras clave en título o descripción),
    género o autor. Devuelve una lista de libros que coinciden con los criterios, incluyendo id,
    título, autor, género y average_rating. Se debe proporcionar al menos un parámetro.
    Devuelve hasta 5 resultados.

    Args:
        query (Optional[str]): Palabras clave para buscar en título o descripción.
        genre (Optional[str]): Género del libro.
        author (Optional[str]): Autor del libro.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con información básica de los libros encontrados.
    """
    if not CRUD_AVAILABLE:
        return [{"error": "Database search functionality is unavailable due to configuration issues."}]
    if not query and not genre and not author:
        return [{"error": "Please provide at least one search parameter (query, genre, or author)."}]

    db: Optional[Session] = None
    results: List[Dict[str, Any]] = []
    try:
        db = SessionLocal()
        logger.info(f"Tool 'search_books' called with query='{query}', genre='{genre}', author='{author}'")
        books = search_books_crud(db=db, query=query, genre=genre, author=author, limit=5)

        if not books:
            logger.info("Tool 'search_books' found no results.")
            return []

        for book in books:
            results.append({
                "id": getattr(book, 'id', None),
                "title": getattr(book, 'title', 'N/A'),
                "author": getattr(book, 'author', 'N/A'),
                "genre": getattr(book, 'genre', 'N/A'),
                "average_rating": round(getattr(book, 'average_rating', 0.0), 1)
                if getattr(book, 'average_rating', None) is not None else None
            })
        logger.info(f"Tool 'search_books' found {len(results)} results.")

    except NotImplementedError as nie:
        logger.error(f"Tool 'search_books' failed: {nie}")
        return [{"error": "Database search functionality is unavailable due to configuration issues."}]
    except Exception as e:
        logger.error(f"Error in search_books tool: {e}", exc_info=True)
        return [{"error": f"Database search failed: {str(e)}"}]
    finally:
        if db:
            try:
                db.close()
            except Exception as db_close_err:
                logger.error(f"Error closing DB session in search_books: {db_close_err}", exc_info=True)
    return results

@tool
def get_book_details(book_id: int) -> Dict[str, Any]:
    """
    Recupera información detallada de un libro dado su ID único.
    Devuelve un diccionario con detalles como id, título, autor, género,
    descripción, average_rating, URL de portada e ISBN.

    Args:
        book_id (int): ID único del libro.

    Returns:
        Dict[str, Any]: Diccionario con los detalles del libro o un mensaje de error.
    """
    if not CRUD_AVAILABLE:
        return {"error": "Database detail functionality is unavailable due to configuration issues."}
    if not isinstance(book_id, int) or book_id <= 0:
        logger.warning(f"Tool 'get_book_details' called with invalid book_id: {book_id}")
        return {"error": "Invalid book_id provided. It must be a positive integer."}

    db: Optional[Session] = None
    try:
        db = SessionLocal()
        logger.info(f"Tool 'get_book_details' called for book_id={book_id}")
        book = get_book_crud(db=db, book_id=book_id)

        if not book:
            logger.warning(f"Book with id {book_id} not found.")
            return {"not_found": f"Book with id {book_id} not found."}

        result: Dict[str, Any] = {
            "id": getattr(book, 'id', None),
            "title": getattr(book, 'title', 'N/A'),
            "author": getattr(book, 'author', 'N/A'),
            "genre": getattr(book, 'genre', 'N/A'),
            "description": getattr(book, 'description', 'N/A'),
            "average_rating": round(getattr(book, 'average_rating', 0.0), 1)
            if getattr(book, 'average_rating', None) is not None else None,
            "cover_image_url": getattr(book, 'cover_image_url', None),
            "isbn": getattr(book, 'isbn', None)
        }
        logger.info(f"Tool 'get_book_details' found details for book_id={book_id}.")
        return result

    except NotImplementedError as nie:
        logger.error(f"Tool 'get_book_details' failed: {nie}")
        return {"error": "Database detail functionality is unavailable due to configuration issues."}
    except Exception as e:
        logger.error(f"Error in get_book_details tool for book_id={book_id}: {e}", exc_info=True)
        return {"error": f"Failed to get details for book {book_id}: {str(e)}"}
    finally:
        if db:
            try:
                db.close()
            except Exception as db_close_err:
                logger.error(f"Error closing DB session in get_book_details: {db_close_err}", exc_info=True)

# Lista de herramientas exportadas para su uso en el grafo conversacional
agent_tools: List[Any] = [search_books, get_book_details]
