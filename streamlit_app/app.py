"""
Main application entry point for LibroRecomienda Streamlit app.

This module provides user authentication (login/registration), book catalog
display with filtering and sorting, and review management (add/delete).
It manages session state, database connections, and user interface logic.

Intended for end-users to browse books, leave reviews, and for admins to access
additional features via session state.

Note:
    - All database sessions are properly closed after use.
    - Logging is configured for error and info reporting.
"""

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from sqlalchemy.exc import IntegrityError
import sys
import os
from datetime import datetime
import logging
import time
from typing import Any, List, Optional

# --- Attempt to import project modules ---
try:
    from librorecomienda.db.session import SessionLocal
    from librorecomienda.crud import (
        create_user, get_user_by_email,
        create_review, get_reviews_for_book_with_user, soft_delete_review
    )
    from librorecomienda.schemas.user import UserCreate
    from librorecomienda.schemas.review import ReviewCreate
    from librorecomienda.core.security import verify_password
    from librorecomienda.models.book import Book
    from librorecomienda.core.config import settings
except ImportError:
    project_root: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    try:
        from librorecomienda.db.session import SessionLocal
        from librorecomienda.crud import (
            create_user, get_user_by_email,
            create_review, get_reviews_for_book_with_user, soft_delete_review
        )
        from librorecomienda.schemas.user import UserCreate
        from librorecomienda.schemas.review import ReviewCreate
        from librorecomienda.core.security import verify_password
        from librorecomienda.models.book import Book
        from librorecomienda.core.config import settings
    except ImportError as e:
        st.error(f"Failed to import project modules in app.py. Error: {e}")
        st.stop()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

st.sidebar.title("Acceso")

def handle_logout() -> None:
    """
    Clears session state and logs out the user.

    Returns:
        None
    """
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.session_state.is_admin = False
    st.sidebar.info("Sesión cerrada.")
    time.sleep(1)
    st.rerun()

def handle_login(email: str, password: str) -> None:
    """
    Handles user login, sets session state if successful.

    Args:
        email (str): User email.
        password (str): User password.

    Returns:
        None
    """
    db_login: Optional[Session] = None
    try:
        db_login = SessionLocal()
        user = get_user_by_email(db_login, email=email)
        if user and verify_password(password, user.hashed_password):
            st.session_state.logged_in = True
            st.session_state.user_email = user.email
            st.session_state.user_id = user.id
            st.session_state.is_admin = user.email in settings.list_admin_emails
            st.sidebar.success("¡Login correcto!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Email o contraseña incorrectos.")
    except Exception as login_e:
        st.error(f"Error durante el login: {login_e}")
    finally:
        if db_login:
            db_login.close()

def handle_registration(reg_email: str, reg_password: str, reg_password_confirm: str) -> None:
    """
    Handles user registration, creates a new user if valid.

    Args:
        reg_email (str): Registration email.
        reg_password (str): Registration password.
        reg_password_confirm (str): Password confirmation.

    Returns:
        None
    """
    if not reg_email or not reg_password or not reg_password_confirm:
        st.warning("Por favor, rellena todos los campos.")
    elif reg_password != reg_password_confirm:
        st.error("Las contraseñas no coinciden.")
    else:
        db_reg: Optional[Session] = None
        try:
            db_reg = SessionLocal()
            existing_user = get_user_by_email(db_reg, email=reg_email)
            if existing_user:
                st.error("Este email ya está registrado.")
            else:
                user_in = UserCreate(email=reg_email, password=reg_password)
                new_user = create_user(db=db_reg, user=user_in)
                if new_user:
                    st.success("¡Registro completado! Ahora puedes iniciar sesión.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Error durante el registro.")
        except Exception as reg_e:
            st.error(f"Error durante el registro: {reg_e}")
        finally:
            if db_reg:
                db_reg.close()

if st.session_state.logged_in:
    st.sidebar.success(f"Conectado como: {st.session_state.user_email}")
    if st.session_state.is_admin:
        st.sidebar.write("👑 (Admin)")
    if st.sidebar.button("Cerrar Sesión"):
        handle_logout()
else:
    login_tab, register_tab = st.sidebar.tabs(["Iniciar Sesión", "Registrarse"])

    with login_tab:
        with st.form("login_form"):
            email: str = st.text_input("Email")
            password: str = st.text_input("Contraseña", type="password")
            submit_login: bool = st.form_submit_button("Entrar")

            if submit_login:
                if not email or not password:
                    st.warning("Por favor, introduce email y contraseña.")
                else:
                    handle_login(email, password)

    with register_tab:
        with st.form("register_form"):
            reg_email: str = st.text_input("Nuevo Email")
            reg_password: str = st.text_input("Nueva Contraseña", type="password")
            reg_password_confirm: str = st.text_input("Confirmar Contraseña", type="password")
            submit_register: bool = st.form_submit_button("Registrar")

            if submit_register:
                handle_registration(reg_email, reg_password, reg_password_confirm)

