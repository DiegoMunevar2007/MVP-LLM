from app.repositories.user_repositories import UserRepository, ConductorRepository
from app.models.database_models import Conductor, User
from app.utils.tiempo_utils import generar_codigo_referido, calcular_fecha_expiracion_premium, extender_fecha_expiracion_premium

def obtener_usuario(wa_id: str, db) -> User:
    repo = UserRepository(db)
    return repo.find_by_id(wa_id)

def crear_usuario(wa_id: str, db):
    repo = ConductorRepository(db)
    nuevo_usuario = repo.create(Conductor(_id=wa_id, rol="conductor"))
    return nuevo_usuario

def actualizar_nombre(wa_id: str, nombre: str, db):
    repo = UserRepository(db)
    usuario_actualizado = repo.actualizar_nombre(wa_id, nombre)
    return usuario_actualizado

def actualizar_estado_chat(wa_id: str, paso_actual: str, db):
    repo = UserRepository(db)
    usuario_actualizado = repo.actualizar_estado_chat(wa_id, paso_actual)
    return usuario_actualizado

def actualizar_estado_registro(wa_id: str, estado_registro: str, db):
    repo = UserRepository(db)
    usuario_actualizado = repo.actualizar_estado_registro(wa_id, estado_registro)
    return usuario_actualizado

def actualizar_contexto_temporal(wa_id: str, contexto: dict, db):
    """
    Actualiza el contexto temporal del usuario (para guardar datos temporales durante flujos)
    """
    repo = UserRepository(db)
    return repo.actualizar_contexto_temporal(wa_id, contexto)

def actualizar_paso_chat(wa_id: str, paso: str, db):
    """
    Actualiza el paso actual del chat del usuario
    """
    return actualizar_estado_chat(wa_id, paso, db)

# ==================== GROWTH LOOP - SISTEMA DE REFERIDOS ====================

def generar_y_asignar_codigo_referido(wa_id: str, db) -> str:
    """
    Genera un código único de referido y lo asigna al usuario
    Returns:
        str: El código generado
    """
    repo = UserRepository(db)
    
    # Intentar generar un código único (máximo 10 intentos)
    for _ in range(10):
        codigo = generar_codigo_referido()
        if repo.verificar_codigo_disponible(codigo):
            repo.asignar_codigo_referido(wa_id, codigo)
            return codigo
    
    # Si no se pudo generar después de 10 intentos, usar un código con timestamp
    import time
    codigo_timestamp = f"SB{int(time.time()) % 10000:04d}"
    repo.asignar_codigo_referido(wa_id, codigo_timestamp)
    return codigo_timestamp

def procesar_codigo_referido(wa_id: str, codigo_referidor: str, db) -> dict:
    """
    Procesa el uso de un código de referido
    Args:
        wa_id: ID del nuevo usuario
        codigo_referidor: Código de referido usado
    Returns:
        dict: {"exito": bool, "mensaje": str, "referidor_id": str}
    """
    repo = UserRepository(db)
    
    # Buscar al usuario que tiene ese código
    referidor = repo.buscar_por_codigo_referido(codigo_referidor)
    
    if not referidor:
        return {
            "exito": False,
            "mensaje": "Código de referido no válido",
            "referidor_id": None
        }
    
    # Registrar que este usuario fue referido
    repo.registrar_referido(wa_id, codigo_referidor)
    
    # Incrementar contador de referidos del referidor
    repo.incrementar_referidos(referidor.id)
    
    # Otorgar 7 días de premium al referidor
    if referidor.fecha_expiracion_premium and referidor.es_premium:
        # Si ya tiene premium, extender la fecha
        nueva_fecha = extender_fecha_expiracion_premium(referidor.fecha_expiracion_premium, 7)
    else:
        # Si no tiene premium, activar por 7 días
        nueva_fecha = calcular_fecha_expiracion_premium(7)
    
    repo.activar_premium(referidor.id, nueva_fecha)
    
    return {
        "exito": True,
        "mensaje": f"¡Código válido! {referidor.name or 'Tu referidor'} ha recibido 7 días de premium.",
        "referidor_id": referidor.id,
        "nombre_referidor": referidor.name
    }

def obtener_estadisticas_referidos(wa_id: str, db) -> dict:
    """
    Obtiene las estadísticas de referidos de un usuario
    """
    repo = UserRepository(db)
    usuario = repo.find_by_id(wa_id)
    
    if not usuario:
        return None
    
    return {
        "codigo_referido": usuario.codigo_referido,
        "numero_referidos": usuario.numero_referidos or 0,
        "es_premium": usuario.es_premium,
        "fecha_expiracion_premium": usuario.fecha_expiracion_premium
    }