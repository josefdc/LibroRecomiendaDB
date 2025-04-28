# src/librorecomienda/agents/graph.py

# --- PASO 7.1: Importar Checkpointer ---
from langgraph.checkpoint.memory import MemorySaver
# ---------------------------------------
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, ToolMessage
from typing import Dict, Any, Optional, List
import logging
import json
# Importar herramientas y estado
from .state import AgentState
try:
    from .tools import agent_tools, CRUD_AVAILABLE
except ImportError as e:
    logging.error(f"Failed to import agent_tools or CRUD_AVAILABLE from .tools: {e}. Graph might not function correctly.")
    agent_tools = []
    CRUD_AVAILABLE = False

# --- Configurar Logging ---
logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- 1. Inicializar el Modelo LLM ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(agent_tools) if agent_tools else llm

# --- 2. Definir las funciones de los Nodos ---

# Nodo LLM Principal (Planificador/Ejecutor)
def call_model(state: AgentState) -> Dict[str, Any]:
    """
    Nodo principal: Llama al LLM con el historial actual.
    El LLM decidirá si responder directamente, hacer una pregunta,
    o solicitar el uso de una herramienta.
    """
    logger.info("--- Calling Main LLM Node ---")
    messages = state['messages']
    preferences = state.get('user_preferences') # Log the preferences received by the node
    logger.info(f"LLM Node Received State: Preferences = {preferences}") # <<< ADDED LOGGING
    # Usar LLM con herramientas si están disponibles
    current_llm = llm_with_tools if agent_tools else llm
    logger.debug(f"Messages sent to LLM: {messages}")
    try:
        response = current_llm.invoke(messages)
        logger.debug(f"LLM Response: {response}")
        # Devolver la respuesta del LLM para que se añada al estado.
        # IMPORTANTE: No sobrescribir el estado, solo devolver el nuevo mensaje
        return {"messages": [response]}
    except Exception as e:
         logger.error(f"Error invoking LLM in call_model: {e}", exc_info=True)
         # Devolver un mensaje de error al usuario
         error_message = "Lo siento, tuve un problema al procesar tu solicitud. Por favor, inténtalo de nuevo."
         return {"messages": [AIMessage(content=error_message)]}


# Nodo para Preguntar Preferencias
def gather_preferences_node(state: AgentState) -> Dict[str, List[BaseMessage]]:
    """
    Genera una pregunta específica para obtener preferencias del usuario.
    """
    logger.info("--- Gathering Preferences Node ---")
    preferences = state.get('user_preferences') or {}
    if not preferences.get('preferred_genres'):
        question = "¿Qué géneros de libros te gustan más?"
    elif not preferences.get('liked_authors'):
        question = "¿Tienes algún autor preferido?"
    else:
        question = "¿Hay algo más que te gustaría contarme sobre tus gustos literarios para afinar la búsqueda?"

    return {"messages": [AIMessage(content=question)]}

