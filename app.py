import routeros_api
from flask import Flask, render_template, request, jsonify, session
import re
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import numpy as np

app = Flask(__name__)
app.secret_key = 'mikrotik-api-key-2024'

# Cargar modelos de transformers para español
try:
    # Modelo para clasificación de intenciones
    tokenizer = AutoTokenizer.from_pretrained("dccuchile/bert-base-spanish-wwm-uncased")
    model = AutoModelForSequenceClassification.from_pretrained("dccuchile/bert-base-spanish-wwm-uncased")
    
    # Pipeline para análisis de texto en español
    nlp_pipeline = pipeline(
        "text-classification", 
        model="finiteautomata/beto-sentiment-analysis", 
        tokenizer="finiteautomata/beto-sentiment-analysis"
    )
    
    print("Modelos de transformers cargados correctamente")
except Exception as e:
    print(f"Error cargando modelos: {e}")
    tokenizer = None
    model = None
    nlp_pipeline = None

# Variable global para almacenar la conexión API
mikrotik_api = None

# Definición de intenciones y sus ejemplos
INTENCIONES = {
    0: {"accion": "ip_address_add", "nombre": "Configurar dirección IP", "ejemplos": [
        "configurar ip 192.168.1.1/24 en ether1",
        "agregar dirección 10.0.0.1/8 a la interfaz wlan2",
        "establecer la ip 172.16.0.1/16 en el puerto ether3"
    ]},
    1: {"accion": "nat_add", "nombre": "Configurar NAT", "ejemplos": [
        "habilitar nat masquerade",
        "configurar enmascaramiento en la wan",
        "activar nat para internet"
    ]},
    2: {"accion": "route_print", "nombre": "Mostrar rutas", "ejemplos": [
        "mostrar tabla de enrutamiento",
        "ver las rutas configuradas",
        "consultar routing table"
    ]},
    3: {"accion": "interface_print", "nombre": "Mostrar interfaces", "ejemplos": [
        "listar interfaces de red",
        "mostrar estado de puertos",
        "ver interfaces disponibles"
    ]},
    4: {"accion": "firewall_filter_print", "nombre": "Mostrar firewall", "ejemplos": [
        "mostrar reglas de firewall",
        "consultar filtros configurados",
        "ver políticas de firewall"
    ]},
    5: {"accion": "dhcp_server_print", "nombre": "Mostrar DHCP", "ejemplos": [
        "mostrar configuración dhcp",
        "ver servidor dhcp",
        "consultar asignaciones dhcp"
    ]},
    6: {"accion": "dns_print", "nombre": "Mostrar DNS", "ejemplos": [
        "mostrar servidores dns",
        "consultar configuración dns",
        "ver resolvers dns"
    ]},
    7: {"accion": "log_print", "nombre": "Mostrar logs", "ejemplos": [
        "ver registros del sistema",
        "mostrar logs de eventos",
        "consultar bitácora del router"
    ]}
}

def clasificar_intencion_bert(instruccion):
    """Clasificar la intención usando un modelo BERT en español"""
    if tokenizer is None or model is None:
        return None
    
    try:
        # Tokenizar la instrucción
        inputs = tokenizer(instruccion, return_tensors="pt", truncation=True, padding=True, max_length=128)
        
        # Obtener predicción
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Obtener la intención predicha
        predicted_class = torch.argmax(outputs.logits, dim=1).item()
        
        # Calcular confianza
        probabilities = torch.softmax(outputs.logits, dim=1)
        confidence = probabilities[0][predicted_class].item()
        
        return predicted_class, confidence
    
    except Exception as e:
        print(f"Error en clasificación BERT: {e}")
        return None

