# project-mqtt/notifier_client/main.py
import sys
import os
import ssl

# --- MODIFIKASI sys.path START ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(current_file_dir)
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)
# --- MODIFIKASI sys.path END ---

import paho.mqtt.client as mqtt
import paho.mqtt.properties as mqtt_props
import json
import random
import time
from dotenv import load_dotenv

from shared import mqtt_config

load_dotenv(dotenv_path=os.path.join(project_root_dir, '.env'))
# DEBUGGING .env load
# print(f"NOTIFIER DEBUG - Username dari env: {os.getenv('MQTT_USERNAME')}")
# print(f"NOTIFIER DEBUG - Password dari env ada?: {'Ya' if os.getenv('MQTT_PASSWORD') else 'Tidak'}")

MQTT_USERNAME = os.getenv("MQTT_USERNAME_NOTIFIER", mqtt_config.MQTT_USERNAME)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD_NOTIFIER", mqtt_config.MQTT_PASSWORD)
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", mqtt_config.MQTT_BROKER_HOST)

def get_rc_value(rc_param):
    if isinstance(rc_param, int): return rc_param
    elif hasattr(rc_param, 'value'): return rc_param.value
    try: return int(rc_param)
    except ValueError: return -1

def on_connect(client, userdata, flags, reason_code, properties):
    rc_value = get_rc_value(reason_code)
    if rc_value == 0:
        print(f"Notifier ({client._client_id.decode()}): Terhubung AMAN ke Broker MQTT (v5/TLS)!")
        (result_req, mid_req) = client.subscribe(mqtt_config.TOPIC_SENSOR_SUHU_REQUEST, qos=mqtt_config.QOS_REQUEST)
        if result_req != mqtt.MQTT_ERR_SUCCESS: print(f"Notifier: Gagal subscribe ke {mqtt_config.TOPIC_SENSOR_SUHU_REQUEST}, error: {mqtt.error_string(result_req)}")
        
        topic_lwt_all_sensors = f"{mqtt_config.TOPIC_LWT_SENSOR_BASE}/+/status"
        (result_lwt, mid_lwt) = client.subscribe(topic_lwt_all_sensors, qos=mqtt_config.QOS_LWT)
        if result_lwt != mqtt.MQTT_ERR_SUCCESS: print(f"Notifier: Gagal subscribe ke topik status sensor, error: {mqtt.error_string(result_lwt)}")
    else:
        print(f"Notifier: Gagal terhubung, return code {rc_value} - {mqtt.error_string(rc_value)}")

# PERBAIKAN SIGNATURE on_disconnect
def on_disconnect(client, userdata, flags_or_rc, reason_code=None, properties=None):
    rc_to_check = reason_code if reason_code is not None else flags_or_rc
    rc_value = get_rc_value(rc_to_check)
    
    if rc_value == 0:
        print(f"Notifier: Terputus secara normal dari broker.")
    else:
        print(f"Notifier: Terputus dari broker dengan kode {rc_value} - {mqtt.error_string(rc_value)}.")
        # print(f"Notifier Disconnect flags: {flags_or_rc}") # Untuk debug jika perlu

