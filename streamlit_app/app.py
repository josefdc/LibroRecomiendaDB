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
from librorecomienda.crud import (
    create_user,
    get_user_by_email,
    create_review,
    get_reviews_for_book_with_user,
    get_users,
    soft_delete_review,
    get_all_reviews_admin, # <-- Import get_all_reviews_admin
)
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
            # Se elimina el argumento 'key' para compatibilidad con versiones anteriores de Streamlit
            with st.expander(f"{book.title} ({book.author or 'Autor Desconocido'})"):
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
                # Use the updated function that returns Row objects (Review, User.email)
                reviews_data = get_reviews_for_book_with_user(db=db_main, book_id=book.id)
                if reviews_data:
                    # reviews_data is a list of Row objects, access attributes by name
                    for review_row in reviews_data:
                        review = review_row.Review # Access the Review object
                        user_email = review_row.email # Access the user's email

                        # Display review details
                        st.markdown(f"**{user_email or 'Usuario Desconocido'}** ({'⭐'*review.rating}):")
                        if review.comment:
                            st.markdown(f"> *{review.comment}*")
                        st.caption(f"_{review.created_at.strftime('%Y-%m-%d %H:%M') if review.created_at else 'Fecha desconocida'}_")

                        # --- Botón Borrar (si es mi reseña y estoy logueado) ---
                        # Compara el user_id de la reseña con el user_id en session_state
                        if st.session_state.get('logged_in', False) and review.user_id == st.session_state.get('user_id'):
                            # Usamos un key único para cada botón de borrar
                            if st.button("🗑️ Borrar mi reseña", key=f"delete_review_{review.id}", type="secondary"):
                                # Optional: Add a confirmation step if desired
                                # st.warning("¿Estás seguro?")
                                # if st.button("Confirmar Borrado", key=f"confirm_delete_{review.id}"):
                                delete_db: Session | None = None
                                try:
                                    delete_db = SessionLocal()
                                    # Llamar a la función CRUD de borrado lógico
                                    success = soft_delete_review(
                                        db=delete_db,
                                        review_id=review.id, # Pasar el ID de la reseña actual
                                        requesting_user_id=st.session_state['user_id']
                                    )
                                    if success:
                                        st.toast("Reseña borrada.", icon="🗑️")
                                        # Limpiar caché si usas @st.cache_data en load_books_from_db
                                        # O simplemente limpiar la caché general de datos si afecta a las reseñas
                                        st.cache_data.clear()
                                        time.sleep(1) # Pausa para ver el toast
                                        st.rerun() # Refrescar la página
                                    else:
                                        # Podría ser que no se encontró o no tenía permiso (soft_delete_review ya loguea el error)
                                        st.warning("No se pudo borrar la reseña (quizás ya estaba borrada o hubo un problema).")
                                except Exception as e_del:
                                    st.error(f"Error al intentar borrar: {e_del}")
                                finally:
                                    if delete_db:
                                        delete_db.close()
                        st.markdown("---") # Separator between reviews
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
if st.session_state.get('is_admin'):
    st.sidebar.divider()
    st.sidebar.header("Panel de Administración")
    admin_option = st.sidebar.radio("Selecciona una vista:", ["Gestión de Usuarios", "Gestión de Reseñas"], key="admin_view")

    with db:
        if admin_option == "Gestión de Usuarios":
            st.subheader("Gestión de Usuarios")
            users_data = get_users(db) # Use directly
            if users_data:
                # Crear un DataFrame de Pandas para mostrar en tabla
                # Usamos los nombres de columna que seleccionamos en get_users
                # Asegúrate de que pandas está instalado: uv pip install pandas
                try:
                    import pandas as pd
                    df_users = pd.DataFrame(users_data, columns=['ID', 'Email', 'Activo', 'Creado', 'Actualizado'])
                    st.dataframe(df_users, use_container_width=True)
                except ImportError:
                    st.error("La librería 'pandas' no está instalada. Por favor, ejecute `uv pip install pandas`.")
                    st.write("Datos de usuarios (sin formato tabla):")
                    st.write(users_data) # Mostrar datos crudos si pandas no está
            else:
                st.write("No hay usuarios registrados.")

        elif admin_option == "Gestión de Reseñas": # <-- Use elif
            st.subheader("Gestión de Reseñas")
            reviews_admin_data = get_all_reviews_admin(db) # Use directly
            if reviews_admin_data:
                reviews_list = []
                for review, user_email, book_title in reviews_admin_data:
                    reviews_list.append(
                        {
                            "ID Reseña": review.id,
                            "Libro": book_title,
                            "Usuario": user_email,
                            "Puntuación": review.rating,
                            "Comentario": review.comment,
                            "Fecha": review.created_at.strftime("%Y-%m-%d %H:%M"),
                            "Estado": "BORRADO" if review.is_deleted else "Activo",
                        }
                    )
                reviews_df = pd.DataFrame(reviews_list)
                st.dataframe(reviews_df, use_container_width=True)
            else:
                st.write("No hay reseñas para mostrar.")

# --- Fin Panel de Administración ---

st.divider()