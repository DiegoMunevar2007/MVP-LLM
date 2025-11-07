"""
Herramientas de LangChain para gestionar suscripciones de conductores
"""
from langchain_core.tools import tool
from typing import List, Optional
from app.repositories.suscripcion_repository import SuscripcionRepository
from app.repositories.parqueadero_repository import ParqueaderoRepository
from app.services.premium_service import PremiumService


def create_suscripcion_tools(db, user_id: str):
    """Factory function para crear herramientas de suscripción"""
    
    suscripcion_repo = SuscripcionRepository(db)
    parqueadero_repo = ParqueaderoRepository(db)
    premium_service = PremiumService(db)
    
    @tool
    def suscribirse_a_parqueadero(parqueadero_id: str) -> str:
        """
        Suscribe al conductor a un parqueadero específico para recibir notificaciones
        cuando haya cupos disponibles. REQUIERE PREMIUM.
        
        Args:
            parqueadero_id: ID del parqueadero al que se desea suscribir
            
        Returns:
            str: Mensaje de confirmación o error
        """
        # PAYWALL - Verificar acceso premium
        acceso = premium_service.verificar_acceso_premium(user_id)
        if not acceso["tiene_acceso"]:
            premium_service.mostrar_paywall_notificaciones(user_id)
            return "🔒 Las notificaciones son una función Premium. Revisa el mensaje anterior para saber cómo obtener acceso gratis."
        
        # Verificar que el parqueadero existe
        parqueadero = parqueadero_repo.find_by_id(parqueadero_id)
        if not parqueadero:
            return f"❌ No se encontró el parqueadero con ID: {parqueadero_id}"
        
        # Verificar si ya está suscrito
        suscripcion_existente = suscripcion_repo.find_active_suscripcion(
            user_id, parqueadero_id
        )
        if suscripcion_existente:
            return f"ℹ️ Ya estás suscrito a **{parqueadero.name}**"
        
        # Crear suscripción
        suscripcion_repo.create_suscripcion(user_id, parqueadero_id)
        
        return f"✅ ¡Suscripción exitosa!\n\nAhora recibirás notificaciones de **{parqueadero.name}** cuando haya cupos disponibles.\n\n⏰ Premium activo: {acceso['dias_restantes']} días restantes"
    
    @tool
    def suscribirse_a_todos() -> str:
        """
        Suscribe al conductor a todos los parqueaderos del sistema.
        Recibirá notificaciones de cualquier parqueadero que tenga cupos disponibles. REQUIERE PREMIUM.
        
        Returns:
            str: Mensaje de confirmación o error
        """
        # PAYWALL - Verificar acceso premium
        acceso = premium_service.verificar_acceso_premium(user_id)
        if not acceso["tiene_acceso"]:
            premium_service.mostrar_paywall_notificaciones(user_id)
            return "🔒 Las notificaciones son una función Premium. Revisa el mensaje anterior para saber cómo obtener acceso gratis."
        
        # Verificar si ya está suscrito a todos
        suscripcion_existente = suscripcion_repo.find_active_suscripcion(
            user_id, None
        )
        if suscripcion_existente:
            return "ℹ️ Ya estás suscrito a todos los parqueaderos"
        
        # Primero desactivar todas las suscripciones específicas
        suscripcion_repo.desactivar_todas_suscripciones(user_id)
        
        # Crear suscripción global
        suscripcion_repo.create_suscripcion(user_id, None)
        
        return f"✅ ¡Suscripción exitosa!\n\nAhora recibirás notificaciones de TODOS los parqueaderos cuando tengan cupos disponibles.\n\n⏰ Premium activo: {acceso['dias_restantes']} días restantes"
    
    @tool
    def ver_mis_suscripciones() -> str:
        """
        Muestra todas las suscripciones activas del conductor.
        
        Returns:
            str: Lista de suscripciones activas o mensaje si no tiene ninguna
        """
        suscripciones = suscripcion_repo.find_suscripciones_by_conductor(user_id)
        
        if not suscripciones:
            return "ℹ️ No tienes suscripciones activas.\n\nPuedes suscribirte a parqueaderos específicos o a todos para recibir notificaciones."
        
        resultado = "📋 **Tus Suscripciones Activas:**\n\n"
        
        for i, suscripcion in enumerate(suscripciones, 1):
            if suscripcion.parqueadero_id is None:
                resultado += f"{i}. 🌐 **Todos los parqueaderos**\n"
            else:
                parqueadero = parqueadero_repo.find_by_id(suscripcion.parqueadero_id)
                if parqueadero:
                    resultado += f"{i}. 🅿️ **{parqueadero.name}**\n"
                    resultado += f"   📍 {parqueadero.ubicacion}\n"
                    resultado += f"   🆔 ID: {parqueadero.id}\n"
            
            if suscripcion.fecha_suscripcion:
                resultado += f"   📅 Desde: {suscripcion.fecha_suscripcion}\n"
            resultado += "\n"
        
        return resultado
    
    @tool
    def desuscribirse_de_parqueadero(parqueadero_id: str) -> str:
        """
        Cancela la suscripción a un parqueadero específico.
        
        Args:
            parqueadero_id: ID del parqueadero del que se desea desuscribir
            
        Returns:
            str: Mensaje de confirmación o error
        """
        # Verificar que el parqueadero existe
        parqueadero = parqueadero_repo.find_by_id(parqueadero_id)
        if not parqueadero:
            return f"❌ No se encontró el parqueadero con ID: {parqueadero_id}"
        
        # Verificar si tiene suscripción activa
        suscripcion = suscripcion_repo.find_active_suscripcion(
            user_id, parqueadero_id
        )
        if not suscripcion:
            return f"ℹ️ No estás suscrito a **{parqueadero.name}**"
        
        # Desactivar suscripción
        exito = suscripcion_repo.desactivar_suscripcion(user_id, parqueadero_id)
        
        if exito:
            return f"✅ Te has desuscrito de **{parqueadero.name}**\n\nYa no recibirás notificaciones de este parqueadero."
        else:
            return "❌ Ocurrió un error al procesar tu desuscripción. Intenta nuevamente."
    
    @tool
    def desuscribirse_de_todos() -> str:
        """
        Cancela todas las suscripciones activas del conductor.
        
        Returns:
            str: Mensaje de confirmación
        """
        cantidad = suscripcion_repo.desactivar_todas_suscripciones(user_id)
        
        if cantidad == 0:
            return "ℹ️ No tienes suscripciones activas para cancelar."
        
        return f"✅ Se han cancelado {cantidad} suscripción(es).\n\nYa no recibirás notificaciones de ningún parqueadero."
    
    @tool
    def ver_estadisticas_referidos() -> str:
        """
        Muestra las estadísticas del programa de referidos: código personal, 
        número de referidos, días premium ganados y estado actual.
        
        Returns:
            str: Estadísticas completas del programa de referidos
        """
        premium_service.mostrar_estadisticas_referidos(user_id)
        return "✅ Te he enviado tus estadísticas del programa de referidos."
    
    return [
        suscribirse_a_parqueadero,
        suscribirse_a_todos,
        ver_mis_suscripciones,
        desuscribirse_de_parqueadero,
        desuscribirse_de_todos,
        ver_estadisticas_referidos
    ]