# --- Main App Content ---
db_main: Optional[Session] = None
try:
    db_main = SessionLocal()

    # --- Obtener Géneros Únicos ---
    try:
        genres_query = db_main.query(Book.genre).filter(Book.genre != None, Book.genre != '').distinct().order_by(Book.genre).all()
        available_genres: List[str] = [g[0] for g in genres_query]
    except Exception as e:
        st.warning(f"No se pudieron cargar los géneros para filtrar: {e}")
        available_genres = []

    st.header("Catálogo de Libros")
    control_cols = st.columns([2, 1])

    with control_cols[0]:
        selected_genres: List[str] = st.multiselect(
            "Filtrar por Género:",
            options=available_genres,
            key="genre_multiselect"
        )
    with control_cols[1]:
        sort_option: str = st.selectbox(
            "Ordenar por:",
            options=['Título (A-Z)', 'Autor (A-Z)', 'Rating (Mayor a menor)', 'Rating (Menor a mayor)'],
            key='book_sort_select'
        )
    st.divider()

    # --- Obtener y Procesar Libros ---
    query = db_main.query(Book)

    if selected_genres:
        query = query.filter(Book.genre.in_(selected_genres))

    if sort_option == 'Título (A-Z)':
        query = query.order_by(asc(Book.title))
    elif sort_option == 'Autor (A-Z)':
        query = query.order_by(asc(Book.author))
    elif sort_option == 'Rating (Mayor a menor)':
        query = query.order_by(desc(Book.average_rating).nullslast())
    elif sort_option == 'Rating (Menor a mayor)':
        query = query.order_by(asc(Book.average_rating).nullsfirst())

    filtered_sorted_books: List[Any] = query.all()

    if not filtered_sorted_books:
        st.warning("No se encontraron libros con los filtros seleccionados o no hay libros en la base de datos.")
    else:
        st.markdown(f"**{len(filtered_sorted_books)} libro(s) encontrado(s)**")
        for book in filtered_sorted_books:
            expander_title: str = f"{book.title} ({book.author or 'Autor Desconocido'})"
            with st.expander(expander_title):
                main_cols = st.columns([1, 3])

                with main_cols[0]:
                    if book.cover_image_url:
                        try:
                            st.image(book.cover_image_url, width=150, caption=f"Portada de {book.title}")
                        except Exception as img_e:
                            st.caption("⚠ Error cargando portada")
                            logger.warning(f"Error loading image {book.cover_image_url}: {img_e}")
                    else:
                        st.caption("🖼 Sin portada")

                with main_cols[1]:
                    st.subheader(f"{book.title}")
                    st.write(f"**Autor:** {book.author or 'Desconocido'}")

                    if book.average_rating is not None:
                        st.metric(label="Rating Promedio", value=f"{book.average_rating:.1f} ⭐")
                    else:
                        st.caption("📊 Aún sin calificar")

                    st.caption(f"**Género:** {book.genre or 'Desconocido'} | **ISBN:** {book.isbn or 'N/A'}")

                if book.description:
                    st.caption("Descripción:")
                    st.caption(book.description)
                else:
                    st.caption("Sin descripción disponible.")

                st.divider()

                st.markdown("#### Reseñas")
                reviews_data = get_reviews_for_book_with_user(db=db_main, book_id=book.id)

                if not reviews_data:
                    st.info("Todavía no hay reseñas para este libro. ¡Sé el primero!")
                else:
                    for review, user_email in reviews_data:
                        review_cols = st.columns([4, 1])
                        with review_cols[0]:
                            st.markdown(f"**{user_email}** ({review.created_at.strftime('%Y-%m-%d %H:%M')}):")
                            st.write(f"Rating: {'⭐'*review.rating}")
                            st.caption(f"> {review.comment}")

                        with review_cols[1]:
                            if st.session_state.get('logged_in') and st.session_state.get('user_id') == review.user_id:
                                delete_key = f"delete_review_{review.id}_book_{book.id}"
                                if st.button("🗑️ Borrar", key=delete_key, help="Borrar mi reseña"):
                                    success = soft_delete_review(db=db_main, review_id=review.id, requesting_user_id=st.session_state.user_id)
                                    if success:
                                        st.success("Reseña borrada.")
                                        st.rerun()
                                    else:
                                        st.error("No se pudo borrar la reseña.")
                        st.markdown("---")

                if st.session_state.get('logged_in', False):
                    st.markdown("---")
                    st.markdown("#### Añade tu reseña")
                    with st.form(key=f"review_form_{book.id}", clear_on_submit=True):
                        rating: int = st.slider("Tu puntuación (estrellas):", 1, 5, 3)
                        comment: str = st.text_area("Tu comentario:")
                        submit_review: bool = st.form_submit_button("Enviar Reseña")

                        if submit_review:
                            if not comment:
                                st.warning("Por favor, escribe un comentario.")
                            else:
                                review_in = ReviewCreate(rating=rating, comment=comment)
                                try:
                                    created = create_review(
                                        db=db_main,
                                        review=review_in,
                                        user_id=st.session_state.user_id,
                                        book_id=book.id
                                    )
                                    if created:
                                        st.success("¡Gracias por tu reseña!")
                                        st.rerun()
                                except IntegrityError:
                                    st.error("Ya has añadido una reseña para este libro.")
                                except Exception as review_e:
                                    st.error(f"Error al guardar la reseña: {review_e}")
                                    logger.exception(f"Error submitting review for book {book.id} by user {st.session_state.user_id}")

except Exception as e:
    st.error(f"Error cargando los libros o reseñas: {e}")
    logger.exception("Error in main app.py block")
finally:
    if 'db_main' in locals() and db_main:
        db_main.close()