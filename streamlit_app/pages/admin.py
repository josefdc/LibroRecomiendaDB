# streamlit_app/pages/admin.py

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
import sys
import os
from datetime import datetime # Import datetime

# --- Attempt to import project modules ---
# This handles running streamlit from the project root ('LibroRecomienda/')
# or potentially directly from 'streamlit_app/' after adjusting path.
try:
    from librorecomienda.db.session import SessionLocal
    from librorecomienda.crud import (
        get_users,
        get_all_reviews_admin,
        restore_review,
        permanently_delete_review
    )
except ImportError:
    # If running streamlit from 'streamlit_app/', adjust the path
    # Add the project root directory ('LibroRecomienda/') to the Python path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    try:
        from librorecomienda.db.session import SessionLocal
        from librorecomienda.crud import (
            get_users,
            get_all_reviews_admin,
            restore_review,
            permanently_delete_review
        )
    except ImportError as e:
        st.error(f"Failed to import project modules in admin.py. Error: {e}")
        st.stop()


# --- Authorization Check ---
# Verify if the user is logged in AND is an administrator
# This relies on session_state being set correctly in the main app.py
if not st.session_state.get('logged_in', False) or not st.session_state.get('is_admin', False):
    st.error("🚫 Access Denied. You must be logged in as an administrator to view this page.")
    st.stop()

# --- End Authorization Check ---

st.title("🔑 Admin Panel")

admin_option = st.radio(
    "Select View:",
    ["User Management", "Review Management"],
    key="admin_view_selector"
)

st.divider()