def extraer_entidades_avanzado(instruccion):
    """Extraer entidades usando múltiples enfoques"""
    # Extraer dirección IP con regex mejorado
    ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})'
    ip_match = re.search(ip_pattern, instruccion)
    ip_address = ip_match.group(1) if ip_match else None
    
    # Extraer interfaz con patrones más específicos
    interface_pattern = r'\b(ether\d+|wlan\d+|bridge\d+|vlan\d+|pppoe-out\d+)\b'
    interface_match = re.search(interface_pattern, instruccion.lower())
    
    interfaz = None
    if interface_match:
        interfaz = interface_match.group(1)
    else:
        # Búsqueda de patrones más flexibles
        flex_patterns = [
            r'(?:interfaz|interface|puerto|en)\s+(ether\d+|wlan\d+|bridge\d+|vlan\d+|pppoe-out\d+)',
            r'(?:interfaz|interface|puerto|en)\s+(\d+)'
        ]
        
        for pattern in flex_patterns:
            match = re.search(pattern, instruccion.lower())
            if match:
                if match.group(1).isdigit():
                    # Si solo encontró un número, asumir que es ether
                    interfaz = f"ether{match.group(1)}"
                else:
                    interfaz = match.group(1)
                break
    
    # Si aún no tenemos interfaz, usar valor por defecto
    if not interfaz:
        # Buscar pistas en el texto
        if any(palabra in instruccion.lower() for palabra in ["ethernet", "ether", "cable", "lan"]):
            interfaz = "ether1"
        elif any(palabra in instruccion.lower() for palabra in ["wlan", "wifi", "inalámbrica", "wireless"]):
            interfaz = "wlan1"
        elif any(palabra in instruccion.lower() for palabra in ["vlan", "virtual"]):
            interfaz = "vlan1"
        else:
            interfaz = "ether1"  # Valor por defecto
    
    return {
        "ip": ip_address,
        "interfaz": interfaz
    }

def obtener_interfaces_disponibles(connection):
    """Obtener lista de interfaces disponibles en el router"""
    try:
        resource = connection.get_resource('/interface')
        interfaces = resource.get()
        return [iface['name'] for iface in interfaces]
    except:
        return []

def validar_interfaz(interfaz, interfaces_disponibles):
    """Validar si una interfaz existe en el router"""
    # Buscar coincidencia exacta
    if interfaz in interfaces_disponibles:
        return interfaz
    
    # Buscar coincidencias parciales
    for iface in interfaces_disponibles:
        if interfaz.lower() in iface.lower():
            return iface
    
    # Si no se encuentra, devolver la primera interfaz Ethernet disponible
    for iface in interfaces_disponibles:
        if 'ether' in iface.lower():
            return iface
    
    # Si no hay interfaces Ethernet, devolver la primera disponible
    return interfaces_disponibles[0] if interfaces_disponibles else "ether1"

def generar_comando_api_avanzado(instruccion):
    """Convertir instrucción en lenguaje natural a comando de API usando modelos avanzados"""
    # Primero intentar con BERT
    resultado_bert = clasificar_intencion_bert(instruccion)
    
    if resultado_bert:
        intent_class, confidence = resultado_bert
        if confidence > 0.7:  # Umbral de confianza
            accion = INTENCIONES.get(intent_class, {}).get("accion")
            if accion:
                # Extraer entidades
                entidades = extraer_entidades_avanzado(instruccion)
                
                # Generar mensaje basado en la acción
                if accion == "ip_address_add":
                    if not entidades["ip"]:
                        return {"tipo": "unknown", "mensaje": "Necesito que especifiques una dirección IP. Ejemplo: 'configurar IP 192.168.1.1/24 en ether1'"}
                    
                    interfaz = entidades["interfaz"] or "ether1"
                    return {
                        "tipo": accion,
                        "params": {"address": entidades["ip"], "interface": interfaz},
                        "mensaje": f"Agregando dirección IP {entidades['ip']} a la interfaz {interfaz}"
                    }
                
                elif accion == "nat_add":
                    interfaz = entidades["interfaz"] or "ether1"
                    return {
                        "tipo": accion,
                        "params": {"chain": "srcnat", "action": "masquerade", "out-interface": interfaz},
                        "mensaje": f"Configurando NAT masquerade en la interfaz {interfaz}"
                    }
                
                else:
                    return {"tipo": accion, "mensaje": f"{INTENCIONES[intent_class]['nombre']}"}
    
    # Si BERT falla o tiene baja confianza, usar enfoque basado en reglas mejorado
    return generar_comando_api_reglas(instruccion)

