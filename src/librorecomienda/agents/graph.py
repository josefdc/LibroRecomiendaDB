"""
Módulo principal para la construcción y ejecución del grafo conversacional del agente de recomendaciones de libros.
Define los nodos, lógica de enrutamiento y configuración del grafo usando LangGraph y LangChain.
Incluye integración con herramientas externas, manejo de preferencias del usuario y generación de recomendaciones.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, ToolMessage
from typing import Dict, Any, Optional, List, Callable
import logging
import json
from .state import AgentState

try:
    from .tools import agent_tools, CRUD_AVAILABLE
except ImportError as e:
    logging.error(
        f"Failed to import agent_tools or CRUD_AVAILABLE from .tools: {e}. Graph might not function correctly."
    )
    agent_tools = []
    CRUD_AVAILABLE = False

logger = logging.getLogger(__name__)

llm: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools: ChatOpenAI = llm.bind_tools(agent_tools) if agent_tools else llm

def call_model(state: AgentState) -> Dict[str, Any]:
    """
    Nodo principal: Llama al LLM con el historial actual.
    El LLM decidirá si responder directamente, hacer una pregunta,
    o solicitar el uso de una herramienta.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        Dict[str, Any]: Diccionario con la(s) respuesta(s) del modelo.
    """
    logger.info("--- Calling Main LLM Node ---")
    messages: List[BaseMessage] = state['messages']
    preferences: Optional[Dict[str, Any]] = state.get('user_preferences')
    logger.info(f"LLM Node Received State: Preferences = {preferences}")
    current_llm: ChatOpenAI = llm_with_tools if agent_tools else llm
    logger.debug(f"Messages sent to LLM: {messages}")
    try:
        response: AIMessage = current_llm.invoke(messages)
        logger.debug(f"LLM Response: {response}")
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Error invoking LLM in call_model: {e}", exc_info=True)
        error_message: str = "Lo siento, tuve un problema al procesar tu solicitud. Por favor, inténtalo de nuevo."
        return {"messages": [AIMessage(content=error_message)]}

def gather_preferences_node(state: AgentState) -> Dict[str, List[BaseMessage]]:
    """
    Genera una pregunta específica para obtener preferencias del usuario.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        Dict[str, List[BaseMessage]]: Mensaje con la pregunta generada.
    """
    logger.info("--- Gathering Preferences Node ---")
    preferences: Dict[str, Any] = state.get('user_preferences') or {}
    if not preferences.get('preferred_genres'):
        question: str = "¿Qué géneros de libros te gustan más?"
    elif not preferences.get('liked_authors'):
        question = "¿Tienes algún autor preferido?"
    else:
        question = "¿Hay algo más que te gustaría contarme sobre tus gustos literarios para afinar la búsqueda?"
    return {"messages": [AIMessage(content=question)]}

def process_user_response_node(state: AgentState) -> Dict[str, Dict]:
    """
    Procesa la última respuesta del usuario para extraer preferencias.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        Dict[str, Dict]: Diccionario con las preferencias extraídas o actuales.
    """
    logger.info("--- Processing User Response Node ---")
    if not state['messages'] or not isinstance(state['messages'][-1], HumanMessage):
        logger.warning("No user message found to process for preferences.")
        return {}
    last_user_message: str = state['messages'][-1].content
    current_preferences: Dict[str, Any] = state.get('user_preferences') or {}
    logger.info(f"Processing user message: '{last_user_message}' with current prefs: {current_preferences}")

    prompt: str = f"""
