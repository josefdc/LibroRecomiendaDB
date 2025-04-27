# streamlit_app/app.py
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func # Necesitamos distinct y func
import time
import types

# --- Importaciones Adicionales ---
from librorecomienda.schemas.user import UserCreate
from librorecomienda.crud.crud_user import get_user_by_email, create_user
from librorecomienda.core.security import verify_password
# Asegúrate que SessionLocal esté importado
from librorecomienda.db.session import SessionLocal

# --- Importaciones de la Aplicación ---
try:
    from librorecomienda.models.book import Book
    MODELS_LOADED = True
except ImportError as e:
    st.error(f"Error importando módulos: {e}. Ejecuta 'uv pip install -e .'?")
    MODELS_LOADED = False
except Exception as e:
     st.error(f"Error inesperado en importación: {e}")
     MODELS_LOADED = False

# --- Inicialización de Session State ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = None
    st.session_state['user_id'] = None

# --- Configuración de la Página ---
st.set_page_config(
    page_title="LibroRecomienda",
    page_icon="📚",
    layout="wide", # Usar ancho completo
    initial_sidebar_state="expanded" # Mostrar sidebar por defecto
)

# --- Funciones Cacheadas ---
@st.cache_data(ttl="10m")
def load_books_from_db():
    """Carga todos los libros de la BD. Cacheable."""
    db: Session | None = None
    try:
        db = SessionLocal()
        books_result = db.query(
            Book.id,
            Book.title,
            Book.author,
            Book.genre,
            Book.average_rating,
            Book.description,
            Book.cover_image_url
        ).order_by(Book.id).all()

        books_data = [
            types.SimpleNamespace(
                id=row.id,
                title=row.title,
                author=row.author,
                genre=row.genre,
                average_rating=row.average_rating,
                description=row.description,
                cover_image_url=row.cover_image_url
            )
            for row in books_result
        ]
        return books_data
    except Exception as e:
        st.error(f"Error al cargar libros: {e}")
        return []
    finally:
        if db:
            db.close()

@st.cache_data(ttl="10m")
def load_unique_genres_from_db():
    """Carga los géneros únicos de la BD. Cacheable."""
    db: Session | None = None
    try:
        db = SessionLocal()
        # Label the distinct/lower expression explicitly
        genres_query = db.query(distinct(func.lower(Book.genre)).label('distinct_genre')).\
                        filter(Book.genre.isnot(None), Book.genre != '').\
                        order_by(func.lower(Book.genre)).all()
        # Access the result using the label
        unique_genres = [row.distinct_genre for row in genres_query if row.distinct_genre]
        return unique_genres
    except Exception as e:
        # Mostrar el error específico de géneros
        st.error(f"Error al cargar géneros: {e}")
        return []
    finally:
        if db:
            db.close()

# --- Carga de Datos ---
if MODELS_LOADED:
    with st.spinner("Cargando datos... ⏳"):
        all_books = load_books_from_db()
        unique_genres = load_unique_genres_from_db()
else:
    all_books, unique_genres = [], []

