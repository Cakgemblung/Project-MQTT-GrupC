# project-mqtt/sensor_simulator/main.py
import sys
import os
import ssl # Untuk konfigurasi TLS yang lebih detail

# --- MODIFIKASI sys.path START ---
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(current_file_dir)
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)
# --- MODIFIKASI sys.path END ---

import paho.mqtt.client as mqtt
import paho.mqtt.properties as mqtt_props
import time
import json
import random
import uuid
from dotenv import load_dotenv

from shared import mqtt_config

load_dotenv(dotenv_path=os.path.join(project_root_dir, '.env'))

MQTT_USERNAME = os.getenv("MQTT_USERNAME_SENSOR", mqtt_config.MQTT_USERNAME) # Membaca var spesifik sensor
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD_SENSOR", mqtt_config.MQTT_PASSWORD) # Membaca var spesifik sensor
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", mqtt_config.MQTT_BROKER_HOST)

SENSOR_ID = "suhu_ruang_server_01"
TOPIC_LWT_SENSOR_SPECIFIC = f"{mqtt_config.TOPIC_LWT_SENSOR_BASE}/{SENSOR_ID}/status"
TOPIC_SENSOR_SUHU_RESPONSE_SPECIFIC = f"{mqtt_config.TOPIC_SENSOR_SUHU_RESPONSE_BASE}/{SENSOR_ID}"

def get_rc_value(rc_param):
    """Helper untuk mendapatkan nilai integer dari reason_code."""
    if isinstance(rc_param, int):
        return rc_param
    elif hasattr(rc_param, 'value'): # Untuk objek ReasonCode
        return rc_param.value
    try:
        return int(rc_param) # Fallback
    except (ValueError, TypeError): # Tangani jika tidak bisa dikonversi
        return -1 # Indikasi error jika tidak bisa dikonversi

