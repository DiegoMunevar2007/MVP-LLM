"""
Servicio de agente LangChain para manejar conversaciones de WhatsApp
con Tool Use (Function Calling) usando LangGraph
"""
import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages     import HumanMessage, AIMessage, SystemMessage

from app.tools.parqueadero_tools import create_parqueadero_tools
from app.tools.suscripcion_tools import create_suscripcion_tools
from app.tools.gestor_tools import create_gestor_tools
from app.tools.reporte_tools import create_reporte_tools
from app.repositories.user_repositories import UserRepository


class LangChainAgentService:
    """
    Servicio que maneja la interacción con usuarios mediante un agente LangChain.
    Utiliza Tool Use (Function Calling) para ejecutar acciones específicas con LangGraph.
    """
    
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        
        # Configurar LLM de OpenAI
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Memory saver para persistir conversaciones
        self.memory = MemorySaver()
        
        # Cache de agentes por usuario
        self.agents_cache = {}
    
    def _get_conductor_system_prompt(self) -> str:
        """Retorna el prompt del sistema para conductores"""
        return """Eres un asistente virtual para un sistema de gestión de parqueaderos en Bogotá, Colombia. 
Tu rol es ayudar a conductores a encontrar parqueaderos con cupos disponibles y gestionar sus suscripciones.

**IMPORTANTE: Debes USAR las herramientas disponibles para responder a las solicitudes del usuario.**

**Tus capacidades incluyen:**
- Consultar parqueaderos con cupos disponibles (usa la herramienta ver_parqueaderos_disponibles)
- Mostrar detalles de parqueaderos específicos (usa obtener_detalle_parqueadero)
- **BÚSQUEDA INTELIGENTE**: Buscar parqueaderos por descripción aproximada (usa buscar_parqueadero_semantico)
- Buscar por nombre exacto (usa buscar_parqueadero_por_nombre)
- Suscribir usuarios a parqueaderos para recibir notificaciones (usa suscribirse_a_parqueadero)
- Ver y gestionar suscripciones activas (usa ver_mis_suscripciones)
- Desuscribir de parqueaderos (usa desuscribirse_de_parqueadero)
- **REPORTAR CUPOS**: Reportar que un parqueadero tiene cupos disponibles (usa reportar_cupos_disponibles)
- Ver reportes activos del conductor (usa ver_mis_reportes)

**Instrucciones importantes:**
1. SIEMPRE usa las herramientas cuando el usuario solicite información o acciones
2. Para búsquedas de parqueaderos:
   - Si el usuario menciona nombre exacto, usa buscar_parqueadero_por_nombre
   - Si el usuario describe ubicación o características, USA buscar_parqueadero_semantico
   - Ejemplos: "cerca al SD", "en la 72", "el del centro" -> buscar_parqueadero_semantico
3. Para reportes de cupos:
   - Si el usuario dice "hay cupos en [parqueadero]", usa reportar_cupos_disponibles
   - Necesitas el parqueadero_id, búscalo primero si solo tienes el nombre
4. Sé amigable, conciso y útil
5. Usa emojis cuando sea apropiado
6. NO REPITAS el saludo si ya hay conversación previa
7. Responde en español de Colombia
8. Si el usuario hace una solicitud directa, EJECUTA la herramienta correspondiente primero

**Ejemplo:**
Usuario: "Busco el Tequendama que está cerca al SD"
Tú: [DEBES usar buscar_parqueadero_semantico("Tequendama cerca al SD")]
Luego presentas la información que retorna la herramienta.

**Ejemplo de reporte:**
Usuario: "Hay cupos en el Tequendama"
Tú: [DEBES buscar el parqueadero primero, luego usar reportar_cupos_disponibles(parqueadero_id)]"""

    def _get_gestor_system_prompt(self) -> str:
        """Retorna el prompt del sistema para gestores"""
        return """Eres un asistente virtual para gestores de parqueaderos en Bogotá, Colombia.
Tu rol es ayudar a los gestores a administrar su parqueadero y mantener actualizada la información de cupos.

**IMPORTANTE: Debes USAR las herramientas disponibles para responder a las solicitudes del usuario.**

**Tus capacidades incluyen:**
- Consultar información de su parqueadero (usa ver_mi_parqueadero)
- Actualizar la cantidad de cupos disponibles (usa actualizar_cupos)
- Cambiar el estado de disponibilidad (usa cambiar_estado_cupos)

**Instrucciones importantes:**
1. SIEMPRE usa las herramientas cuando el gestor solicite información o acciones
2. Sé profesional, claro y eficiente
3. Confirma siempre los cambios realizados
4. NO REPITAS el saludo si ya hay conversación previa
5. Responde en español de Colombia
6. Informa sobre las notificaciones enviadas"""

    def _create_conductor_agent(self, user_id: str):
        """Crea un agente especializado para conductores usando LangGraph"""
        
        # Obtener herramientas
        parqueadero_tools = create_parqueadero_tools(self.db)
        suscripcion_tools = create_suscripcion_tools(self.db, user_id)
        reporte_tools = create_reporte_tools(self.db, user_id)
        tools = parqueadero_tools + suscripcion_tools + reporte_tools
        
        # Crear agente con LangGraph usando el prompt como system message
        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.memory,
            prompt=self._get_conductor_system_prompt()
        )
        
        return agent
    
    def _create_gestor_agent(self, user_id: str):
        """Crea un agente especializado para gestores usando LangGraph"""
        
        # Obtener herramientas
        gestor_tools = create_gestor_tools(self.db, user_id)
        parqueadero_tools = create_parqueadero_tools(self.db)
        tools = gestor_tools + [parqueadero_tools[1]]  # obtener_detalle_parqueadero
        
        # Crear agente con LangGraph usando el prompt como system message
        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.memory,
            prompt=self._get_gestor_system_prompt()
        )
        
        return agent
    
    def process_message(self, user_id: str, message: str, rol: str) -> str:
        """
        Procesa un mensaje del usuario usando el agente LangChain apropiado.
        
        Args:
            user_id: ID del usuario en WhatsApp
            message: Mensaje de texto del usuario
            rol: Rol del usuario ('conductor' o 'gestor_parqueadero')
            
        Returns:
            str: Respuesta generada por el agente
        """
        try:
            # Crear configuración de thread para el usuario
            config = {"configurable": {"thread_id": user_id}}
            
            # Obtener o crear el agente apropiado
            cache_key = f"{user_id}_{rol}"
            if cache_key not in self.agents_cache:
                if rol == "conductor":
                    self.agents_cache[cache_key] = self._create_conductor_agent(user_id)
                elif rol == "gestor_parqueadero":
                    self.agents_cache[cache_key] = self._create_gestor_agent(user_id)
                else:
                    return "❌ Rol de usuario no reconocido. Contacta al administrador."
            
            agent = self.agents_cache[cache_key]
            
            # Obtener información del usuario para el primer mensaje
            state = agent.get_state(config)
            if len(state.values.get("messages", [])) == 0:
                usuario = self.user_repo.find_by_id(user_id)
                if usuario and usuario.name:
                    # Agregar contexto del nombre en el primer mensaje
                    message = f"[Usuario: {usuario.name}] {message}"
            
            # Ejecutar el agente
            result = agent.invoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )
            
            # Extraer la respuesta del agente
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, AIMessage):
                    return last_message.content
            
            return "No pude procesar tu mensaje. Por favor, intenta nuevamente."
            
        except Exception as e:
            print(f"Error procesando mensaje con agente LangChain: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Ocurrió un error al procesar tu mensaje. Por favor, intenta nuevamente."
    
    def reset_conversation(self, user_id: str):
        """Reinicia la conversación de un usuario"""
        # Eliminar del cache
        for key in list(self.agents_cache.keys()):
            if key.startswith(user_id):
                del self.agents_cache[key]
    
    def get_conversation_context(self, user_id: str) -> List[Dict[str, str]]:
        """
        Obtiene el contexto de la conversación actual del usuario.
        
        Returns:
            List[Dict]: Lista de mensajes con formato {"role": "user/assistant", "content": "..."}
        """
        try:
            config = {"configurable": {"thread_id": user_id}}
            # Buscar el agente en cache
            for key, agent in self.agents_cache.items():
                if key.startswith(user_id):
                    state = agent.get_state(config)
                    messages = state.values.get("messages", [])
                    
                    context = []
                    for msg in messages:
                        if isinstance(msg, HumanMessage):
                            context.append({"role": "user", "content": msg.content})
                        elif isinstance(msg, AIMessage):
                            context.append({"role": "assistant", "content": msg.content})
                    
                    return context
            
            return []
        except:
            return []
