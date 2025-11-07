"""
Herramientas de LangChain para reportar parqueaderos con cupos
"""
from langchain_core.tools import tool
from app.repositories.reporte_repository import ReporteRepository
from app.repositories.parqueadero_repository import ParqueaderoRepository
from app.services.notification_service import NotificationService
from app.services.premium_service import PremiumService


def create_reporte_tools(db, user_id: str):
    """Factory function para crear herramientas de reportes"""
    
    reporte_repo = ReporteRepository(db)
    parqueadero_repo = ParqueaderoRepository(db)
    notification_service = NotificationService(db)
    premium_service = PremiumService(db)
    
    @tool
    def reportar_cupos_disponibles(parqueadero_id: str) -> str:
        """
        Permite a un conductor reportar que un parqueadero tiene cupos disponibles.
        Después de 5 reportes de distintos usuarios, el sistema activará automáticamente
        el parqueadero y notificará a los suscriptores.
        
        USAR ESTA HERRAMIENTA cuando el usuario diga:
        - "Hay cupos en [parqueadero]"
        - "Vi que [parqueadero] tiene cupos"
        - "Quiero reportar que [parqueadero] tiene espacios"
        - "El parqueadero [X] tiene cupos disponibles"
        
        Args:
            parqueadero_id: ID del parqueadero a reportar
            
        Returns:
            str: Mensaje confirmando el reporte y estado actual
        """
        # Verificar que el parqueadero existe
        parqueadero = parqueadero_repo.find_by_id(parqueadero_id)
        if not parqueadero:
            return f"❌ No se encontró el parqueadero con ID: {parqueadero_id}"
        
        # Verificar si el usuario ya reportó este parqueadero
        ya_reporto = reporte_repo.verificar_reporte_existente(parqueadero_id, user_id)
        if ya_reporto:
            reportes_actuales = reporte_repo.contar_reportes_activos(parqueadero_id)
            return f"ℹ️ Ya has reportado que **{parqueadero.name}** tiene cupos disponibles.\n\n" \
                   f"📊 Reportes actuales: **{reportes_actuales}/5**\n\n" \
                   f"⏳ Cuando se alcancen 5 reportes de diferentes usuarios, se activarán los cupos automáticamente."
        
        # Crear el reporte
        reporte_repo.crear_reporte(parqueadero_id, user_id)
        
        # Contar reportes actuales
        reportes_actuales = reporte_repo.contar_reportes_activos(parqueadero_id)
        
        # Si se alcanzaron 5 reportes, activar cupos
        if reportes_actuales >= 5:
            # Activar cupos en el parqueadero
            resultado = parqueadero_repo.actualizar_cupos_con_notificacion(
                parqueadero_id,
                cupos_libres="Algunos cupos",
                tiene_cupos=True,
                rango_cupos="Reportado por usuarios",
                estado_ocupacion="Disponible según reportes de conductores",
                notification_service=notification_service
            )
            
            # Marcar reportes como procesados (reiniciando el contador)
            reporte_repo.marcar_reportes_como_procesados(parqueadero_id)
            
            # Limpiar todos los reportes del parqueadero para reiniciar el contador
            reporte_repo.limpiar_reportes_parqueadero(parqueadero_id)
            
            notificaciones_enviadas = resultado.get('notificaciones_enviadas', 0)
            
            # GROWTH LOOP CTA - Recordar código de referido después del reporte
            premium_service.recordar_codigo_referido(user_id)
            
            return f"🎉 **¡Reporte registrado exitosamente!**\n\n" \
                   f"✅ Se alcanzaron **5 reportes** para **{parqueadero.name}**\n\n" \
                   f"🚗 **El parqueadero ha sido activado** con cupos disponibles\n" \
                   f"📢 Se enviaron **{notificaciones_enviadas} notificaciones** a los suscriptores\n\n" \
                   f"🔄 El contador de reportes se ha reiniciado a 0\n\n" \
                   f"¡Gracias por tu colaboración! 🙏"
        else:
            reportes_faltantes = 5 - reportes_actuales
            
            # GROWTH LOOP CTA - Recordar código de referido después del reporte
            premium_service.recordar_codigo_referido(user_id)
            
            return f"✅ **Reporte registrado exitosamente**\n\n" \
                   f"📍 Parqueadero: **{parqueadero.name}**\n" \
                   f"📊 Reportes actuales: **{reportes_actuales}/5**\n" \
                   f"⏳ Faltan **{reportes_faltantes} reporte(s)** más para activar los cupos automáticamente\n\n" \
                   f"¡Gracias por tu colaboración! Cuando se alcancen 5 reportes, se notificará a todos los suscriptores."
    
    @tool
    def ver_mis_reportes() -> str:
        """
        Muestra los reportes activos que ha hecho el conductor.
        
        Returns:
            str: Lista de reportes activos del conductor
        """
        # Buscar todos los reportes activos del conductor
        reportes = reporte_repo.collection.find({
            "conductor_id": user_id,
            "procesado": False
        })
        
        reportes_list = []
        for doc in reportes:
            parqueadero_id = doc.get("parqueadero_id")
            parqueadero = parqueadero_repo.find_by_id(parqueadero_id)
            if parqueadero:
                reportes_actuales = reporte_repo.contar_reportes_activos(parqueadero_id)
                reportes_list.append({
                    "nombre": parqueadero.name,
                    "reportes": reportes_actuales,
                    "fecha": doc.get("fecha_reporte")
                })
        
        if not reportes_list:
            return "ℹ️ No tienes reportes activos.\n\n" \
                   "Puedes reportar parqueaderos con cupos disponibles para ayudar a la comunidad."
        
        resultado = "📋 **Tus reportes activos:**\n\n"
        for i, rep in enumerate(reportes_list, 1):
            resultado += f"{i}. **{rep['nombre']}**\n"
            resultado += f"   📊 Reportes: {rep['reportes']}/5\n"
            resultado += f"   📅 Fecha: {rep['fecha']}\n\n"
        
        return resultado
    
    return [
        reportar_cupos_disponibles,
        ver_mis_reportes
    ]
