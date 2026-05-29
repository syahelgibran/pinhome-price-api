import numpy as np
import pandas as pd
import joblib
from flask import Flask, request, jsonify

# 1. Inisialisasi Aplikasi Flask
app = Flask(__name__)

# 2. Memuat Model AI (Pastikan nama file sesuai)
print("⏳ Memuat model XGBoost...")
model = joblib.load('xgb_model.joblib')
print("✅ Model berhasil dimuat!")

# 3. Membuat Endpoint Prediksi (Menerima metode POST)
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Mengambil data JSON dari user
        json_data = request.get_json()
        
        # Ekstrak data fitur (misalnya user mengirim list data)
        # Bentuk JSON: {"data": [[Kamar, Luas, ... 118 fitur ...]]}
        input_features = json_data['data']
        
        # Prediksi menggunakan model (Hasilnya masih Logaritma!)
        log_prediction = model.predict(input_features)
        
        # INVERSE LOG-TRANSFORM: Mengembalikan angka logaritma menjadi Rupiah asli
        real_price = np.expm1(log_prediction)
        
        # MENGAMBIL ANGKA TUNGGAL DARI DALAM ARRAY MENGGUNAKAN INDEKS NOL
        harga_final = real_price[0]
        
        # Format hasil balasan (Response)
        response = {
            'status': 'success',
            'estimasi_harga': float(harga_final)
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

# Pengaman untuk testing lokal (Jangan jalankan app.run di production)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)