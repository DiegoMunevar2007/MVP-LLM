"""
Servicio especializado para mensajes de bienvenida y registro de usuarios
"""
from app.logic.send_message import send_message


class MensajeBienvenidaService:
    """
    Servicio enfocado en mensajes de bienvenida y proceso de registro.
    Responsabilidad: Comunicación inicial con usuarios nuevos y existentes.
    """
    
    def enviar_bienvenida(self, user_id: str):
        """Envía mensaje de bienvenida a nuevos usuarios"""
        mensaje_bienvenida = """¡Bienvenido! 👋🚗

Soy tu asistente para consulta de cupos de parqueaderos en Uniandes.

*Aquí puedo ayudarte a:*

🅿️ *Encontrar cupos disponibles:*
   • Consultar los cupos de parqueaderos en tiempo real
   • Buscar un parqueadero por ubicación o descripción
   • Ver detalles de cada parqueadero

🔔 *Recibir notificaciones:*
   • Suscribirse a parqueaderos específicos
   • Recibir alertas cuando haya cupos libres
   • Gestionar tus suscripciones fácilmente

📊 *Reportar cupos:*    
   • Informar cuando encuentres un parqueadero disponible
   • Ver tus reportes activos

Solo necesito tu nombre para empezar. ¿Cuál es? 😊"""
        send_message(user_id, mensaje_bienvenida)
    
    def solicitar_nombre(self, user_id: str):
        """Solicita el nombre para completar el registro"""
        send_message(user_id, "Por favor, envía tu nombre para completar el registro 📝")
    
    def confirmar_registro(self, user_id: str, nombre: str):
        """Confirma el registro exitoso"""
        mensaje_confirmacion = f"""✅ ¡Excelente {nombre}!

Ya estás registrado en nuestro sistema. Ahora puedes:

• Buscar parqueaderos con cupos disponibles
• Recibir notificaciones de cupos libres
• Reportar cupos disponibles a otros conductores
• Gestionar tus suscripciones

¿En qué puedo ayudarte? 🚗💨"""
        send_message(user_id, mensaje_confirmacion)
    
    def saludar_usuario_registrado(self, user_id: str, nombre: str):
        """Saluda a un usuario ya registrado"""
        send_message(user_id, f"Hola de nuevo {nombre} 👋🚘!")
    
    def enviar_bienvenida_gestor(self, user_id: str):
        """Envía mensaje de bienvenida a nuevos gestores de parqueadero"""
        mensaje_bienvenida = """¡Bienvenido Gestor! 🏢

Soy tu asistente para gestión inteligente de tu parqueadero en Bogotá.

**Aquí puedo ayudarte a:**

🅿️ **Administrar tu parqueadero:**
   • Ver información y estado actual
   • Actualizar disponibilidad de cupos
   • Consultar detalles del parqueadero

🔔 **Comunicación automatizada:**
   • Notificaciones automáticas a conductores suscritos
   • Alertas cuando haya cambios importantes
   • Gestión centralizada de cupos

📊 **Seguimiento:**
   • Ver estado en tiempo real
   • Histórico de cambios
   • Información de conductores suscritos

Solo necesito tu nombre para empezar. ¿Cuál es? 😊"""
        send_message(user_id, mensaje_bienvenida)
    
    def confirmar_registro_gestor(self, user_id: str, nombre: str):
        """Confirma el registro exitoso de un gestor"""
        mensaje_confirmacion = f"""✅ ¡Excelente {nombre}!

Ya estás registrado como gestor de parqueadero. Ahora puedes:

• Ver información detallada de tu parqueadero
• Actualizar cupos en tiempo real
• Notificar automáticamente a conductores suscritos
• Gestionar la disponibilidad de espacios

¿En qué puedo ayudarte? 🚗📍"""
        send_message(user_id, mensaje_confirmacion)
