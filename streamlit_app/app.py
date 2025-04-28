# streamlit_app/app.py

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
    # ... (existing import error handling, ensure settings is imported here too) ...
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
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

# Configure logging
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

# --- Sidebar for Login/Registration/Logout ---
st.sidebar.title("Acceso")

if st.session_state.logged_in:
    st.sidebar.success(f"Conectado como: {st.session_state.user_email}")
    if st.session_state.is_admin:
        st.sidebar.write("👑 (Admin)")
    if st.sidebar.button("Cerrar Sesión"):
        # Clear session state on logout
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.user_id = None
        st.session_state.is_admin = False
        st.sidebar.info("Sesión cerrada.")
        time.sleep(1) # Brief pause before rerun
        st.rerun()
else:
    login_tab, register_tab = st.sidebar.tabs(["Iniciar Sesión", "Registrarse"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Entrar")

            if submit_login:
                if not email or not password:
                    st.warning("Por favor, introduce email y contraseña.")
                else:
                    db_login: Session | None = None
                    try:
                        db_login = SessionLocal()
                        user = get_user_by_email(db_login, email=email)
                        if user and verify_password(password, user.hashed_password):
                            st.session_state.logged_in = True
                            st.session_state.user_email = user.email
                            st.session_state.user_id = user.id
                            # Check if the user is an admin based on settings
                            st.session_state.is_admin = user.email in settings.list_admin_emails
                            st.sidebar.success("¡Login correcto!")
                            time.sleep(1) # Brief pause
                            st.rerun()
                        else:
                            st.error("Email o contraseña incorrectos.")
                    except Exception as login_e:
                        st.error(f"Error durante el login: {login_e}")
                    finally:
                        if db_login:
                            db_login.close()

    with register_tab:
        with st.form("register_form"):
            reg_email = st.text_input("Nuevo Email")
            reg_password = st.text_input("Nueva Contraseña", type="password")
            reg_password_confirm = st.text_input("Confirmar Contraseña", type="password")
            submit_register = st.form_submit_button("Registrar")

            if submit_register:
                if not reg_email or not reg_password or not reg_password_confirm:
                    st.warning("Por favor, rellena todos los campos.")
                elif reg_password != reg_password_confirm:
                    st.error("Las contraseñas no coinciden.")
                else:
                    db_reg: Session | None = None
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
                                time.sleep(2) # Pause to show message
                                # Optionally switch to login tab or rerun
                                st.rerun() # Rerun to clear form/show login
                            else:
                                st.error("Error durante el registro.")
                    except Exception as reg_e:
                        st.error(f"Error durante el registro: {reg_e}")
                    finally:
                        if db_reg:
                            db_reg.close()

# --- Main App Content ---
# --- Catálogo de Libros y Reseñas ---
db_main: Session | None = None
try:
    db_main = SessionLocal()

    # --- PASO 1.2: Obtener Géneros Únicos ---
    try:
        genres_query = db_main.query(Book.genre).filter(Book.genre != None, Book.genre != '').distinct().order_by(Book.genre).all()
        available_genres = [g[0] for g in genres_query]
    except Exception as e:
        st.warning(f"No se pudieron cargar los géneros para filtrar: {e}")
        available_genres = []
    # --- Fin Obtener Géneros ---

    # --- PASO 1.3: Widgets de Filtro y Ordenamiento ---
    st.header("Catálogo de Libros")
    control_cols = st.columns([2, 1])

    with control_cols[0]:
        selected_genres = st.multiselect(
            "Filtrar por Género:",
            options=available_genres,
            key="genre_multiselect"
        )
    with control_cols[1]:
        sort_option = st.selectbox(
            "Ordenar por:",
            options=['Título (A-Z)', 'Autor (A-Z)', 'Rating (Mayor a menor)', 'Rating (Menor a mayor)'],
            key='book_sort_select'
        )
    st.divider()
    # --- Fin Widgets ---

    # --- PASO 2: Obtener y Procesar Libros ---
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

    filtered_sorted_books = query.all()
    # --- Fin Obtener y Procesar Libros ---

    if not filtered_sorted_books:
        st.warning("No se encontraron libros con los filtros seleccionados o no hay libros en la base de datos.")
    else:
        st.markdown(f"**{len(filtered_sorted_books)} libro(s) encontrado(s)**")
        # --- PASO 3: Refinar Bucle de Visualización ---
        for book in filtered_sorted_books:
            expander_title = f"{book.title} ({book.author or 'Autor Desconocido'})"
            with st.expander(expander_title):

                # --- Nuevo Layout Interno ---
                main_cols = st.columns([1, 3])

                with main_cols[0]: # Columna Izquierda: Imagen
                    if book.cover_image_url:
                        try:
                            st.image(book.cover_image_url, width=150, caption=f"Portada de {book.title}")
                        except Exception as img_e:
                            st.caption(f"⚠ Error cargando portada")
                            logger.warning(f"Error loading image {book.cover_image_url}: {img_e}")
                    else:
                        st.caption("🖼 Sin portada")

                with main_cols[1]: # Columna Derecha: Título, Autor, Rating
                    st.subheader(f"{book.title}")
                    st.write(f"**Autor:** {book.author or 'Desconocido'}")

                    if book.average_rating is not None:
                        st.metric(label="Rating Promedio", value=f"{book.average_rating:.1f} ⭐")
                    else:
                        st.caption("📊 Aún sin calificar")

                    st.caption(f"**Género:** {book.genre or 'Desconocido'} | **ISBN:** {book.isbn or 'N/A'}")

                # Descripción (debajo de las columnas principales - NO anidado)
                if book.description:
                    # Display description directly using caption or markdown
                    st.caption("Descripción:")
                    st.caption(book.description) # Or st.markdown(book.description)
                else:
                    st.caption("Sin descripción disponible.")


                st.divider() # Separador antes de las reseñas

                # --- Sección de Reseñas ---
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

                # --- Añadir Reseña ---
                if st.session_state.get('logged_in', False):
                    st.markdown("---")
                    st.markdown("#### Añade tu reseña")
                    with st.form(key=f"review_form_{book.id}", clear_on_submit=True):
                        rating = st.slider("Tu puntuación (estrellas):", 1, 5, 3)
                        comment = st.text_area("Tu comentario:")
                        submit_review = st.form_submit_button("Enviar Reseña")

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
                # --- Fin Nuevo Layout Interno ---

except Exception as e:
    st.error(f"Error cargando los libros o reseñas: {e}")
    logger.exception("Error in main app.py block")
finally:
    if 'db_main' in locals() and db_main:
        db_main.close()