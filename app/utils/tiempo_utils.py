"""
Utilidades para manejo de fechas y tiempo con zona horaria de Bogotá
"""
from datetime import datetime, timedelta
import pytz
import random
import string

def obtener_tiempo_bogota() -> str:
    """
    Obtiene el tiempo actual en la zona horaria de Bogotá
    Returns:
        str: Timestamp en formato "YYYY-MM-DD HH:MM:SS" en zona horaria de Bogotá
    """
    zona_bogota = pytz.timezone('America/Bogota')
    tiempo_actual = datetime.now(zona_bogota)
    return tiempo_actual.strftime("%Y-%m-%d %H:%M:%S")

def obtener_tiempo_bogota_formato(formato: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Obtiene el tiempo actual en la zona horaria de Bogotá con formato personalizado
    Args:
        formato (str): Formato del timestamp (por defecto: "%Y-%m-%d %H:%M:%S")
    Returns:
        str: Timestamp formateado en zona horaria de Bogotá
    """
    zona_bogota = pytz.timezone('America/Bogota')
    tiempo_actual = datetime.now(zona_bogota)
    return tiempo_actual.strftime(formato)

def obtener_fecha_bogota() -> str:
    """
    Obtiene solo la fecha actual en la zona horaria de Bogotá
    Returns:
        str: Fecha en formato "YYYY-MM-DD"
    """
    return obtener_tiempo_bogota_formato("%Y-%m-%d")

def obtener_hora_bogota() -> str:
    """
    Obtiene solo la hora actual en la zona horaria de Bogotá
    Returns:
        str: Hora en formato "HH:MM:SS"
    """
    return obtener_tiempo_bogota_formato("%H:%M:%S")

def formatear_tiempo_para_usuario(timestamp: str) -> str:
    """
    Formatea un timestamp para mostrar al usuario de manera más legible
    Args:
        timestamp (str): Timestamp en formato "YYYY-MM-DD HH:MM:SS"
    Returns:
        str: Timestamp formateado para el usuario
    """
    try:
        # Parsear el timestamp
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        # Formatear para mostrar al usuario (más legible)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return timestamp or "N/A"

def tiempo_relativo(timestamp: str) -> str:
    """
    Convierte un timestamp en texto relativo (hace cuánto tiempo)
    Args:
        timestamp (str): Timestamp en formato "YYYY-MM-DD HH:MM:SS"
    Returns:
        str: Tiempo relativo (ej: "Hace 5 min", "Hace 2 horas")
    """
    try:
        zona_bogota = pytz.timezone('America/Bogota')
        
        # Parsear el timestamp y asignar zona horaria de Bogotá
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        dt = zona_bogota.localize(dt)
        
        # Obtener tiempo actual en Bogotá
        ahora = datetime.now(zona_bogota)
        
        # Calcular diferencia
        diferencia = ahora - dt
        
        # Convertir a formato legible
        segundos = int(diferencia.total_seconds())
        
        if segundos < 60:
            return "Hace unos segundos"
        elif segundos < 3600:  # Menos de 1 hora
            minutos = segundos // 60
            return f"Hace {minutos} min"
        elif segundos < 86400:  # Menos de 1 día
            horas = segundos // 3600
            return f"Hace {horas}h"
        elif segundos < 604800:  # Menos de 1 semana
            dias = segundos // 86400
            return f"Hace {dias}d"
        else:
            # Más de 1 semana, mostrar fecha
            return dt.strftime("%d/%m/%Y")
            
    except (ValueError, TypeError):
        return "Desconocido"

def generar_codigo_referido() -> str:
    """
    Genera un código alfanumérico único de 6 caracteres para el programa de referidos
    Returns:
        str: Código de 6 caracteres (mayúsculas y números)
    """
    caracteres = string.ascii_uppercase + string.digits
    return ''.join(random.choices(caracteres, k=6))

def calcular_fecha_expiracion_premium(dias: int) -> str:
    """
    Calcula la fecha de expiración del premium sumando días a la fecha actual
    Args:
        dias (int): Número de días a sumar
    Returns:
        str: Timestamp de expiración en formato "YYYY-MM-DD HH:MM:SS"
    """
    zona_bogota = pytz.timezone('America/Bogota')
    tiempo_actual = datetime.now(zona_bogota)
    fecha_expiracion = tiempo_actual + timedelta(days=dias)
    return fecha_expiracion.strftime("%Y-%m-%d %H:%M:%S")

def extender_fecha_expiracion_premium(fecha_actual: str, dias_adicionales: int) -> str:
    """
    Extiende una fecha de expiración existente sumando días adicionales
    Args:
        fecha_actual (str): Fecha actual de expiración en formato "YYYY-MM-DD HH:MM:SS"
        dias_adicionales (int): Días a sumar
    Returns:
        str: Nueva fecha de expiración
    """
    try:
        zona_bogota = pytz.timezone('America/Bogota')
        dt = datetime.strptime(fecha_actual, "%Y-%m-%d %H:%M:%S")
        dt = zona_bogota.localize(dt)
        nueva_fecha = dt + timedelta(days=dias_adicionales)
        return nueva_fecha.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        # Si hay error, calcular desde ahora
        return calcular_fecha_expiracion_premium(dias_adicionales)

def verificar_premium_activo(fecha_expiracion: str) -> bool:
    """
    Verifica si un usuario tiene premium activo comparando la fecha de expiración
    Args:
        fecha_expiracion (str): Fecha de expiración en formato "YYYY-MM-DD HH:MM:SS"
    Returns:
        bool: True si el premium está activo, False si expiró
    """
    if not fecha_expiracion:
        return False
    
    try:
        zona_bogota = pytz.timezone('America/Bogota')
        dt_expiracion = datetime.strptime(fecha_expiracion, "%Y-%m-%d %H:%M:%S")
        dt_expiracion = zona_bogota.localize(dt_expiracion)
        ahora = datetime.now(zona_bogota)
        return ahora < dt_expiracion
    except (ValueError, TypeError):
        return False