# Nodo para Procesar Respuesta del Usuario
def process_user_response_node(state: AgentState) -> Dict[str, Dict]:
    """
    Procesa la última respuesta del usuario para extraer preferencias.
    """
    logger.info("--- Processing User Response Node ---") # <<< CONFIRMATION LOG
    if not state['messages'] or not isinstance(state['messages'][-1], HumanMessage):
        logger.warning("No user message found to process for preferences.")
        return {} # Return empty dict, don't modify state if no user message

    last_user_message = state['messages'][-1].content
    current_preferences = state.get('user_preferences') or {}
    logger.info(f"Processing user message: '{last_user_message}' with current prefs: {current_preferences}") # <<< DETAIL LOG

    prompt = f"""
Analiza la siguiente respuesta del usuario y extrae sus preferencias de lectura (géneros, autores, libros mencionados, etc.).
Preferencias actuales conocidas: {current_preferences}
Respuesta del usuario: "{last_user_message}"
Devuelve SOLAMENTE un diccionario JSON actualizado con las preferencias encontradas. Si encuentras nuevas preferencias, añádelas o actualiza las existentes. Si no se mencionan preferencias claras, devuelve el diccionario actual o uno vacío si no había nada antes. NO incluyas explicaciones, solo el JSON.
Ejemplo de formato de salida: {{"preferred_genres": ["Ciencia Ficción", "Fantasía"], "liked_authors": ["Brandon Sanderson"]}}
Formato de salida estricto: {{...}}
"""
    try:
        logger.debug("Calling LLM to extract preferences.")
        response = llm.invoke(prompt) # Usar LLM base, no necesita herramientas
        logger.debug(f"LLM response for preferences: {response.content}")

        content_to_parse = response.content.strip()
        if content_to_parse.startswith("```json"):
            content_to_parse = content_to_parse[7:]
        if content_to_parse.endswith("```"):
            content_to_parse = content_to_parse[:-3]
        content_to_parse = content_to_parse.strip()

        if not content_to_parse or content_to_parse == '{}':
             extracted_prefs = {}
        else:
            extracted_prefs = json.loads(content_to_parse)

        if not isinstance(extracted_prefs, dict):
             raise ValueError("LLM did not return a valid JSON dictionary.")

        logger.info(f"Extracted preferences: {extracted_prefs}")
        # Fusionar: Prioriza valores nuevos, limpia valores vacíos
        updated_preferences = {**current_preferences, **extracted_prefs}
        updated_preferences = {k: v for k, v in updated_preferences.items() if v} # Elimina claves con valor None o lista vacía

        logger.info(f"Updated preferences state: {updated_preferences}") # <<< CONFIRM UPDATE
        return {"user_preferences": updated_preferences}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response for preferences: {e}. Response was: {response.content}")
        return {"user_preferences": current_preferences} # Return current prefs on error
    except Exception as e:
        logger.error(f"Failed to process user response for preferences: {e}", exc_info=True)
        return {"user_preferences": current_preferences} # Return current prefs on error


# Nodo para Generar Recomendaciones
def generate_recommendations_node(state: AgentState) -> Dict[str, Any]:
    """
    Genera recomendaciones basadas en preferencias y resultados de búsqueda válidos.
    Actualiza 'search_results' en el estado con los resultados procesados.
    Devuelve 'recommendations' y 'search_results' o 'messages' si hay error.
    """
    logger.info("--- Generating Recommendations Node ---")
    preferences = state.get('user_preferences')
    processed_search_results = []

    if state['messages']:
        for msg in reversed(state['messages']):
            if isinstance(msg, ToolMessage) and msg.name == 'search_books' and msg.content:
                try:
                    content_data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(content_data, list):
                         valid_results = [item for item in content_data if isinstance(item, dict) and 'error' not in item and 'not_found' not in item]
                         if valid_results:
                             processed_search_results = valid_results
                             logger.info(f"Found {len(processed_search_results)} valid search results from ToolMessage.")
                             break
                except Exception as e:
                    logger.error(f"Error processing ToolMessage content in generate_recommendations: {e}", exc_info=True)

    if not preferences:
        logger.warning("Cannot generate recommendations: Missing preferences.")
        return {"messages": [AIMessage(content="Necesito entender mejor tus gustos antes de recomendar. ¿Qué tipo de libros prefieres?")]}

    if not processed_search_results:
        logger.warning("Cannot generate recommendations: Missing valid search results.")
        # Podríamos instruir al LLM para que busque aquí, pero por ahora devolvemos mensaje
        return {"messages": [AIMessage(content="No encontré resultados de búsqueda relevantes para generar recomendaciones. ¿Podrías intentar buscar con otros términos o refinar tus preferencias?")]}

    # --- Lógica de Selección/Filtrado ---
    recommendations = []
    preferred_genres = preferences.get('preferred_genres', [])
    if isinstance(preferred_genres, str): # Asegurar que sea lista
        preferred_genres = [preferred_genres]
    elif not isinstance(preferred_genres, list):
        preferred_genres = []

    logger.debug(f"Filtering {len(processed_search_results)} search results based on preferred genres: {preferred_genres}")

    # Filtrar por género
    genre_filtered_recs = []
    if preferred_genres:
        for book in processed_search_results:
            book_genre = book.get('genre')
            if book_genre and any(pref_genre.lower() in book_genre.lower() for pref_genre in preferred_genres):
                genre_filtered_recs.append(book)
    else:
        # Si no hay preferencia de género, considerar todos los resultados
        genre_filtered_recs = processed_search_results[:]

    # Tomar hasta 3 recomendaciones (priorizando las filtradas por género)
    recommendations = genre_filtered_recs[:3]

    # Si no se encontraron coincidencias de género pero hay resultados, tomar los primeros generales
    if not recommendations and processed_search_results:
         logger.info("No specific genre matches found, taking top search results.")
         recommendations = processed_search_results[:3]
    # Rellenar si el filtro dio menos de 3 pero había más resultados generales
    elif len(recommendations) < 3 and len(processed_search_results) > len(recommendations):
         logger.info("Filling remaining recommendations with top search results.")
         existing_ids = {rec['id'] for rec in recommendations if rec.get('id')}
         for book in processed_search_results:
             if book.get('id') not in existing_ids:
                 recommendations.append(book)
                 if len(recommendations) >= 3:
                     break

    logger.info(f"Generated {len(recommendations)} recommendations.")
    # Devolver recomendaciones y los resultados que se usaron
    return {"recommendations": recommendations, "search_results": processed_search_results}

