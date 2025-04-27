# streamlit_app/app.py
import streamlit as st
import pandas as pd
import time
from sqlalchemy.orm import Session

# Importaciones del proyecto (ajusta las rutas según tu estructura)
from librorecomienda.db.session import SessionLocal
from librorecomienda.models.book import Book
from librorecomienda.models.user import User # Asegúrate de importar User
from librorecomienda.schemas.user import UserCreate
from librorecomienda.schemas.review import ReviewCreate
from librorecomienda.crud import create_user, get_user_by_email, create_review, get_reviews_for_book_with_user, get_users # Importar get_users
from librorecomienda.core.security import verify_password, get_password_hash
from librorecomienda.core.config import settings # Importar settings

# --- Inicialización del Estado de Sesión ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_email'] = None
    st.session_state['user_id'] = None
    st.session_state['is_admin'] = False # <-- Añadir esta línea

# ... (resto de inicializaciones si las hay) ...

# --- Funciones Auxiliares (si las tienes) ---
# Ejemplo de función para cargar libros (si la tienes separada)
# Si no, la lógica estará directamente en la sección principal
@st.cache_data(ttl=3600) # Cachear por 1 hora
def load_books_from_db():
    db: Session | None = None
    try:
        db = SessionLocal()
        # Seleccionar todas las columnas necesarias, incluyendo isbn
        books_result = db.query(
            Book.id, Book.title, Book.author, Book.genre,
            Book.average_rating, Book.description,
            Book.cover_image_url,
            Book.isbn  # <-- Asegúrate que esta columna esté seleccionada
        ).order_by(Book.title).all() # Ordenar por título para consistencia

        # Convertir a un objeto más fácil de usar si prefieres (opcional)
        # import types # Necesitarías importar types
        # books_data = [
        #     types.SimpleNamespace(
        #         id=row.id, title=row.title, author=row.author, genre=row.genre,
        #         average_rating=row.average_rating, description=row.description,
        #         cover_image_url=row.cover_image_url,
        #         isbn=row.isbn # <-- Añade el isbn aquí también
        #     ) for row in books_result
        # ]
        # return books_data
        return books_result # Devolver directamente los resultados de SQLAlchemy (Row objects)
    except Exception as e:
        st.error(f"Error cargando libros desde la base de datos: {e}")
        return []
    finally:
        if db:
            db.close()

# --- Barra Lateral: Login / Registro / Logout ---
st.sidebar.title("Acceso")

if not st.session_state.get('logged_in', False):
    login_tab, register_tab = st.sidebar.tabs(["Iniciar Sesión", "Registrarse"])

    with login_tab:
        with st.form("login_form"):
            st.subheader("Iniciar Sesión")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Contraseña", type="password", key="login_password")
            login_submitted = st.form_submit_button("Entrar")

            if login_submitted:
                if not login_email or not login_password:
                    st.warning("Por favor, introduce email y contraseña.")
                else:
                    db: Session | None = None
                    try:
                        db = SessionLocal()
                        user = get_user_by_email(db, email=login_email)
                        if user and user.is_active and verify_password(login_password, user.hashed_password):
                            st.session_state['logged_in'] = True
                            st.session_state['user_email'] = user.email
                            st.session_state['user_id'] = user.id
                            # --- Añadir esta verificación ---
                            if user.email in settings.list_admin_emails:
                                st.session_state['is_admin'] = True
                                st.toast("Acceso de administrador concedido.", icon="🔑")
                            else:
                                st.session_state['is_admin'] = False
                            # --- Fin de la verificación ---
                            st.success("¡Login exitoso!")
                            time.sleep(1)
                            # No cerrar db aquí si se necesita más adelante en la misma ejecución
                            # db.close() # Mover close si es posible o gestionarlo al final
                            st.rerun()
                        else:
                            st.error("Email o contraseña incorrectos.")
                    except Exception as e:
                        st.error(f"Error durante el login: {e}")
                    finally:
                        if db:
                            db.close()

    with register_tab:
        with st.form("register_form"):
            st.subheader("Registrarse")
            register_email = st.text_input("Email", key="register_email")
            register_password = st.text_input("Contraseña", type="password", key="register_password")
            register_confirm_password = st.text_input("Confirmar Contraseña", type="password", key="register_confirm_password")
            register_submitted = st.form_submit_button("Registrar")

            if register_submitted:
                if not register_email or not register_password or not register_confirm_password:
                    st.warning("Por favor, rellena todos los campos.")
                elif register_password != register_confirm_password:
                    st.error("Las contraseñas no coinciden.")
                else:
                    db: Session | None = None
                    try:
                        db = SessionLocal()
                        existing_user = get_user_by_email(db, email=register_email)
                        if existing_user:
                            st.error("Este email ya está registrado.")
                        else:
                            user_in = UserCreate(email=register_email, password=register_password)
                            new_user = create_user(db=db, user=user_in)
                            st.success(f"¡Usuario {new_user.email} registrado con éxito! Ahora puedes iniciar sesión.")
                            time.sleep(2)
                            # Podrías hacer login automático aquí o simplemente limpiar
                    except Exception as e:
                        st.error(f"Error durante el registro: {e}")
                    finally:
                        if db:
                            db.close()
