# Asistente-IA-Soporte-Tecnico-MikroTik
Un asistente inteligente que permite interactuar con routers MikroTik mediante lenguaje natural, utilizando procesamiento de lenguaje natural (NLP) y modelos de transformers para entender y ejecutar comandos de configuración.

## 🚀 Características
* 🤖 Interfaz conversacional tipo chatbot
* 🔌 Conexión API a routers MikroTik
* 💬 Comprensión de lenguaje natural en español
* ⚡ Ejecución de comandos de configuración
* 🔄 Reconocimiento de intenciones sociales (agradecimientos, saludos, etc.)
* 📊 Visualización de datos de configuración
* 🔐 Soporte para múltiples routers en la misma red

## 📋 Comandos Soportados
### 🔧 Configuración
* Configuración de direcciones IP
* Habilitación de NAT masquerade
* Configuración de servidores DHCP y DNS

### 🔍 Consultas
* Tabla de enrutamiento
* Interfaces de red
* Reglas de firewall
* Registros del sistema (logs)
* Configuración DHCP
* Servidores DNS

### 💬 Interacciones Sociales
* Agradecimientos
* Saludos y despedidas
* Elogios
* Consultas sobre el estado del asistente

### ⚙️ Requisitos del Sistema
* Python 3.8 o superior
* Router MikroTik con API habilitada
* Conexión de red al router

## 📦 Instalación
1. Clona el repositorio:

git clone https://github.com/tu-usuario/asistente-mikrotik-ai.git
cd asistente-mikrotik-ai

2. Instala las dependencias:

pip install -r requirements.txt

3. Descarga el modelo de lenguaje para spaCy:

python -m spacy download es_core_news_sm

## 🚀 Uso
1. Inicia la aplicación:

python app.py

2. Abre tu navegador y ve a http://localhost:5000

3. Completa los datos de conexión:

* Dirección IP del router
* Usuario y contraseña
* Puerto (generalmente 8728)
  
4. ¡Comienza a chatear con el asistente!

## 💡 Ejemplos de Comandos
* "Configurar la IP 192.168.1.1/24 en la interfaz ether2"
* "Habilitar NAT masquerade"
* "Mostrar la tabla de enrutamiento"
* "Ver las reglas de firewall"
* "Gracias por la ayuda"
   
## 🛠️ Tecnologías Utilizadas
* Flask: Framework web para la interfaz
* routeros_api: Cliente API para MikroTik
* spaCy: Procesamiento de lenguaje natural
* Transformers: Modelos de lenguaje para español
* BERT: Modelo de clasificación de intenciones

## 🔒 Seguridad
* Las credenciales se almacenan temporalmente en la sesión
* Conexiones SSL/TLS soportadas
* Validación de entradas del usuario

## ❓ Solución de Problemas
### Error de conexión
* Verifica que el servicio API esté habilitado en el router
* Confirma que las credenciales sean correctas
* Asegúrate de que el firewall permita conexiones en el puerto 8728

### Error de comando
* El asistente pedirá aclaraciones si no entiende un comando
* Usa ejemplos de la lista de comandos soportados

## 🤝 Contribuir
Las contribuciones son bienvenidas. Por favor:
1. Haz fork del proyecto
2. Crea una rama para tu feature (git checkout -b feature/AmazingFeature)
3. Commit tus cambios (git commit -m 'Add some AmazingFeature')
4. Push a la rama (git push origin feature/AmazingFeature)
5. Abre un Pull Request

## 📄 Licencia
Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.