# Nodo para Generar Explicaciones
def generate_explanations_node(state: AgentState) -> Dict[str, Dict[str, str]]:
    """
    Genera explicaciones para cada libro recomendado.
    """
    logger.info("--- Generating Explanations Node ---")
    recommendations = state.get('recommendations')
    preferences = state.get('user_preferences')
    explanations = {}

    if not recommendations:
        logger.warning("No recommendations available to generate explanations.")
        return {"explanations": {}}

    prefs_str = json.dumps(preferences) if preferences else "ninguna preferencia específica mencionada"

    for book in recommendations:
        book_id = book.get('id')
        if book_id is None: continue
        book_id_str = str(book_id)
        book_info = f"Título: {book.get('title', 'N/A')}, Autor: {book.get('author', 'N/A')}, Género: {book.get('genre', 'N/A')}, Rating: {book.get('average_rating', 'N/A')}"
        prompt = f"""
Dado que un usuario tiene estas preferencias: {prefs_str}.
Explica brevemente (1-2 frases) por qué el siguiente libro podría gustarle.
Libro: {book_info}.
Enfócate en conectar el libro con las preferencias si es posible. Si no hay conexión clara, da una razón general basada en el libro mismo. Sé conciso y directo.
"""
        try:
            logger.debug(f"Generating explanation for book ID {book_id_str}")
            response = llm.invoke(prompt) # Usar LLM base
            explanations[book_id_str] = response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate explanation for book ID {book_id_str}: {e}", exc_info=True)
            explanations[book_id_str] = "No se pudo generar una explicación detallada en este momento."

    logger.info(f"Generated explanations for {len(explanations)} recommendations.")
    return {"explanations": explanations}


