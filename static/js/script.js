const map = L.map('map').setView([51.505, -0.09], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

let marker = null;
const bortleDescriptions = {
    1: "Excellent dark-sky site. The Milky Way is highly detailed.",
    2: "Typical truly dark site. The Milky Way appears complex.",
    3: "Rural sky. Some light pollution visible along horizons.",
    4: "Rural/suburban transition. Light pollution domes visible.",
    5: "Suburban sky. The Milky Way is very weak or invisible.",
    6: "Bright suburban sky. The Milky Way is barely visible.",
    7: "Suburban/urban transition. Entire sky is grayish.",
    8: "City sky. Sky is light gray or orange.",
    9: "Inner-city sky. Sky is brilliantly lit."
};

function updateCoordinates(lat, lng) {
    if (!marker) {
        marker = L.marker([lat, lng]).addTo(map)
            .bindPopup(`Selected location:<br>${lat.toFixed(4)}, ${lng.toFixed(4)}`)
            .openPopup();
    } else {
        marker.setLatLng([lat, lng])
            .setPopupContent(`Selected location:<br>${lat.toFixed(4)}, ${lng.toFixed(4)}`);
    }
    document.getElementById("latitude").value = lat.toFixed(6);
    document.getElementById("longitude").value = lng.toFixed(6);
}

async function getBortleLevel() {
    const lat = parseFloat(document.getElementById("latitude").value);
    const lon = parseFloat(document.getElementById("longitude").value);

    if (isNaN(lat) || isNaN(lon)) {
        showError("Please select a location on the map first");
        return;
    }

    try {
        showLoading();
        
        const response = await fetch(`/api/light-pollution?lat=${lat}&lon=${lon}`);
        
        if (!response.ok) {
            const err = await response.json().catch(() => null);
            throw new Error(err?.error || `Server error: ${response.status}`);
        }
        
        const data = await response.json();
        showResults(data);
        
    } catch (error) {
        console.error("API Error:", error);
        showError(error.message);
        showFallbackEstimation(lat, lon);
    }
}

function showLoading() {
    document.getElementById("result").innerHTML = `
        <div class="loading-spinner"></div>
        <span>Analyzing light pollution...</span>
    `;
    document.getElementById("description").textContent = "";
    document.getElementById("source").textContent = "";
    document.getElementById("check-btn").disabled = true;
}

function showResults(data) {
    document.getElementById("result").innerHTML = `
        <span class="bortle-level">Bortle Scale: ${data.bortle_level}</span>
    `;
    document.getElementById("description").textContent = 
        bortleDescriptions[data.bortle_level] || "No description available";
    document.getElementById("source").textContent = `Data source: ${data.source}`;
    document.getElementById("check-btn").disabled = false;
    
    if (marker) {
        marker.setPopupContent(`
            Location: ${data.location}<br>
            Bortle Scale: ${data.bortle_level}<br>
            ${bortleDescriptions[data.bortle_level]}
        `);
    }
}

function showError(message) {
    document.getElementById("result").innerHTML = `
        <span class="error-icon">⚠️</span>
        <span class="error-message">${message}</span>
    `;
    document.getElementById("description").textContent = "Trying alternative methods...";
    document.getElementById("check-btn").disabled = false;
}

function showFallbackEstimation(lat, lon) {
    const estimated = Math.min(9, Math.max(1, 
        Math.floor((Math.abs(lat) / 10) + (Math.abs(lon) / 180 * 3))
    ));
    
    document.getElementById("result").innerHTML = `
        <span class="estimated">Estimated Bortle: ${estimated}</span>
    `;
    document.getElementById("description").textContent = 
        bortleDescriptions[estimated] || "Approximate estimation";
    document.getElementById("source").textContent = "Source: Fallback algorithm";
}

document.addEventListener('DOMContentLoaded', () => {
    map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        updateCoordinates(lat, lng);
    });

    document.getElementById('check-btn').addEventListener('click', getBortleLevel);
});

