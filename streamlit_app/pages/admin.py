"""
Admin panel for LibroRecomienda Streamlit app.

This module provides administrative views for user and review management.
It includes authorization checks, user listing with search/sort, and review
management (restore, permanent delete) with filtering and confirmation dialogs.

Intended for use by administrators only.
"""

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from librorecomienda.db.session import SessionLocal
    from librorecomienda.crud import (
        get_users,
        get_all_reviews_admin,
        restore_review,
        permanently_delete_review
    )
except ImportError:
    project_root: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
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


def is_admin_logged_in() -> bool:
    """
    Checks if the current session is logged in as an administrator.

    Returns:
        bool: True if logged in and is admin, False otherwise.
    """
    return st.session_state.get('logged_in', False) and st.session_state.get('is_admin', False)


if not is_admin_logged_in():
    st.error("🚫 Access Denied. You must be logged in as an administrator to view this page.")
    st.stop()

st.title("🔑 Admin Panel")

admin_option: str = st.radio(
    "Select View:",
    ["User Management", "Review Management"],
    key="admin_view_selector"
)

st.divider()


def fetch_and_prepare_users(db: Session) -> List[Dict[str, Any]]:
    """
    Fetches users from the database and prepares them for display.

    Args:
        db (Session): SQLAlchemy session.

    Returns:
        List[Dict[str, Any]]: List of user dictionaries with keys:
            'ID', 'Email', 'Active', 'Created', 'Updated'.
    """
    users_data = get_users(db)
    users_list: List[Dict[str, Any]] = []
    if users_data:
        users_list = [
            {"ID": u[0], "Email": u[1], "Active": u[2], "Created": u[3], "Updated": u[4]}
            for u in users_data if isinstance(u[3], datetime)
        ]
        users_list.extend([
            {"ID": u[0], "Email": u[1], "Active": u[2], "Created": datetime.min, "Updated": u[4]}
            for u in users_data if not isinstance(u[3], datetime)
        ])
    return users_list


def filter_and_sort_users(
    users: List[Dict[str, Any]],
    search_term: str,
    sort_option: str
) -> List[Dict[str, Any]]:
    """
    Filters and sorts the user list based on search term and sort option.

    Args:
        users (List[Dict[str, Any]]): List of user dictionaries.
        search_term (str): Search term for email.
        sort_option (str): Sorting option selected.

    Returns:
        List[Dict[str, Any]]: Filtered and sorted user list.
    """
    filtered_users = [u for u in users if search_term in u['Email'].lower()] if search_term else users
    reverse_sort = False
    sort_key = lambda u: u['ID']
    if sort_option == 'ID (Desc)':
        reverse_sort = True
    elif sort_option == 'Email (A-Z)':
        sort_key = lambda u: u['Email']
    elif sort_option == 'Email (Z-A)':
        sort_key = lambda u: u['Email']
        reverse_sort = True
    elif sort_option == 'Creación (Nuevos primero)':
        sort_key = lambda u: u['Created']
        reverse_sort = True
    elif sort_option == 'Creación (Antiguos primero)':
        sort_key = lambda u: u['Created']
    try:
        return sorted(filtered_users, key=sort_key, reverse=reverse_sort)
    except Exception as sort_e:
        st.error(f"Error al ordenar usuarios: {sort_e}")
        return filtered_users


def fetch_and_prepare_reviews(db: Session) -> List[Dict[str, Any]]:
    """
    Fetches all reviews for admin and prepares them for display.

    Args:
        db (Session): SQLAlchemy session.

    Returns:
        List[Dict[str, Any]]: List of review dictionaries.
    """
    reviews_admin_data = get_all_reviews_admin(db)
    all_reviews_list: List[Dict[str, Any]] = []
    if reviews_admin_data:
        for review, user_email, book_title in reviews_admin_data:
            all_reviews_list.append({
                "ID Reseña": review.id,
                "Libro": book_title or "N/A",
                "Usuario": user_email or "N/A",
                "Puntuación": review.rating if review.rating is not None else 0,
                "Comentario": review.comment or "",
                "Fecha": review.created_at if isinstance(review.created_at, datetime) else datetime.min,
                "is_deleted_flag": review.is_deleted,
                "Estado": "BORRADO" if review.is_deleted else "Activo",
            })
    return all_reviews_list