def on_connect(client, userdata, flags, reason_code, properties):
    rc_value = get_rc_value(reason_code)
    if rc_value == 0:
        print(f"Sensor ({client._client_id.decode()}): Terhubung AMAN ke Broker MQTT (v5/TLS)!")
        online_payload = {"status": "ONLINE", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        client.publish(TOPIC_LWT_SENSOR_SPECIFIC, json.dumps(online_payload), qos=1, retain=True)
        
        (result, mid) = client.subscribe(TOPIC_SENSOR_SUHU_RESPONSE_SPECIFIC, qos=mqtt_config.QOS_RESPONSE)
        if result != mqtt.MQTT_ERR_SUCCESS:
             print(f"Sensor: Gagal subscribe ke topik response, error: {mqtt.error_string(result)}")
    else:
        print(f"Sensor: Gagal terhubung, return code {rc_value} - {mqtt.error_string(rc_value)}")

def on_disconnect(client, userdata, flags_or_rc, reason_code=None, properties=None):
    rc_to_check = reason_code if reason_code is not None else flags_or_rc
    rc_value = get_rc_value(rc_to_check)
    
    if rc_value == 0:
        print(f"Sensor: Terputus secara normal dari broker.")
    else:
        print(f"Sensor: Terputus dari broker dengan kode {rc_value} - {mqtt.error_string(rc_value)}. LWT seharusnya terkirim jika pemutusan tidak normal.")

# PERBAIKAN SIGNATURE on_publish
def on_publish(client, userdata, mid, reason_code_obj=None, properties=None):
    # Untuk Paho MQTT v2 dengan CallbackAPIVersion.VERSION2, signature ini seharusnya dipanggil.
    # reason_code_obj bisa berupa objek ReasonCode atau None.
    # Kita bisa biarkan kosong jika log publish utama sudah cukup detail di tempat lain.
    # Contoh jika ingin menggunakan reason code:
    # if reason_code_obj is not None and hasattr(reason_code_obj, 'value'):
    #     rc_pub_value = get_rc_value(reason_code_obj)
    #     if rc_pub_value == 0: # Success untuk QoS 1 & 2 (PUBACK/PUBCOMP diterima)
    #         print(f"Sensor: Pesan dengan MID {mid} dikonfirmasi terpublikasi (RC: {rc_pub_value}).")
    #     elif rc_pub_value > 0: # Ada masalah
    #         print(f"Sensor: Pesan dengan MID {mid} GAGAL terpublikasi sepenuhnya (RC: {rc_pub_value} - {mqtt.error_string(rc_pub_value)}).")
    # else:
    #     # Untuk QoS 0 atau jika reason code tidak tersedia dari callback ini
    #     # print(f"Sensor: Pesan dengan MID {mid} telah dikirim (proses publish dimulai).")
    pass


def on_message(client, userdata, msg):
    print(f"Sensor: Menerima RESPONSE dari topik '{msg.topic}'")
    try:
        payload_data = json.loads(msg.payload.decode())
        print(f"Sensor: Response Payload: {json.dumps(payload_data, indent=2)}")
        correlation_id = None
        if msg.properties and hasattr(msg.properties, 'CorrelationData'):
            correlation_id = msg.properties.CorrelationData
            if isinstance(correlation_id, bytes):
                correlation_id = correlation_id.decode()
        if correlation_id:
            print(f"Sensor: Response terkait dengan Correlation ID: {correlation_id}")
    except Exception as e:
        print(f"Sensor: Error memproses response: {e}")

def connect_mqtt():
    client_id_prefix = f"sensor-simulator-{SENSOR_ID}"
    client_id = f"{client_id_prefix}-{random.randint(0, 1000)}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    else:
        print("Sensor: PERINGATAN - Username/Password MQTT tidak diset. Mencoba koneksi anonim.")

    ca_certs_path = os.path.join(project_root_dir, mqtt_config.MQTT_TLS_CA_CERTS)
    if not os.path.exists(ca_certs_path):
        print(f"ERROR KRITIS: File CA Certificate tidak ditemukan di {ca_certs_path}")
        return None
    try:
        client.tls_set(ca_certs=ca_certs_path,
                       certfile=None, keyfile=None,
                       cert_reqs=ssl.CERT_REQUIRED,
                       tls_version=ssl.PROTOCOL_TLS_CLIENT)
        print(f"TLS/SSL dikonfigurasi. Mencoba koneksi aman ke {MQTT_BROKER_HOST}:{mqtt_config.MQTT_BROKER_PORT}")
        print(f"Menggunakan CA cert dari: {ca_certs_path}")
    except Exception as e:
        print(f"Error saat konfigurasi TLS/SSL: {e}")
        return None

    lwt_payload = {"status": "OFFLINE_UNEXPECTED", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    lwt_properties = mqtt_props.Properties(mqtt_props.PacketTypes.WILLMESSAGE)
    lwt_properties.MessageExpiryInterval = mqtt_config.MESSAGE_EXPIRY_INTERVAL_SECONDS
    client.will_set(
        TOPIC_LWT_SENSOR_SPECIFIC, payload=json.dumps(lwt_payload),
        qos=mqtt_config.QOS_LWT, retain=True, properties=lwt_properties)

    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_HOST, mqtt_config.MQTT_BROKER_PORT, mqtt_config.MQTT_KEEPALIVE_INTERVAL)
    except ssl.SSLCertVerificationError as e: print(f"GAGAL KONEKSI TLS: SSLCertVerificationError - {e}"); return None
    except ConnectionRefusedError as e: print(f"GAGAL KONEKSI: ConnectionRefusedError - {e}"); return None
    except Exception as e: print(f"Gagal terhubung ke broker (TLS): {e}"); return None
    return client

def run_sensor():
    client = connect_mqtt()
    if not client: return
    client.loop_start()
    try:
        while True:
            suhu = round(random.uniform(20.0, 50.0), 2)
            level_darurat, pesan_tambahan, retain_message = "NORMAL", "Suhu dalam batas normal.", False
            if suhu > 40.0: level_darurat, pesan_tambahan, retain_message = "KRITIS", "PERHATIAN! Suhu ruang server melebihi batas aman!", True
            elif suhu > 35.0: level_darurat, pesan_tambahan = "PERINGATAN", "Suhu ruang server meningkat, mohon periksa."

            correlation_id = str(uuid.uuid4())
            payload = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sensor_id": SENSOR_ID,
                "type": "TEMPERATURE_ALERT_REQUEST", "value": suhu, "unit": "Celsius",
                "level": level_darurat, "message": pesan_tambahan, "correlation_id": correlation_id}
            
            publish_props = mqtt_props.Properties(mqtt_props.PacketTypes.PUBLISH)
            publish_props.MessageExpiryInterval = mqtt_config.MESSAGE_EXPIRY_INTERVAL_SECONDS
            publish_props.ResponseTopic = TOPIC_SENSOR_SUHU_RESPONSE_SPECIFIC
            publish_props.CorrelationData = correlation_id.encode()
            
            # Mengirim pesan
            msg_info = client.publish( # client.publish mengembalikan objek MqttMessageInfo
                mqtt_config.TOPIC_SENSOR_SUHU_REQUEST, json.dumps(payload),
                qos=mqtt_config.QOS_REQUEST, retain=retain_message, properties=publish_props)
            
            # Menunggu konfirmasi publish untuk QoS 1 dan 2 (opsional, tapi baik untuk debug)
            # if mqtt_config.QOS_REQUEST > 0:
            #     try:
            #         msg_info.wait_for_publish(timeout=5) # Tunggu hingga 5 detik
            #         if msg_info.is_published():
            #             # Kode reason dari PUBACK/PUBCOMP (jika ada dan didukung callback Paho)
            #             # biasanya akan ditangani di on_publish jika callbacknya menerima reason code.
            #             # Untuk sekarang, kita anggap panggilan publish() yang sukses sudah cukup indikasi.
            #             print(f"Sensor: REQUEST level '{level_darurat}' (ID: {correlation_id}, MID: {msg_info.mid}) dikirim dan dikonfirmasi (retain={retain_message}, expiry={mqtt_config.MESSAGE_EXPIRY_INTERVAL_SECONDS}s)")
            #         else:
            #             print(f"Sensor: REQUEST level '{level_darurat}' (ID: {correlation_id}, MID: {msg_info.mid}) Timeout menunggu konfirmasi publish.")
            #     except RuntimeError: # Terjadi jika loop tidak berjalan
            #         print(f"Sensor: REQUEST level '{level_darurat}' (ID: {correlation_id}, MID: {msg_info.mid}) Runtime error menunggu konfirmasi (loop tidak berjalan?).")
            #     except ValueError: # Terjadi jika MID tidak valid
            #         print(f"Sensor: REQUEST level '{level_darurat}' (ID: {correlation_id}, MID: {msg_info.mid}) Value error menunggu konfirmasi.")

            # Log sederhana setelah pemanggilan publish
            if msg_info.rc == mqtt.MQTT_ERR_SUCCESS:
                 print(f"Sensor: REQUEST level '{level_darurat}' (ID: {correlation_id}, MID: {msg_info.mid}) dikirim ke antrian (retain={retain_message}, expiry={mqtt_config.MESSAGE_EXPIRY_INTERVAL_SECONDS}s)")
            else:
                 print(f"Sensor: Gagal mengirim request ke antrian, error code: {msg_info.rc} - {mqtt.error_string(msg_info.rc)}")

            time.sleep(15)
    except KeyboardInterrupt:
        print("Sensor: Menghentikan sensor simulator...")
        offline_payload = {"status": "OFFLINE_GRACEFUL", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if client and client.is_connected():
            # Untuk pesan terakhir ini, kita tidak terlalu peduli konfirmasi detail, QoS 1 cukup
            client.publish(TOPIC_LWT_SENSOR_SPECIFIC, json.dumps(offline_payload), qos=1, retain=True)
    finally:
        if client and client.is_connected():
            client.loop_stop()
            # Sebelum disconnect, kita bisa tunggu sebentar untuk memastikan pesan terakhir (jika ada) terkirim
            # time.sleep(1) # Opsional
            client.disconnect()
        print("Sensor: Koneksi MQTT ditutup.")

if __name__ == '__main__':
    run_sensor()