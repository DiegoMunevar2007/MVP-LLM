from app.models.whatsapp_webhook import WebhookPayload, Message
from app.services.whatsapp_message_service import WhatsAppMessageService
from app.services.whatsapp_flow_service import WhatsAppFlowService
from app.services.langchain_agent_service import LangChainAgentService
from app.logic.send_message import send_message
import app.logic.sesion as sesion
import os

def handle_message(payload: WebhookPayload, db):
    """
    Entrada principal para procesar mensajes (texto e interactivos)
    """
    msg = payload.get_mensaje()
    if not msg:
        return None
    
    # Verificar si es mensaje de texto o interactivo
    if not msg.text and not msg.interactive:
        return None
    
    # Inicializar servicios
    message_service = WhatsAppMessageService(db)
    flow_service = WhatsAppFlowService(db)
    
    usuario = handle_auth(msg, db, message_service)
    if not usuario:
        return None
    
    # Solo procesar si el usuario está completamente registrado
    if usuario.estado_registro == "completo":
        handle_user_interaction(msg, usuario, db, message_service, flow_service)
    
    return usuario

def handle_auth(msg: Message, db, message_service: WhatsAppMessageService):
    """
    Maneja autenticación y registro de usuarios
    """
    usuario = sesion.obtener_usuario(msg.from_, db)
    
    # Usuario no existe
    if not usuario:
        return handle_nuevo_usuario(msg.from_, db, message_service)
    
    # Usuario existe pero no completó registro
    if usuario.estado_registro != "completo":
        return handle_usuario_nombre(msg, db, message_service)
    
    return usuario

def handle_nuevo_usuario(user_id: str, db, message_service: WhatsAppMessageService):
    """
    Inicia el proceso de registro para nuevos usuarios
    """
    sesion.crear_usuario(user_id, db)
    message_service.enviar_bienvenida(user_id)
    message_service.solicitar_nombre(user_id)
    sesion.actualizar_estado_registro(user_id, "esperando_nombre", db)
    return None

def handle_usuario_nombre(msg: Message, db, message_service: WhatsAppMessageService):
    """
    Maneja la actualización del nombre para usuarios en proceso de registro
    """
    usuario = sesion.obtener_usuario(msg.from_, db)
    
    # Para registro, solo aceptar mensajes de texto
    if msg.type == "text" and msg.text and msg.text.body:
        texto = msg.text.body.strip()
        
        # Estado: esperando nombre
        if usuario.estado_registro == "esperando_nombre":
            # Guardar nombre y pasar a pedir código de referido
            sesion.actualizar_nombre(msg.from_, texto, db)
            message_service.solicitar_codigo_referido(msg.from_)
            sesion.actualizar_estado_registro(msg.from_, "esperando_codigo_referido", db)
            return None
        
        # Estado: esperando código de referido
        elif usuario.estado_registro == "esperando_codigo_referido":
            if texto.upper() == "SALTAR":
                # Usuario saltó el código, completar registro
                usuario_actualizado = sesion.obtener_usuario(msg.from_, db)
                
                # Generar código de referido
                codigo_generado = sesion.generar_y_asignar_codigo_referido(msg.from_, db)
                
                # Completar registro
                sesion.actualizar_estado_registro(msg.from_, "completo", db)
                usuario_actualizado = sesion.obtener_usuario(msg.from_, db)
                
                # Confirmación con código
                message_service.confirmar_registro(msg.from_, usuario_actualizado.name, codigo_generado)
                return usuario_actualizado
            else:
                # Procesar código de referido
                resultado = sesion.procesar_codigo_referido(msg.from_, texto.upper(), db)
                
                if resultado["exito"]:
                    # Código válido, completar registro
                    usuario_actualizado = sesion.obtener_usuario(msg.from_, db)
                    
                    # Generar su propio código de referido
                    codigo_generado = sesion.generar_y_asignar_codigo_referido(msg.from_, db)
                    
                    # Completar registro
                    sesion.actualizar_estado_registro(msg.from_, "completo", db)
                    usuario_actualizado = sesion.obtener_usuario(msg.from_, db)
                    
                    mensaje_exito = f"✅ {resultado['mensaje']}\n\n"
                    mensaje_exito += f"Tu código de referido: `{codigo_generado}`\n\n"
                    mensaje_exito += "¡Ya estás registrado! 🎉"
                    send_message(msg.from_, mensaje_exito)
                    
                    return usuario_actualizado
                else:
                    # Código inválido
                    mensaje_error = f"❌ {resultado['mensaje']}\n\nIntenta nuevamente o escribe *SALTAR* para continuar sin código."
                    send_message(msg.from_, mensaje_error)
                    return None
    
    return None

