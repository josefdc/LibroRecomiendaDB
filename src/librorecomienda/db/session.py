"""
Configuración y utilidades para la gestión de la sesión de base de datos SQLAlchemy en LibroRecomienda.
Incluye la creación del motor, la fábrica de sesiones y la clase base para los modelos ORM.
Proporciona una función de dependencia para obtener y cerrar sesiones de base de datos de forma segura.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from librorecomienda.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Proporciona una sesión de base de datos para su uso en dependencias (por ejemplo, en FastAPI).

    Yields:
        Session: Sesión de base de datos SQLAlchemy.

    Ensures:
        La sesión se cierra correctamente después de su uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()