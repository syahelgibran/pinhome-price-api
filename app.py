import time
import sqlite3
import numpy as np
import joblib
from flask import Flask, request, jsonify
from preprocessor import preprocess_input, LOCATIONS, CONDITIONS

# 1. Inisialisasi Aplikasi Flask
app = Flask(__name__)

# 2. Inisialisasi Database Telemetri (SQLite)
DB_PATH = 'predictions.db'

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                kamar_tidur INTEGER,
                kamar_mandi INTEGER,
                luas_tanah REAL,
                luas_bangunan REAL,
                lokasi TEXT,
                kondisi TEXT,
                predicted_price REAL,
                latency_ms REAL
            )
        ''')
        conn.commit()
        conn.close()
        print("[SUCCESS] Database telemetri berhasil diinisialisasi!")
    except Exception as e:
        print(f"[ERROR] Gagal menginisialisasi database: {e}")

init_db()

# 3. CORS Headers Hook (Tanpa library tambahan)
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 4. Memuat Model XGBoost
print("[INFO] Memuat model XGBoost...")
model = joblib.load('xgb_model.joblib')
print("[SUCCESS] Model berhasil dimuat!")

def validate_payload(data):
    """
    Validasi data input API.
    """
    if not data:
        return "Payload JSON tidak boleh kosong."
        
    required_fields = ['kamar_tidur', 'kamar_mandi', 'luas_tanah', 'luas_bangunan', 'lokasi', 'kondisi']
    for field in required_fields:
        if field not in data:
            return f"Field wajib '{field}' tidak ditemukan."
            
    # Validasi tipe data dan batasan nilai numerik
    try:
        if int(data['kamar_tidur']) < 0:
            return "kamar_tidur harus berupa bilangan bulat non-negatif."
        if int(data['kamar_mandi']) < 0:
            return "kamar_mandi harus berupa bilangan bulat non-negatif."
        if float(data['luas_tanah']) <= 0:
            return "luas_tanah harus lebih besar dari 0."
        if float(data['luas_bangunan']) <= 0:
            return "luas_bangunan harus lebih besar dari 0."
    except (ValueError, TypeError):
        return "kamar_tidur dan kamar_mandi harus numerik bulat; luas_tanah dan luas_bangunan harus desimal/angka."
        
    return None

def log_prediction_to_db(data, predicted_price, latency_ms):
    """
    Menyimpan log prediksi ke database SQLite untuk monitoring (telemetri).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO prediction_logs 
            (kamar_tidur, kamar_mandi, luas_tanah, luas_bangunan, lokasi, kondisi, predicted_price, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(data['kamar_tidur']),
            int(data['kamar_mandi']),
            float(data['luas_tanah']),
            float(data['luas_bangunan']),
            str(data['lokasi']),
            str(data['kondisi']),
            float(predicted_price),
            float(latency_ms)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Gagal menyimpan log prediksi ke DB: {e}")


# 5. Endpoint Metadata untuk Frontend
@app.route('/metadata', methods=['GET'])
def get_metadata():
    """
    Mengembalikan daftar lokasi dan kondisi valid yang dikenali oleh model.
    Dapat digunakan oleh frontend untuk membangun dropdown secara dinamis.
    """
    return jsonify({
        'status': 'success',
        'locations': LOCATIONS,
        'conditions': CONDITIONS
    }), 200


# 6. Endpoint Logs untuk Telemetri Real-time
@app.route('/logs', methods=['GET'])
def get_logs():
    """
    Mengembalikan 5 data log prediksi terakhir untuk visualisasi telemetri di frontend.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, kamar_tidur, kamar_mandi, luas_tanah, luas_bangunan, lokasi, kondisi, predicted_price, latency_ms 
            FROM prediction_logs 
            ORDER BY id DESC 
            LIMIT 5
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for r in rows:
            logs.append({
                'timestamp': r[0],
                'kamar_tidur': r[1],
                'kamar_mandi': r[2],
                'luas_tanah': r[3],
                'luas_bangunan': r[4],
                'lokasi': r[5],
                'kondisi': r[6],
                'predicted_price': r[7],
                'latency_ms': r[8]
            })
            
        return jsonify({
            'status': 'success',
            'logs': logs
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


# 7. Endpoint Prediksi
@app.route('/predict', methods=['POST'])
def predict():
    start_time = time.time()
    try:
        # Ambil data JSON
        json_data = request.get_json()
        
        # Validasi payload
        error_msg = validate_payload(json_data)
        if error_msg:
            return jsonify({'status': 'validation_error', 'message': error_msg}), 400
            
        # Preprocessing input menggunakan mapper dinamis ke 118 fitur
        input_vector = preprocess_input(json_data)
        
        # Prediksi (dalam skala log)
        log_prediction = model.predict(input_vector)
        
        # Inverse log-transform ke Rupiah asli (np.expm1)
        real_price = np.expm1(log_prediction)
        harga_final = float(real_price[0])
        
        # Hitung durasi/latency dalam milidetik
        latency_ms = (time.time() - start_time) * 1000
        
        # Simpan ke log database
        log_prediction_to_db(json_data, harga_final, latency_ms)
        
        # Format response
        response = {
            'status': 'success',
            'estimasi_harga': harga_final,
            'latency_ms': latency_ms
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

# Pengaman untuk testing lokal
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)