def generar_comando_api_reglas(instruccion):
    """Enfoque basado en reglas como fallback"""
    instruccion = instruccion.lower()
    
    # Extraer entidades
    entidades = extraer_entidades_avanzado(instruccion)
    
    # Detectar intención basada en palabras clave con prioridades
    palabras_clave = {
        "ip": ["ip", "dirección", "address", "configurar ip", "agregar ip"],
        "nat": ["nat", "enmascaramiento", "masquerade", "enmascarar"],
        "rutas": ["rutas", "enrutamiento", "routing", "tabla de rutas"],
        "interfaces": ["interfaces", "puertos", "conexiones", "interface"],
        "firewall": ["firewall", "filtros", "reglas firewall", "políticas"],
        "dhcp": ["dhcp", "servidor dhcp", "asignación ip"],
        "dns": ["dns", "servidor dns", "resolución"],
        "logs": ["logs", "registros", "bitácora", "eventos"]
    }
    
    # Contar ocurrencias de palabras clave
    conteo = {key: 0 for key in palabras_clave}
    for key, palabras in palabras_clave.items():
        for palabra in palabras:
            if palabra in instruccion:
                conteo[key] += 1
    
    # Determinar la intención principal
    intencion_principal = max(conteo.items(), key=lambda x: x[1])[0] if max(conteo.values()) > 0 else None
    
    if intencion_principal == "ip" and conteo["ip"] > 0:
        if not entidades["ip"]:
            return {"tipo": "unknown", "mensaje": "Necesito que especifiques una dirección IP. Ejemplo: 'configurar IP 192.168.1.1/24 en ether1'"}
        
        interfaz = entidades["interfaz"] or "ether1"
        return {
            "tipo": "ip_address_add",
            "params": {"address": entidades["ip"], "interface": interfaz},
            "mensaje": f"Agregando dirección IP {entidades['ip']} a la interfaz {interfaz}"
        }
    
    elif intencion_principal == "nat" and conteo["nat"] > 0:
        interfaz = entidades["interfaz"] or "ether1"
        return {
            "tipo": "nat_add",
            "params": {"chain": "srcnat", "action": "masquerade", "out-interface": interfaz},
            "mensaje": f"Configurando NAT masquerade en la interfaz {interfaz}"
        }
    
    elif intencion_principal == "rutas":
        return {"tipo": "route_print", "mensaje": "Mostrando tabla de enrutamiento"}
    
    elif intencion_principal == "interfaces":
        return {"tipo": "interface_print", "mensaje": "Mostrando interfaces de red"}
    
    elif intencion_principal == "firewall":
        return {"tipo": "firewall_filter_print", "mensaje": "Mostrando reglas de firewall"}
    
    elif intencion_principal == "dhcp":
        return {"tipo": "dhcp_server_print", "mensaje": "Mostrando configuración DHCP"}
    
    elif intencion_principal == "dns":
        return {"tipo": "dns_print", "mensaje": "Mostrando configuración DNS"}
    
    elif intencion_principal == "logs":
        return {"tipo": "log_print", "mensaje": "Mostrando registros del sistema"}
    
    else:
        return {"tipo": "unknown", "mensaje": "No entendí tu solicitud. Puedo ayudarte con: configuración de IP, NAT, o mostrar información del router."}