# --- Sidebar (Modificada para añadir Login/Registro/Logout) ---
with st.sidebar:
    st.header("👤 Acceso")

    if not st.session_state['logged_in']:
        login_tab, register_tab = st.tabs(["Iniciar Sesión", "Registrarse"])

        # Pestaña de Login
        with login_tab:
            with st.form("login_form", clear_on_submit=True):
                login_email = st.text_input("Email", key="login_email")
                login_password = st.text_input("Contraseña", type="password", key="login_pass")
                login_submitted = st.form_submit_button("Entrar")

                if login_submitted:
                    if not login_email or not login_password:
                        st.warning("Por favor, introduce email y contraseña.")
                    else:
                        db: Session | None = None # Initialize db to None
                        try:
                            db = SessionLocal()
                            user = get_user_by_email(db, email=login_email)
                            if user and user.is_active and verify_password(login_password, user.hashed_password):
                                st.session_state['logged_in'] = True
                                st.session_state['user_email'] = user.email
                                st.session_state['user_id'] = user.id
                                st.success("¡Login exitoso!")
                                # st.balloons() # ¡Celebración!
                                time.sleep(1) # Pequeña pausa para ver el mensaje
                                st.rerun() # Refresca la app
                            else:
                                st.error("Email o contraseña incorrectos, o usuario inactivo.")
                        except Exception as e:
                            st.error(f"Error durante el login: {e}")
                        finally:
                            if db:
                                db.close()

        # Pestaña de Registro
        with register_tab:
            with st.form("register_form", clear_on_submit=True):
                reg_email = st.text_input("Email", key="reg_email")
                reg_password = st.text_input("Contraseña", type="password", key="reg_pass")
                reg_password_confirm = st.text_input("Confirmar Contraseña", type="password", key="reg_pass_conf")
                register_submitted = st.form_submit_button("Crear Cuenta")

                if register_submitted:
                    if not reg_email or not reg_password or not reg_password_confirm:
                        st.warning("Por favor, completa todos los campos.")
                    elif reg_password != reg_password_confirm:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        db: Session | None = None # Initialize db to None
                        try:
                            db = SessionLocal()
                            existing_user = get_user_by_email(db, email=reg_email)
                            if existing_user:
                                st.error("El email ya está registrado. Intenta iniciar sesión.")
                            else:
                                user_in = UserCreate(email=reg_email, password=reg_password)
                                new_user = create_user(db=db, user=user_in)
                                st.success(f"¡Usuario {new_user.email} registrado! Ahora puedes iniciar sesión.")
                        except Exception as e:
                            st.error(f"Error al registrar usuario: {e}")
                        finally:
                            if db:
                                db.close()
    else:
        # Si ya está logueado
        st.write(f"Bienvenido/a,")
        st.subheader(st.session_state['user_email'])
        if st.button("Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.session_state['user_email'] = None
            st.session_state['user_id'] = None
            st.success("Sesión cerrada.")
            time.sleep(1)
            st.rerun() # Refrescar

    st.divider() # Separador antes de los filtros
    st.header("🔍 Filtros y Orden")

    # Filtro por Texto (existente)
    search_term = st.text_input("Buscar por Título o Autor", key="search_bar")

    # Filtro por Género (Nuevo)
    # Usamos los géneros únicos cargados de la BD
    # Convertimos a title() para que se vean mejor (ej. 'computers' -> 'Computers')
    display_genres = sorted([g.title() for g in unique_genres])
    selected_genres = st.multiselect(
        "Filtrar por Género(s)",
        options=display_genres,
        key="genre_filter"
    )

    # Selección de Orden (Nuevo)
    sort_options = {
        "Título (A-Z)": ("title", False),
        "Título (Z-A)": ("title", True),
        "Autor (A-Z)": ("author", False),
        "Autor (Z-A)": ("author", True),
        "Rating (Mayor a Menor)": ("average_rating", True),
        "Rating (Menor a Mayor)": ("average_rating", False),
        "Por Defecto (ID)": ("id", False) # Opcional: volver al orden original
    }
    selected_sort_label = st.selectbox(
        "Ordenar por",
        options=list(sort_options.keys()),
        key="sort_select"
    )
    sort_key, sort_reverse = sort_options[selected_sort_label]


# --- Título Principal ---
    sort_key, sort_reverse = sort_options[selected_sort_label]


# --- Título Principal ---
st.title("📚 Catálogo de Libros - LibroRecomienda")
st.markdown("Explora los libros disponibles en nuestra base de datos.")
st.divider()

# --- Lógica Principal ---
if not MODELS_LOADED:
    st.warning("No se pueden cargar los modelos de la base de datos. La aplicación no puede continuar.")
elif not all_books:
    st.warning("No hay libros en la base de datos o hubo un error al cargarlos.")
else:
    # 1. Aplicar Filtro de Género
    if selected_genres:
         # Convertir géneros seleccionados a minúsculas para comparar
         selected_genres_lower = [g.lower() for g in selected_genres]
         working_list = [
             book for book in all_books
             if (book.genre or "").lower() in selected_genres_lower
         ]
    else:
         # Si no se selecciona género, usar todos los libros
         working_list = all_books

    # 2. Aplicar Filtro de Texto (sobre la lista ya filtrada por género)
    if search_term:
         search_term_lower = search_term.lower()
         filtered_books = [
             book for book in working_list
             if (search_term_lower in (book.title or "").lower()) or \
                (search_term_lower in (book.author or "").lower())
         ]
         # Mensaje se mostrará después de ordenar
    else:
         filtered_books = working_list
         # Mensaje se mostrará después de ordenar

    # 3. Aplicar Ordenación (sobre la lista filtrada por género y texto)
    # Usamos lambdas y manejamos valores None para evitar errores al ordenar
    if sort_key == "title":
         filtered_books.sort(key=lambda b: (b.title or "").lower(), reverse=sort_reverse)
    elif sort_key == "author":
         filtered_books.sort(key=lambda b: (b.author or "").lower(), reverse=sort_reverse)
    elif sort_key == "average_rating":
         # Poner los None al final si es ascendente, al principio si es descendente
         none_sort_val = float('-inf') if sort_reverse else float('inf')
         filtered_books.sort(key=lambda b: b.average_rating if b.average_rating is not None else none_sort_val, reverse=sort_reverse)
    elif sort_key == "id": # Orden por defecto
         filtered_books.sort(key=lambda b: b.id, reverse=sort_reverse)
    # else: # No ordenar si es "Por Defecto (ID)" y reverse=False (ya están por ID de la query)

    # Mostrar mensaje de cuántos libros se muestran *después* de filtrar y ordenar
    if search_term or selected_genres:
        st.info(f"Mostrando {len(filtered_books)} libros que coinciden con los filtros.")
    else:
        st.info(f"Mostrando los {len(filtered_books)} libros disponibles.")


    # 4. Mostrar libros filtrados y ordenados
    if not filtered_books:
         st.warning("No se encontraron libros que coincidan con los filtros seleccionados.")
    else:
        col1, col2 = st.columns(2)
        columns = [col1, col2]

        for i, book in enumerate(filtered_books):
            # Distribuir libros entre las columnas
            with columns[i % len(columns)]:
                with st.container(border=True):
                    # Crear 2 columnas internas: una para la imagen, otra para el texto
                    col_img, col_data = st.columns([1, 3])
                    with col_img:
                        if book.cover_image_url:
                            st.image(book.cover_image_url, width=100)
                        else:
                            st.caption("No hay portada")
                    with col_data:
                        st.subheader(book.title or "Título no disponible")
                        st.caption(f"Autor(es): {book.author or 'Desconocido'} | Género: {book.genre or 'N/A'}")
                        rating_value = f"{book.average_rating:.1f} ⭐" if book.average_rating is not None else "N/A"
                        st.metric(label="Rating Prom.", value=rating_value)

                    # Expander para la descripción (fuera de las columnas internas, pero dentro del container)
                    if book.description:
                        with st.expander("Ver descripción"):
                            st.write(book.description)
                    else:
                        st.write("_Sin descripción disponible._")

                    # --- Sección para Añadir Reseña (Solo si está logueado) ---
                    if st.session_state['logged_in']:
                        st.divider() # Separador visual
                        with st.form(key=f"review_form_{book.id}", clear_on_submit=True):
                            st.write("**Deja tu reseña:**")
                            user_rating = st.slider(
                                "Calificación (Estrellas):",
                                min_value=1, max_value=5, value=3, step=1,
                                key=f"rating_{book.id}"
                            )
                            user_comment = st.text_area(
                                "Comentario (Opcional):",
                                key=f"comment_{book.id}"
                            )
                            submitted = st.form_submit_button("Enviar Reseña")

                            if submitted:
                                if st.session_state['user_id']:
                                    review_in = ReviewCreate(rating=user_rating, comment=user_comment if user_comment else None)
                                    db = SessionLocal()
                                    try:
                                        create_review(
                                            db=db,
                                            review=review_in,
                                            user_id=st.session_state['user_id'],
                                            book_id=book.id
                                        )
                                        st.success("¡Gracias por tu reseña!")
                                        st.cache_data.clear() # Forzar recarga
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error al guardar la reseña: {e}")
                                    finally:
                                        db.close()
                                else:
                                    st.error("Error: No se pudo identificar al usuario.")

                    # --- Mostrar Reseñas Existentes ---
                    st.markdown("**Reseñas de otros usuarios:**")
                    db = SessionLocal()
                    try:
                        reviews_with_users = get_reviews_for_book_with_user(db, book_id=book.id, limit=10)
                        if reviews_with_users:
                            for review, user_email in reviews_with_users:
                                with st.container(border=True):
                                    rating_stars = "⭐" * review.rating + "☆" * (5 - review.rating)
                                    reviewer = user_email if user_email else "Usuario Anónimo"
                                    review_date = review.created_at.strftime('%Y-%m-%d %H:%M') if review.created_at else 'Fecha desconocida'
                                    st.caption(f"{rating_stars} por **{reviewer}** el {review_date}")
                                    if review.comment:
                                        st.write(review.comment)
                                    else:
                                        st.write("_Sin comentario._")
                        else:
                            st.write("_Todavía no hay reseñas para este libro._")
                    except Exception as e:
                        st.error(f"Error al cargar reseñas: {e}")
                    finally:
                        db.close()

# --- Pie de página (Opcional) ---
st.divider()
st.caption("LibroRecomienda - Proyecto Final Bases de Datos")