from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), index=True, nullable=True)
    genre = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    average_rating = Column(Float, nullable=True) # Podría calcularse o venir de una fuente externa
    cover_image_url = Column(String(512), nullable=True)

    # Relación con Reviews (un libro puede tener muchas reseñas)
    reviews = relationship("Review", back_populates="book")