from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from librorecomienda.db.session import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(255), index=True, nullable=True)
    genre = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    average_rating = Column(Float, nullable=True, default=None)
    cover_image_url = Column(String(512), nullable=True)

    isbn = Column(String(20), unique=True, index=True, nullable=True)

    # Relación con Reviews (un libro puede tener muchas reseñas)
    # Add cascade option
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")

    def __repr__(self):
         return f"<Book(id={self.id}, title='{self.title[:30]}...', isbn='{self.isbn}'>"