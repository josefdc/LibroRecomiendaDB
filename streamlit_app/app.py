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
# ...

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
# ... (código existente para mostrar libros, filtros, etc.) ...

# Ejemplo de cómo podría ser la sección de mostrar libros (simplificado)
db_main: Session | None = None
try:
    db_main = SessionLocal()
    books = db_main.query(Book).order_by(Book.title).all()

    if not books:
        st.warning("No hay libros en la base de datos. Ejecuta `scripts/populate_db.py`.")
    else:
        st.header("Catálogo de Libros")
        # Aquí iría tu lógica de filtros y búsqueda si la tienes

        for book in books:
            with st.expander(f"{book.title} ({book.author})"):
                col1, col2 = st.columns([1, 3])
                with col1:
                    if book.cover_image_url:
                        st.image(book.cover_image_url, width=150)
                    else:
                        st.caption("Sin portada")
                with col2:
                    st.subheader(f"{book.title}")
                    st.write(f"**Autor:** {book.author}")
                    st.write(f"**ISBN:** {book.isbn}")
                    st.write(f"**Género:** {book.genre}")

                # --- Sección de Reseñas --- 
                st.markdown("#### Reseñas de otros usuarios")
                reviews = get_reviews_for_book_with_user(db=db_main, book_id=book.id)
                if reviews:
                    for review_data in reviews:
                        st.markdown(f"**{review_data.user_email}** ({'⭐'*review_data.rating}): *{review_data.comment or 'Sin comentario'}* - _{review_data.created_at.strftime('%Y-%m-%d')}_ ")
                else:
                    st.caption("Todavía no hay reseñas para este libro.")

                # --- Añadir Reseña (Solo si está logueado) ---
                if st.session_state.get('logged_in', False):
                    st.markdown("#### Añade tu reseña")
                    with st.form(key=f"review_form_{book.id}"):
                        rating = st.slider("Puntuación", 1, 5, 3, key=f"rating_{book.id}")
                        comment = st.text_area("Comentario (opcional)", key=f"comment_{book.id}")
                        submit_review = st.form_submit_button("Enviar Reseña")

                        if submit_review:
                            review_in = ReviewCreate(rating=rating, comment=comment)
                            try:
                                create_review(db=db_main, review=review_in, user_id=st.session_state['user_id'], book_id=book.id)
                                st.success("¡Reseña añadida con éxito!")
                                time.sleep(1)
                                st.rerun() # Recargar para ver la nueva reseña
                            except Exception as e:
                                st.error(f"Error al añadir la reseña: {e}")
                                # Podrías querer hacer rollback aquí si create_review no lo maneja
                                # db_main.rollback()

except Exception as e:
    st.error(f"Error cargando los libros o reseñas: {e}")
finally:
    if db_main:
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