"""
Chat page for LibroRecomienda Streamlit app.

This module provides a conversational interface for users to interact with
the book recommendation agent powered by LangGraph. It manages session state,
message history, and handles agent execution and error reporting.

Intended for end-users to receive book recommendations and interact with the AI agent.
"""

import streamlit as st
import uuid
from langchain_core.messages import AIMessage, HumanMessage
import logging
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import sys
    import os
    src_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from librorecomienda.agents.graph import graph, CRUD_AVAILABLE
    logger.info("Grafo del agente importado correctamente.")
    if not CRUD_AVAILABLE:
        logger.warning("Las funciones CRUD no están disponibles. Las herramientas del agente no funcionarán.")

except ImportError as e:
    logger.error(f"Error al importar el grafo del agente: {e}", exc_info=True)
    st.error(f"No se pudo importar el grafo del agente. Asegúrate de que la ruta sea correcta y las dependencias estén instaladas. Error: {e}")
    st.stop()
except AttributeError as e:
    logger.error(f"Error de atributo al importar: {e}", exc_info=True)
    st.error("Asegúrate de que 'graph' (el grafo compilado con checkpointer) esté disponible y exportado correctamente en agents/graph.py. Error: {e}")
    st.stop()
except Exception as e:
    logger.error(f"Error inesperado durante la importación: {e}", exc_info=True)
    st.error(f"Ocurrió un error inesperado al cargar el agente: {e}")
    st.stop()

st.set_page_config(page_title="Chat de Recomendaciones", page_icon="💬")
st.title("💬 Chat de Recomendaciones")
st.caption("Habla con nuestro agente para encontrar tu próxima lectura.")


def initialize_chat_session() -> None:
    """
    Initializes the chat session state if not already present.

    Returns:
        None
    """
    if "chat_thread_id" not in st.session_state:
        st.session_state.chat_thread_id = str(uuid.uuid4())
        logger.info(f"Nueva sesión de chat iniciada con thread_id: {st.session_state.chat_thread_id}")
        st.session_state.chat_messages = [
            AIMessage(content="¡Hola! Soy tu asistente de recomendaciones de libros. ¿Qué tipo de libros te interesan?")
        ]


def display_message_history(messages: List[Any]) -> None:
    """
    Displays the chat message history in the Streamlit UI.

    Args:
        messages (List[Any]): List of AIMessage or HumanMessage objects.

    Returns:
        None
    """
    for msg in messages:
        if isinstance(msg, AIMessage):
            st.chat_message("assistant", avatar="🤖").write(msg.content)
        elif isinstance(msg, HumanMessage):
            st.chat_message("user", avatar="👤").write(msg.content)


def handle_user_input(prompt: str) -> None:
    """
    Handles user input, sends it to the agent, and updates the chat history.

    Args:
        prompt (str): The user's input message.

    Returns:
        None
    """
    st.session_state.chat_messages.append(HumanMessage(content=prompt))
    st.chat_message("user", avatar="👤").write(prompt)
    logger.info(f"Usuario (Thread: {st.session_state.chat_thread_id}): {prompt}")

    config: Dict[str, Any] = {"configurable": {"thread_id": st.session_state.chat_thread_id}}
    inputs: Dict[str, Any] = {"messages": [HumanMessage(content=prompt)]}

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            try:
                final_state: Optional[Dict[str, Any]] = None
                logger.debug(f"Llamando al grafo con input: {inputs} y config: {config}")
                for chunk in graph.stream(inputs, config=config, stream_mode="values"):
                    final_state = chunk

                logger.debug(f"Estado final recibido del grafo: {final_state}")

                if final_state and "messages" in final_state and final_state["messages"]:
                    ai_response_message = final_state["messages"][-1]
                    if isinstance(ai_response_message, AIMessage):
                        response_content: str = ai_response_message.content
                        if response_content and not ai_response_message.tool_calls:
                            st.markdown(response_content)
                            st.session_state.chat_messages.append(ai_response_message)
                            logger.info(f"Agente (Thread: {st.session_state.chat_thread_id}): {response_content}")
                        elif ai_response_message.tool_calls:
                            logger.info(f"Agente (Thread: {st.session_state.chat_thread_id}): Realizó llamada a herramienta.")
                        else:
                            logger.warning("El último mensaje del agente AI estaba vacío.")
                            st.error("El agente devolvió una respuesta vacía.")
                            st.session_state.chat_messages.append(AIMessage(content="Lo siento, no pude generar una respuesta clara."))
                    else:
                        logger.error(f"El último mensaje no fue AIMessage: {type(ai_response_message)}")
                        st.error("El agente no devolvió un mensaje de AI válido.")
                        st.session_state.chat_messages.append(AIMessage(content="Lo siento, tuve un problema con el formato de la respuesta."))
                else:
                    logger.error(f"El estado final no contenía 'messages' o estaba vacío: {final_state}")
                    st.error("El agente no devolvió una respuesta.")
                    st.session_state.chat_messages.append(AIMessage(content="Lo siento, no pude generar una respuesta."))
            except Exception as e:
                logger.error(f"Error durante la ejecución del grafo en Streamlit (Thread: {st.session_state.chat_thread_id}): {e}", exc_info=True)
                st.error(f"Ocurrió un error al procesar tu solicitud: {e}")
                st.session_state.chat_messages.append(AIMessage(content=f"Lo siento, ocurrió un error interno: {e}"))


def clear_chat_history() -> None:
    """
    Clears the current chat message history and resets the initial AI greeting.

    Returns:
        None
    """
    st.session_state.chat_messages = [
        AIMessage(content="¡Hola! ¿Sobre qué tipo de libros te gustaría hablar hoy?")
    ]
    st.rerun()


# --- Main Chat Page Logic ---

initialize_chat_session()
display_message_history(st.session_state.chat_messages)

if prompt := st.chat_input("Escribe tu mensaje aquí..."):
    handle_user_input(prompt)

if st.button("Limpiar historial de chat"):
    clear_chat_history()
