"""
Configuration module for LibroRecomienda.

This module defines the Settings class, which loads environment variables
and provides application-wide configuration, including database URLs,
API keys, environment, and admin email management.

Usage:
    Import the `settings` object to access configuration throughout the project.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        DATABASE_URL (str): Database connection string.
        OPENAI_API_KEY (str): API key for OpenAI services.
        GOOGLE_BOOKS_API_KEY (str): API key for Google Books API.
        ENVIRONMENT (str): Current environment (e.g., 'production', 'development').
        ADMIN_EMAILS (str): Comma-separated list of admin emails.
    """
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "NO_API_KEY_SET")
    GOOGLE_BOOKS_API_KEY: str = os.getenv("GOOGLE_BOOKS_API_KEY", "NO_GOOGLE_KEY_SET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    ADMIN_EMAILS: str = os.getenv("ADMIN_EMAILS", "")

    @property
    def list_admin_emails(self) -> List[str]:
        """
        Returns the list of admin emails parsed from ADMIN_EMAILS.

        Returns:
            List[str]: List of admin email addresses.
        """
        return [email.strip() for email in self.ADMIN_EMAILS.split(',') if email.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()