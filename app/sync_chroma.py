"""
Script de sincronización de parqueaderos con ChromaDB
Ejecutar este script para sincronizar todos los parqueaderos de MongoDB con ChromaDB
"""
from app.database.db_conn import get_database
from app.repositories.parqueadero_semantic_repository import ParqueaderoSemanticRepository


def sincronizar_parqueaderos():
    """Sincroniza todos los parqueaderos de MongoDB con ChromaDB"""
    print("🔄 Iniciando sincronización de parqueaderos con ChromaDB...")
    
    try:
        # Obtener conexión a la base de datos
        db = get_database()
        
        # Crear repositorio semántico
        semantic_repo = ParqueaderoSemanticRepository(db)
        
        # Sincronizar
        count = semantic_repo.sincronizar_todo()
        
        print(f"✅ Sincronización completada: {count} parqueaderos sincronizados")
        
        # Verificar conteo en ChromaDB
        chroma_count = semantic_repo.chroma.get_collection_count()
        print(f"📊 Total de documentos en ChromaDB: {chroma_count}")
        
    except Exception as e:
        print(f"❌ Error durante la sincronización: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    sincronizar_parqueaderos()
