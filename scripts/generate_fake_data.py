# scripts/generate_fake_data.py
import random
import logging
import sys
import os # Necesario para la importación relativa si no se usa uv run
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError # Para capturar errores específicos

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Añadir 'src' al PYTHONPATH (alternativa si no usas 'uv run') ---
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir)
# src_path = os.path.join(project_root, 'src')
# if src_path not in sys.path:
#     sys.path.insert(0, src_path)

# --- Importaciones del Proyecto ---
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
    sys.exit(1) # Salir si hay error crítico

# --- Constantes de Configuración ---
NUM_FAKE_USERS = 50        # Número de usuarios falsos a crear/verificar
MAX_REVIEWS_PER_USER = 15  # Máximo número de reseñas por cada usuario
MIN_REVIEWS_PER_USER = 2   # Mínimo número de reseñas por cada usuario
FAKE_PASSWORD = "password123" # Contraseña común para usuarios de prueba

# --- Inicializar Faker ---
fake = Faker(['es_ES', 'en_US']) # Múltiples locales para variedad de nombres/emails
logger.info("Instancia de Faker creada.")

# --- Función Principal ---
def generate_data():
    if not MODELS_LOADED:
        logger.error("No se pudieron cargar los módulos del proyecto. Abortando.")
        return

    logger.info("=============================================")
    logger.info(" Iniciando script de generación de datos falsos")
    logger.info("=============================================")

    db: Session | None = None
    created_user_ids = []
    book_ids = []

    try:
        logger.info("Abriendo sesión de base de datos...")
        db = SessionLocal()

        # 1. Crear o Verificar Usuarios Falsos
        logger.info(f"--- Fase 1: Creando/Verificando {NUM_FAKE_USERS} Usuarios Falsos ---")
        for i in range(NUM_FAKE_USERS):
            # Generar datos de usuario
            first_name = fake.first_name().lower().replace("'", "") # Evitar apóstrofes
            last_name = fake.last_name().lower().replace("'", "")
            domain = fake.domain_name()
            # Construir email más realista y único
            fake_email = f"{first_name}.{last_name}{random.randint(1,999)}@{domain}"

            # Verificar si ya existe en la BD
            existing_user = get_user_by_email(db, email=fake_email)

            if not existing_user:
                user_in = UserCreate(email=fake_email, password=FAKE_PASSWORD)
                try:
                    # La función create_user ya hace commit y refresh
                    new_user = create_user(db=db, user=user_in)
                    created_user_ids.append(new_user.id)
                    logger.info(f"  ({i+1}/{NUM_FAKE_USERS}) Usuario Creado: {new_user.email} (ID: {new_user.id})")
                except IntegrityError: # Captura error si el email ya existe (raro por el número aleatorio)
                     db.rollback() # Deshacer la transacción fallida
                     logger.warning(f"  ({i+1}/{NUM_FAKE_USERS}) Error de integridad al crear {fake_email}, probablemente ya existe. Intentando obtenerlo...")
                     existing_user = get_user_by_email(db, email=fake_email)
                     if existing_user:
                          created_user_ids.append(existing_user.id)
                except Exception as e:
                    logger.error(f"  ({i+1}/{NUM_FAKE_USERS}) Error inesperado creando usuario {fake_email}: {e}")
                    db.rollback() # Deshacer si hay otro error
            else:
                # Si ya existe, simplemente usamos su ID
                logger.info(f"  ({i+1}/{NUM_FAKE_USERS}) Usuario Encontrado: {existing_user.email} (ID: {existing_user.id})")
                created_user_ids.append(existing_user.id)

        if not created_user_ids:
            logger.error("No se pudieron crear ni encontrar usuarios. Abortando generación de reseñas.")
            return

        logger.info(f"--- Fase 1 Completada: {len(created_user_ids)} IDs de usuario listos. ---")

        # 2. Obtener IDs de Libros Existentes
        logger.info("--- Fase 2: Obteniendo IDs de Libros Existentes ---")
        book_ids = [id_tuple[0] for id_tuple in db.query(Book.id).all()] # Extraer el ID de la tupla
        if not book_ids:
            logger.error("No hay libros en la base de datos. No se pueden generar reseñas.")
            return
        logger.info(f"Se encontraron {len(book_ids)} libros disponibles.")
        logger.info("--- Fase 2 Completada. ---")


        # 3. Crear Reseñas Falsas
        logger.info(f"--- Fase 3: Generando Reseñas Falsas ({MIN_REVIEWS_PER_USER}-{MAX_REVIEWS_PER_USER} por usuario) ---")
        total_reviews_added = 0
        processed_users = 0

        for user_id in created_user_ids:
            processed_users += 1
            # Determinar cuántas reseñas hará este usuario
            num_reviews_to_create = random.randint(MIN_REVIEWS_PER_USER, min(MAX_REVIEWS_PER_USER, len(book_ids)))

            # Seleccionar libros al azar para este usuario (sin repetición)
            # Asegurarse de que num_reviews_to_create no sea mayor que los libros disponibles
            actual_num_reviews = min(num_reviews_to_create, len(book_ids))
            if actual_num_reviews <= 0:
                continue # No hay libros para reseñar o num_reviews es 0
            selected_book_ids = random.sample(book_ids, actual_num_reviews)

            logger.info(f"  Usuario ID: {user_id} ({processed_users}/{len(created_user_ids)}) - Creando {actual_num_reviews} reseñas...")

            reviews_for_this_user = 0
            for book_id in selected_book_ids:
                # Generar datos de la reseña
                fake_rating = random.randint(1, 5)
                # Generar comentario con probabilidad (ej: 70% de las veces)
                fake_comment_text = fake.paragraph(nb_sentences=random.randint(1, 4)) if random.random() < 0.7 else None

                try:
                    # Crear el objeto schema
                    review_in = ReviewCreate(rating=fake_rating, comment=fake_comment_text)
                    # Llamar a la función CRUD (que hace commit)
                    create_review(db=db, review=review_in, user_id=user_id, book_id=book_id)
                    reviews_for_this_user += 1
                except IntegrityError as ie:
                     # Podría ocurrir si ya existe una reseña para este user/book y tienes UniqueConstraint
                     logger.warning(f"  Error de integridad al crear review para User {user_id}, Book {book_id}: {ie}. ¿Ya existe?")
                     db.rollback() # Deshacer transacción fallida
                except Exception as e:
                    logger.error(f"  Error inesperado creando review para User {user_id}, Book {book_id}: {e}")
                    db.rollback() # Deshacer transacción fallida

            if reviews_for_this_user > 0:
                 logger.info(f"  Usuario ID: {user_id} - Se crearon {reviews_for_this_user} reseñas.")
                 total_reviews_added += reviews_for_this_user
            # No es necesario commit aquí si create_review ya lo hace

        logger.info(f"--- Fase 3 Completada: Total reseñas falsas añadidas: {total_reviews_added} ---")

    except Exception as e:
        logger.exception(f"Error CRÍTICO durante la generación de datos: {e}")
        if db: db.rollback() # Intentar deshacer si hubo un error grave
    finally:
        if db:
            logger.info("Cerrando sesión de base de datos.")
            db.close()

# --- Punto de Entrada del Script ---
if __name__ == "__main__":
    generate_data()
    logger.info("============================================")
    logger.info(" Script de Generación de Datos Finalizado")
    logger.info("============================================")
