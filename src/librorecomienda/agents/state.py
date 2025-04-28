# src/librorecomienda/agents/state.py

from typing import List, Optional, Dict, Any
# Annotated se movió a 'typing' en Python 3.9+
# Si usas una versión anterior, podría ser from typing_extensions import Annotated
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage

# Importa la función reductora para mensajes
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Define el estado del agente de recomendación de libros.
    Esta estructura se pasa entre los nodos del grafo LangGraph.

    Atributos:
        input: La última entrada (mensaje) del usuario.
        messages: El historial completo de la conversación. Utiliza add_messages
                  para asegurar que los nuevos mensajes se añadan correctamente.
        user_preferences: Un diccionario para almacenar las preferencias
                          extraídas del usuario (ej. géneros, autores, etc.).
        search_results: Una lista de resultados de búsqueda de libros
                        obtenidos de la base de datos.
        recommendations: Una lista de libros recomendados al usuario.
        explanations: Un diccionario que mapea IDs de libros recomendados
                      a sus explicaciones generadas.
    """
    input: Optional[str] # La última entrada del usuario

    # El historial de chat. 'add_messages' asegura que se añadan en lugar de reemplazarse.
    messages: Annotated[list[AnyMessage], add_messages]

    # Preferencias extraídas de la conversación
    user_preferences: Optional[Dict[str, Any]]

    # Resultados de la búsqueda en la base de datos (ej. lista de dicts con info de libros)
    search_results: Optional[List[Dict[str, Any]]]

    # Recomendaciones finales generadas (ej. lista de dicts con info de libros)
    recommendations: Optional[List[Dict[str, Any]]]

    # Explicaciones para cada recomendación (ej. {book_id: explanation_string})
    explanations: Optional[Dict[str, str]]
