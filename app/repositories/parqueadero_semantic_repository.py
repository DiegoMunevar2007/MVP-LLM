"""
Repositorio para búsqueda semántica de parqueaderos usando ChromaDB
"""
from typing import List, Dict, Any, Optional
from app.database.chroma_conn import get_chroma_connection
from app.repositories.parqueadero_repository import ParqueaderoRepository
from app.models.database_models import Parqueadero


class ParqueaderoSemanticRepository:
    """Repositorio para búsqueda semántica de parqueaderos"""
    
    def __init__(self, db):
        """
        Inicializa el repositorio
        
        Args:
            db: Instancia de la base de datos MongoDB
        """
        self.chroma = get_chroma_connection()
        self.parqueadero_repo = ParqueaderoRepository(db)
    
    def buscar_parqueaderos(self, query: str, limit: int = 5) -> List[Parqueadero]:
        """
        Busca parqueaderos usando búsqueda semántica
        
        Args:
            query: Consulta de búsqueda del usuario (ej: "Tequendama cerca al SD")
            limit: Número máximo de resultados
            
        Returns:
            Lista de objetos Parqueadero ordenados por relevancia
        """
        # Buscar IDs similares en ChromaDB
        resultados_chroma = self.chroma.buscar_parqueaderos_similares(query, n_results=limit)
        
        if not resultados_chroma:
            return []
        
        # Obtener información completa y actualizada de MongoDB
        parqueaderos = []
        for resultado in resultados_chroma:
            parqueadero_id = resultado['id']
            parqueadero = self.parqueadero_repo.find_by_id(parqueadero_id)
            
            if parqueadero:
                # Agregar score de similitud como atributo adicional
                parqueadero.similarity_score = 1 - resultado.get('distance', 0)  # Convertir distancia a score
                parqueaderos.append(parqueadero)
        
        return parqueaderos
    
    def agregar_parqueadero(self, parqueadero: Parqueadero):
        """
        Agrega un parqueadero nuevo tanto a MongoDB como a ChromaDB
        
        Args:
            parqueadero: Objeto Parqueadero a agregar
        """
        # Agregar a ChromaDB para búsqueda semántica
        self.chroma.add_parqueadero(
            parqueadero_id=parqueadero.id,
            name=parqueadero.name,
            ubicacion=parqueadero.ubicacion,
            metadata={
                'capacidad': parqueadero.capacidad,
                'tiene_cupos': parqueadero.tiene_cupos,
                'cupos_libres': parqueadero.cupos_libres
            }
        )
    
    def actualizar_parqueadero(self, parqueadero: Parqueadero):
        """
        Actualiza información de un parqueadero en ChromaDB
        
        Args:
            parqueadero: Objeto Parqueadero actualizado
        """
        # Actualizar en ChromaDB (upsert)
        self.chroma.add_parqueadero(
            parqueadero_id=parqueadero.id,
            name=parqueadero.name,
            ubicacion=parqueadero.ubicacion,
            metadata={
                'capacidad': parqueadero.capacidad,
                'tiene_cupos': parqueadero.tiene_cupos,
                'cupos_libres': parqueadero.cupos_libres,
                'estado_ocupacion': parqueadero.estado_ocupacion
            }
        )
    
    def eliminar_parqueadero(self, parqueadero_id: str):
        """
        Elimina un parqueadero de ChromaDB
        
        Args:
            parqueadero_id: ID del parqueadero a eliminar
        """
        self.chroma.delete_parqueadero(parqueadero_id)
    
    def sincronizar_todo(self):
        """
        Sincroniza todos los parqueaderos de MongoDB con ChromaDB
        Útil para inicialización o recuperación después de fallos
        """
        # Obtener todos los parqueaderos de MongoDB
        parqueaderos = self.parqueadero_repo.find_all()
        
        # Convertir a dict para sincronización
        parqueaderos_dict = [p.model_dump(by_alias=True) for p in parqueaderos]
        
        # Sincronizar con ChromaDB
        self.chroma.sincronizar_parqueaderos(parqueaderos_dict)
        
        return len(parqueaderos_dict)
