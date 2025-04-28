"""
Script para generación de datos falsos en la base de datos de LibroRecomienda.

Este módulo crea usuarios y reseñas de prueba utilizando Faker y las funciones
CRUD del proyecto. Está pensado para poblar entornos de desarrollo o pruebas
con datos realistas y variados.

Uso:
    Ejecutar directamente este script para poblar la base de datos con usuarios
    y reseñas aleatorias. Requiere que la base de datos y los modelos estén
    correctamente configurados.

Nota:
    - El script NO crea libros, solo utiliza los existentes.
    - Los usuarios generados tendrán una contraseña común definida en FAKE_PASSWORD.
"""

import random
import logging
import sys
import os
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from librorecomienda.db.session import SessionLocal
    from librorecomienda.models.user import User
    from librorecomienda.models.book import Book
    from librorecomienda.models.review import Review
    from librorecomienda.schemas.user import UserCreate
    from librorecomienda.schemas.review import ReviewCreate
    from librorecomienda.crud.crud_user import create_user, get_user_by_email
    from librorecomienda.crud.crud_review import create_review
    MODELS_LOADED = True
    logger.info("Módulos del proyecto importados correctamente.")
except ImportError as e:
    logger.error(f"Error importando módulos: {e}.")
    logger.error("Asegúrate de haber ejecutado 'uv pip install -e .'")
    logger.error("Y que los archivos CRUD/Schemas/Models existen y son importables.")
    MODELS_LOADED = False
    sys.exit(1)

NUM_FAKE_USERS: int = 50
MAX_REVIEWS_PER_USER: int = 15
MIN_REVIEWS_PER_USER: int = 2
FAKE_PASSWORD: str = "password123"

fake = Faker(['es_ES', 'en_US'])
logger.info("Instancia de Faker creada.")

def generate_data() -> None:
    """
    Genera usuarios y reseñas falsas en la base de datos.

    Crea usuarios con emails únicos y, para cada usuario, genera un número
    aleatorio de reseñas para libros existentes. Utiliza Faker para los datos
    y maneja errores de integridad y de base de datos.

    Returns:
        None

    Raises:
        SystemExit: Si los modelos del proyecto no se cargan correctamente.
    """
    if not MODELS_LOADED:
        logger.error("No se pudieron cargar los módulos del proyecto. Abortando.")
        return

    logger.info("=============================================")
    logger.info(" Iniciando script de generación de datos falsos")
    logger.info("=============================================")

    db: Optional[Session] = None
    created_user_ids: List[int] = []
    book_ids: List[int] = []

    try:
        logger.info("Abriendo sesión de base de datos...")
        db = SessionLocal()

        logger.info(f"--- Fase 1: Creando/Verificando {NUM_FAKE_USERS} Usuarios Falsos ---")
        for i in range(NUM_FAKE_USERS):
            fake_email: str = fake.safe_email()
            existing_user = get_user_by_email(db, email=fake_email)

            if not existing_user:
                user_in = UserCreate(email=fake_email, password=FAKE_PASSWORD)
                try:
                    new_user = create_user(db=db, user=user_in)
                    created_user_ids.append(new_user.id)
                    logger.info(f"  ({i+1}/{NUM_FAKE_USERS}) Usuario Creado: {new_user.email} (ID: {new_user.id})")
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"  ({i+1}/{NUM_FAKE_USERS}) Error de integridad al crear {fake_email}, probablemente ya existe. Intentando obtenerlo...")
                    existing_user = get_user_by_email(db, email=fake_email)
                    if existing_user:
                        created_user_ids.append(existing_user.id)
                except Exception as e:
                    logger.error(f"  ({i+1}/{NUM_FAKE_USERS}) Error inesperado creando usuario {fake_email}: {e}")
                    db.rollback()
            else:
                logger.info(f"  ({i+1}/{NUM_FAKE_USERS}) Usuario Encontrado: {existing_user.email} (ID: {existing_user.id})")
                created_user_ids.append(existing_user.id)

        if not created_user_ids:
            logger.error("No se pudieron crear ni encontrar usuarios. Abortando generación de reseñas.")
            return

        logger.info(f"--- Fase 1 Completada: {len(created_user_ids)} IDs de usuario listos. ---")

        logger.info("--- Fase 2: Obteniendo IDs de Libros Existentes ---")
        book_ids = [id_tuple[0] for id_tuple in db.query(Book.id).all()]
        if not book_ids:
            logger.error("No hay libros en la base de datos. No se pueden generar reseñas.")
            return
        logger.info(f"Se encontraron {len(book_ids)} libros disponibles.")
        logger.info("--- Fase 2 Completada. ---")

        logger.info(f"--- Fase 3: Generando Reseñas Falsas ({MIN_REVIEWS_PER_USER}-{MAX_REVIEWS_PER_USER} por usuario) ---")
        total_reviews_added: int = 0
        processed_users: int = 0

        for user_id in created_user_ids:
            processed_users += 1
            num_reviews_to_create: int = random.randint(MIN_REVIEWS_PER_USER, min(MAX_REVIEWS_PER_USER, len(book_ids)))
            actual_num_reviews: int = min(num_reviews_to_create, len(book_ids))
            if actual_num_reviews <= 0:
                continue
            selected_book_ids: List[int] = random.sample(book_ids, actual_num_reviews)

            logger.info(f"  Usuario ID: {user_id} ({processed_users}/{len(created_user_ids)}) - Creando {actual_num_reviews} reseñas...")

            reviews_for_this_user: int = 0
            for book_id in selected_book_ids:
                fake_rating: int = random.randint(1, 5)
                fake_comment_text: Optional[str] = fake.paragraph(nb_sentences=random.randint(1, 4)) if random.random() < 0.7 else None

                try:
                    review_in = ReviewCreate(rating=fake_rating, comment=fake_comment_text)
                    create_review(db=db, review=review_in, user_id=user_id, book_id=book_id)
                    reviews_for_this_user += 1
                except IntegrityError as ie:
                    logger.warning(f"  Error de integridad al crear review para User {user_id}, Book {book_id}: {ie}. ¿Ya existe?")
                    db.rollback()
                except Exception as e:
                    logger.error(f"  Error inesperado creando review para User {user_id}, Book {book_id}: {e}")
                    db.rollback()

            if reviews_for_this_user > 0:
                logger.info(f"  Usuario ID: {user_id} - Se crearon {reviews_for_this_user} reseñas.")
                total_reviews_added += reviews_for_this_user

        logger.info(f"--- Fase 3 Completada: Total reseñas falsas añadidas: {total_reviews_added} ---")

    except Exception as e:
        logger.exception(f"Error CRÍTICO durante la generación de datos: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            logger.info("Cerrando sesión de base de datos.")
            db.close()

if __name__ == "__main__":
    generate_data()
    logger.info("============================================")
    logger.info(" Script de Generación de Datos Finalizado")
    logger.info("============================================")