else:
    st.sidebar.write(f"Conectado como: {st.session_state['user_email']}")
    if st.session_state.get('is_admin', False):
        st.sidebar.markdown("**Rol:** Administrador 🔑")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = None
        st.session_state['user_id'] = None
        st.session_state['is_admin'] = False # <-- Añadir esta línea
        st.success("Sesión cerrada.")
        time.sleep(1)
        st.rerun()

# --- Título Principal --- 
st.title("📚 LibroRecomienda")
st.write("Encuentra y comparte reseñas de tus libros favoritos.")

# --- Catálogo de Libros y Reseñas --- 
try:
    # Cargar libros (usando la función cacheada o directamente)
    # all_books = load_books_from_db() # Si usas la función auxiliar
    db_main = SessionLocal() # Abrir sesión si no usas la función auxiliar
    all_books = db_main.query(Book).order_by(Book.title).all() # Carga directa

    if not all_books:
        st.warning("No hay libros en la base de datos. Ejecuta `scripts/populate_db.py`.")
    else:
        st.header("Catálogo de Libros")
        # Aquí iría tu lógica de filtros y búsqueda si la tienes
        # Ejemplo simple de filtro (si lo implementas)
        # search_term = st.text_input("Buscar libro por título o autor")
        # filtered_books = [book for book in all_books if search_term.lower() in book.title.lower() or (book.author and search_term.lower() in book.author.lower())] if search_term else all_books
        filtered_books = all_books # Sin filtro por ahora

        for book in filtered_books:
            # Usar book.id como parte de la clave del expander para unicidad
            with st.expander(f"{book.title} ({book.author or 'Autor Desconocido'})", key=f"expander_{book.id}"):
                col1, col2 = st.columns([1, 3])
                with col1:
                    if book.cover_image_url:
                        # Añadir manejo de errores para la imagen
                        try:
                            st.image(book.cover_image_url, width=150)
                        except Exception as img_e:
                            st.caption(f"Error cargando portada: {img_e}")
                    else:
                        st.caption("Sin portada")
                with col2:
                    st.subheader(f"{book.title}")
                    st.write(f"**Autor:** {book.author or 'Desconocido'}")
                    # st.write(f"**Año:** {book.publication_year}") # Ya comentado/eliminado
                    # --- Mostrar ISBN si existe --- 
                    if book.isbn:
                        st.write(f"**ISBN:** {book.isbn}")
                    # -------------------------------
                    st.write(f"**Género:** {book.genre or 'Desconocido'}")
                    # Mostrar descripción si existe
                    if book.description:
                        st.caption(f"Descripción: {book.description[:200]}...") # Mostrar solo una parte

                # --- Sección de Reseñas --- 
                st.markdown("#### Reseñas de otros usuarios")
                # Asegurarse de pasar la sesión correcta a las funciones CRUD
                reviews = get_reviews_for_book_with_user(db=db_main, book_id=book.id)
                if reviews:
                    for review_data in reviews:
                        # Usar getattr para acceder a los atributos de forma segura
                        user_email = getattr(review_data, 'user_email', 'Usuario Desconocido')
                        rating = getattr(review_data, 'rating', 0)
                        comment = getattr(review_data, 'comment', 'Sin comentario')
                        created_at = getattr(review_data, 'created_at', None)
                        date_str = created_at.strftime('%Y-%m-%d') if created_at else 'Fecha desconocida'
                        st.markdown(f"**{user_email}** ({'⭐'*rating}): *{comment}* - _{date_str}_ ")
                else:
                    st.caption("Todavía no hay reseñas para este libro.")

                # --- Añadir Reseña (Solo si está logueado) ---
                if st.session_state.get('logged_in', False):
                    st.markdown("#### Añade tu reseña")
                    # Usar book.id en la clave del formulario para unicidad
                    with st.form(key=f"review_form_{book.id}"):
                        rating = st.slider("Puntuación", 1, 5, 3, key=f"rating_{book.id}")
                        comment = st.text_area("Comentario (opcional)", key=f"comment_{book.id}")
                        submit_review = st.form_submit_button("Enviar Reseña")

                        if submit_review:
                            review_in = ReviewCreate(rating=rating, comment=comment)
                            try:
                                # Asegurarse de pasar la sesión correcta
                                create_review(db=db_main, review=review_in, user_id=st.session_state['user_id'], book_id=book.id)
                                st.success("¡Reseña añadida con éxito!")
                                time.sleep(1)
                                # Limpiar cache si usas @st.cache_data en load_books_from_db
                                # load_books_from_db.clear()
                                st.rerun() # Recargar para ver la nueva reseña
                            except Exception as e:
                                st.error(f"Error al añadir la reseña: {e}")
                                # db_main.rollback() # Rollback si es necesario

