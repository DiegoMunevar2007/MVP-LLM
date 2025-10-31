"""
Herramientas de LangChain para consultar información de parqueaderos
"""
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from app.repositories.parqueadero_repository import ParqueaderoRepository


def create_parqueadero_tools(db):
    """Factory function para crear herramientas de parqueaderos"""
    
    parqueadero_repo = ParqueaderoRepository(db)
    
    @tool
    def ver_parqueaderos_disponibles() -> str:
        """
        Consulta todos los parqueaderos que tienen cupos disponibles.
        Retorna una lista con nombre, ubicación y cupos disponibles.
        
        Returns:
            str: Lista formateada de parqueaderos con cupos disponibles
        """
        parqueaderos = parqueadero_repo.find_with_available_spots()
        
        if not parqueaderos:
            return "No hay parqueaderos con cupos disponibles en este momento."
        
        resultado = "🅿️ **Parqueaderos con Cupos Disponibles:**\n\n"
        for i, p in enumerate(parqueaderos, 1):
            estado = p.estado_ocupacion or "Disponible"
            cupos = p.rango_cupos or p.cupos_libres
            resultado += f"{i}. **{p.name}**\n"
            resultado += f"   📍 {p.ubicacion}\n"
            resultado += f"   🚗 Cupos: {cupos}\n"
            resultado += f"   📊 Estado: {estado}\n"
            resultado += f"   🆔 ID: {p.id}\n"
            if p.ultima_actualizacion:
                resultado += f"   🕐 Actualizado: {p.ultima_actualizacion}\n"
            resultado += "\n"
        
        return resultado
    
    @tool
    def obtener_detalle_parqueadero(parqueadero_id: str) -> str:
        """
        Obtiene información detallada de un parqueadero específico por su ID.
        
        Args:
            parqueadero_id: ID del parqueadero a consultar
            
        Returns:
            str: Información detallada del parqueadero
        """
        parqueadero = parqueadero_repo.find_by_id(parqueadero_id)
        
        if not parqueadero:
            return f"No se encontró el parqueadero con ID: {parqueadero_id}"
        
        resultado = f"🅿️ **{parqueadero.name}**\n\n"
        resultado += f"📍 **Ubicación:** {parqueadero.ubicacion}\n"
        resultado += f"🏢 **Capacidad Total:** {parqueadero.capacidad} vehículos\n"
        
        cupos = parqueadero.rango_cupos or parqueadero.cupos_libres
        resultado += f"🚗 **Cupos Disponibles:** {cupos}\n"
        
        if parqueadero.estado_ocupacion:
            resultado += f"📊 **Estado:** {parqueadero.estado_ocupacion}\n"
        
        if parqueadero.ultima_actualizacion:
            resultado += f"🕐 **Última Actualización:** {parqueadero.ultima_actualizacion}\n"
        
        estado = "✅ Disponible" if parqueadero.tiene_cupos else "❌ Sin cupos"
        resultado += f"\n**Estado Actual:** {estado}\n"
        resultado += f"🆔 **ID:** {parqueadero.id}"
        
        return resultado
    
    @tool
    def buscar_parqueadero_por_nombre(nombre: str) -> str:
        """
        Busca un parqueadero por su nombre.
        
        Args:
            nombre: Nombre del parqueadero a buscar
            
        Returns:
            str: Información del parqueadero encontrado o mensaje de error
        """
        parqueadero = parqueadero_repo.find_by_name(nombre)
        
        if not parqueadero:
            return f"No se encontró ningún parqueadero con el nombre: {nombre}"
        
        return obtener_detalle_parqueadero(parqueadero.id)
    
    return [
        ver_parqueaderos_disponibles,
        obtener_detalle_parqueadero,
        buscar_parqueadero_por_nombre
    ]