# Nodo para Formatear Salida
def format_output_node(state: AgentState) -> Dict[str, List[BaseMessage]]:
    """
    Formatea la salida final (recomendaciones + explicaciones o mensaje de error) para el usuario.
    """
    logger.info("--- Formatting Output Node ---")
    recommendations = state.get('recommendations')
    explanations = state.get('explanations') or {}

    # Si el nodo anterior (generate_recommendations) devolvió un mensaje, usarlo
    # Buscamos el último mensaje AIMessage en el historial
    last_ai_message = None
    if state.get('messages'):
        for msg in reversed(state['messages']):
            if isinstance(msg, AIMessage):
                last_ai_message = msg
                break

    if not recommendations and last_ai_message:
         # Comprobar si el mensaje parece ser uno de los errores de generate_recommendations
         possible_error_starts = ["Necesito entender mejor", "No encontré resultados"]
         if any(last_ai_message.content.startswith(start) for start in possible_error_starts):
             logger.info("Formatting output based on message from previous node.")
             return {"messages": [last_ai_message]} # Devolver el mensaje de error/info

    if not recommendations:
         logger.info("No recommendations to format and no specific message found.")
         message = "Lo siento, no pude generar recomendaciones en este momento."
         return {"messages": [AIMessage(content=message)]}

    response_parts = ["Aquí tienes algunas recomendaciones que podrían gustarte:\n"]
    for book in recommendations:
        book_id = book.get('id')
        book_id_str = str(book_id) if book_id is not None else 'unknown'
        explanation = explanations.get(book_id_str, "Una opción interesante basada en tu búsqueda.")

        title = book.get('title', 'Título Desconocido')
        author = book.get('author', 'Autor Desconocido')
        rating = book.get('average_rating')
        rating_str = f" (Rating: {rating}/5)" if rating is not None else ""

        response_parts.append(f"\n- **{title}** por {author}{rating_str}:")
        response_parts.append(f"  *Por qué te podría gustar:* {explanation}")

    response_parts.append("\n\n¿Te gustaría obtener más detalles sobre alguno de estos libros, buscar algo diferente o refinar las preferencias?")
    final_response = "\n".join(response_parts)

    logger.info("Formatted final response for the user.")
    return {"messages": [AIMessage(content=final_response)]}


# --- Funciones de Enrutamiento ---

# RENAMED from route_logic
def route_after_llm(state: AgentState) -> str:
    """
    Decide el siguiente nodo DESPUÉS de que el nodo LLM principal haya ejecutado.
    """
    logger.info("--- Routing Logic (After LLM) ---")
    messages = state['messages']
    if not messages: # Should not happen if called after LLM
        logger.warning("Routing (After LLM) called with empty messages.")
        return END
    last_message = messages[-1] # Should be the AIMessage from the llm node
    preferences = state.get('user_preferences') or {}

    logger.info(f"Routing (After LLM) Check: Last message type = {type(last_message)}")
    logger.info(f"Routing (After LLM) Check: Preferences in state = {preferences}")

    # Ensure last_message is AIMessage before proceeding
    if not isinstance(last_message, AIMessage):
        logger.error(f"Routing (After LLM) expected AIMessage, got {type(last_message)}. Routing to END.")
        return END

    # 1. If LLM called a tool
    if last_message.tool_calls:
        if agent_tools:
            logger.info("Routing decision (After LLM): Go to tools")
            return "tools"
        else:
            logger.warning("Routing decision (After LLM): LLM requested tools, but none available. Ending.")
            return END

    # 2. If LLM responded without tool call
    else: # No tool_calls
        # Check if preferences are still missing
        if not preferences or not preferences.get('preferred_genres'): # Check if key pref is missing
            logger.info("Routing decision (After LLM): Gather preferences (LLM responded, but prefs still missing)")
            return "gather_preferences"
        else:
            # Preferences exist. Did we just come from a successful tool call?
            # Check the second to last message
            if len(messages) > 1 and isinstance(messages[-2], ToolMessage) and messages[-2].name == 'search_books':
                tool_msg = messages[-2]
                tool_results_content = None
                try:
                    content_data = json.loads(tool_msg.content) if isinstance(tool_msg.content, str) else tool_msg.content
                    if isinstance(content_data, list):
                        tool_results_content = [item for item in content_data if isinstance(item, dict) and 'error' not in item]
                except Exception as e:
                    logger.error(f"Routing (After LLM) failed to parse ToolMessage content: {e}")

                if tool_results_content: # Tool had results, prefs exist
                    logger.info("Routing decision (After LLM): Generate recommendations (LLM processed successful tool call)")
                    return "generate_recommendations"
                else: # Tool failed or no results
                    logger.info("Routing decision (After LLM): END (LLM processed failed/empty tool call, wait for user)")
                    return END
            else: # LLM responded conversationally, no recent tool call
                logger.info("Routing decision (After LLM): END (LLM responded conversationally, wait for user)")
                return END

    # Fallback (should be unreachable if last_message is always AIMessage)
    logger.warning(f"Routing (After LLM) reached fallback for message type: {type(last_message)}")
    return END


