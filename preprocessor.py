import os
import numpy as np

# Resolve directory of this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_PATH = os.path.join(BASE_DIR, 'model_features.txt')

# Load feature names expected by the model
if not os.path.exists(FEATURES_PATH):
    raise FileNotFoundError(f"Feature names file not found at: {FEATURES_PATH}")

with open(FEATURES_PATH, 'r', encoding='utf-8') as f:
    FEATURE_NAMES = [line.strip() for line in f if line.strip()]

# Dynamically extract locations and conditions from the features list
LOCATIONS = sorted([feat.replace("Lokasi_Clean_", "") for feat in FEATURE_NAMES if feat.startswith("Lokasi_Clean_")])
CONDITIONS = sorted([feat.replace("Kondisi_", "") for feat in FEATURE_NAMES if feat.startswith("Kondisi_")])

def preprocess_input(data):
    """
    Converts a single raw property dictionary into the 118-dimension vector
    required by the XGBoost model.
    
    Expected format:
    {
        "kamar_tidur": float/int,
        "kamar_mandi": float/int,
        "luas_tanah": float/int,
        "luas_bangunan": float/int,
        "lokasi": str,
        "kondisi": str
    }
    """
    # Create zero vector of length 118
    vector = np.zeros(len(FEATURE_NAMES))
    
    # Map continuous features (first 4 elements in the list)
    vector[0] = float(data.get('kamar_tidur', 0))
    vector[1] = float(data.get('kamar_mandi', 0))
    vector[2] = float(data.get('luas_tanah', 0))
    vector[3] = float(data.get('luas_bangunan', 0))
    
    # Map categorical Location
    lokasi = data.get('lokasi')
    if lokasi:
        lokasi_col = f"Lokasi_Clean_{lokasi}"
        if lokasi_col in FEATURE_NAMES:
            idx = FEATURE_NAMES.index(lokasi_col)
            vector[idx] = 1.0
            
    # Map categorical Condition
    kondisi = data.get('kondisi')
    if kondisi:
        kondisi_col = f"Kondisi_{kondisi}"
        if kondisi_col in FEATURE_NAMES:
            idx = FEATURE_NAMES.index(kondisi_col)
            vector[idx] = 1.0
            
    return vector.reshape(1, -1)
