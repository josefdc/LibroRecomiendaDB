# streamlit_app/pages/chat.py

import streamlit as st
import uuid # Para generar IDs de conversación únicos
from langchain_core.messages import AIMessage, HumanMessage
import logging

# Configurar logging básico para Streamlit (opcional pero útil)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importa tu grafo compilado (asegúrate que la ruta sea correcta)
try:
    # Asegúrate de que la importación refleje la estructura de tu proyecto
    # Si graph.py está en src/librorecomienda/agents/graph.py
    # y streamlit_app está al mismo nivel que src/, necesitas ajustar el sys.path o usar rutas relativas correctas
    # Una forma común es añadir src al path si ejecutas streamlit desde la raíz
    import sys
    import os
    # Añade el directorio 'src' al path si no está ya
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from librorecomienda.agents.graph import graph, CRUD_AVAILABLE # Asume que 'graph' es el objeto compilado y CRUD_AVAILABLE indica si las tools están listas
    logger.info("Grafo del agente importado correctamente.")
    if not CRUD_AVAILABLE:
        logger.warning("Las funciones CRUD no están disponibles. Las herramientas del agente no funcionarán.")

except ImportError as e:
    logger.error(f"Error al importar el grafo del agente: {e}", exc_info=True)
    st.error(f"No se pudo importar el grafo del agente. Asegúrate de que la ruta sea correcta y las dependencias estén instaladas. Error: {e}")
    st.stop()
except AttributeError as e:
     logger.error(f"Error de atributo al importar: {e}", exc_info=True)
     st.error(f"Asegúrate de que 'graph' (el grafo compilado con checkpointer) esté disponible y exportado correctamente en agents/graph.py. Error: {e}")
     st.stop()
except Exception as e:
    logger.error(f"Error inesperado durante la importación: {e}", exc_info=True)
    st.error(f"Ocurrió un error inesperado al cargar el agente: {e}")
    st.stop()


# --- Título de la Página ---
st.set_page_config(page_title="Chat de Recomendaciones", page_icon="💬") # Configura título e icono de la pestaña
st.title("💬 Chat de Recomendaciones")
st.caption("Habla con nuestro agente para encontrar tu próxima lectura.")

# --- Inicialización del Estado de Sesión del Chat ---
# Usamos claves específicas para este chat para no interferir con otros estados
if "chat_thread_id" not in st.session_state:
    # Cada nueva sesión de chat obtiene un ID único
    st.session_state.chat_thread_id = str(uuid.uuid4())
    logger.info(f"Nueva sesión de chat iniciada con thread_id: {st.session_state.chat_thread_id}")
    st.session_state.chat_messages = [
        AIMessage(content="¡Hola! Soy tu asistente de recomendaciones de libros. ¿Qué tipo de libros te interesan?")
    ]
# --- Fin Inicialización ---


# --- Mostrar Historial de Mensajes ---
# Itera sobre los mensajes guardados en el estado de sesión y muéstralos
for msg in st.session_state.chat_messages:
    if isinstance(msg, AIMessage):
        st.chat_message("assistant", avatar="🤖").write(msg.content)
    elif isinstance(msg, HumanMessage):
        st.chat_message("user", avatar="👤").write(msg.content)
# --- Fin Mostrar Historial ---


# --- Entrada del Usuario y Ejecución del Agente ---
if prompt := st.chat_input("Escribe tu mensaje aquí..."):
    # 1. Añadir y mostrar el mensaje del usuario
    st.session_state.chat_messages.append(HumanMessage(content=prompt))
    st.chat_message("user", avatar="👤").write(prompt)
    logger.info(f"Usuario (Thread: {st.session_state.chat_thread_id}): {prompt}")

    # 2. Preparar configuración para LangGraph (con el thread_id de esta sesión)
    config = {"configurable": {"thread_id": st.session_state.chat_thread_id}}

    # 3. Llamar al agente (grafo LangGraph)
    # Prepara el input para el grafo (solo el último mensaje humano es necesario
    # si el historial completo está en 'messages' dentro del estado del grafo)
    # Nota: El estado interno del grafo ('messages') es manejado por el checkpointer.
    # Aquí solo pasamos el nuevo input.
    inputs = {"messages": [HumanMessage(content=prompt)]}

    # Muestra un indicador de espera mientras el agente procesa
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            try:
                # Llama al grafo usando stream para obtener la respuesta final
                # Usamos stream_mode="values" para obtener el estado final completo
                final_state = None
                logger.debug(f"Llamando al grafo con input: {inputs} y config: {config}")
                # Aumentar el límite de recursión si es necesario para grafos complejos
                # CORRECCIÓN: Eliminar recursion_limit=25 ya que no es un argumento válido para stream
                for chunk in graph.stream(inputs, config=config, stream_mode="values"):
                    # El último chunk contendrá el estado final después de la ejecución
                    logger.debug(f"Chunk recibido del stream: {chunk.keys()}") # Ver qué nodos se ejecutan
                    final_state = chunk

                logger.debug(f"Estado final recibido del grafo: {final_state}")

                # 4. Extraer y mostrar la última respuesta del AI
                if final_state and "messages" in final_state and final_state["messages"]:
                    # La respuesta del AI es el último mensaje en la lista del estado final
                    ai_response_message = final_state["messages"][-1]
                    if isinstance(ai_response_message, AIMessage):
                        response_content = ai_response_message.content
                        # Asegurarse de que no sea una respuesta vacía o solo de llamada a herramienta
                        if response_content and not ai_response_message.tool_calls:
                            st.markdown(response_content) # Mostrar la respuesta
                            # 5. Añadir respuesta del AI al historial de sesión (para mostrar)
                            st.session_state.chat_messages.append(ai_response_message)
                            logger.info(f"Agente (Thread: {st.session_state.chat_thread_id}): {response_content}")
                        elif ai_response_message.tool_calls:
                             logger.info(f"Agente (Thread: {st.session_state.chat_thread_id}): Realizó llamada a herramienta.")
                             # Podrías poner un mensaje placeholder o simplemente no añadir nada visible si la llamada a herramienta es interna
                             # st.markdown("Estoy buscando información...") # Opcional
                             # No añadir la llamada a herramienta como mensaje visible
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
                # Añadir un mensaje de error al historial de chat
                st.session_state.chat_messages.append(AIMessage(content=f"Lo siento, ocurrió un error interno: {e}"))


# --- Fin Entrada del Usuario ---

# --- (Opcional) Botón para limpiar historial de la sesión actual ---
if st.button("Limpiar historial de chat"):
    st.session_state.chat_messages = [
        AIMessage(content="¡Hola! ¿Sobre qué tipo de libros te gustaría hablar hoy?")
    ]
    # OJO: Esto NO limpia el estado del checkpointer (MemorySaver).
    # Para limpiar MemorySaver, necesitarías reiniciar el proceso Streamlit
    # o implementar lógica específica si usaras un checkpointer persistente.
    # Podríamos generar un NUEVO thread_id para simular un reinicio completo:
    # st.session_state.chat_thread_id = str(uuid.uuid4())
    # logger.info(f"Historial de chat limpiado. Nuevo thread_id: {st.session_state.chat_thread_id}")
    st.rerun()