# NEW Entry Router
def route_entry(state: AgentState) -> str:
    """
    Determines the first node to execute based on the last message added.
    This acts as the main dispatcher after a message is added to the state.
    """
    logger.info("--- Routing Logic (Entry) ---")
    messages = state['messages']
    if not messages:
        logger.info("Routing decision (Entry): No messages, go to LLM (initial state)")
        return "llm" # Initial state, let LLM ask first question

    last_message = messages[-1]
    logger.info(f"Routing (Entry) Check: Last message type = {type(last_message)}")

    if isinstance(last_message, HumanMessage):
        # After user speaks, process their response for preferences
        logger.info("Routing decision (Entry): Human message, go to process_user_response")
        return "process_user_response"
    elif isinstance(last_message, ToolMessage):
        # After tool runs, go to LLM to process results
        logger.info("Routing decision (Entry): Tool message, go to LLM")
        return "llm"
    elif isinstance(last_message, AIMessage):
        # If the last message was AI (e.g., from gather_prefs or format_output), end the turn.
        # If the AI message included a tool call, route_after_llm will handle it next.
        # If the AI message was just conversational, end the turn.
        # This router is primarily for dispatching *after* Human or Tool messages.
        # If we reach here after an AIMessage, it implies the graph should pause or the next step
        # is determined by the conditional edge *from* the node that produced the AIMessage.
        # Let's route to LLM as a safe default if the graph structure leads here unexpectedly.
        logger.info("Routing decision (Entry): AIMessage received. Assuming previous node handles next step or ending turn. Defaulting to LLM if called unexpectedly.")
        # This path might indicate a structural issue if hit often.
        # The conditional edge from 'llm' (route_after_llm) should handle AI messages from 'llm'.
        # Edges from 'gather_preferences' and 'format_output' go to END.
        return "llm" # Or potentially END, depending on desired behavior for unexpected AI message arrival here.
    else:
        logger.warning(f"Routing (Entry): Unknown last message type {type(last_message)}. Ending.")
        return END


# --- 3. Construir el Grafo ---
graph_builder = StateGraph(AgentState)

# Añadir nodos
graph_builder.add_node("llm", call_model)
if agent_tools:
    tool_node = ToolNode(agent_tools)
    graph_builder.add_node("tools", tool_node)
graph_builder.add_node("gather_preferences", gather_preferences_node)
graph_builder.add_node("process_user_response", process_user_response_node)
graph_builder.add_node("generate_recommendations", generate_recommendations_node)
graph_builder.add_node("generate_explanations", generate_explanations_node)
graph_builder.add_node("format_output", format_output_node)


# --- Definir Aristas (Revisado) ---

# Punto de Entrada: Usar START y la lógica de route_entry para decidir el primer *real* nodo

# Decisiones desde el punto de entrada (START)
graph_builder.add_conditional_edges(
    START, # Source is the graph entry
    route_entry, # Function that returns the name of the first node to run
    {
        "process_user_response": "process_user_response",
        "llm": "llm",
        END: END
    }
)

# Después de procesar la respuesta del usuario, ir al LLM
graph_builder.add_edge("process_user_response", "llm")

# Después de ejecutar herramientas (si existen), volver al LLM
if "tools" in graph_builder.nodes:
    graph_builder.add_edge("tools", "llm")

# Después de preguntar preferencias, esperar input del usuario (termina el turno)
graph_builder.add_edge("gather_preferences", END)

# Decisiones Condicionales DESPUÉS del LLM principal
routing_map_after_llm = {
    "tools": "tools",
    "gather_preferences": "gather_preferences",
    "generate_recommendations": "generate_recommendations",
    END: END
}
if "tools" not in graph_builder.nodes:
    del routing_map_after_llm["tools"]

graph_builder.add_conditional_edges(
    "llm", # Origen: LLM
    route_after_llm, # Lógica para decidir DESPUÉS de que LLM haya corrido
    routing_map_after_llm
)

