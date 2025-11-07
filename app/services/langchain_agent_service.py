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
from app.repositories.message_repository import MessageRepository


class LangChainAgentService:
    """
    Servicio que maneja la interacción con usuarios mediante un agente LangChain.
    Utiliza Tool Use (Function Calling) para ejecutar acciones específicas con LangGraph.
    """
    
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.message_repo = MessageRepository(db)
        
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
- Suscribir usuarios a parqueaderos para recibir notificaciones (usa suscribirse_a_parqueadero) **[REQUIERE PREMIUM]**
- Ver y gestionar suscripciones activas (usa ver_mis_suscripciones)
- Desuscribir de parqueaderos (usa desuscribirse_de_parqueadero)
- **REPORTAR CUPOS**: Reportar que un parqueadero tiene cupos disponibles (usa reportar_cupos_disponibles)
- Ver reportes activos del conductor (usa ver_mis_reportes)
- **PROGRAMA DE REFERIDOS**: Ver estadísticas de referidos y código personal (usa ver_estadisticas_referidos)

**Instrucciones importantes:**
1. SIEMPRE usa las herramientas cuando el usuario solicite información o acciones
2. Para búsquedas de parqueaderos:
   - Si el usuario menciona nombre exacto, usa buscar_parqueadero_por_nombre
   - Si el usuario describe ubicación o características, USA buscar_parqueadero_semantico
   - Si el usuario pregunta "qué parqueaderos tienen cupos", "cuál tiene cupos", "hay otro", etc. -> USA ver_parqueaderos_disponibles
   - Ejemplos: "cerca al SD", "en la 72", "el del centro" -> buscar_parqueadero_semantico
3. Para reportes de cupos:
   - Si el usuario dice "hay cupos en [parqueadero]", usa reportar_cupos_disponibles
   - Necesitas el parqueadero_id, búscalo primero si solo tienes el nombre
4. **PROGRAMA DE REFERIDOS**:
   - Las notificaciones son PREMIUM (requieren código de referido o pago)
   - Cada usuario tiene un código único de 6 caracteres
   - Por cada referido que usa su código, gana 7 días de acceso premium
   - Si el usuario pregunta por notificaciones sin premium, explícale el paywall
   - Si pregunta por su código o referidos, usa ver_estadisticas_referidos
5. Sé amigable, conciso y útil
6. Usa emojis cuando sea apropiado
7. NO REPITAS el saludo si ya hay conversación previa
8. Responde en español de Colombia
9. Si el usuario hace una solicitud directa, EJECUTA la herramienta correspondiente primero
10. Nunca devuelvas el ID de los parqueaderos en la respuesta al usuario, solo la información relevante
11. SIEMPRE responde con la información actual de las herramientas, nunca inventes parqueaderos

**Patrones que DEBEN usar ver_parqueaderos_disponibles:**
- "qué parqueaderos tienen cupos"
- "cuál tiene cupos"
- "hay otro parqueadero"
- "¿ningún otro?"
- "cuáles están disponibles"
- "dime todos los parqueaderos"
- "ve qué hay disponible"

**Ejemplo:**
Usuario: "Busco el Tequendama que está cerca al SD"
Tú: [DEBES usar buscar_parqueadero_semantico("Tequendama cerca al SD")]
Luego presentas la información que retorna la herramienta.