def filter_and_sort_reviews(
    reviews: List[Dict[str, Any]],
    search_term: str,
    filter_option: str,
    sort_option: str
) -> List[Dict[str, Any]]:
    """
    Filters and sorts the review list based on search, status, and sort options.

    Args:
        reviews (List[Dict[str, Any]]): List of review dictionaries.
        search_term (str): Search term for book, user, or comment.
        filter_option (str): Status filter ("Todas", "Solo Activas", "Solo Borradas").
        sort_option (str): Sorting option selected.

    Returns:
        List[Dict[str, Any]]: Filtered and sorted review list.
    """
    if search_term:
        reviews = [
            r for r in reviews if
            search_term in r['Libro'].lower() or
            search_term in r['Usuario'].lower() or
            search_term in r['Comentario'].lower()
        ]
    if filter_option == "Solo Activas":
        reviews = [r for r in reviews if not r["is_deleted_flag"]]
    elif filter_option == "Solo Borradas":
        reviews = [r for r in reviews if r["is_deleted_flag"]]
    reverse_sort = True
    sort_key = lambda r: r['Fecha']
    if sort_option == 'Fecha (Antiguas primero)':
        reverse_sort = False
    elif sort_option == 'Puntuación (Alta primero)':
        sort_key = lambda r: r['Puntuación']
        reverse_sort = True
    elif sort_option == 'Puntuación (Baja primero)':
        sort_key = lambda r: r['Puntuación']
        reverse_sort = False
    elif sort_option == 'Libro (A-Z)':
        sort_key = lambda r: r['Libro']
        reverse_sort = False
    elif sort_option == 'Usuario (A-Z)':
        sort_key = lambda r: r['Usuario']
        reverse_sort = False
    try:
        return sorted(reviews, key=sort_key, reverse=reverse_sort)
    except Exception as sort_e:
        st.error(f"Error al ordenar reseñas: {sort_e}")
        return reviews


