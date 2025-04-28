# LibroRecomienda 📚🤖

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

**Proyecto Final - Bases De Datos**
**Autor:** Jose Felipe Duarte
**Fecha:** April 27, 2025

---

## Descripción General

LibroRecomienda es una aplicación web interactiva diseñada como proyecto final. Su objetivo es proporcionar a los usuarios recomendaciones de libros personalizadas y explicables a través de una interfaz conversacional impulsada por un agente inteligente construido con LangGraph y modelos de lenguaje grande (LLMs). La aplicación permite explorar un catálogo de libros, leer y añadir reseñas, y dialogar con el agente para refinar las sugerencias.

El proyecto demuestra la integración de tecnologías modernas como Streamlit para la interfaz, SQLAlchemy y Alembic para la gestión de la base de datos (compatible con PostgreSQL y SQLite), y Langchain/LangGraph para la orquestación del agente conversacional.

![Screenshot from 2025-04-27 21-40-19](https://github.com/user-attachments/assets/91f35090-d280-4768-bdc3-edc46423e341)


---

## Características Principales Implementadas

* **Catálogo de Libros:**
  * Visualización del catálogo completo en `streamlit_app/app.py`.
  * Vista detallada de cada libro (imagen, autor, género, ISBN, descripción, rating promedio).
  * Filtros y opciones de ordenamiento en la vista principal.
* **Gestión de Usuarios:**
  * Registro de nuevos usuarios (`crud_user.py`, `streamlit_app/app.py`).
  * Autenticación (Login/Logout) (`streamlit_app/app.py`).
  * Distinción de roles (Usuario / Administrador) basada en `ADMIN_EMAILS` en `config.py`.
* **Gestión de Reseñas:**
  * Los usuarios logueados pueden añadir reseñas (puntuación + comentario) a los libros (`crud_review.py`, `streamlit_app/app.py`).
  * Visualización de reseñas existentes para cada libro (excluyendo las borradas lógicamente) (`crud_review.py`).
  * Los usuarios pueden borrar (lógicamente) sus propias reseñas (`crud_review.py`, `streamlit_app/app.py`).
  * Cálculo y actualización automática del rating promedio del libro al añadir/modificar/borrar reseñas (`crud_review.py`).
* **Panel de Administración (Página Dedicada):** (`streamlit_app/pages/admin.py`)
  * Acceso restringido a usuarios administradores.
  * Vista para gestionar usuarios (listar usuarios registrados) (`crud_user.py`).
  * Vista para gestionar reseñas (`crud_review.py`):
    * Listar *todas* las reseñas (incluyendo activas y borradas).
    * Filtrar reseñas por estado (Activas, Borradas).
    * Opción para restaurar reseñas borradas lógicamente.
    * Opción para eliminar reseñas permanentemente (con confirmación).
* **Agente Conversacional (LangGraph):** (`streamlit_app/pages/chat.py`, `src/librorecomienda/agents/`)
  * Interfaz de chat dedicada.
  * Mantenimiento de memoria conversacional por sesión (`MemorySaver` en `graph.py`).
  * Capacidad de llamar a herramientas para interactuar con la base de datos (`search_books`, `get_book_details` en `tools.py`).
  * Generación de recomendaciones basada en la conversación.
  * Flujo conversacional básico gestionado por LangGraph (`graph.py`).

---

## Diagrama Entidad-Relación (ERD)

A continuación se muestra el modelo conceptual de la base de datos utilizada en el proyecto.

**Descripción de Entidades y Relaciones:**

* **User:** (`users` table in `models/user.py`)
  * `id` [PK]: Identificador único del usuario.
  * `email` [Unique]: Dirección de correo electrónico (usada para login).
  * `hashed_password`: Contraseña almacenada de forma segura.
  * `is_active`: Indicador de si la cuenta está activa (default: True).
  * `created_at`, `updated_at`: Marcas de tiempo automáticas.
* **Book:** (`books` table in `models/book.py`)
  * `id` [PK]: Identificador único del libro.
  * `title`: Título del libro.
  * `author`: Autor del libro.
  * `genre`: Género principal.
  * `description`: Sinopsis o descripción.
  * `average_rating`: Puntuación promedio calculada de las reseñas.
  * `cover_image_url`: URL de la imagen de portada.
  * `isbn` [Unique]: ISBN del libro.
* **Review:** (`reviews` table in `models/review.py`)
  * `id` [PK]: Identificador único de la reseña.
  * `rating`: Puntuación dada por el usuario (1-5).
  * `comment`: Comentario opcional.
  * `created_at`: Fecha y hora de creación.
  * `is_deleted`: Indicador de borrado lógico (default: False).
  * `user_id` [FK -> User.id]: Usuario que escribió la reseña.
  * `book_id` [FK -> Book.id]: Libro al que pertenece la reseña.
* **Relaciones:**
  * Un `User` puede escribir muchas `Review`s (1-N).
  * Un `Book` puede tener muchas `Review`s (1-N).
  * Una `Review` pertenece exactamente a un `User` y a un `Book`.

![graphviz](https://github.com/user-attachments/assets/5691b998-786f-485a-804c-e4e49b74c20e)

---

## Tecnologías Utilizadas

* **Backend & ORM:** Python 3.11+, SQLAlchemy 2.x
* **Migraciones DB:** Alembic
* **Base de Datos:** PostgreSQL (recomendado) / SQLite (para desarrollo/pruebas)
* **Framework Web UI:** Streamlit
* **Agente IA:** Langchain, LangGraph
* **Modelos LLM:** OpenAI GPT-4o-mini (configurable vía `ChatOpenAI` en `graph.py`)
* **Validación de Datos:** Pydantic v2
* **Gestión de Dependencias:** uv (basado en `pyproject.toml`)
* **Testing:** Pytest
* **Generación de Datos Falsos:** Faker (`scripts/generate_fake_data.py`)
* **Variables de Entorno:** python-dotenv, Pydantic-Settings

---

## Estructura del Proyecto

```text
LibroRecomienda/
├── .env             # (No versionado) Variables de entorno (DATABASE_URL, API Keys)
├── .venv/           # Entorno virtual (creado por uv o venv)
├── alembic.ini      # Configuración de Alembic
├── migrations/      # Scripts de migración de Alembic
│   ├── versions/    # Archivos de migración específicos
│   └── ...
├── scripts/         # Scripts útiles
│   ├── generate_fake_data.py # Genera usuarios y reseñas falsas
│   └── populate_db.py      # (Opcional) Script para poblar libros inicialmente
├── src/
│   └── librorecomienda/ # Código fuente principal del paquete Python
│       ├── agents/    # Lógica del agente LangGraph (state, tools, graph)
│       ├── core/      # Configuración central (config.py), seguridad (security.py)
│       ├── crud/      # Funciones CRUD (crud_book.py, crud_review.py, crud_user.py)
│       ├── db/        # Configuración de la sesión de SQLAlchemy (session.py)
│       ├── models/    # Modelos SQLAlchemy (book.py, review.py, user.py)
│       ├── schemas/   # Modelos Pydantic (review.py, user.py)
│       └── __init__.py
├── streamlit_app/   # Código de la interfaz de usuario Streamlit
│   ├── app.py       # Página principal (catálogo, login)
│   └── pages/       # Páginas adicionales (admin.py, chat.py)
├── tests/           # Pruebas con Pytest
│   ├── crud/        # Pruebas para las funciones CRUD
│   ├── models/      # Pruebas para los modelos SQLAlchemy
│   └── conftest.py  # Fixtures de configuración de pruebas (ej. sesión de BD)
├── pyproject.toml   # Definición del proyecto y dependencias para uv/pip
├── README.md        # Este archivo
├── uv.lock          # Archivo de bloqueo de dependencias de uv
└── ...              # Otros archivos (ej. .gitignore, collect_snapshot.py)
```

---

## Instalación y Configuración

Sigue estos pasos para poner en marcha el proyecto localmente:

1. **Prerrequisitos:**
   * Python >= 3.11
   * Un servidor de base de datos PostgreSQL (recomendado) o SQLite instalado.
   * `uv` instalado globalmente (`pip install uv` o sigue las [instrucciones oficiales](https://github.com/astral-sh/uv)).
   * Git.

2. **Clonar el Repositorio:**

   ```bash
   git clone https://github.com/josefdc/LibroRecomiendaDB
   cd LibroRecomienda
   ```

3. **Crear y Activar Entorno Virtual (usando uv):**

   ```bash
   uv venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate  # Windows (cmd/powershell)
   ```

4. **Instalar Dependencias (usando uv):**
   * Instala las dependencias principales y de desarrollo definidas en `pyproject.toml`:

     ```bash
     uv pip install -e .[dev]
     ```
   * El flag `-e .` instala el proyecto `librorecomienda` en modo editable. `[dev]` instala las dependencias de desarrollo (como `pytest`, `faker`).

5. **Variables de Entorno:**
   * Crea un archivo llamado `.env` en la raíz del proyecto (`LibroRecomienda/.env`).
   * Añade las siguientes variables, ajustando los valores según tu configuración:

     ```dotenv
     # --- Base de Datos ---
     # Ejemplo para PostgreSQL local (asegúrate que la BD 'librorecomienda_db' exista)
     DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/librorecomienda_db

     # Ejemplo para SQLite (creará un archivo librorecomienda.db en la raíz)
     # DATABASE_URL=sqlite:///./librorecomienda.db

     # --- APIs Externas ---
     # API Key para el LLM (ej. OpenAI)
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

     # (Opcional) API Key para Google Books (si implementas esa funcionalidad)
     # GOOGLE_BOOKS_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxx

     # --- Configuración de la Aplicación ---
     # Lista de emails de administradores separados por coma (sin espacios alrededor)
     ADMIN_EMAILS=admin@example.com,tu_email@dominio.com

     # Entorno (opcional, puede ser usado para configuraciones específicas)
     # ENVIRONMENT=development
     ```
   * **Importante:** Si usas PostgreSQL, asegúrate de que la base de datos (`librorecomienda_db` en el ejemplo) exista en tu servidor antes de continuar. Si usas SQLite, el archivo se creará automáticamente.

6. **Migraciones de Base de Datos:**
   * Aplica las migraciones para crear/actualizar las tablas en la base de datos configurada en `.env`:

     ```bash
     alembic upgrade head
     ```

---

## Ejecución

1. **Poblar Base de Datos (Opcional pero Recomendado):**
   * Para generar usuarios y reseñas falsas para probar la aplicación:

     ```bash
     python scripts/generate_fake_data.py
     ```
   * *(Nota: El script `populate_db.py` podría necesitar ser adaptado o usado si tienes una fuente específica para cargar libros iniciales).*

2. **Iniciar la Aplicación Streamlit:**

   ```bash
   streamlit run streamlit_app/app.py
   ```
   * Abre la URL local que te indique Streamlit (generalmente `http://localhost:8501`) en tu navegador.

---

## Ejecución de Pruebas

* Asegúrate de tener las dependencias de desarrollo instaladas (`uv pip install -e .[dev]`).
* Desde la raíz del proyecto (`LibroRecomienda/`), ejecuta:

  ```bash
  pytest
  ```
* Las pruebas usarán una base de datos SQLite en memoria (`sqlite:///:memory:`) definida en `tests/conftest.py` para no interferir con tu base de datos principal.

---

## Licencia

Este proyecto se distribuye bajo la licencia  Ver el archivo `LICENSE` para más detalles 