def ejecutar_comando_api(comando):
    """Ejecutar un comando en el router mediante routeros_api"""
    global mikrotik_api
    
    if not mikrotik_api:
        return False, "No hay conexión activa con el router"
    
    try:
        connection = mikrotik_api.get_api()
        
        # Obtener interfaces disponibles para validación
        interfaces_disponibles = obtener_interfaces_disponibles(connection) 

        if comando["tipo"] == "ip_address_add":

            interfaz_validada = validar_interfaz(comando["params"]["interface"], interfaces_disponibles)
            
            resource = connection.get_resource('/ip/address')
            resource.add(
                address=comando["params"]["address"], 
                interface=interfaz_validada
            )
            return True, f"✓ Dirección IP {comando['params']['address']} agregada correctamente a {interfaz_validada}"

            resource = connection.get_resource('/ip/address')
            resource.add(address=comando["params"]["address"], interface=comando["params"]["interface"])
            return True, f"✓ Dirección IP {comando['params']['address']} agregada correctamente a {comando['params']['interface']}"
        
        elif comando["tipo"] == "nat_add":
            resource = connection.get_resource('/ip/firewall/nat')
            resource.add(chain=comando["params"]["chain"], action=comando["params"]["action"], 
                         out_interface=comando["params"]["out-interface"])
            return True, f"✓ Regla NAT agregada correctamente en {comando['params']['out-interface']}"
        
        elif comando["tipo"] == "route_print":
            resource = connection.get_resource('/ip/route')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "log_print":
            resource = connection.get_resource('/log')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "ip_address_print":
            resource = connection.get_resource('/ip/address')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "firewall_filter_print":
            resource = connection.get_resource('/ip/firewall/filter')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "firewall_nat_print":
            resource = connection.get_resource('/ip/firewall/nat')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "interface_print":
            resource = connection.get_resource('/interface')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "dhcp_server_print":
            resource = connection.get_resource('/ip/dhcp-server')
            result = resource.get()
            return True, result
        
        elif comando["tipo"] == "dns_print":
            resource = connection.get_resource('/ip/dns')
            result = resource.get()
            return True, result
        
        else:
            return False, "Tipo de comando no válido"
            
    except Exception as e:
        return False, f"Error al ejecutar comando: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/connect', methods=['POST'])
def api_connect():
    global mikrotik_api
    
    data = request.json
    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    
    try:
        # Crear conexión API
        mikrotik_api = routeros_api.RouterOsApiPool(
            host,
            username=username,
            password=password,
            port=8728,
            use_ssl=False,
            plaintext_login=True
        )
        
        # Probar la conexión
        connection = mikrotik_api.get_api()
        identity = connection.get_resource('/system/identity').get()
        router_name = identity[0]['name']
        
        # Guardar información de conexión en sesión
        session['connected'] = True
        session['router_name'] = router_name
        
        return jsonify({
            'success': True, 
            'message': f'Conectado a: {router_name}',
            'router_name': router_name  # Asegúrate de incluir esta línea
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error de conexión: {str(e)}'})
    
@app.route('/api/command', methods=['POST'])
def api_command():
    global mikrotik_api
    
    if not mikrotik_api:
        return jsonify({'success': False, 'message': 'No hay conexión activa con un router'})
    
    # Procesar el comando
    data = request.json
    user_input = data.get('message', '')
    
    # Generar comando de API usando el nuevo sistema
    comando = generar_comando_api_avanzado(user_input)
    
    if comando['tipo'] == 'unknown':
        return jsonify({'success': False, 'message': comando['mensaje']})
    
    # Ejecutar comando
    success, result = ejecutar_comando_api(comando)
    
    if success:
        return jsonify({
            'success': True,
            'message': comando['mensaje'],
            'data': result
        })
    else:
        return jsonify({'success': False, 'message': result})

@app.route('/api/disconnect', methods=['POST'])
def api_disconnect():
    global mikrotik_api
    
    if mikrotik_api:
        try:
            mikrotik_api.disconnect()
        except:
            pass
        mikrotik_api = None
    
    if 'connected' in session:
        session.pop('connected')
    
    return jsonify({'success': True, 'message': 'Desconectado del router'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)