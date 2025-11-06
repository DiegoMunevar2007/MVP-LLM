"""
Script para inicializar índices en MongoDB para optimizar consultas
"""
from app.database.db_conn import get_db


def create_message_indexes():
    """
    Crea índices en la colección de mensajes de conversación para optimizar las consultas.
    """
    db = get_db()
    collection = db["mensajes_conversacion"]
    
    # Índice compuesto para user_id, activo y timestamp (para consultas de mensajes activos)
    collection.create_index([
        ("user_id", 1),
        ("activo", 1),
        ("timestamp", -1)
    ], name="user_activo_timestamp_idx")
    
    print("✅ Índice creado: user_id + activo + timestamp (descendente)")
    
    # Índice compuesto para user_id y timestamp (para consultas generales)
    collection.create_index([
        ("user_id", 1),
        ("timestamp", -1)
    ], name="user_timestamp_idx")
    
    print("✅ Índice creado: user_id + timestamp (descendente)")
    
    # Índice simple para user_id (para consultas rápidas por usuario)
    collection.create_index("user_id", name="user_idx")
    
    print("✅ Índice creado: user_id")
    
    print("🎉 Todos los índices de mensajes de conversación han sido creados exitosamente")


if __name__ == "__main__":
    create_message_indexes()
