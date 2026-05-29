import streamlit as st
import requests
import json

# Format currency helper
def format_rupiah(amount):
    return f"Rp {amount:,.0f}".replace(',', '.')

# Page settings
st.set_page_config(page_title="Estimasi Harga Rumah Pinhome", layout="centered", page_icon="🏠")

# Sidebar Configuration for local vs cloud endpoint
st.sidebar.header("⚙️ Konfigurasi API")
api_mode = st.sidebar.radio(
    "Pilih Endpoint API:",
    ["Production (Railway)", "Lokal (Development)"]
)

if api_mode == "Production (Railway)":
    base_url = "https://web-production-605e4.up.railway.app"
else:
    base_url = "http://localhost:5000"

# Fetch fallback data
try:
    from preprocessor import LOCATIONS as FALLBACK_LOCATIONS, CONDITIONS as FALLBACK_CONDITIONS
except ImportError:
    FALLBACK_LOCATIONS = ["Kota Depok", "Kota Jakarta Selatan", "Kota Bandung", "Kota Surabaya", "Kota Tangerang"]
    FALLBACK_CONDITIONS = ["Baru", "Second", "Tidak diketahui"]

# Cache metadata to prevent reloading on every user input change
@st.cache_data(ttl=600)
def fetch_metadata(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

# Load metadata dynamically
metadata_url = f"{base_url}/metadata"
metadata = fetch_metadata(metadata_url)

if metadata and metadata.get('status') == 'success':
    locations = metadata['locations']
    conditions = metadata['conditions']
    st.sidebar.success("🟢 Terhubung ke API (Metadata Aktif)")
else:
    locations = FALLBACK_LOCATIONS
    conditions = FALLBACK_CONDITIONS
    st.sidebar.warning("⚠️ API Offline (Menggunakan Fallback Lokal)")

# Main Title & Subtitle
st.title("🏠 Estimasi Harga Rumah Pinhome")
st.markdown("""
Aplikasi ini memprediksi harga pasar properti real estate di Indonesia menggunakan model **XGBoost Regressor** 
yang telah dioptimalkan dengan **Bayesian Optimization** pada data penjualan Pinhome.
""")
st.markdown("---")

st.subheader("Input Spesifikasi Rumah")

# Input Form
with st.form("prediction_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        kamar_tidur = st.number_input("Jumlah Kamar Tidur", min_value=0, max_value=20, value=3, step=1)
        kamar_mandi = st.number_input("Jumlah Kamar Mandi", min_value=0, max_value=20, value=2, step=1)
        lokasi = st.selectbox("Pilih Lokasi (Kota/Kabupaten)", options=locations)
        
    with col2:
        luas_tanah = st.number_input("Luas Tanah (m²)", min_value=1, max_value=10000, value=120, step=10)
        luas_bangunan = st.number_input("Luas Bangunan (m²)", min_value=1, max_value=10000, value=100, step=10)
        kondisi = st.selectbox("Kondisi Rumah", options=conditions)
        
    submit = st.form_submit_button("Hitung Estimasi Harga")

    if submit:
        # Build raw JSON payload
        data_payload = {
            "kamar_tidur": int(kamar_tidur),
            "kamar_mandi": int(kamar_mandi),
            "luas_tanah": float(luas_tanah),
            "luas_bangunan": float(luas_bangunan),
            "lokasi": lokasi,
            "kondisi": kondisi
        }
        
        predict_url = f"{base_url}/predict"
        
        try:
            with st.spinner("Menghubungi Server AI XGBoost..."):
                response = requests.post(predict_url, json=data_payload, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                if 'estimasi_harga' in result:
                    harga = result['estimasi_harga']
                    latency = result.get('latency_ms', 0)
                    
                    st.balloons()
                    st.success("Estimasi Harga Berhasil Dihitung!")
                    st.subheader("Hasil Estimasi:")
                    st.header(format_rupiah(harga))
                    st.caption(f"Latensi Server: {latency:.2f} ms | Endpoint: `{predict_url}`")
                else:
                    st.error("Format respons API tidak valid.")
                    st.json(result)
        except Exception as e:
            st.error(f"Gagal melakukan estimasi. Error: {str(e)}")
            st.info("Pastikan server API Flask Anda sedang berjalan jika memilih mode Lokal (Development).")