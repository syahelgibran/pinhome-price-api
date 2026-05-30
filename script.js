// Global Constants for endpoints
const ENDPOINTS = {
    production: "home-price-prediction.up.railway.app",
    local: "http://localhost:5000"
};

// Fallback arrays if API is offline on startup
const FALLBACK_LOCATIONS = [
    "Kab. Bandung", "Kab. Bekasi", "Kab. Bogor", "Kab. Tangerang",
    "Kota Bandung", "Kota Bekasi", "Kota Bogor", "Kota Depok",
    "Kota Jakarta Barat", "Kota Jakarta Pusat", "Kota Jakarta Selatan",
    "Kota Jakarta Timur", "Kota Jakarta Utara", "Kota Surabaya", "Kota Tangerang", "Kota Tangerang Selatan"
];
const FALLBACK_CONDITIONS = ["Baru", "Second", "Tidak diketahui"];

let ACTIVE_URL = ENDPOINTS.production;
let logsInterval = null;

// Helper to format currency
function formatRupiah(amount) {
    return "Rp " + new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(amount);
}

// 1. Initial Load & Setup
document.addEventListener("DOMContentLoaded", () => {
    setupEndpoints();
    initializeData();
});

// Setup radio toggles for API mode
function setupEndpoints() {
    const radios = document.querySelectorAll('input[name="api-mode"]');
    const endpointInput = document.getElementById("custom-endpoint");

    radios.forEach(radio => {
        radio.addEventListener("change", (e) => {
            const mode = e.target.value;
            ACTIVE_URL = ENDPOINTS[mode];
            endpointInput.value = ACTIVE_URL;
            
            // Re-initialize with new endpoint URL
            initializeData();
        });
    });

    // Handle manual text changes in endpoint URL input
    endpointInput.addEventListener("change", (e) => {
        ACTIVE_URL = e.target.value.trim();
        initializeData();
    });
}

// Initialize categories and telemetry
async function initializeData() {
    updateApiBadge("testing", "Testing connection...");
    
    // Load metadata dropdown options
    const success = await fetchMetadata();
    
    if (success) {
        updateApiBadge("online", "Connected");
    } else {
        updateApiBadge("offline", "Using Fallback");
    }

    // Load database logs initially
    fetchTelemetryLogs();
    
    // Set up real-time background polling every 5 seconds
    if (logsInterval) clearInterval(logsInterval);
    logsInterval = setInterval(fetchTelemetryLogs, 5000);
}

// Fetch categories from /metadata
async function fetchMetadata() {
    const lokasiSelect = document.getElementById("lokasi");
    const kondisiSelect = document.getElementById("kondisi");
    const lokasiSpinner = document.getElementById("lokasi-spinner");
    const kondisiSpinner = document.getElementById("kondisi-spinner");

    // Display spinners during loading
    lokasiSpinner.style.display = "block";
    kondisiSpinner.style.display = "block";
    lokasiSelect.disabled = true;
    kondisiSelect.disabled = true;

    try {
        const response = await fetch(`${ACTIVE_URL}/metadata`, { method: "GET" });
        if (!response.ok) throw new Error("Metadata API offline");
        const data = await response.json();

        if (data.status === "success" && data.locations && data.conditions) {
            populateDropdown(lokasiSelect, data.locations, "Select Location...");
            populateDropdown(kondisiSelect, data.conditions, "Select Condition...");
            return true;
        }
    } catch (error) {
        console.warn("Failed fetching from /metadata endpoint, loading static fallbacks:", error);
        populateDropdown(lokasiSelect, FALLBACK_LOCATIONS, "Select Location (Fallback)...");
        populateDropdown(kondisiSelect, FALLBACK_CONDITIONS, "Select Condition (Fallback)...");
        return false;
    } finally {
        // Stop spinners
        lokasiSpinner.style.display = "none";
        kondisiSpinner.style.display = "none";
        lokasiSelect.disabled = false;
        kondisiSelect.disabled = false;
    }
}

