# scripts/populate_db.py (Ejemplo muy básico)
import asyncio
import logging
from sqlalchemy.orm import Session
# Asegúrate que sys.path esté correcto si ejecutas desde fuera de uv run
from librorecomienda.db.session import SessionLocal, engine, Base
from librorecomienda.models.book import Book
from librorecomienda.clients.google_books import search_books_google_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crea las tablas si no existen (alternativa a alembic para scripts simples, pero Alembic es mejor)
# Base.metadata.create_all(bind=engine)

async def populate_books(db: Session, search_query: str, count: int):
    logger.info(f"Buscando '{search_query}' en Google Books API...")
    google_books_data = await search_books_google_api(query=search_query, max_results=count)

    if not google_books_data:
        logger.warning(f"No se obtuvieron datos de Google Books para '{search_query}'.")
        return 0

    added_count = 0
    for item in google_books_data:
        volume_info = item.get("volumeInfo", {})
        title = volume_info.get("title")
        authors = volume_info.get("authors", [])
        author_str = ", ".join(authors) if authors else None
        description = volume_info.get("description")
        genre = volume_info.get("categories", [None])[0] # Toma la primera categoría como género
        # Extract image URL
        image_links = volume_info.get("imageLinks", {})
        cover_url = image_links.get("thumbnail") # O 'smallThumbnail'

        if not title:
            continue # Saltar si no hay título

        # Evitar duplicados (estrategia simple por título y autor)
        exists = db.query(Book).filter(Book.title == title, Book.author == author_str).first()
        if exists:
            logger.info(f"Libro ya existe: '{title}' por {author_str}. Saltando.")
            continue

        # Crear instancia del modelo Book, including the cover URL
        new_book = Book(
            title=title[:255], # Trunca si es necesario
            author=author_str[:255] if author_str else None,
            genre=genre[:100] if genre else None,
            description=description,
            cover_image_url=cover_url[:512] if cover_url else None, # Add the cover URL
            # average_rating=volume_info.get("averageRating", 0.0) # Podrías usar el rating de Google
        )
        db.add(new_book)
        added_count += 1
        logger.info(f"Añadiendo libro: '{title}'")

    try:
        db.commit()
        logger.info(f"Commit exitoso. {added_count} libros nuevos añadidos para la búsqueda '{search_query}'.")
    except Exception as e:
        db.rollback()
        logger.exception(f"Error al hacer commit a la base de datos: {e}")
        return 0
    return added_count

async def main():
    db = SessionLocal()
    try:
        # Lista de búsquedas para poblar
        queries = [
            "python programming",
            "machine learning",
            "ciencia ficcion",
            "gabriel garcia marquez",
            "bases de datos",
            "langchain",
            # Añade más temas o autores relevantes
        ]
        total_added = 0
        for query in queries:
            count = await populate_books(db, query, 15) # Busca 15 libros por tema
            total_added += count
            await asyncio.sleep(1) # Pequeña pausa para no saturar la API
        logger.info(f"Población de base de datos completada. Total añadidos: {total_added}")
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Iniciando script para poblar la base de datos desde Google Books API...")
    asyncio.run(main())
    logger.info("Script finalizado.")