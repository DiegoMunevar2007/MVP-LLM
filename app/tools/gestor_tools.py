"""
Herramientas de LangChain para gestores de parqueaderos
"""
from langchain_core.tools import tool
from typing import Optional
from app.repositories.parqueadero_repository import ParqueaderoRepository
from app.repositories.user_repositories import GestorParqueaderoRepository
from app.services.notification_service import NotificationService


def create_gestor_tools(db, user_id: str):
    """Factory function para crear herramientas de gestor"""
    
    parqueadero_repo = ParqueaderoRepository(db)
    gestor_repo = GestorParqueaderoRepository(db)
    notification_service = NotificationService(db)
    
    def _inferir_estado(cupos_str: str) -> str:
        """Infiere el estado de ocupación basándose en los cupos disponibles"""
        try:
            # Extraer el número del string
            cupos_numero = cupos_str.replace("+", "").replace("-", "").split()[0]
            cupos = int(cupos_numero)
            
            if cupos == 0:
                return "Sin cupos disponibles"
            elif cupos <= 3:
                return "Pocos cupos disponibles"
            elif cupos <= 10:
                return "Disponibilidad moderada"
            else:
                return "Buena disponibilidad"
        except ValueError:
            return "Cupos disponibles"
    
    @tool
    def ver_mi_parqueadero() -> str:
        """
        Muestra la información del parqueadero que gestiona el usuario actual.
        
        Returns:
            str: Información detallada del parqueadero gestionado
        """
        # Obtener información del gestor
        gestor = gestor_repo.find_by_id(user_id)
        if not gestor or not gestor.parqueadero_id:
            return "❌ No tienes un parqueadero asignado. Contacta al administrador."
        
        # Obtener información del parqueadero
        parqueadero = parqueadero_repo.find_by_id(gestor.parqueadero_id)
        if not parqueadero:
            return "❌ No se pudo encontrar la información de tu parqueadero."
        
        resultado = f"🅿️ **Tu Parqueadero: {parqueadero.name}**\n\n"
        resultado += f"📍 **Ubicación:** {parqueadero.ubicacion}\n"
        resultado += f"🏢 **Capacidad Total:** {parqueadero.capacidad} vehículos\n"
        
        cupos = parqueadero.rango_cupos or parqueadero.cupos_libres
        resultado += f"🚗 **Cupos Disponibles:** {cupos}\n"
        
        if parqueadero.estado_ocupacion:
            resultado += f"📊 **Estado:** {parqueadero.estado_ocupacion}\n"
        
        if parqueadero.ultima_actualizacion:
            resultado += f"🕐 **Última Actualización:** {parqueadero.ultima_actualizacion}\n"
        
        estado = "✅ Tiene cupos" if parqueadero.tiene_cupos else "❌ Sin cupos"
        resultado += f"\n**Estado Actual:** {estado}\n"
        resultado += f"**ID del Parqueadero:** `{parqueadero.id}`"
        
        return resultado
    
    @tool
    def actualizar_cupos(cupos_disponibles: str, descripcion_estado: Optional[str] = None) -> str:
        """
        Actualiza la cantidad de cupos disponibles en el parqueadero gestionado.
        Si hay cupos disponibles, notifica automáticamente a los suscriptores.
        
        Args:
            cupos_disponibles: Número exacto o rango de cupos (ej: "5", "10-15", "20+")
            descripcion_estado: Descripción opcional del estado (ej: "Casi lleno", "Disponible", "Muy ocupado")
            
        Returns:
            str: Mensaje de confirmación con número de notificaciones enviadas
        """
        # Obtener información del gestor
        gestor = gestor_repo.find_by_id(user_id)
        if not gestor or not gestor.parqueadero_id:
            return "❌ No tienes un parqueadero asignado."
        
        # Determinar si tiene cupos
        tiene_cupos = True
        cupos_numero = cupos_disponibles.replace("+", "").replace("-", "").split()[0]
        
        try:
            if int(cupos_numero) == 0:
                tiene_cupos = False
        except ValueError:
            # Si no se puede convertir, asumimos que hay cupos
            pass
        
        # Determinar rango y estado
        rango_cupos = cupos_disponibles
        estado_ocupacion = descripcion_estado or _inferir_estado(cupos_disponibles)
        
        # Actualizar parqueadero con notificaciones
        resultado_actualizacion = parqueadero_repo.actualizar_cupos_con_notificacion(
            gestor.parqueadero_id,
            cupos_numero,
            tiene_cupos,
            rango_cupos,
            estado_ocupacion,
            notification_service
        )
        
        parqueadero = resultado_actualizacion["parqueadero"]
        notificaciones = resultado_actualizacion["notificaciones_enviadas"]
        
        mensaje = f"✅ **Actualización exitosa**\n\n"
        mensaje += f"🅿️ **{parqueadero['name']}**\n"
        mensaje += f"🚗 Cupos actualizados: {rango_cupos}\n"
        mensaje += f"📊 Estado: {estado_ocupacion}\n"
        
        if notificaciones > 0:
            mensaje += f"\n📨 Se enviaron {notificaciones} notificaciones a conductores suscritos."
        else:
            mensaje += f"\n📭 No hay conductores suscritos para notificar."
        
        return mensaje
    
    @tool
    def cambiar_estado_cupos(tiene_cupos: bool) -> str:
        """
        Cambia el estado general de disponibilidad de cupos (tiene/no tiene cupos).
        
        Args:
            tiene_cupos: True si hay cupos disponibles, False si está lleno
            
        Returns:
            str: Mensaje de confirmación
        """
        # Obtener información del gestor
        gestor = gestor_repo.find_by_id(user_id)
        if not gestor or not gestor.parqueadero_id:
            return "❌ No tienes un parqueadero asignado."
        
        cupos = "0" if not tiene_cupos else "1+"
        estado = "Sin cupos disponibles" if not tiene_cupos else "Cupos disponibles"
        
        parqueadero = parqueadero_repo.actualizar_cupos_con_rango(
            gestor.parqueadero_id,
            cupos,
            tiene_cupos,
            cupos,
            estado
        )
        
        resultado = f"✅ Estado actualizado para **{parqueadero.name}**\n\n"
        resultado += f"📊 Estado: {estado}\n"
        
        if tiene_cupos:
            resultado += "\n💡 Tip: Puedes actualizar la cantidad exacta de cupos con la herramienta 'actualizar_cupos'"
        
        return resultado
    
    return [
        ver_mi_parqueadero,
        actualizar_cupos,
        cambiar_estado_cupos
    ]
