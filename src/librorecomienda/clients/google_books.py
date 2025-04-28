"""
Cliente asíncrono para interactuar con la API de Google Books.
Permite buscar libros externos usando la API pública de Google Books, útil como fuente complementaria
a la base de datos local del proyecto LibroRecomienda.
"""

import httpx
from librorecomienda.core.config import settings
import logging
from typing import Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

async def search_books_google_api(query: str, max_results: int = 10) -> Optional[List[Any]]:
    """
    Busca libros usando la API de Google Books.

    Args:
        query (str): Término de búsqueda (palabras clave, título, autor, etc.).
        max_results (int, opcional): Número máximo de resultados a devolver (por defecto 10).

    Returns:
        Optional[List[Any]]: Lista de libros (cada uno como dict) si la búsqueda fue exitosa, None si hubo error.

    Raises:
        httpx.RequestError: Si ocurre un error de red al hacer la petición.
        httpx.HTTPStatusError: Si la respuesta HTTP es un error.
    """
    if settings.GOOGLE_BOOKS_API_KEY == "NO_GOOGLE_KEY_SET":
        logger.error("Google Books API Key no está configurada.")
        return None

    params = {
        "q": query,
        "key": settings.GOOGLE_BOOKS_API_KEY,
        "maxResults": max_results,
        "printType": "books"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_BOOKS_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(
                f"Búsqueda en Google Books para '{query}' exitosa. "
                f"{len(data.get('items', []))} resultados obtenidos."
            )
            return data.get("items", [])
    except httpx.RequestError as exc:
        logger.error(f"Error en la petición a Google Books API: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        logger.error(f"Error HTTP en Google Books API: {exc.response.status_code} - {exc.response.text}")
        return None
    except Exception as e:
        logger.exception(f"Error inesperado al buscar en Google Books: {e}")
        return None
