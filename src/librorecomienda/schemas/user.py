# src/librorecomienda/schemas/user.py
from pydantic import BaseModel, EmailStr

# Schema para recibir datos al crear usuario
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Schema para devolver datos del usuario (sin contraseña)
class UserSchema(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    # Podrías añadir created_at si quieres mostrarlo

    class Config:
        from_attributes = True # Permite crear desde el objeto ORM