def on_message(client, userdata, msg):
    print("-" * 30)
    print(f"Notifier: Menerima pesan dari topik '{msg.topic}' (QoS: {msg.qos}, Retain: {msg.retain})")
    response_topic, correlation_data = None, None
    if msg.properties:
        if hasattr(msg.properties, 'ResponseTopic'): response_topic = msg.properties.ResponseTopic
        if hasattr(msg.properties, 'CorrelationData'): correlation_data = msg.properties.CorrelationData
    try:
        payload_data = json.loads(msg.payload.decode())
        print("Notifier: Payload Diterima:")
        print(json.dumps(payload_data, indent=2))
        if msg.topic == mqtt_config.TOPIC_SENSOR_SUHU_REQUEST:
            print("Notifier: Memproses REQUEST notifikasi suhu...")
            if payload_data.get("level") == "KRITIS": print("!!! ALARM SUHU: NOTIFIKASI KRITIS TERDETEKSI !!!")
            elif payload_data.get("level") == "PERINGATAN": print("--- PERINGATAN SUHU: PERIKSA KONDISI ---")
            if response_topic:
                response_payload = {
                    "status": "ACKNOWLEDGED", "original_request_id": payload_data.get("correlation_id"),
                    "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "message": f"Notifikasi suhu level '{payload_data.get('level')}' telah diterima."}
                response_props = mqtt_props.Properties(mqtt_props.PacketTypes.PUBLISH)
                if correlation_data: response_props.CorrelationData = correlation_data
                res = client.publish(response_topic, json.dumps(response_payload), qos=mqtt_config.QOS_RESPONSE, properties=response_props)
                if res.rc == mqtt.MQTT_ERR_SUCCESS: print(f"Notifier: RESPONSE dikirim ke topik '{response_topic}'")
                else: print(f"Notifier: Gagal mengirim RESPONSE, error: {mqtt.error_string(res.rc)}")
            else: print("Notifier: Tidak ada Response Topic di request, tidak mengirim balasan.")
        elif msg.topic.startswith(mqtt_config.TOPIC_LWT_SENSOR_BASE):
            sensor_id_from_topic = msg.topic.split('/')[2]
            status = payload_data.get("status", "UNKNOWN_STATUS")
            print(f"--- STATUS SENSOR '{sensor_id_from_topic}': {status} ---")
            if status == "OFFLINE_UNEXPECTED": print(f"!!! PERHATIAN: Sensor {sensor_id_from_topic} OFFLINE tidak normal !!!")
    except json.JSONDecodeError: print(f"Notifier: Menerima payload non-JSON: {msg.payload.decode()}")
    except Exception as e: print(f"Notifier: Error memproses pesan: {e}")
    print("-" * 30)

def connect_mqtt():
    client_id_prefix = "notifier-client"
    client_id = f"{client_id_prefix}-{random.randint(0, 1000)}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    else: # Tambahkan log jika tidak ada username/password
        print("Notifier: PERINGATAN - Username/Password MQTT tidak diset. Mencoba koneksi anonim.")


    ca_certs_path = os.path.join(project_root_dir, mqtt_config.MQTT_TLS_CA_CERTS)
    if not os.path.exists(ca_certs_path):
        print(f"ERROR KRITIS: File CA Certificate tidak ditemukan di {ca_certs_path}"); return None
    try:
        client.tls_set(ca_certs=ca_certs_path,
                       certfile=None, keyfile=None,
                       cert_reqs=ssl.CERT_REQUIRED,
                       tls_version=ssl.PROTOCOL_TLS_CLIENT)
        print(f"TLS/SSL dikonfigurasi. Mencoba koneksi aman ke {MQTT_BROKER_HOST}:{mqtt_config.MQTT_BROKER_PORT}")
        print(f"Menggunakan CA cert dari: {ca_certs_path}")
    except Exception as e: print(f"Error saat konfigurasi TLS/SSL: {e}"); return None

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_HOST, mqtt_config.MQTT_BROKER_PORT, mqtt_config.MQTT_KEEPALIVE_INTERVAL)
    except ssl.SSLCertVerificationError as e: print(f"GAGAL KONEKSI TLS: SSLCertVerificationError - {e}"); return None
    except ConnectionRefusedError as e: print(f"GAGAL KONEKSI: ConnectionRefusedError - {e}"); return None
    except Exception as e: print(f"Gagal terhubung ke broker (TLS): {e}"); return None
    return client

def run_notifier():
    client = connect_mqtt()
    if not client: return
    try:
        print("Notifier: Menunggu notifikasi... (Tekan Ctrl+C untuk keluar)")
        client.loop_forever()
    except KeyboardInterrupt: print("Notifier: Menghentikan notifier client...")
    finally:
        if client and client.is_connected(): client.disconnect()
        print("Notifier: Koneksi MQTT ditutup.")
if __name__ == '__main__':
    run_notifier()