Analiza la siguiente respuesta del usuario y extrae sus preferencias de lectura (géneros, autores, libros mencionados, etc.).
Preferencias actuales conocidas: {current_preferences}
Respuesta del usuario: "{last_user_message}"
Devuelve SOLAMENTE un diccionario JSON actualizado con las preferencias encontradas. Si encuentras nuevas preferencias, añádelas o actualiza las existentes. Si no se mencionan preferencias claras, devuelve el diccionario actual o uno vacío si no había nada antes. NO incluyas explicaciones, solo el JSON.
Ejemplo de formato de salida: {{"preferred_genres": ["Ciencia Ficción", "Fantasía"], "liked_authors": ["Brandon Sanderson"]}}
Formato de salida estricto: {{...}}
"""
    try:
        logger.debug("Calling LLM to extract preferences.")
        response: AIMessage = llm.invoke(prompt)
        logger.debug(f"LLM response for preferences: {response.content}")

        content_to_parse: str = response.content.strip()
        if content_to_parse.startswith("```json"):
            content_to_parse = content_to_parse[7:]
        if content_to_parse.endswith("```"):
            content_to_parse = content_to_parse[:-3]
        content_to_parse = content_to_parse.strip()

        if not content_to_parse or content_to_parse == '{}':
            extracted_prefs: Dict[str, Any] = {}
        else:
            extracted_prefs = json.loads(content_to_parse)

        if not isinstance(extracted_prefs, dict):
            raise ValueError("LLM did not return a valid JSON dictionary.")

        logger.info(f"Extracted preferences: {extracted_prefs}")
        updated_preferences: Dict[str, Any] = {**current_preferences, **extracted_prefs}
        updated_preferences = {k: v for k, v in updated_preferences.items() if v}
        logger.info(f"Updated preferences state: {updated_preferences}")
        return {"user_preferences": updated_preferences}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response for preferences: {e}. Response was: {response.content}")
        return {"user_preferences": current_preferences}
    except Exception as e:
        logger.error(f"Failed to process user response for preferences: {e}", exc_info=True)
        return {"user_preferences": current_preferences}

def generate_recommendations_node(state: AgentState) -> Dict[str, Any]:
    """
    Genera recomendaciones basadas en preferencias y resultados de búsqueda válidos.
    Actualiza 'search_results' en el estado con los resultados procesados.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        Dict[str, Any]: Diccionario con recomendaciones y resultados de búsqueda, o mensaje de error.
    """
    logger.info("--- Generating Recommendations Node ---")
    preferences: Optional[Dict[str, Any]] = state.get('user_preferences')
    processed_search_results: List[Dict[str, Any]] = []

    if state['messages']:
        for msg in reversed(state['messages']):
            if isinstance(msg, ToolMessage) and msg.name == 'search_books' and msg.content:
                try:
                    content_data: Any = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                    if isinstance(content_data, list):
                        valid_results: List[Dict[str, Any]] = [
                            item for item in content_data
                            if isinstance(item, dict) and 'error' not in item and 'not_found' not in item
                        ]
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
        return {"messages": [AIMessage(content="No encontré resultados de búsqueda relevantes para generar recomendaciones. ¿Podrías intentar buscar con otros términos o refinar tus preferencias?")]}

    recommendations: List[Dict[str, Any]] = []
    preferred_genres: List[str] = preferences.get('preferred_genres', [])
    if isinstance(preferred_genres, str):
        preferred_genres = [preferred_genres]
    elif not isinstance(preferred_genres, list):
        preferred_genres = []

    logger.debug(f"Filtering {len(processed_search_results)} search results based on preferred genres: {preferred_genres}")

    genre_filtered_recs: List[Dict[str, Any]] = []
    if preferred_genres:
        for book in processed_search_results:
            book_genre: Optional[str] = book.get('genre')
            if book_genre and any(pref_genre.lower() in book_genre.lower() for pref_genre in preferred_genres):
                genre_filtered_recs.append(book)
    else:
        genre_filtered_recs = processed_search_results[:]

    recommendations = genre_filtered_recs[:3]

    if not recommendations and processed_search_results:
        logger.info("No specific genre matches found, taking top search results.")
        recommendations = processed_search_results[:3]
    elif len(recommendations) < 3 and len(processed_search_results) > len(recommendations):
        logger.info("Filling remaining recommendations with top search results.")
        existing_ids = {rec['id'] for rec in recommendations if rec.get('id')}
        for book in processed_search_results:
            if book.get('id') not in existing_ids:
                recommendations.append(book)
                if len(recommendations) >= 3:
                    break

    logger.info(f"Generated {len(recommendations)} recommendations.")
    return {"recommendations": recommendations, "search_results": processed_search_results}

def generate_explanations_node(state: AgentState) -> Dict[str, Dict[str, str]]:
    """
    Genera explicaciones para cada libro recomendado.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        Dict[str, Dict[str, str]]: Diccionario con explicaciones por ID de libro.
    """
    logger.info("--- Generating Explanations Node ---")
    recommendations: Optional[List[Dict[str, Any]]] = state.get('recommendations')
    preferences: Optional[Dict[str, Any]] = state.get('user_preferences')
    explanations: Dict[str, str] = {}

    if not recommendations:
        logger.warning("No recommendations available to generate explanations.")
        return {"explanations": {}}

    prefs_str: str = json.dumps(preferences) if preferences else "ninguna preferencia específica mencionada"

    for book in recommendations:
        book_id = book.get('id')
        if book_id is None:
            continue
        book_id_str: str = str(book_id)
        book_info: str = (
            f"Título: {book.get('title', 'N/A')}, Autor: {book.get('author', 'N/A')}, "
            f"Género: {book.get('genre', 'N/A')}, Rating: {book.get('average_rating', 'N/A')}"
        )
        prompt: str = f"""
