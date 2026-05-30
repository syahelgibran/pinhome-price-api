import os
import sqlite3
import unittest
from app import app, DB_PATH
from preprocessor import preprocess_input, FEATURE_NAMES

class PropertyValuationApiTests(unittest.TestCase):
    
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        
    def test_preprocess_input(self):
        # Test valid input mapping
        data = {
            "kamar_tidur": 3,
            "kamar_mandi": 2,
            "luas_tanah": 120,
            "luas_bangunan": 100,
            "lokasi": "Kota Depok",
            "kondisi": "Second"
        }
        vector = preprocess_input(data)
        self.assertEqual(vector.shape, (1, 118))
        
        # Check numerical mapping
        self.assertEqual(vector[0, 0], 3.0)
        self.assertEqual(vector[0, 1], 2.0)
        self.assertEqual(vector[0, 2], 120.0)
        self.assertEqual(vector[0, 3], 100.0)
        
        # Check Lokasi_Clean_Kota Depok is hot (1.0)
        depok_idx = FEATURE_NAMES.index("Lokasi_Clean_Kota Depok")
        self.assertEqual(vector[0, depok_idx], 1.0)
        
        # Check Kondisi_Second is hot (1.0)
        second_idx = FEATURE_NAMES.index("Kondisi_Second")
        self.assertEqual(vector[0, second_idx], 1.0)

    def test_metadata_endpoint(self):
        response = self.client.get('/metadata')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('locations', data)
        self.assertIn('conditions', data)
        self.assertIn("Kota Depok", data['locations'])
        self.assertIn("Second", data['conditions'])

    def test_predict_endpoint_valid(self):
        payload = {
            "kamar_tidur": 3,
            "kamar_mandi": 2,
            "luas_tanah": 120,
            "luas_bangunan": 100,
            "lokasi": "Kota Depok",
            "kondisi": "Second"
        }
        response = self.client.post('/predict', json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('estimasi_harga', data)
        self.assertIsInstance(data['estimasi_harga'], float)
        self.assertTrue(data['estimasi_harga'] > 0)
        self.assertIn('latency_ms', data)

    def test_predict_endpoint_invalid(self):
        # 1. Missing field (kondisi)
        payload = {
            "kamar_tidur": 3,
            "kamar_mandi": 2,
            "luas_tanah": 120,
            "luas_bangunan": 100,
            "lokasi": "Kota Depok"
        }
        response = self.client.post('/predict', json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['status'], 'validation_error')
        self.assertIn("kondisi", data['message'])

        # 2. Invalid negative values
        payload = {
            "kamar_tidur": -1,
            "kamar_mandi": 2,
            "luas_tanah": 120,
            "luas_bangunan": 100,
            "lokasi": "Kota Depok",
            "kondisi": "Second"
        }
        response = self.client.post('/predict', json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertEqual(data['status'], 'validation_error')
        self.assertIn("kamar_tidur", data['message'])

    def test_database_logging(self):
        # Count logs before request
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prediction_logs")
        count_before = cursor.fetchone()[0]
        conn.close()
        
        # Fire prediction request
        payload = {
            "kamar_tidur": 4,
            "kamar_mandi": 3,
            "luas_tanah": 200,
            "luas_bangunan": 180,
            "lokasi": "Kota Bandung",
            "kondisi": "Baru"
        }
        response = self.client.post('/predict', json=payload)
        self.assertEqual(response.status_code, 200)
        
        # Count logs after request
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prediction_logs")
        count_after = cursor.fetchone()[0]
        self.assertEqual(count_after, count_before + 1)
        
        # Verify logged values inside sqlite
        cursor.execute("SELECT kamar_tidur, kamar_mandi, luas_tanah, luas_bangunan, lokasi, kondisi FROM prediction_logs ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        self.assertEqual(row, (4, 3, 200.0, 180.0, "Kota Bandung", "Baru"))
        conn.close()

    def test_logs_endpoint(self):
        # Retrieve logs via GET
        response = self.client.get('/logs')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('logs', data)
        self.assertIsInstance(data['logs'], list)

    def test_cors_headers(self):
        # Ensure CORS headers are injected on metadata endpoint
        res_meta = self.client.get('/metadata')
        self.assertEqual(res_meta.headers.get('Access-Control-Allow-Origin'), '*')
        
        # Ensure CORS headers are injected on prediction endpoint
        res_pred = self.client.post('/predict', json={})
        self.assertEqual(res_pred.headers.get('Access-Control-Allow-Origin'), '*')
        
        # Ensure CORS headers are injected on logs endpoint
        res_logs = self.client.get('/logs')
        self.assertEqual(res_logs.headers.get('Access-Control-Allow-Origin'), '*')

if __name__ == "__main__":
    unittest.main()
