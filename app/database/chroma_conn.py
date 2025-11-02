"""
Conexión y gestión de ChromaDB para búsqueda semántica de parqueaderos
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional


class ChromaDBConnection:
    """Clase para manejar la conexión y operaciones con ChromaDB"""
    
    def __init__(self):
        """Inicializa la conexión con ChromaDB"""
        # Configuración para conectarse al servidor ChromaDB
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = os.getenv("CHROMA_PORT", "8000")
        
        self.client = chromadb.HttpClient(
            host=chroma_host,
            port=int(chroma_port),
            settings=Settings(
                anonymized_telemetry=False
            )
        )
        
        # Nombre de la colección para parqueaderos
        self.collection_name = "parqueaderos"
        
        # Crear o obtener la colección
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Obtiene o crea la colección de parqueaderos"""
        try:
            collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Usar distancia coseno para similitud
            )
            return collection
        except Exception as e:
            print(f"Error creando/obteniendo colección: {e}")
            raise
    
    def add_parqueadero(self, parqueadero_id: str, name: str, ubicacion: str, 
                       metadata: Optional[Dict[str, Any]] = None):
        """
        Añade o actualiza un parqueadero en ChromaDB
        
        Args:
            parqueadero_id: ID del parqueadero en MongoDB
            name: Nombre del parqueadero
            ubicacion: Ubicación del parqueadero
            metadata: Metadatos adicionales del parqueadero
        """
        try:
            # Crear el documento que contiene toda la información buscable
            document = f"{name}. Ubicación: {ubicacion}"
            
            # Metadatos para filtrado
            if metadata is None:
                metadata = {}
            metadata.update({
                "name": name,
                "ubicacion": ubicacion
            })
            
            # Agregar a ChromaDB
            self.collection.upsert(
                ids=[parqueadero_id],
                documents=[document],
                metadatas=[metadata]
            )
            
            print(f"Parqueadero {name} añadido/actualizado en ChromaDB")
            
        except Exception as e:
            print(f"Error añadiendo parqueadero a ChromaDB: {e}")
            raise
    
    def buscar_parqueaderos_similares(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Busca parqueaderos similares a la consulta usando búsqueda semántica
        
        Args:
            query: Consulta de búsqueda del usuario
            n_results: Número máximo de resultados a retornar
            
        Returns:
            Lista de diccionarios con los parqueaderos encontrados y sus scores
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )
            
            # Formatear resultados
            parqueaderos = []
            if results and results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    parqueadero = {
                        'id': results['ids'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'document': results['documents'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    }
                    parqueaderos.append(parqueadero)
            
            return parqueaderos
            
        except Exception as e:
            print(f"Error buscando parqueaderos similares: {e}")
            return []
    
    def delete_parqueadero(self, parqueadero_id: str):
        """
        Elimina un parqueadero de ChromaDB
        
        Args:
            parqueadero_id: ID del parqueadero a eliminar
        """
        try:
            self.collection.delete(ids=[parqueadero_id])
            print(f"Parqueadero {parqueadero_id} eliminado de ChromaDB")
        except Exception as e:
            print(f"Error eliminando parqueadero de ChromaDB: {e}")
            raise
    
    def sincronizar_parqueaderos(self, parqueaderos: List[Dict[str, Any]]):
        """
        Sincroniza todos los parqueaderos de MongoDB con ChromaDB
        
        Args:
            parqueaderos: Lista de parqueaderos con formato dict
        """
        try:
            for parqueadero in parqueaderos:
                self.add_parqueadero(
                    parqueadero_id=parqueadero.get('_id', parqueadero.get('id')),
                    name=parqueadero['name'],
                    ubicacion=parqueadero['ubicacion'],
                    metadata={
                        'capacidad': parqueadero.get('capacidad'),
                        'tiene_cupos': parqueadero.get('tiene_cupos'),
                        'cupos_libres': parqueadero.get('cupos_libres')
                    }
                )
            print(f"Sincronizados {len(parqueaderos)} parqueaderos con ChromaDB")
        except Exception as e:
            print(f"Error sincronizando parqueaderos: {e}")
            raise
    
    def get_collection_count(self) -> int:
        """Retorna el número de documentos en la colección"""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"Error obteniendo conteo de colección: {e}")
            return 0


# Instancia global de conexión
_chroma_connection = None


def get_chroma_connection() -> ChromaDBConnection:
    """Obtiene o crea la instancia global de ChromaDB"""
    global _chroma_connection
    if _chroma_connection is None:
        _chroma_connection = ChromaDBConnection()
    return _chroma_connection
