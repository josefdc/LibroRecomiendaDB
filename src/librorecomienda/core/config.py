# src/librorecomienda/core/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv() # Carga las variables de entorno desde .env

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "NO_API_KEY_SET")
    GOOGLE_BOOKS_API_KEY: str = os.getenv("GOOGLE_BOOKS_API_KEY", "NO_GOOGLE_KEY_SET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    # --- Añadir esta línea ---
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "") # Lista de emails separados por coma

    # Propiedad para obtener la lista fácilmente
    @property
    def list_admin_emails(self) -> list[str]:
        return [email.strip() for email in self.ADMIN_EMAILS.split(',') if email.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore" # Ignorar variables extra en .env

settings = Settings()