from app.repositories.base_repository import BaseRepository
from app.models.database_models import User, Conductor, GestorParqueadero, EstadoChat
from typing import Union, List, Dict, Any
from pymongo.database import Database
from app.utils.tiempo_utils import obtener_tiempo_bogota

class ConductorRepository(BaseRepository):
    def __init__(self, db: Database):
        super().__init__(db, "usuarios", Conductor)

    def find_all(self) -> list[Conductor]:
        documents = self.collection.find()
        users = []
        for doc in documents:
            if doc["rol"] == "conductor":
                users.append(Conductor(**doc))
        return users

    def create(self, data: Conductor) -> Conductor:
        validated_data = Conductor(**data.model_dump(by_alias=True))
        result = self.collection.insert_one(validated_data.model_dump(by_alias=True))
        resultado = self.find_by_id(str(result.inserted_id))
        return resultado
    
class GestorParqueaderoRepository(BaseRepository):
    def __init__(self, db: Database):
        super().__init__(db, "usuarios", GestorParqueadero)

    def find_all(self) -> list[GestorParqueadero]:
        documents = self.collection.find()
        users = []
        for doc in documents:
            if doc["rol"] == "gestor_parqueadero":
                users.append(GestorParqueadero(**doc))
        return users

    def create(self, data: GestorParqueadero) -> GestorParqueadero:
        validated_data = GestorParqueadero(**data.model_dump(by_alias=True))
        result = self.collection.insert_one(validated_data.model_dump(by_alias=True))
        resultado = self.find_by_id(str(result.inserted_id))
        return resultado

    def obtener_parqueadero_id(self, gestor_id: str):
        gestor = self.find_by_id(gestor_id)
        return gestor.parqueadero_id if gestor else None
    def update(self, gestor: GestorParqueadero) -> GestorParqueadero:
        update_data = gestor.model_dump(by_alias=True)
        self.collection.update_one({"_id": gestor.id}, {"$set": update_data})
        return self.find_by_id(gestor.id)

class UserRepository(BaseRepository):
    def __init__(self, db: Database):
        super().__init__(db, "usuarios", User)

    def find_all(self) -> list[User]:
        documents = self.collection.find()
        users = [User(**doc) for doc in documents]
        return users

    def create(self, data: Union[Conductor, GestorParqueadero]) -> User:
        validated_data = User(**data.model_dump(by_alias=True))
        result = self.collection.insert_one(validated_data.model_dump(by_alias=True))
        resultado = self.find_by_id(str(result.inserted_id))
        return resultado
    
    def actualizar_estado_chat(self, user_id: str, paso_actual: str) -> User:
        update_data = {
            "estado_chat.ultima_interaccion": obtener_tiempo_bogota(),
            "estado_chat.paso_actual": paso_actual
        }
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)

    def actualizar_estado_registro(self, user_id: str, estado_registro: str) -> User:
        update_data = {
            "estado_registro": estado_registro
        }
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    def actualizar_nombre(self, user_id: str, nombre: str) -> User:
        update_data = {
            "name": nombre,
            "estado_registro": "completo"  
        }
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    def actualizar_contexto_temporal(self, user_id: str, contexto: dict) -> User:
        """Actualiza el contexto temporal del usuario"""
        update_data = {
            "estado_chat.contexto_temporal": contexto
        }
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    # ==================== GROWTH LOOP - SISTEMA DE REFERIDOS Y PREMIUM ====================
    
    def asignar_codigo_referido(self, user_id: str, codigo: str) -> User:
        """Asigna un código de referido único al usuario"""
        update_data = {"codigo_referido": codigo}
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    def buscar_por_codigo_referido(self, codigo: str) -> User:
        """Busca un usuario por su código de referido"""
        doc = self.collection.find_one({"codigo_referido": codigo})
        return User(**doc) if doc else None
    
    def registrar_referido(self, user_id: str, codigo_referidor: str) -> User:
        """Registra que este usuario fue referido por alguien"""
        update_data = {"referido_por": codigo_referidor}
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    def incrementar_referidos(self, user_id: str) -> User:
        """Incrementa el contador de referidos del usuario"""
        self.collection.update_one({"_id": user_id}, {"$inc": {"numero_referidos": 1}})
        return self.find_by_id(user_id)
    
    def activar_premium(self, user_id: str, fecha_expiracion: str) -> User:
        """Activa el acceso premium del usuario con fecha de expiración"""
        update_data = {
            "es_premium": True,
            "fecha_expiracion_premium": fecha_expiracion
        }
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    def extender_premium(self, user_id: str, nueva_fecha_expiracion: str) -> User:
        """Extiende la fecha de expiración del premium"""
        update_data = {"fecha_expiracion_premium": nueva_fecha_expiracion}
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    def desactivar_premium(self, user_id: str) -> User:
        """Desactiva el acceso premium del usuario"""
        update_data = {
            "es_premium": False,
            "fecha_expiracion_premium": None
        }
        self.collection.update_one({"_id": user_id}, {"$set": update_data})
        return self.find_by_id(user_id)
    
    def verificar_codigo_disponible(self, codigo: str) -> bool:
        """Verifica si un código de referido está disponible (no existe)"""
        return self.collection.find_one({"codigo_referido": codigo}) is None