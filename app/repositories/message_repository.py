from app.repositories.base_repository import BaseRepository
from app.models.whatsapp_webhook import Message
from app.models.database_models import MensajeConversacion
from app.utils.tiempo_utils import obtener_tiempo_bogota
from typing import List


class MessageRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "mensajes", Message)
        # Colección separada para mensajes de conversación con el agente
        self.conversacion_collection = db["mensajes_conversacion"]

    def crear_mensaje(self, mensaje: dict):
        self.collection.insert_one(mensaje)

    def obtener_mensajes(self, usuario_id):
        return self.collection.find({"to": usuario_id})

    def eliminar_mensaje(self, mensaje_id):
        self.collection.delete_one({"_id": mensaje_id})
    
    # ===== MÉTODOS PARA MENSAJES DE CONVERSACIÓN CON EL AGENTE =====
    
    def guardar_mensaje_usuario(self, user_id: str, contenido: str) -> MensajeConversacion:
        """
        Guarda un mensaje del usuario en la conversación.
        
        Args:
            user_id: WhatsApp ID del usuario
            contenido: Contenido del mensaje del usuario
            
        Returns:
            MensajeConversacion: Mensaje guardado
        """
        mensaje = {
            "user_id": user_id,
            "rol": "user",
            "contenido": contenido,
            "timestamp": obtener_tiempo_bogota(),
            "activo": True
        }
        
        result = self.conversacion_collection.insert_one(mensaje)
        mensaje["_id"] = str(result.inserted_id)
        return MensajeConversacion(**mensaje)
    
    def guardar_mensaje_asistente(self, user_id: str, contenido: str) -> MensajeConversacion:
        """
        Guarda la respuesta del asistente (LLM) en la conversación.
        
        Args:
            user_id: WhatsApp ID del usuario
            contenido: Contenido de la respuesta del asistente
            
        Returns:
            MensajeConversacion: Mensaje guardado
        """
        mensaje = {
            "user_id": user_id,
            "rol": "assistant",
            "contenido": contenido,
            "timestamp": obtener_tiempo_bogota(),
            "activo": True
        }
        
        result = self.conversacion_collection.insert_one(mensaje)
        mensaje["_id"] = str(result.inserted_id)
        return MensajeConversacion(**mensaje)
    
    def obtener_ultimos_mensajes(self, user_id: str, limite: int = 5) -> List[MensajeConversacion]:
        """
        Obtiene los últimos N mensajes ACTIVOS de la conversación de un usuario.
        Los mensajes se ordenan por timestamp ascendente (más antiguos primero).
        
        Args:
            user_id: WhatsApp ID del usuario
            limite: Número máximo de mensajes a obtener (por defecto 5)
            
        Returns:
            List[MensajeConversacion]: Lista de mensajes activos ordenados por timestamp
        """
        # Obtener los últimos N mensajes ACTIVOS ordenados por timestamp descendente
        mensajes_cursor = self.conversacion_collection.find(
            {"user_id": user_id, "activo": True}
        ).sort("timestamp", -1).limit(limite * 2)  # *2 para obtener pares completos
        
        mensajes = []
        for doc in mensajes_cursor:
            doc["_id"] = str(doc["_id"])
            mensajes.append(MensajeConversacion(**doc))
        
        # Invertir para tener orden cronológico (más antiguos primero)
        mensajes.reverse()
        
        # Limitar a los últimos N pares de mensajes (user + assistant)
        return mensajes[-limite*2:]
    
    def limpiar_conversacion(self, user_id: str) -> int:
        """
        Marca todos los mensajes de conversación de un usuario como inactivos.
        No elimina los mensajes, solo los desactiva para mantener el historial.
        
        Args:
            user_id: WhatsApp ID del usuario
            
        Returns:
            int: Número de mensajes marcados como inactivos
        """
        result = self.conversacion_collection.update_many(
            {"user_id": user_id, "activo": True},
            {"$set": {"activo": False}}
        )
        return result.modified_count
    
    def contar_mensajes_conversacion(self, user_id: str, solo_activos: bool = True) -> int:
        """
        Cuenta el número de mensajes en la conversación de un usuario.
        
        Args:
            user_id: WhatsApp ID del usuario
            solo_activos: Si es True, cuenta solo mensajes activos. Si es False, cuenta todos.
            
        Returns:
            int: Número de mensajes
        """
        filtro = {"user_id": user_id}
        if solo_activos:
            filtro["activo"] = True
        return self.conversacion_collection.count_documents(filtro)
    
    def desactivar_mensajes_antiguos(self, user_id: str, mantener_ultimos: int = 10) -> int:
        """
        Marca como inactivos los mensajes antiguos, manteniendo solo los últimos N activos.
        Los mensajes no se eliminan, solo se desactivan para mantener el historial completo.
        
        Args:
            user_id: WhatsApp ID del usuario
            mantener_ultimos: Número de mensajes activos a mantener (por defecto 10)
            
        Returns:
            int: Número de mensajes marcados como inactivos
        """
        # Obtener todos los mensajes ACTIVOS del usuario ordenados por timestamp descendente
        mensajes_activos = list(self.conversacion_collection.find(
            {"user_id": user_id, "activo": True}
        ).sort("timestamp", -1))
        
        # Si hay más mensajes activos de los que queremos mantener
        if len(mensajes_activos) > mantener_ultimos:
            # Obtener los IDs de los mensajes a desactivar (los más antiguos)
            mensajes_a_desactivar = mensajes_activos[mantener_ultimos:]
            ids_a_desactivar = [msg["_id"] for msg in mensajes_a_desactivar]
            
            # Marcar los mensajes antiguos como inactivos
            result = self.conversacion_collection.update_many(
                {"_id": {"$in": ids_a_desactivar}},
                {"$set": {"activo": False}}
            )
            
            return result.modified_count
        
        return 0
    
    def obtener_historial_completo(self, user_id: str) -> List[MensajeConversacion]:
        """
        Obtiene TODOS los mensajes (activos e inactivos) de un usuario.
        Útil para análisis o auditoría del historial completo.
        
        Args:
            user_id: WhatsApp ID del usuario
            
        Returns:
            List[MensajeConversacion]: Lista completa de mensajes ordenados por timestamp
        """
        mensajes_cursor = self.conversacion_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", 1)  # Orden ascendente (del más antiguo al más reciente)
        
        mensajes = []
        for doc in mensajes_cursor:
            doc["_id"] = str(doc["_id"])
            mensajes.append(MensajeConversacion(**doc))
        
        return mensajes
    
    def reactivar_mensajes(self, user_id: str, cantidad: int = 10) -> int:
        """
        Reactiva los últimos N mensajes inactivos de un usuario.
        Útil si se quiere recuperar conversaciones antiguas.
        
        Args:
            user_id: WhatsApp ID del usuario
            cantidad: Número de mensajes a reactivar
            
        Returns:
            int: Número de mensajes reactivados
        """
        # Obtener los últimos N mensajes INACTIVOS
        mensajes_inactivos = list(self.conversacion_collection.find(
            {"user_id": user_id, "activo": False}
        ).sort("timestamp", -1).limit(cantidad))
        
        if len(mensajes_inactivos) > 0:
            ids_a_reactivar = [msg["_id"] for msg in mensajes_inactivos]
            
            result = self.conversacion_collection.update_many(
                {"_id": {"$in": ids_a_reactivar}},
                {"$set": {"activo": True}}
            )
            
            return result.modified_count
        
        return 0