def extract_message_text(msg: Message) -> str:
    """
    Extrae el texto del mensaje, ya sea de texto tradicional o interactivo
    """
    print(f"Debug - Tipo de mensaje: {msg.type}")
    
    if msg.type == "text" and msg.text:
        text = msg.text.body.lower().strip()
        print(f"Debug - Texto extraído: {text}")
        return text
    elif msg.type == "interactive" and msg.interactive:
        print(f"Debug - Mensaje interactivo: {msg.interactive}")
        if msg.interactive.type == "button_reply" and msg.interactive.button_reply:
            text = msg.interactive.button_reply.id.lower().strip()
            print(f"Debug - ID botón extraído: {text}")
            return text
        elif msg.interactive.type == "list_reply" and msg.interactive.list_reply:
            text = msg.interactive.list_reply.id.lower().strip()
            print(f"Debug - ID lista extraído: {text}")
            return text
    
    print("Debug - No se pudo extraer texto")
    return ""

def handle_user_interaction(msg: Message, usuario, db, message_service: WhatsAppMessageService, flow_service: WhatsAppFlowService):
    """
    Maneja la interacción principal con usuarios registrados usando agente LangChain.
    Ya no usa mensajes interactivos, sino conversación natural con Tool Use.
    """
    text = extract_message_text(msg)
    
    # Actualizar estado a conversando si es la primera interacción
    if usuario.estado_chat.paso_actual == "inicial":
        # Ya no enviamos saludo manual, el agente lo maneja
        sesion.actualizar_paso_chat(msg.from_, "conversando", db)
    
    # Usar el agente de LangChain para procesar el mensaje
    agent_service = LangChainAgentService(db)
    
    try:
        # Procesar mensaje con el agente según el rol
        respuesta = agent_service.process_message(msg.from_, text, usuario.rol)
        
        # Enviar respuesta por WhatsApp (send_message ya tiene PHONE_NUMBER_ID internamente)
        send_message(msg.from_, respuesta)
        
    except Exception as e:
        print(f"Error en interacción con agente: {e}")
        if usuario.rol == "conductor":
            # Fallback al sistema anterior si hay error
            handle_conductor(text, msg.from_, db, flow_service)
        elif usuario.rol == "gestor_parqueadero":
            handle_gestor(text, msg.from_, db, flow_service)
        else:
            message_service.error_rol_no_reconocido(msg.from_)

def handle_conductor(text: str, user_id: str, db, flow_service: WhatsAppFlowService):
    """
    Maneja el flujo específico para conductores
    """
    usuario = sesion.obtener_usuario(user_id, db)
    current_step = usuario.estado_chat.paso_actual
    
    # Comandos especiales que funcionan en cualquier momento
    if text.lower().startswith("desuscribir"):
        flow_service.handle_desuscribir_comando(text, user_id)
        return
    
    # Mostrar menú si está en estado inicial o si solicita el menú
    if current_step == "inicial" or text in ["menu", "menú"]:
        flow_service.mostrar_menu_conductor(user_id)
        return
    
    # Procesar opciones del menú principal
    if current_step == "esperando_opcion_menu":
        flow_service.handle_conductor_menu_option(text, user_id)
        return
    
    # Procesar opciones del menú de suscripciones
    if current_step == "esperando_opcion_suscripcion":
        flow_service.handle_suscripcion_menu_option(text, user_id)
        return
    
    # Procesar selección de parqueadero para suscripción
    if current_step == "esperando_seleccion_parqueadero":
        flow_service.handle_seleccion_parqueadero_suscripcion(text, user_id)
        return
    
    # Procesar selección de parqueadero para ver detalles
    if current_step == "viendo_parqueaderos":
        flow_service.handle_seleccion_parqueadero_detalles(text, user_id)
        return
    
    # Gestionar suscripciones (desuscribir)
    if current_step == "gestionando_suscripciones":
        flow_service.handle_gestion_suscripciones(text, user_id)
        return
    
    # Si no está en ningún flujo específico, mostrar menú
    flow_service.mostrar_menu_conductor(user_id)

def handle_gestor(text: str, user_id: str, db, flow_service: WhatsAppFlowService):
    """
    Maneja el flujo específico para gestores de parqueaderos
    """
    usuario = sesion.obtener_usuario(user_id, db)
    current_step = usuario.estado_chat.paso_actual
    
    # Mostrar menú si está en estado inicial o si solicita el menú
    if current_step == "inicial" or text in ["menu", "menú"]:
        flow_service.mostrar_menu_gestor(user_id)
        return
    
    # Procesar opciones del menú
    if current_step == "esperando_opcion_menu":
        flow_service.handle_gestor_menu_option(text, user_id)
        return
    
    if current_step == "esperando_cambio_cupos":
        flow_service.handle_cupos_gestor(text, user_id)
        return
    
    if current_step == "esperando_confirmacion_cupos":
        flow_service.handle_cupos_gestor(text, user_id)
        return
    
    # Si no está en ningún flujo específico, mostrar menú
    flow_service.mostrar_menu_gestor(user_id)