# Flujo de generación de recomendaciones
# Check the state *after* generate_recommendations runs
def check_recommendation_output(state: AgentState) -> str:
    # Check if the *last* message added by generate_recommendations indicates an issue
    last_message = state['messages'][-1] if state.get('messages') else None
    if isinstance(last_message, AIMessage) and any(last_message.content.startswith(start) for start in ["Necesito entender mejor", "No encontré resultados"]):
        logger.info("Routing after generate_recommendations: Found message, routing to format_output.")
        return "format_output" # Route to format the message
    elif state.get('recommendations'):
        logger.info("Routing after generate_recommendations: Found recommendations, routing to generate_explanations.")
        return "generate_explanations" # Route to explain if recommendations exist
    else:
        # Fallback if recommendations are missing and no specific message was added
        logger.warning("Routing after generate_recommendations: No recommendations or specific message found. Routing to format_output (will likely show generic error).")
        return "format_output"

graph_builder.add_conditional_edges(
    "generate_recommendations",
    check_recommendation_output,
    {
        "generate_explanations": "generate_explanations",
        "format_output": "format_output"
    }
)
graph_builder.add_edge("generate_explanations", "format_output")
graph_builder.add_edge("format_output", END) # Termina el turno después de mostrar recomendaciones/mensaje


# --- Compilar el Grafo ---
memory = MemorySaver()
try:
    # Compilar con el checkpointer
    graph = graph_builder.compile(checkpointer=memory)
    logger.info("Graph compiled successfully with MemorySaver checkpointer.")
except Exception as e:
    logger.error(f"Error compiling graph with checkpointer: {e}", exc_info=True)
    graph = None # Indicar que el grafo no está listo

# --- (Opcional) Prueba básica ---
if __name__ == "__main__":
    # Configurar logging para ver los pasos
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting graph test execution with MemorySaver...")

    if graph is None:
         logger.error("Graph could not be compiled. Aborting test.")
    elif not CRUD_AVAILABLE:
         logger.error("CRUD functions not available (check tools.py imports/setup). Skipping graph execution test.")
    else:
        # --- Definir un ID de conversación ---
        conversation_id = "test_conversation_123"
        config = {"configurable": {"thread_id": conversation_id}}
        print(f"\n--- Iniciando/Continuando conversación ID: {conversation_id} ---")

        while True:
            user_input = input("Tú: ")
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("Agente: ¡Hasta luego!")
                break

            # Preparar la entrada para el grafo
            inputs = {"messages": [HumanMessage(content=user_input)]}
            print("--- Procesando... ---")
            events = []
            final_output_message = "Agente: (No se recibió respuesta)"

            try:
                # Usar stream con el config que incluye thread_id
                # Stream events
                print("\n--- Streaming Events ---")
                # CORRECCIÓN: recursion_limit no es válido para stream, eliminarlo.
                for event in graph.stream(inputs, config=config, stream_mode="values"): # Eliminado recursion_limit
                    # event es un diccionario con claves como 'messages', 'preferences', etc.
                    # Imprimimos la clave del nodo que acaba de terminar
                    keys = event.keys()

                    # Imprimir el último mensaje AIMessage que no sea una llamada a herramienta
                    if event.get("messages") and isinstance(event["messages"][-1], AIMessage) and not event["messages"][-1].tool_calls:
                         final_output_message = f"Agente: {event['messages'][-1].content}"

                # Imprimir la respuesta final del agente para este turno
                print(final_output_message)
                print("-" * 30 + "\n")

                # Opcional: Imprimir el estado final del turno para depuración
                # current_state = graph.get_state(config)
                # print("\n--- Estado Actual de la Conversación ---")
                # for key, value in current_state.values.items():
                #     print(f"- {key}: {value}")
                # print("-" * 30 + "\n")


            except Exception as e:
                logger.error(f"Error during graph execution for conversation {conversation_id}: {e}", exc_info=True)
                print("Agente: Lo siento, ocurrió un error al procesar tu mensaje.")
                # Podrías imprimir eventos hasta el error si es útil
                break # Salir del bucle en caso de error grave