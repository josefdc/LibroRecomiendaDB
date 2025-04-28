# src/librorecomienda/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Importa la configuración centralizada
from librorecomienda.core.config import settings

# Crea el motor SQLAlchemy usando la URL de la configuración
# pool_pre_ping=True verifica las conexiones antes de usarlas, bueno para conexiones de larga duración
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Crea una fábrica de sesiones configurada
# autocommit=False y autoflush=False son configuraciones estándar seguras
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crea una clase Base para que nuestros modelos la hereden
Base = declarative_base()

# Dependencia para FastAPI (o uso directo): Obtiene una sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db # Proporciona la sesión
    finally:
        db.close() # Asegura que la sesión se cierre después de usarla