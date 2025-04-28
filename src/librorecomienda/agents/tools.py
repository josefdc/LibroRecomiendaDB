# src/librorecomienda/agents/tools.py

from langchain_core.tools import tool
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

# Importa la sesión de BD y las funciones CRUD necesarias
# Asegúrate de que las rutas sean correctas y que crud_book.py exista
try:
    from librorecomienda.db.session import SessionLocal
    # Asume que tienes funciones CRUD con nombres similares a estos:
    # Ajusta los nombres si los tuyos son diferentes.
    from librorecomienda.crud.crud_book import (
         search_books as search_books_crud, # Renombra para evitar colisión
         # CORRECCIÓN: Importar la función correcta
         get_book_by_id as get_book_crud
    )
    # Importa el modelo si necesitas devolver objetos complejos o para type hints
    # from librorecomienda.models.book import Book
    CRUD_AVAILABLE = True
except ImportError as e:
    # Manejo de error si las importaciones fallan
    logging.error(f"Error importing CRUD/DB modules in tools.py: {e}. "
                  f"Ensure 'librorecomienda.crud.crud_book.py' exists and is importable. "
                  f"Tool functions will return errors until this is fixed.")
    CRUD_AVAILABLE = False
    # Define stubs para que el archivo se cargue, pero las herramientas fallarán
    def search_books_crud(*args, **kwargs):
        raise NotImplementedError("CRUD function 'search_books_crud' not available due to import error.")
    def get_book_crud(*args, **kwargs):
        raise NotImplementedError("CRUD function 'get_book_by_id' not available due to import error.")
    def SessionLocal():
        raise NotImplementedError("DB Session 'SessionLocal' not available due to import error.")


logger = logging.getLogger(__name__)

# --- Definición de Herramientas ---

@tool
def search_books(query: Optional[str] = None, genre: Optional[str] = None, author: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Searches the book database based on an optional query (keywords in title or description),
    genre, or author. Returns a list of books matching the criteria, including id, title, author, genre, and average_rating.
    Provide at least one parameter (query, genre, or author). Returns up to 5 results.
    """
    if not CRUD_AVAILABLE:
        return [{"error": "Database search functionality is unavailable due to configuration issues."}]
    if not query and not genre and not author:
        return [{"error": "Please provide at least one search parameter (query, genre, or author)."}]

    db: Optional[Session] = None
    results = []
    try:
        db = SessionLocal()
        logger.info(f"Tool 'search_books' called with query='{query}', genre='{genre}', author='{author}'")
        # Llama a tu función CRUD existente (ajusta nombre y parámetros si es necesario)
        books = search_books_crud(db=db, query=query, genre=genre, author=author, limit=5) # Limitar resultados

        # Formatear resultados para el LLM (lista de diccionarios simples)
        if not books:
             logger.info("Tool 'search_books' found no results.")
             return [] # Return empty list if no books found

        for book in books:
            # Ensure necessary attributes exist before accessing
            results.append({
                "id": getattr(book, 'id', None),
                "title": getattr(book, 'title', 'N/A'),
                "author": getattr(book, 'author', 'N/A'),
                "genre": getattr(book, 'genre', 'N/A'),
                # Handle potential missing average_rating
                "average_rating": round(getattr(book, 'average_rating', 0.0), 1) if getattr(book, 'average_rating', None) is not None else None
            })
        logger.info(f"Tool 'search_books' found {len(results)} results.")

    except NotImplementedError as nie:
        logger.error(f"Tool 'search_books' failed: {nie}")
        return [{"error": "Database search functionality is unavailable due to configuration issues."}]
    except Exception as e:
        logger.error(f"Error in search_books tool: {e}", exc_info=True)
        # Es importante devolver algo, incluso en caso de error,
        # o una cadena indicando el error, para que el LLM sepa que falló.
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
    Retrieves detailed information for a specific book given its unique ID.
    Returns a dictionary with book details including id, title, author, genre,
    description, average rating, cover image URL, and ISBN.
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
        # La función importada ahora es get_book_by_id, pero la llamamos get_book_crud gracias al alias
        book = get_book_crud(db=db, book_id=book_id)

        if not book:
            logger.warning(f"Book with id {book_id} not found.")
            # Devolver una clave específica para 'no encontrado' ayuda al LLM a distinguirlo de un error
            return {"not_found": f"Book with id {book_id} not found."}

        # Formatear resultado como diccionario simple, checking attributes
        result = {
            "id": getattr(book, 'id', None),
            "title": getattr(book, 'title', 'N/A'),
            "author": getattr(book, 'author', 'N/A'),
            "genre": getattr(book, 'genre', 'N/A'),
            "description": getattr(book, 'description', 'N/A'),
            "average_rating": round(getattr(book, 'average_rating', 0.0), 1) if getattr(book, 'average_rating', None) is not None else None,
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

# --- Lista de Herramientas para Exportar ---
# Facilita la importación en graph.py
agent_tools = [search_books, get_book_details]