except Exception as e:
    st.error(f"Error cargando los libros o reseñas: {e}")
    # Asegurarse de cerrar la sesión si se abrió aquí
    if 'db_main' in locals() and db_main:
        db_main.close()
finally:
    # Asegurarse de cerrar la sesión si se abrió en el bloque try principal
    if 'db_main' in locals() and db_main:
        db_main.close()


# --- Sección de Administración (Solo visible para admins) ---
if st.session_state.get('is_admin', False):
    st.divider()
    st.header("🔑 Panel de Administración")
    st.subheader("Lista de Usuarios")

    admin_db: Session | None = None
    try:
        admin_db = SessionLocal()
        # Obtener la lista de usuarios usando la nueva función CRUD
        # Podríamos añadir paginación aquí más adelante
        all_users_data = get_users(db=admin_db, limit=200) # Obtener hasta 200 usuarios

        if all_users_data:
            # Crear un DataFrame de Pandas para mostrar en tabla
            # Usamos los nombres de columna que seleccionamos en get_users
            # Asegúrate de que pandas está instalado: uv pip install pandas
            try:
                import pandas as pd
                df_users = pd.DataFrame(all_users_data, columns=['ID', 'Email', 'Activo', 'Creado', 'Actualizado'])
                st.dataframe(df_users, use_container_width=True)
            except ImportError:
                st.error("La librería 'pandas' no está instalada. Por favor, ejecute `uv pip install pandas`.")
                st.write("Datos de usuarios (sin formato tabla):")
                st.write(all_users_data) # Mostrar datos crudos si pandas no está
        else:
            st.warning("No se encontraron usuarios.")

    except Exception as e:
        st.error(f"Error cargando la lista de usuarios: {e}")
    finally:
        if admin_db:
            admin_db.close()

# --- Pie de página (opcional) ---
st.divider()
st.caption("LibroRecomienda - 2025")