// Populate select elements
function populateDropdown(selectElement, items, placeholder) {
    selectElement.innerHTML = `<option value="" disabled selected>${placeholder}</option>`;
    items.forEach(item => {
        const opt = document.createElement("option");
        opt.value = item;
        opt.textContent = item;
        selectElement.appendChild(opt);
    });
}

// Fetch SQLite Logs from /logs
async function fetchTelemetryLogs() {
    try {
        const response = await fetch(`${ACTIVE_URL}/logs`, { method: "GET" });
        if (!response.ok) throw new Error("Telemetry offline");
        const data = await response.json();

        if (data.status === "success" && data.logs) {
            updateTelemetryTable(data.logs);
        }
    } catch (error) {
        // Fail silently to prevent console spamming
    }
}

// Update the DOM telemetry table
function updateTelemetryTable(logs) {
    const tbody = document.getElementById("telemetry-tbody");
    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-secondary);">No logs found in DB. Run predictions to see live logs!</td></tr>`;
        return;
    }

    tbody.innerHTML = logs.map(log => {
        const formattedPrice = formatRupiah(log.predicted_price);
        
        // Parse UTC timestamp to local locale
        const date = new Date(log.timestamp + "Z").toLocaleString('id-ID', {
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            day: 'numeric', month: 'short'
        });

        return `
            <tr>
                <td>${date}</td>
                <td>${log.kamar_tidur}</td>
                <td>${log.kamar_mandi}</td>
                <td>${log.luas_tanah} / ${log.luas_bangunan} m²</td>
                <td>${log.lokasi}</td>
                <td>${log.kondisi}</td>
                <td style="color: var(--emerald-green); font-weight: 600; text-shadow: 0 0 6px rgba(16,185,129,0.1);">${formattedPrice}</td>
                <td><code>${log.latency_ms.toFixed(1)} ms</code></td>
            </tr>
        `;
    }).join("");
}

// Update active API connection status badge
function updateApiBadge(status, text) {
    const badge = document.getElementById("api-status-badge");
    badge.className = `status-badge ${status}`;
    badge.textContent = text;
}

// 2. Form Submission Handling
const form = document.getElementById("valuation-form");
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const btn = document.getElementById("btn-submit");
    const btnSpinner = document.getElementById("btn-spinner");
    const placeholder = document.getElementById("result-placeholder");
    const display = document.getElementById("result-display");

    // Start UI processing states
    btn.disabled = true;
    btnSpinner.style.display = "block";
    btn.querySelector("span").style.opacity = "0.5";

    // Grab input values
    const payload = {
        kamar_tidur: parseInt(document.getElementById("kamar_tidur").value),
        kamar_mandi: parseInt(document.getElementById("kamar_mandi").value),
        luas_tanah: parseFloat(document.getElementById("luas_tanah").value),
        luas_bangunan: parseFloat(document.getElementById("luas_bangunan").value),
        lokasi: document.getElementById("lokasi").value,
        kondisi: document.getElementById("kondisi").value
    };

    try {
        const response = await fetch(`${ACTIVE_URL}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        
        if (response.ok && result.status === "success") {
            // Unhide display, hide placeholder
            placeholder.classList.add("hidden");
            display.classList.remove("hidden");

            // Animate price output
            animatePrice(result.estimasi_harga);
            document.getElementById("latency-val").textContent = `${result.latency_ms.toFixed(1)} ms`;

            // Refresh table logs immediately
            fetchTelemetryLogs();
        } else {
            alert(`API Error: ${result.message || "Gagal memproses prediksi"}`);
        }
    } catch (error) {
        console.error("Prediction API Request Failed:", error);
        alert("Failed to connect to the prediction server. Please verify the API endpoint is active.");
    } finally {
        // Reset button states
        btn.disabled = false;
        btnSpinner.style.display = "none";
        btn.querySelector("span").style.opacity = "1";
    }
});

// Count up price output animation
function animatePrice(targetValue) {
    const output = document.getElementById("price-output");
    const duration = 1000; // Time in ms
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function: outQuad
        const ease = progress * (2 - progress);
        
        const currentValue = Math.floor(ease * targetValue);
        output.textContent = formatRupiah(currentValue);

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            output.textContent = formatRupiah(targetValue);
        }
    }

    requestAnimationFrame(update);
}
