# src/librorecomienda/core/config.py
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Encuentra el directorio raíz del proyecto (asumiendo que config.py está en src/librorecomienda/core)
# Sube 4 niveles: core -> librorecomienda -> src -> Raíz del Proyecto
PROJECT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = PROJECT_DIR / '.env'

# Carga explícita del .env ANTES de inicializar BaseSettings
# Esto es más robusto que depender solo de SettingsConfigDict para encontrarlo.
if ENV_PATH.is_file():
    load_dotenv(dotenv_path=ENV_PATH)
    # print(f"Loaded environment variables from: {ENV_PATH}") # Descomentar para depurar
else:
    print(f"Warning: .env file not found at {ENV_PATH}") # Advertencia si no se encuentra

class Settings(BaseSettings):
    # Indica que las variables pueden venir del entorno (además del .env cargado)
    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra='ignore')

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db") # Fallback a SQLite si no está definida
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "NO_API_KEY_SET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    GOOGLE_BOOKS_API_KEY: str = os.getenv("GOOGLE_BOOKS_API_KEY", "NO_GOOGLE_KEY_SET")

    # Puedes añadir más configuraciones aquí si las necesitas
    # Ejemplo: API_V1_STR: str = "/api/v1"

settings = Settings()

# Líneas de depuración (opcional, quitar en producción)
# print(f"DATABASE_URL: {settings.DATABASE_URL}")
# print(f"OPENAI_API_KEY loaded: {'Yes' if settings.OPENAI_API_KEY != 'NO_API_KEY_SET' else 'No'}")
# print(f"ENVIRONMENT: {settings.ENVIRONMENT}")