"""
Servicio para gestionar el sistema Premium y Paywall
"""
from app.repositories.user_repositories import UserRepository
from app.utils.tiempo_utils import verificar_premium_activo
from app.logic.send_message import send_message


class PremiumService:
    """
    Servicio que gestiona el acceso premium y paywall para notificaciones
    """
    
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def verificar_acceso_premium(self, user_id: str) -> dict:
        """
        Verifica si un usuario tiene acceso premium activo
        Returns:
            dict: {
                "tiene_acceso": bool,
                "es_premium": bool,
                "fecha_expiracion": str,
                "dias_restantes": int
            }
        """
        usuario = self.user_repo.find_by_id(user_id)
        
        if not usuario:
            return {
                "tiene_acceso": False,
                "es_premium": False,
                "fecha_expiracion": None,
                "dias_restantes": 0
            }
        
        # Verificar si el premium está activo
        tiene_acceso = False
        if usuario.es_premium and usuario.fecha_expiracion_premium:
            tiene_acceso = verificar_premium_activo(usuario.fecha_expiracion_premium)
            
            # Si expiró, actualizar en la base de datos
            if not tiene_acceso and usuario.es_premium:
                self.user_repo.desactivar_premium(user_id)
        
        # Calcular días restantes
        dias_restantes = 0
        if tiene_acceso and usuario.fecha_expiracion_premium:
            dias_restantes = self._calcular_dias_restantes(usuario.fecha_expiracion_premium)
        
        return {
            "tiene_acceso": tiene_acceso,
            "es_premium": usuario.es_premium,
            "fecha_expiracion": usuario.fecha_expiracion_premium,
            "dias_restantes": dias_restantes
        }
    
    def _calcular_dias_restantes(self, fecha_expiracion: str) -> int:
        """Calcula los días restantes hasta la expiración"""
        from datetime import datetime
        import pytz
        
        try:
            zona_bogota = pytz.timezone('America/Bogota')
            dt_expiracion = datetime.strptime(fecha_expiracion, "%Y-%m-%d %H:%M:%S")
            dt_expiracion = zona_bogota.localize(dt_expiracion)
            ahora = datetime.now(zona_bogota)
            
            diferencia = dt_expiracion - ahora
            return max(0, diferencia.days)
        except (ValueError, TypeError):
            return 0
    
    def mostrar_paywall_notificaciones(self, user_id: str):
        """
        Muestra el paywall cuando un usuario sin premium intenta acceder a notificaciones
        """
        usuario = self.user_repo.find_by_id(user_id)
        codigo_referido = usuario.codigo_referido if usuario else "N/A"
        numero_referidos = usuario.numero_referidos if usuario else 0
        
        mensaje_paywall = f"""🔒 *Función Premium - Notificaciones*

Las notificaciones automáticas de cupos disponibles son una función *Premium*.

🌟 *¿Cómo obtener Premium gratis?*

Comparte tu código de referido con tus amigos:
📋 Tu código: `{codigo_referido}`

*¡Por cada amigo que use tu código, obtienes 7 días gratis!*

📊 Tus estadísticas:
• Referidos actuales: {numero_referidos}
• Días premium ganados: {numero_referidos * 7}

💡 *Cómo funciona:*
1. Comparte tu código `{codigo_referido}` con amigos
2. Ellos lo ingresan al registrarse
3. ¡Automáticamente recibes 7 días premium por cada uno!

_Próximamente: Opción de pago para Premium ilimitado_"""
        
        send_message(user_id, mensaje_paywall)
    
    def recordar_codigo_referido(self, user_id: str):
        """
        Envía un recordatorio del código de referido después de reportar cupos (Growth Loop CTA)
        """
        usuario = self.user_repo.find_by_id(user_id)
        
        if not usuario:
            return
        
        codigo_referido = usuario.codigo_referido or "N/A"
        numero_referidos = usuario.numero_referidos or 0
        
        acceso_premium = self.verificar_acceso_premium(user_id)
        
        if acceso_premium["tiene_acceso"]:
            # Usuario tiene premium, mostrar estadísticas
            mensaje = f"""✅ *¡Gracias por reportar!*

🎁 *Sigue ganando días premium:*

Tu código: `{codigo_referido}`
Referidos: {numero_referidos}
Días premium restantes: {acceso_premium['dias_restantes']}

Comparte tu código y obtén *7 días más* por cada amigo. 🚀"""
        else:
            # Usuario NO tiene premium, incentivar referidos
            mensaje = f"""✅ *¡Gracias por reportar!*

🎁 *¿Quieres recibir notificaciones automáticas?*

Comparte tu código de referido:
📋 `{codigo_referido}`

*¡Gana 7 días premium gratis por cada amigo!*

Referidos actuales: {numero_referidos}"""
        
        send_message(user_id, mensaje)
    
    def mostrar_estadisticas_referidos(self, user_id: str):
        """
        Muestra las estadísticas completas del programa de referidos
        """
        usuario = self.user_repo.find_by_id(user_id)
        
        if not usuario:
            send_message(user_id, "❌ No se encontró tu información de usuario.")
            return
        
        codigo_referido = usuario.codigo_referido or "N/A"
        numero_referidos = usuario.numero_referidos or 0
        
        acceso_premium = self.verificar_acceso_premium(user_id)
        
        mensaje = f"""📊 *Tus estadísticas del programa de referidos*

🎫 *Tu código:* `{codigo_referido}`

👥 *Referidos:* {numero_referidos} personas
🎁 *Días ganados:* {numero_referidos * 7} días

🌟 *Estado Premium:*"""
        
        if acceso_premium["tiene_acceso"]:
            mensaje += f"""
✅ Activo
⏰ Días restantes: {acceso_premium['dias_restantes']}

*¡Sigue compartiendo para extender tu premium!*"""
        else:
            mensaje += f"""
❌ Inactivo

*¡Comparte tu código para activar premium!*
Cada referido = 7 días gratis 🎉"""
        
        send_message(user_id, mensaje)
