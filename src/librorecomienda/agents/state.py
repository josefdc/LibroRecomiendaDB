# src/librorecomienda/agents/state.py

"""
Define la estructura de estado compartida entre los nodos del agente conversacional de recomendaciones de libros.
Este estado es utilizado y modificado por los distintos nodos del grafo LangGraph durante la conversación.
Incluye historial de mensajes, preferencias del usuario, resultados de búsqueda, recomendaciones y explicaciones.
"""

from typing import List, Optional, Dict, Any, Annotated
from typing import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Representa el estado del agente de recomendación de libros durante la conversación.

    Atributos:
        input (Optional[str]): La última entrada (mensaje) del usuario.
        messages (Annotated[list[AnyMessage], add_messages]): El historial completo de la conversación.
            Utiliza 'add_messages' para asegurar que los nuevos mensajes se añadan correctamente.
        user_preferences (Optional[Dict[str, Any]]): Diccionario con las preferencias extraídas del usuario
            (por ejemplo, géneros, autores, etc.).
        search_results (Optional[List[Dict[str, Any]]]): Lista de resultados de búsqueda de libros obtenidos de la base de datos.
        recommendations (Optional[List[Dict[str, Any]]]): Lista de libros recomendados al usuario.
        explanations (Optional[Dict[str, str]]): Diccionario que mapea IDs de libros recomendados a sus explicaciones generadas.
    """
    input: Optional[str]
    messages: Annotated[List[AnyMessage], add_messages]
    user_preferences: Optional[Dict[str, Any]]
    search_results: Optional[List[Dict[str, Any]]]
    recommendations: Optional[List[Dict[str, Any]]]
    explanations: Optional[Dict[str, str]]