# --- Logic to display the selected admin view ---
db_admin: Session | None = None
try:
    db_admin = SessionLocal()

    if admin_option == "User Management":
        st.subheader("User Management")

        # --- Widgets de Búsqueda y Ordenamiento ---
        col_search, col_sort = st.columns([2, 1])
        with col_search:
            search_user_term = st.text_input("Buscar por Email:", key="user_search").lower()
        with col_sort:
            sort_user_option = st.selectbox(
                "Ordenar por:",
                ('ID (Asc)', 'ID (Desc)', 'Email (A-Z)', 'Email (Z-A)', 'Creación (Nuevos primero)', 'Creación (Antiguos primero)'),
                key='user_sort'
            )
        # --- Fin Widgets ---

        users_data = get_users(db_admin) # Obtener todos los usuarios

        if users_data:
            # Convertir a lista de diccionarios
            # Assuming get_users returns tuples (id, email, is_active, created_at, updated_at)
            users_list = [
                {"ID": u[0], "Email": u[1], "Active": u[2], "Created": u[3], "Updated": u[4]}
                for u in users_data if isinstance(u[3], datetime) # Ensure 'Created' is datetime
            ]
            # Handle cases where 'Created' might be None or not datetime
            users_list.extend([
                {"ID": u[0], "Email": u[1], "Active": u[2], "Created": datetime.min, "Updated": u[4]}
                for u in users_data if not isinstance(u[3], datetime)
            ])


            # --- Aplicar Filtro de Búsqueda ---
            if search_user_term:
                users_list = [u for u in users_list if search_user_term in u['Email'].lower()]

            # --- Aplicar Ordenamiento ---
            reverse_sort = False
            sort_key_lambda = lambda u: u['ID'] # Default sort key

            if sort_user_option == 'ID (Desc)':
                reverse_sort = True
            elif sort_user_option == 'Email (A-Z)':
                 sort_key_lambda = lambda u: u['Email']
            elif sort_user_option == 'Email (Z-A)':
                 sort_key_lambda = lambda u: u['Email']
                 reverse_sort = True
            elif sort_user_option == 'Creación (Nuevos primero)':
                 sort_key_lambda = lambda u: u['Created']
                 reverse_sort = True
            elif sort_user_option == 'Creación (Antiguos primero)':
                 sort_key_lambda = lambda u: u['Created']

            try:
                 sorted_users_list = sorted(users_list, key=sort_key_lambda, reverse=reverse_sort)
            except Exception as sort_e:
                 st.error(f"Error al ordenar usuarios: {sort_e}")
                 sorted_users_list = users_list # Mostrar sin ordenar en caso de error

            # --- Mostrar DataFrame Filtrado y Ordenado ---
            if sorted_users_list:
                st.markdown(f"**{len(sorted_users_list)} Usuario(s) encontrado(s)**")
                try:
                    df_users = pd.DataFrame(sorted_users_list)
                    # Display relevant columns, handle potential missing 'Created' if needed
                    display_cols = ['ID', 'Email', 'Active', 'Created', 'Updated']
                    # Ensure 'Created' column is formatted nicely if it exists and contains datetimes
                    if 'Created' in df_users.columns:
                         # Convert min datetime back to None or 'N/A' for display if needed
                         df_users['Created'] = df_users['Created'].apply(lambda x: x if x != datetime.min else None)
                         # Optional: Format datetime
                         # df_users['Created'] = pd.to_datetime(df_users['Created']).dt.strftime('%Y-%m-%d %H:%M')

                    st.dataframe(df_users[display_cols], use_container_width=True)
                except ImportError:
                    st.error("Pandas not installed.")
                    st.write(sorted_users_list)
            else:
                st.info("No se encontraron usuarios que coincidan con la búsqueda.")
        else:
            st.info("No registered users found.")


    elif admin_option == "Review Management":
        st.subheader("Review Management")

        # Filtro de Estado (existente)
        filter_option = st.radio(
            "Mostrar reseñas:",
            ("Todas", "Solo Activas", "Solo Borradas"),
            key="review_filter",
            horizontal=True,
        )

        # --- Widgets de Búsqueda y Ordenamiento ---
        col_search_rev, col_sort_rev = st.columns([2, 1])
        with col_search_rev:
             search_review_term = st.text_input("Buscar en Libro, Usuario o Comentario:", key="review_search").lower()
        with col_sort_rev:
             sort_review_option = st.selectbox(
                 "Ordenar por:",
                 ('Fecha (Nuevas primero)', 'Fecha (Antiguas primero)', 'Puntuación (Alta primero)', 'Puntuación (Baja primero)', 'Libro (A-Z)', 'Usuario (A-Z)'),
                 key='review_sort'
             )
        # --- Fin Widgets ---

        # --- Confirmation State Handling (existente) ---
        if 'confirming_delete_review_id' not in st.session_state:
            st.session_state.confirming_delete_review_id = None

        # --- Obtener y Preparar Datos ---
        reviews_admin_data = get_all_reviews_admin(db_admin)
        if reviews_admin_data:
            all_reviews_list = []
            for review, user_email, book_title in reviews_admin_data:
                 all_reviews_list.append({
                      "ID Reseña": review.id,
                      "Libro": book_title or "N/A", # Handle potential None
                      "Usuario": user_email or "N/A", # Handle potential None
                      "Puntuación": review.rating if review.rating is not None else 0, # Handle None rating for sorting
                      "Comentario": review.comment or "", # Ensure string
                      "Fecha": review.created_at if isinstance(review.created_at, datetime) else datetime.min, # Use min datetime for None dates for sorting
                      "is_deleted_flag": review.is_deleted,
                      "Estado": "BORRADO" if review.is_deleted else "Activo",
                 })

            # --- Aplicar Filtro de Búsqueda ---
            if search_review_term:
                reviews_after_search = [
                    r for r in all_reviews_list if
                    search_review_term in r['Libro'].lower() or
                    search_review_term in r['Usuario'].lower() or
                    search_review_term in r['Comentario'].lower()
                ]
            else:
                reviews_after_search = all_reviews_list

            # --- Aplicar Filtro de Estado ---
            if filter_option == "Solo Activas":
                reviews_after_status_filter = [r for r in reviews_after_search if not r["is_deleted_flag"]]
            elif filter_option == "Solo Borradas":
                reviews_after_status_filter = [r for r in reviews_after_search if r["is_deleted_flag"]]
            else: # "Todas"
                reviews_after_status_filter = reviews_after_search

            # --- Aplicar Ordenamiento ---
            reverse_sort_rev = True # Default: Nuevas primero
            sort_key_rev_lambda = lambda r: r['Fecha'] # Default sort key (datetime object)

            if sort_review_option == 'Fecha (Antiguas primero)':
                 reverse_sort_rev = False
            elif sort_review_option == 'Puntuación (Alta primero)':
                 sort_key_rev_lambda = lambda r: r['Puntuación']
                 reverse_sort_rev = True
            elif sort_review_option == 'Puntuación (Baja primero)':
                 sort_key_rev_lambda = lambda r: r['Puntuación']
                 reverse_sort_rev = False
            elif sort_review_option == 'Libro (A-Z)':
                 sort_key_rev_lambda = lambda r: r['Libro']
                 reverse_sort_rev = False
            elif sort_review_option == 'Usuario (A-Z)':
                 sort_key_rev_lambda = lambda r: r['Usuario']
                 reverse_sort_rev = False

            try:
                 reviews_to_display = sorted(reviews_after_status_filter, key=sort_key_rev_lambda, reverse=reverse_sort_rev)
            except Exception as sort_e:
                 st.error(f"Error al ordenar reseñas: {sort_e}")
                 reviews_to_display = reviews_after_status_filter

            # --- Nuevo Layout de Visualización ---
            st.markdown(f"--- **{len(reviews_to_display)} Reseña(s) Encontrada(s)** ---")

            if not reviews_to_display:
                 st.info(f"No hay reseñas que coincidan con los filtros seleccionados.")
            else:
                 for review_data in reviews_to_display:
                      review_id = review_data["ID Reseña"]
                      is_deleted = review_data["is_deleted_flag"]
                      display_date = review_data['Fecha'].strftime('%Y-%m-%d %H:%M') if review_data['Fecha'] != datetime.min else 'N/A'

                      # Usar un contenedor para cada reseña
                      with st.container(border=True): # Add border for visual separation
                           col_info, col_actions = st.columns([4, 1]) # Adjust ratio as needed

                           with col_info:
                                st.markdown(f"**ID:** {review_id} | **Libro:** {review_data['Libro']} | **Usuario:** {review_data['Usuario']}")
                                # Display stars for rating
                                rating_stars = '⭐' * review_data['Puntuación'] if review_data['Puntuación'] else 'N/A'
                                st.markdown(f"**Rating:** {rating_stars} ({review_data['Puntuación']}) | **Fecha:** {display_date} | **Estado:** {review_data['Estado']}")
                                if review_data['Comentario']:
                                     # Use st.expander for potentially long comments
                                     with st.expander("Ver Comentario"):
                                          st.caption(review_data['Comentario'])
                                elif review_data['Comentario'] == "": # Explicitly check for empty string if needed
                                     st.caption("Comentario: (Vacío)")


                           with col_actions:
                                # Botón Restaurar
                                if is_deleted:
                                     if st.button("♻️ Restaurar", key=f"restore_{review_id}", help="Marcar como activa."):
                                         success = restore_review(db=db_admin, review_id=review_id)
                                         if success: st.success(f"Reseña {review_id} restaurada."); st.rerun()
                                         else: st.error(f"Error al restaurar {review_id}.")
                                else:
                                     st.write("") # Placeholder

                                # Botón Eliminar y Confirmación
                                delete_key = f"delete_{review_id}"
                                confirm_key = f"confirm_delete_{review_id}"
                                cancel_key = f"cancel_delete_{review_id}"

                                if st.session_state.confirming_delete_review_id == review_id:
                                     st.warning("¿Seguro?")
                                     confirm_cols = st.columns(2)
                                     if confirm_cols[0].button("✅ Sí", key=confirm_key, help="Eliminar permanentemente."):
                                         success = permanently_delete_review(db=db_admin, review_id=review_id)
                                         st.session_state.confirming_delete_review_id = None
                                         if success: st.success(f"Reseña {review_id} eliminada."); st.rerun()
                                         else: st.error(f"Error al eliminar {review_id}."); st.rerun()
                                     if confirm_cols[1].button("❌ No", key=cancel_key):
                                         st.session_state.confirming_delete_review_id = None
                                         st.rerun()
                                else:
                                     if st.button("🗑️🔥 Borrar", key=delete_key, help="Eliminar permanentemente."):
                                         st.session_state.confirming_delete_review_id = review_id
                                         st.rerun()
                           # Removed the st.divider() inside the loop when using border=True

        else: # Si no hay reseñas en la base de datos
             st.info("No hay reseñas en la base de datos.")

except Exception as admin_e:
    st.error(f"An error occurred in the admin panel: {admin_e}")
    # Consider logging the full traceback here for debugging
finally:
    if db_admin:
        db_admin.close()