Dado que un usuario tiene estas preferencias: {prefs_str}.
Explica brevemente (1-2 frases) por qué el siguiente libro podría gustarle.
Libro: {book_info}.
Enfócate en conectar el libro con las preferencias si es posible. Si no hay conexión clara, da una razón general basada en el libro mismo. Sé conciso y directo.
"""
        try:
            logger.debug(f"Generating explanation for book ID {book_id_str}")
            response: AIMessage = llm.invoke(prompt)
            explanations[book_id_str] = response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate explanation for book ID {book_id_str}: {e}", exc_info=True)
            explanations[book_id_str] = "No se pudo generar una explicación detallada en este momento."

    logger.info(f"Generated explanations for {len(explanations)} recommendations.")
    return {"explanations": explanations}

def format_output_node(state: AgentState) -> Dict[str, List[BaseMessage]]:
    """
    Formatea la salida final (recomendaciones + explicaciones o mensaje de error) para el usuario.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        Dict[str, List[BaseMessage]]: Mensaje(s) formateados para el usuario.
    """
    logger.info("--- Formatting Output Node ---")
    recommendations: Optional[List[Dict[str, Any]]] = state.get('recommendations')
    explanations: Dict[str, str] = state.get('explanations') or {}

    last_ai_message: Optional[AIMessage] = None
    if state.get('messages'):
        for msg in reversed(state['messages']):
            if isinstance(msg, AIMessage):
                last_ai_message = msg
                break

    if not recommendations and last_ai_message:
        possible_error_starts: List[str] = ["Necesito entender mejor", "No encontré resultados"]
        if any(last_ai_message.content.startswith(start) for start in possible_error_starts):
            logger.info("Formatting output based on message from previous node.")
            return {"messages": [last_ai_message]}

    if not recommendations:
        logger.info("No recommendations to format and no specific message found.")
        message: str = "Lo siento, no pude generar recomendaciones en este momento."
        return {"messages": [AIMessage(content=message)]}

    response_parts: List[str] = ["Aquí tienes algunas recomendaciones que podrían gustarte:\n"]
    for book in recommendations:
        book_id = book.get('id')
        book_id_str: str = str(book_id) if book_id is not None else 'unknown'
        explanation: str = explanations.get(book_id_str, "Una opción interesante basada en tu búsqueda.")

        title: str = book.get('title', 'Título Desconocido')
        author: str = book.get('author', 'Autor Desconocido')
        rating = book.get('average_rating')
        rating_str: str = f" (Rating: {rating}/5)" if rating is not None else ""

        response_parts.append(f"\n- **{title}** por {author}{rating_str}:")
        response_parts.append(f"  *Por qué te podría gustar:* {explanation}")

    response_parts.append("\n\n¿Te gustaría obtener más detalles sobre alguno de estos libros, buscar algo diferente o refinar las preferencias?")
    final_response: str = "\n".join(response_parts)

    logger.info("Formatted final response for the user.")
    return {"messages": [AIMessage(content=final_response)]}

def route_after_llm(state: AgentState) -> str:
    """
    Decide el siguiente nodo DESPUÉS de que el nodo LLM principal haya ejecutado.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        str: Nombre del siguiente nodo o END.
    """
    logger.info("--- Routing Logic (After LLM) ---")
    messages: List[BaseMessage] = state['messages']
    if not messages:
        logger.warning("Routing (After LLM) called with empty messages.")
        return END
    last_message: BaseMessage = messages[-1]
    preferences: Dict[str, Any] = state.get('user_preferences') or {}

    logger.info(f"Routing (After LLM) Check: Last message type = {type(last_message)}")
    logger.info(f"Routing (After LLM) Check: Preferences in state = {preferences}")

    if not isinstance(last_message, AIMessage):
        logger.error(f"Routing (After LLM) expected AIMessage, got {type(last_message)}. Routing to END.")
        return END

    if last_message.tool_calls:
        if agent_tools:
            logger.info("Routing decision (After LLM): Go to tools")
            return "tools"
        else:
            logger.warning("Routing decision (After LLM): LLM requested tools, but none available. Ending.")
            return END
    else:
        if not preferences or not preferences.get('preferred_genres'):
            logger.info("Routing decision (After LLM): Gather preferences (LLM responded, but prefs still missing)")
            return "gather_preferences"
        else:
            if len(messages) > 1 and isinstance(messages[-2], ToolMessage) and messages[-2].name == 'search_books':
                tool_msg: ToolMessage = messages[-2]
                tool_results_content: Optional[List[Dict[str, Any]]] = None
                try:
                    content_data: Any = json.loads(tool_msg.content) if isinstance(tool_msg.content, str) else tool_msg.content
                    if isinstance(content_data, list):
                        tool_results_content = [item for item in content_data if isinstance(item, dict) and 'error' not in item]
                except Exception as e:
                    logger.error(f"Routing (After LLM) failed to parse ToolMessage content: {e}")

                if tool_results_content:
                    logger.info("Routing decision (After LLM): Generate recommendations (LLM processed successful tool call)")
                    return "generate_recommendations"
                else:
                    logger.info("Routing decision (After LLM): END (LLM processed failed/empty tool call, wait for user)")
                    return END
            else:
                logger.info("Routing decision (After LLM): END (LLM responded conversationally, wait for user)")
                return END

    logger.warning(f"Routing (After LLM) reached fallback for message type: {type(last_message)}")
    return END

def route_entry(state: AgentState) -> str:
    """
    Determina el primer nodo a ejecutar basado en el último mensaje añadido.
    Actúa como dispatcher principal tras añadir un mensaje al estado.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        str: Nombre del primer nodo a ejecutar.
    """
    logger.info("--- Routing Logic (Entry) ---")
    messages: List[BaseMessage] = state['messages']
    if not messages:
        logger.info("Routing decision (Entry): No messages, go to LLM (initial state)")
        return "llm"

    last_message: BaseMessage = messages[-1]
    logger.info(f"Routing (Entry) Check: Last message type = {type(last_message)}")

    if isinstance(last_message, HumanMessage):
        logger.info("Routing decision (Entry): Human message, go to process_user_response")
        return "process_user_response"
    elif isinstance(last_message, ToolMessage):
        logger.info("Routing decision (Entry): Tool message, go to LLM")
        return "llm"
    elif isinstance(last_message, AIMessage):
        logger.info("Routing decision (Entry): AIMessage received. Assuming previous node handles next step or ending turn. Defaulting to LLM if called unexpectedly.")
        return "llm"
    else:
        logger.warning(f"Routing (Entry): Unknown last message type {type(last_message)}. Ending.")
        return END

graph_builder: StateGraph = StateGraph(AgentState)
graph_builder.add_node("llm", call_model)
if agent_tools:
    tool_node: ToolNode = ToolNode(agent_tools)
    graph_builder.add_node("tools", tool_node)
graph_builder.add_node("gather_preferences", gather_preferences_node)
graph_builder.add_node("process_user_response", process_user_response_node)
graph_builder.add_node("generate_recommendations", generate_recommendations_node)
graph_builder.add_node("generate_explanations", generate_explanations_node)
graph_builder.add_node("format_output", format_output_node)

graph_builder.add_conditional_edges(
    START,
    route_entry,
    {
        "process_user_response": "process_user_response",
        "llm": "llm",
        END: END
    }
)
graph_builder.add_edge("process_user_response", "llm")
if "tools" in graph_builder.nodes:
    graph_builder.add_edge("tools", "llm")
graph_builder.add_edge("gather_preferences", END)

routing_map_after_llm: Dict[str, str] = {
    "tools": "tools",
    "gather_preferences": "gather_preferences",
    "generate_recommendations": "generate_recommendations",
    END: END
}
if "tools" not in graph_builder.nodes:
    del routing_map_after_llm["tools"]

graph_builder.add_conditional_edges(
    "llm",
    route_after_llm,
    routing_map_after_llm
)

def check_recommendation_output(state: AgentState) -> str:
    """
    Determina el siguiente nodo tras generar recomendaciones.

    Args:
        state (AgentState): Estado actual del agente.

    Returns:
        str: Nombre del siguiente nodo.
    """
    last_message: Optional[BaseMessage] = state['messages'][-1] if state.get('messages') else None
    if isinstance(last_message, AIMessage) and any(
        last_message.content.startswith(start) for start in ["Necesito entender mejor", "No encontré resultados"]
    ):
        logger.info("Routing after generate_recommendations: Found message, routing to format_output.")
        return "format_output"
    elif state.get('recommendations'):
        logger.info("Routing after generate_recommendations: Found recommendations, routing to generate_explanations.")
        return "generate_explanations"
    else:
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
graph_builder.add_edge("format_output", END)

memory: MemorySaver = MemorySaver()
try:
    graph = graph_builder.compile(checkpointer=memory)
    logger.info("Graph compiled successfully with MemorySaver checkpointer.")
except Exception as e:
    logger.error(f"Error compiling graph with checkpointer: {e}", exc_info=True)
    graph = None

if __name__ == "__main__":
    """
    Prueba interactiva básica del grafo conversacional.
    Permite simular una conversación en consola con el agente.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting graph test execution with MemorySaver...")

    if graph is None:
        logger.error("Graph could not be compiled. Aborting test.")
    elif not CRUD_AVAILABLE:
        logger.error("CRUD functions not available (check tools.py imports/setup). Skipping graph execution test.")
    else:
        conversation_id: str = "test_conversation_123"
        config: Dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
        print(f"\n--- Iniciando/Continuando conversación ID: {conversation_id} ---")

        while True:
            user_input: str = input("Tú: ")
            if user_input.lower() in ["salir", "exit", "quit"]:
                print("Agente: ¡Hasta luego!")
                break

            inputs: Dict[str, List[HumanMessage]] = {"messages": [HumanMessage(content=user_input)]}
            print("--- Procesando... ---")
            final_output_message: str = "Agente: (No se recibió respuesta)"

            try:
                print("\n--- Streaming Events ---")
                for event in graph.stream(inputs, config=config, stream_mode="values"):
                    if event.get("messages") and isinstance(event["messages"][-1], AIMessage) and not event["messages"][-1].tool_calls:
                        final_output_message = f"Agente: {event['messages'][-1].content}"

                print(final_output_message)
                print("-" * 30 + "\n")
            except Exception as e:
                logger.error(f"Error during graph execution for conversation {conversation_id}: {e}", exc_info=True)
                print("Agente: Lo siento, ocurrió un error al procesar tu mensaje.")
                break