**Ejemplo de consulta de disponibles:**
Usuario: "¿Ningún otro parqueadero?"
Tú: [DEBES usar ver_parqueaderos_disponibles()]
Luego presentas el resultado.

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
        
        # Obtener información del usuario
        usuario = self.user_repo.find_by_id(user_id)
        nombre_usuario = usuario.name if usuario and usuario.name else "Usuario"
        
        # Obtener herramientas
        parqueadero_tools = create_parqueadero_tools(self.db)
        suscripcion_tools = create_suscripcion_tools(self.db, user_id)
        reporte_tools = create_reporte_tools(self.db, user_id)
        tools = parqueadero_tools + suscripcion_tools + reporte_tools
        
        # Crear prompt personalizado con el nombre del usuario
        system_prompt = f"{self._get_conductor_system_prompt()}\n\n**INFORMACIÓN DEL USUARIO:** Estás hablando con {nombre_usuario}."
        
        # Crear agente con LangGraph usando el prompt como system message
        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.memory,
            prompt=system_prompt
        )
        
        return agent
    
    def _create_gestor_agent(self, user_id: str):
        """Crea un agente especializado para gestores usando LangGraph"""
        
        # Obtener información del usuario
        usuario = self.user_repo.find_by_id(user_id)
        nombre_usuario = usuario.name if usuario and usuario.name else "Gestor"
        
        # Obtener herramientas
        gestor_tools = create_gestor_tools(self.db, user_id)
        parqueadero_tools = create_parqueadero_tools(self.db)
        tools = gestor_tools + [parqueadero_tools[1]]  # obtener_detalle_parqueadero
        
        # Crear prompt personalizado con el nombre del usuario
        system_prompt = f"{self._get_gestor_system_prompt()}\n\n**INFORMACIÓN DEL GESTOR:** Estás hablando con {nombre_usuario}."
        
        # Crear agente con LangGraph usando el prompt como system message
        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.memory,
            prompt=system_prompt
        )
        
        return agent
    
    def process_message(self, user_id: str, message: str, rol: str) -> str:
        """
        Procesa un mensaje del usuario usando el agente LangChain apropiado.
        Carga los últimos 5 mensajes desde MongoDB y guarda el nuevo intercambio.
        
        Args:
            user_id: ID del usuario en WhatsApp
            message: Mensaje de texto del usuario
            rol: Rol del usuario ('conductor' o 'gestor_parqueadero')
            
        Returns:
            str: Respuesta generada por el agente
        """
        try:
            # Guardar el mensaje del usuario en MongoDB
            self.message_repo.guardar_mensaje_usuario(user_id, message)
            
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
            
            # Cargar mensajes previos desde MongoDB (sin incluir el mensaje actual)
            mensajes_previos = self.message_repo.obtener_ultimos_mensajes(user_id, limite=5)
            
            # Convertir mensajes de MongoDB a formato LangChain
            langchain_messages = []
            
            # Cargar mensajes previos si existen
            for msg in mensajes_previos:
                if msg.rol == "user":
                    langchain_messages.append(HumanMessage(content=msg.contenido))
                elif msg.rol == "assistant":
                    langchain_messages.append(AIMessage(content=msg.contenido))
            
            # Agregar el mensaje actual
            langchain_messages.append(HumanMessage(content=message))
            
            # Actualizar el estado del agente con los mensajes de MongoDB
            if len(langchain_messages) > 0:
                agent.update_state(config, {"messages": langchain_messages})
            
            # Ejecutar el agente con el nuevo mensaje
            result = agent.invoke(
                {"messages": langchain_messages},
                config=config
            )
            
            # Extraer la respuesta del agente
            messages = result.get("messages", [])
            respuesta = "No pude procesar tu mensaje. Por favor, intenta nuevamente."
            
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, AIMessage):
                    respuesta = last_message.content
            
            # Guardar la respuesta del asistente en MongoDB
            self.message_repo.guardar_mensaje_asistente(user_id, respuesta)
            
            # Desactivar mensajes antiguos para mantener solo los últimos 10 activos
            # (los mensajes no se eliminan, solo se marcan como inactivos)
            desactivados = self.message_repo.desactivar_mensajes_antiguos(user_id, mantener_ultimos=10)
            if desactivados > 0:
                print(f"📦 Archivado automático: {desactivados} mensajes marcados como inactivos para {user_id}")
            
            return respuesta
            
        except Exception as e:
            print(f"Error procesando mensaje con agente LangChain: {e}")
            import traceback
            traceback.print_exc()
            return "❌ Ocurrió un error al procesar tu mensaje. Por favor, intenta nuevamente."
    
    def reset_conversation(self, user_id: str):
        """Reinicia la conversación de un usuario y marca los mensajes como inactivos en MongoDB"""
        # Eliminar del cache
        keys_to_delete = [key for key in self.agents_cache.keys() if key.startswith(user_id)]
        for key in keys_to_delete:
            del self.agents_cache[key]
        
        # Marcar todos los mensajes como inactivos (no se eliminan, se archivan)
        mensajes_desactivados = self.message_repo.limpiar_conversacion(user_id)
        print(f"� Conversación reiniciada para {user_id}. {mensajes_desactivados} mensajes archivados (marcados como inactivos).")
    
    def get_conversation_context(self, user_id: str) -> List[Dict[str, str]]:
        """
        Obtiene el contexto de los últimos 5 mensajes de la conversación del usuario desde MongoDB.
        
        Returns:
            List[Dict]: Lista de máximo 5 mensajes con formato {"role": "user/assistant", "content": "..."}
        """
        try:
            # Obtener mensajes desde MongoDB
            mensajes = self.message_repo.obtener_ultimos_mensajes(user_id, limite=5)
            
            context = []
            for msg in mensajes:
                context.append({
                    "role": msg.rol,
                    "content": msg.contenido,
                    "timestamp": msg.timestamp
                })
            
            return context
        except Exception as e:
            print(f"Error obteniendo contexto de conversación: {e}")
            return []
