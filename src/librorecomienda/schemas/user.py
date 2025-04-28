"""
Esquemas Pydantic para la entidad User en la API de LibroRecomienda.
Define los modelos de entrada y salida para validación y serialización de usuarios.
"""

from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseModel):
    """
    Esquema para la creación de un usuario.

    Atributos:
        email (EmailStr): Correo electrónico del usuario.
        password (str): Contraseña en texto plano (será hasheada antes de almacenar).
    """
    email: EmailStr
    password: str

class UserSchema(BaseModel):
    """
    Esquema de salida para un usuario (sin contraseña).

    Atributos:
        id (int): ID del usuario.
        email (EmailStr): Correo electrónico del usuario.
        is_active (bool): Estado de activación del usuario.
    """
    id: int
    email: EmailStr
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
