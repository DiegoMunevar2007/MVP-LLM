import uuid
from pydantic import BaseModel, Field
from typing import Optional

class EstadoChat(BaseModel):
    ultima_interaccion: Optional[str] = None  # Timestamp de la última interacción
    paso_actual: Optional[str] = None  # Paso actual en el flujo de conversación
    contexto_temporal: Optional[dict] = None  # Para guardar datos temporales durante flujos

class Parqueadero(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    name: str 
    ubicacion: str
    capacidad: int
    tiene_cupos: bool = True
    cupos_libres: str = "0"  # Valor por defecto para compatibilidad
    rango_cupos: Optional[str] = None  # Nuevo campo para almacenar el rango
    estado_ocupacion: Optional[str] = None  # Descripción del estado (lleno, pocos cupos, etc.)
    ultima_actualizacion: Optional[str] = None
    similarity_score: Optional[float] = None  # Para búsquedas semánticas
    class Config:
        allow_population_by_field_name = True

class User(BaseModel):
    id: Optional[str] = Field(alias="_id")  # MongoDB usa _id como clave primaria
    name: Optional[str] = None
    rol: Optional[str] = None  # "conductor" o "gestor_parqueadero"
    estado_chat: EstadoChat = EstadoChat()
    estado_registro: Optional[str] = None  # "esperando_nombre", "completo", etc.
    
    # Growth Loop - Sistema de referidos y premium
    es_premium: bool = False  # Indica si el usuario tiene acceso premium
    fecha_expiracion_premium: Optional[str] = None  # Timestamp de expiración del premium
    codigo_referido: Optional[str] = None  # Código único de 6 caracteres para referir
    referido_por: Optional[str] = None  # Código de quien lo refirió
    numero_referidos: int = 0  # Contador de personas que usaron su código
    
    class Config:
        allow_population_by_field_name = True  # Permite usar "id" y "_id" indistintamente

class Conductor(User):
    cosas: Optional[str] = None


class GestorParqueadero(User):
    parqueadero_id: Optional[str] = None  # ID del parqueadero que gestiona

class Suscripcion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    conductor_id: str  # WhatsApp ID del conductor
    parqueadero_id: Optional[str] = None  # Si es None, está suscrito a todos los parqueaderos
    fecha_suscripcion: Optional[str] = None
    activa: bool = True
    
    class Config:
        allow_population_by_field_name = True


class ReporteParqueadero(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    parqueadero_id: str  # ID del parqueadero reportado
    conductor_id: str  # WhatsApp ID del conductor que reportó
    fecha_reporte: Optional[str] = None  # Timestamp del reporte
    tipo_reporte: str = "cupos_disponibles"  # Tipo de reporte
    procesado: bool = False  # Si ya se procesó y activó cupos
    
    class Config:
        allow_population_by_field_name = True


class MensajeConversacion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    user_id: str  # WhatsApp ID del usuario
    rol: str  # "user" o "assistant"
    contenido: str  # Contenido del mensaje
    timestamp: str  # Timestamp del mensaje para ordenar
    activo: bool = True  # Indica si el mensaje está activo (se usa en la memoria del agente)
    
    class Config:
        allow_population_by_field_name = True