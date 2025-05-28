# project-mqtt/shared/mqtt_config.py

# Konfigurasi Broker MQTT
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 8883  # Port TLS/SSL
MQTT_KEEPALIVE_INTERVAL = 60

# Kredensial (akan diambil dari .env)
MQTT_USERNAME = None
MQTT_PASSWORD = None

# Path ke CA certificate (relatif dari root proyek)
MQTT_TLS_CA_CERTS = "shared/ca.crt"

# Topik
TOPIC_BASE_NOTIFIKASI = "notifikasi/darurat"
TOPIC_SENSOR_SUHU_REQUEST = f"{TOPIC_BASE_NOTIFIKASI}/suhu/request"
TOPIC_SENSOR_SUHU_RESPONSE_BASE = f"{TOPIC_BASE_NOTIFIKASI}/suhu/response"

TOPIC_LWT_SENSOR_BASE = "status/sensor"

# QoS Level
QOS_REQUEST = 2
QOS_RESPONSE = 1
QOS_LWT = 1

# Pengaturan Message Expiry (dalam detik)
MESSAGE_EXPIRY_INTERVAL_SECONDS = 300