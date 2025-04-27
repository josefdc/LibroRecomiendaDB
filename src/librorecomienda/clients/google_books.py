# src/librorecomienda/clients/google_books.py (Ejemplo básico)
import httpx
from librorecomienda.core.config import settings
import logging # Es bueno añadir logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

async def search_books_google_api(query: str, max_results: int = 10):
    """Busca libros usando la API de Google Books."""
    if settings.GOOGLE_BOOKS_API_KEY == "NO_GOOGLE_KEY_SET":
        logger.error("Google Books API Key no está configurada.")
        return None

    params = {
        "q": query,
        "key": settings.GOOGLE_BOOKS_API_KEY,
        "maxResults": max_results,
        "printType": "books" # Para obtener solo libros
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_BOOKS_API_URL, params=params)
            response.raise_for_status() # Lanza excepción para errores HTTP (4xx, 5xx)
            data = response.json()
            logger.info(f"Búsqueda en Google Books para '{query}' exitosa. {len(data.get('items', []))} resultados obtenidos.")
            return data.get("items", []) # Devuelve la lista de libros (items)
    except httpx.RequestError as exc:
        logger.error(f"Error en la petición a Google Books API: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        logger.error(f"Error HTTP en Google Books API: {exc.response.status_code} - {exc.response.text}")
        return None
    except Exception as e:
        logger.exception(f"Error inesperado al buscar en Google Books: {e}")
        return None

# No olvides crear src/librorecomienda/clients/__init__.py (puede estar vacío)