db_admin: Optional[Session] = None
try:
    db_admin = SessionLocal()

    if admin_option == "User Management":
        st.subheader("User Management")

        col_search, col_sort = st.columns([2, 1])
        with col_search:
            search_user_term: str = st.text_input("Buscar por Email:", key="user_search").lower()
        with col_sort:
            sort_user_option: str = st.selectbox(
                "Ordenar por:",
                ('ID (Asc)', 'ID (Desc)', 'Email (A-Z)', 'Email (Z-A)', 'Creación (Nuevos primero)', 'Creación (Antiguos primero)'),
                key='user_sort'
            )

        users_list = fetch_and_prepare_users(db_admin)

        if users_list:
            sorted_users_list = filter_and_sort_users(users_list, search_user_term, sort_user_option)
            st.markdown(f"**{len(sorted_users_list)} Usuario(s) encontrado(s)**")
            try:
                df_users = pd.DataFrame(sorted_users_list)
                display_cols = ['ID', 'Email', 'Active', 'Created', 'Updated']
                if 'Created' in df_users.columns:
                    df_users['Created'] = df_users['Created'].apply(lambda x: x if x != datetime.min else None)
                st.dataframe(df_users[display_cols], use_container_width=True)
            except ImportError:
                st.error("Pandas not installed.")
                st.write(sorted_users_list)
        else:
            st.info("No registered users found.")

    elif admin_option == "Review Management":
        st.subheader("Review Management")

        filter_option: str = st.radio(
            "Mostrar reseñas:",
            ("Todas", "Solo Activas", "Solo Borradas"),
            key="review_filter",
            horizontal=True,
        )

        col_search_rev, col_sort_rev = st.columns([2, 1])
        with col_search_rev:
            search_review_term: str = st.text_input("Buscar en Libro, Usuario o Comentario:", key="review_search").lower()
        with col_sort_rev:
            sort_review_option: str = st.selectbox(
                "Ordenar por:",
                ('Fecha (Nuevas primero)', 'Fecha (Antiguas primero)', 'Puntuación (Alta primero)', 'Puntuación (Baja primero)', 'Libro (A-Z)', 'Usuario (A-Z)'),
                key='review_sort'
            )

        if 'confirming_delete_review_id' not in st.session_state:
            st.session_state.confirming_delete_review_id = None

        reviews_list = fetch_and_prepare_reviews(db_admin)
        if reviews_list:
            reviews_to_display = filter_and_sort_reviews(
                reviews_list,
                search_review_term,
                filter_option,
                sort_review_option
            )
            st.markdown(f"--- **{len(reviews_to_display)} Reseña(s) Encontrada(s)** ---")
            if not reviews_to_display:
                st.info(f"No hay reseñas que coincidan con los filtros seleccionados.")
            else:
                for review_data in reviews_to_display:
                    review_id: int = review_data["ID Reseña"]
                    is_deleted: bool = review_data["is_deleted_flag"]
                    display_date: str = review_data['Fecha'].strftime('%Y-%m-%d %H:%M') if review_data['Fecha'] != datetime.min else 'N/A'

                    with st.container(border=True):
                        col_info, col_actions = st.columns([4, 1])

                        with col_info:
                            st.markdown(f"**ID:** {review_id} | **Libro:** {review_data['Libro']} | **Usuario:** {review_data['Usuario']}")
                            rating_stars: str = '⭐' * review_data['Puntuación'] if review_data['Puntuación'] else 'N/A'
                            st.markdown(f"**Rating:** {rating_stars} ({review_data['Puntuación']}) | **Fecha:** {display_date} | **Estado:** {review_data['Estado']}")
                            if review_data['Comentario']:
                                with st.expander("Ver Comentario"):
                                    st.caption(review_data['Comentario'])
                            elif review_data['Comentario'] == "":
                                st.caption("Comentario: (Vacío)")

                        with col_actions:
                            if is_deleted:
                                if st.button("♻️ Restaurar", key=f"restore_{review_id}", help="Marcar como activa."):
                                    success = restore_review(db=db_admin, review_id=review_id)
                                    if success:
                                        st.success(f"Reseña {review_id} restaurada.")
                                        st.rerun()
                                    else:
                                        st.error(f"Error al restaurar {review_id}.")
                            else:
                                st.write("")

                            delete_key = f"delete_{review_id}"
                            confirm_key = f"confirm_delete_{review_id}"
                            cancel_key = f"cancel_delete_{review_id}"

                            if st.session_state.confirming_delete_review_id == review_id:
                                st.warning("¿Seguro?")
                                confirm_cols = st.columns(2)
                                if confirm_cols[0].button("✅ Sí", key=confirm_key, help="Eliminar permanentemente."):
                                    success = permanently_delete_review(db=db_admin, review_id=review_id)
                                    st.session_state.confirming_delete_review_id = None
                                    if success:
                                        st.success(f"Reseña {review_id} eliminada.")
                                        st.rerun()
                                    else:
                                        st.error(f"Error al eliminar {review_id}.")
                                        st.rerun()
                                if confirm_cols[1].button("❌ No", key=cancel_key):
                                    st.session_state.confirming_delete_review_id = None
                                    st.rerun()
                            else:
                                if st.button("🗑️🔥 Borrar", key=delete_key, help="Eliminar permanentemente."):
                                    st.session_state.confirming_delete_review_id = review_id
                                    st.rerun()
        else:
            st.info("No hay reseñas en la base de datos.")

except Exception as admin_e:
    st.error(f"An error occurred in the admin panel: {admin_e}")
finally:
    if db_admin:
        db_admin.close()
