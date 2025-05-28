# Proyek Aplikasi Notifikasi Darurat Berbasis MQTT

## Deskripsi Proyek  
Proyek ini adalah implementasi sistem notifikasi darurat sederhana yang menggunakan protokol MQTT (Message Queuing Telemetry Transport) untuk komunikasi antara sensor simulator dan aplikasi notifier client. Aplikasi ini dirancang untuk menunjukkan berbagai fitur inti dan lanjutan dari MQTT, termasuk keamanan, keandalan pengiriman pesan, dan pola komunikasi modern.  
Sensor simulator secara periodik mengirimkan data suhu, dan jika suhu melebihi ambang batas tertentu, ia akan mengirimkan notifikasi darurat (KRITIS atau PERINGATAN). Notifier client akan menerima notifikasi ini dan juga status operasional sensor.

## Fitur Utama yang Diimplementasikan  
Proyek ini mengimplementasikan fitur-fitur MQTT berikut:

1. **MQTT & MQTTSecure (TLS/SSL):**  
   - Komunikasi antara client dan broker dienkripsi menggunakan TLS/SSL (MQTTS) untuk memastikan kerahasiaan data.  
   - Menggunakan self-signed certificates untuk CA dan server broker.

2. **Authentication (Username/Password):**  
   - Broker Mosquitto dikonfigurasi untuk memerlukan autentikasi username dan password dari setiap client yang ingin terhubung, mencegah akses tidak sah.

3. **Quality of Service (QoS) Level 2:**  
   - Pesan notifikasi suhu (request) dikirim dengan QoS 2 untuk memastikan pengiriman "exactly once delivery".  
   - Notifier client juga subscribe dengan QoS 2.

4. **Retained Message:**  
   - Pesan status terakhir sensor dipublish dengan flag `retain=True`.  
   - Notifikasi suhu dengan level "KRITIS" juga di-retain.

5. **Last Will and Testament (LWT):**  
   - Sensor simulator mendaftarkan pesan LWT saat terhubung ke broker.  
   - Jika sensor terputus secara tidak normal, broker akan mempublish pesan LWT ke topik status sensor.

6. **Message Expiry (MQTTv5):**  
   - Pesan notifikasi suhu memiliki interval kadaluarsa.  
   - Pesan LWT juga memiliki interval kadaluarsa.

7. **Request-Response Pattern (MQTTv5):**  
   - Sensor simulator mengirim notifikasi suhu sebagai "request" dan menyertakan properti `ResponseTopic` dan `CorrelationData`.  
   - Notifier client mengirimkan "response" ke `ResponseTopic` dengan `CorrelationData`.

8. **Flow Control (MQTTv5):**  
   - Flow control dinegosiasikan otomatis antara client dan broker.

9. **Ping Pong (Keep Alive):**  
   - Dikelola otomatis oleh library Paho MQTT untuk menjaga koneksi tetap aktif.

## Struktur Direktori Proyek

```
mqtt-project/
├── .vscode/                 # Konfigurasi VS Code (opsional)
├── notifier_client/
│   └── main.py              # Kode Notifier Client (Subscriber)
├── sensor_simulator/
│   └── main.py              # Kode Sensor Simulator (Publisher)
├── shared/
│   ├── __init__.py
│   ├── ca.crt               # Sertifikat CA untuk TLS
│   └── mqtt_config.py       # Konfigurasi MQTT bersama
├── venv/                    # Virtual environment Python
├── .env                     # Kredensial MQTT (JANGAN DI-COMMIT)
├── .gitignore               # Mengecualikan file dari Git
├── mosquitto.conf           # Konfigurasi Mosquitto
├── passwdfile               # File password Mosquitto
├── requirements.txt         # Dependensi Python
└── README.md                # Dokumentasi proyek
```

## Setup dan Instalasi

### Prasyarat  
- Python 3.7+  
- Mosquitto MQTT Broker (versi 2.0+)  
- OpenSSL

### Langkah Setup

1. **Clone Repository:**

   ```bash
   git clone [URL_REPO_ANDA]
   cd mqtt-project

## Cara Menjalankan Proyek

### 1. Buat Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

### 2. Install Dependensi

```bash
pip install -r requirements.txt
```

### 3. Generate Sertifikat TLS (Jika Belum Ada)

```bash
# Membuat self-signed certificate dan key
openssl req -new -x509 -days 365 -nodes -out ca.crt -keyout ca.key
```

### 4. Jalankan Mosquitto Broker

```bash
mosquitto -c mosquitto.conf
```

### 5. Jalankan Sensor Simulator & Notifier Client di Terminal Berbeda

```bash
# Terminal 1
python sensor_simulator/main.py

# Terminal 2
python notifier_client/main.py
```

### SCREENSHOOT

![image](https://github.com/user-attachments/assets/8a05e969-6c54-43c1-be63-f1dcc6a8d474)
![image](https://github.com/user-attachments/assets/a15d6764-5753-4b9b-a06e-eded9d1dfc3a)

