"""
Repositorio para gestionar reportes de parqueaderos
"""
from app.repositories.base_repository import BaseRepository
from app.models.database_models import ReporteParqueadero
from app.utils.tiempo_utils import obtener_tiempo_bogota
from typing import List


class ReporteRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "reportes_parqueaderos", ReporteParqueadero)
    
    def crear_reporte(self, parqueadero_id: str, conductor_id: str, tipo_reporte: str = "cupos_disponibles") -> ReporteParqueadero:
        """
        Crea un nuevo reporte de parqueadero
        
        Args:
            parqueadero_id: ID del parqueadero reportado
            conductor_id: WhatsApp ID del conductor que reporta
            tipo_reporte: Tipo de reporte (por defecto "cupos_disponibles")
            
        Returns:
            ReporteParqueadero: Reporte creado
        """
        data = {
            "parqueadero_id": parqueadero_id,
            "conductor_id": conductor_id,
            "tipo_reporte": tipo_reporte,
            "fecha_reporte": obtener_tiempo_bogota(),
            "procesado": False
        }
        
        return super().create(data)
    
    def verificar_reporte_existente(self, parqueadero_id: str, conductor_id: str) -> bool:
        """
        Verifica si un conductor ya reportó este parqueadero (sin procesar)
        
        Args:
            parqueadero_id: ID del parqueadero
            conductor_id: WhatsApp ID del conductor
            
        Returns:
            bool: True si ya existe un reporte activo del mismo conductor
        """
        reporte = self.collection.find_one({
            "parqueadero_id": parqueadero_id,
            "conductor_id": conductor_id,
            "procesado": False
        })
        return reporte is not None
    
    def contar_reportes_activos(self, parqueadero_id: str) -> int:
        """
        Cuenta los reportes activos (no procesados) de un parqueadero
        
        Args:
            parqueadero_id: ID del parqueadero
            
        Returns:
            int: Número de reportes activos
        """
        count = self.collection.count_documents({
            "parqueadero_id": parqueadero_id,
            "procesado": False
        })
        return count
    
    def obtener_reportes_activos(self, parqueadero_id: str) -> List[ReporteParqueadero]:
        """
        Obtiene todos los reportes activos de un parqueadero
        
        Args:
            parqueadero_id: ID del parqueadero
            
        Returns:
            List[ReporteParqueadero]: Lista de reportes activos
        """
        documents = self.collection.find({
            "parqueadero_id": parqueadero_id,
            "procesado": False
        })
        
        reportes = []
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            reportes.append(ReporteParqueadero(**doc))
        
        return reportes
    
    def marcar_reportes_como_procesados(self, parqueadero_id: str) -> int:
        """
        Marca todos los reportes de un parqueadero como procesados
        
        Args:
            parqueadero_id: ID del parqueadero
            
        Returns:
            int: Número de reportes marcados como procesados
        """
        result = self.collection.update_many(
            {
                "parqueadero_id": parqueadero_id,
                "procesado": False
            },
            {
                "$set": {"procesado": True}
            }
        )
        
        return result.modified_count
    
    def obtener_conductores_reportantes(self, parqueadero_id: str) -> List[str]:
        """
        Obtiene la lista de IDs de conductores que reportaron un parqueadero
        
        Args:
            parqueadero_id: ID del parqueadero
            
        Returns:
            List[str]: Lista de WhatsApp IDs de conductores
        """
        reportes = self.obtener_reportes_activos(parqueadero_id)
        return [reporte.conductor_id for reporte in reportes]
