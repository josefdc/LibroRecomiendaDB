"""
Modelo ORM para la entidad Book en la base de datos de LibroRecomienda.
Define los campos principales de un libro y su relación con las reseñas.
"""

from sqlalchemy import Column, Integer, String, Text, Float
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class Book(Base):
    """
    Representa un libro en la base de datos.

    Atributos:
        id (int): Identificador primario del libro.
        title (str): Título del libro.
        author (str): Autor del libro.
        genre (str): Género literario.
        description (str): Descripción o sinopsis del libro.
        average_rating (float): Valoración promedio calculada a partir de las reseñas.
        cover_image_url (str): URL de la imagen de portada.
        isbn (str): ISBN único del libro.
        reviews (List[Review]): Lista de reseñas asociadas al libro.
    """
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), index=True, nullable=True)
    genre = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    average_rating = Column(Float, nullable=True, default=None)
    cover_image_url = Column(String(512), nullable=True)
    isbn = Column(String(20), unique=True, index=True, nullable=True)

    reviews = relationship(
        "Review",
        back_populates="book",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """
        Representación legible del objeto Book para depuración.

        Returns:
            str: Cadena representando el libro.
        """
        return f"<Book(id={self.id}, title='{self.title[:30]}...', isbn='{self.isbn}')>"