# scripts/populate_db.py
import logging
import sys
import os
import asyncio # Import asyncio

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Añadir 'src' al PYTHONPATH (si es necesario) ---
# ... (código existente para añadir src al path) ...

# --- Importaciones del Proyecto ---
try:
    from sqlalchemy.orm import Session
    from librorecomienda.db.session import SessionLocal
    from librorecomienda.models.book import Book
    # --- Cambiar esta línea ---
    from librorecomienda.clients.google_books import search_books_google_api
    # -------------------------
    from librorecomienda.core.config import settings
    MODELS_LOADED = True
    logger.info("Módulos del proyecto importados correctamente.")
except ImportError as e:
    logger.error(f"Error importando módulos: {e}.")
    logger.error("Asegúrate de haber ejecutado 'uv pip install -e .' y 'uv pip install httpx'")
    MODELS_LOADED = False
    sys.exit(1)

# --- Constantes ---
SEARCH_QUERIES = [
    "python programming",
    "data science",
    "machine learning",
    "artificial intelligence",
    "software engineering best practices",
    "classic literature",
    "science fiction",
    "fantasy novels",
    "historical fiction",
    "biography"
]
MAX_RESULTS_PER_QUERY = 10 # Número de libros a intentar obtener por cada búsqueda

# --- Función para Poblar Libros ---
def populate_books(db: Session):
    if not MODELS_LOADED:
        logger.error("No se pudieron cargar los módulos. Abortando población.")
        return

    logger.info("--- Iniciando Población de Libros --- ")
    # No necesitamos instanciar un cliente
    total_books_added = 0

    for query in SEARCH_QUERIES:
        logger.info(f"Buscando libros para: '{query}'...")
        try:
            # --- Llamar a la función async usando asyncio.run() ---
            google_books_data = asyncio.run(
                search_books_google_api(query, max_results=MAX_RESULTS_PER_QUERY)
            )
            # -----------------------------------------------------

            if google_books_data is None: # La función devuelve None en caso de error
                logger.error(f"Error al buscar libros para '{query}'. Ver logs anteriores.")
                continue
            if not google_books_data:
                logger.warning(f"No se encontraron resultados para '{query}'.")
                continue

            logger.info(f"Se encontraron {len(google_books_data)} resultados para '{query}'. Procesando...")

            for item in google_books_data:
                volume_info = item.get('volumeInfo', {})

                title = volume_info.get('title')
                authors = volume_info.get('authors', [])
                author_str = ", ".join(authors) if authors else None
                description = volume_info.get('description')
                genre = volume_info.get('categories', [None])[0] # Tomar la primera categoría como género
                image_links = volume_info.get('imageLinks', {})
                cover_url = image_links.get('thumbnail') or image_links.get('smallThumbnail')

                # --- Extraer ISBN --- 
                industry_identifiers = volume_info.get('industryIdentifiers', [])
                isbn_13 = None
                isbn_10 = None
                for identifier in industry_identifiers:
                    id_type = identifier.get('type')
                    id_value = identifier.get('identifier')
                    if id_type == 'ISBN_13':
                        isbn_13 = id_value
                    elif id_type == 'ISBN_10':
                        isbn_10 = id_value

                # Priorizamos ISBN_13 si existe, si no, usamos ISBN_10
                book_isbn = isbn_13 if isbn_13 else isbn_10
                # Truncar si excede el límite de la BD (String(20))
                book_isbn = book_isbn[:20] if book_isbn else None
                # --------------------

                if not title:
                    logger.warning("Libro sin título encontrado, saltando.")
                    continue

                # Evitar duplicados
                exists = db.query(Book).filter(Book.title == title, Book.author == author_str).first()
                if exists:
                    logger.info(f"Libro ya existe (título/autor): '{title}'. Saltando.")
                    continue
                if book_isbn:
                     exists_isbn = db.query(Book).filter(Book.isbn == book_isbn).first()
                     if exists_isbn:
                           logger.info(f"Libro ya existe (ISBN): '{title}' [{book_isbn}]. Saltando.")
                           continue

                new_book = Book(
                    title=title[:255],
                    author=author_str[:255] if author_str else None,
                    genre=genre[:100] if genre else None,
                    description=description,
                    cover_image_url=cover_url[:512] if cover_url else None,
                    isbn=book_isbn
                )
                db.add(new_book)
                total_books_added += 1
                logger.info(f"  Añadido: '{new_book.title}' (ISBN: {new_book.isbn or 'N/A'})")

            # Hacer commit por lotes
            try:
                db.commit()
                logger.info(f"Commit realizado para libros de '{query}'.")
            except Exception as commit_exc:
                logger.error(f"Error haciendo commit para '{query}': {commit_exc}")
                db.rollback()

        except Exception as e:
            logger.exception(f"Error procesando la query '{query}': {e}")
            db.rollback()

    logger.info(f"--- Población de Libros Finalizada: {total_books_added} libros añadidos en total. ---")

# --- Punto de Entrada --- 
if __name__ == "__main__":
    db_session: Session | None = None
    try:
        logger.info("Abriendo sesión de base de datos para poblar...")
        db_session = SessionLocal()
        populate_books(db_session)
    except Exception as main_exc:
        logger.exception(f"Error CRÍTICO durante la población: {main_exc}")
    finally:
        if db_session:
            logger.info("Cerrando sesión de base de datos.")
            db_session.close()