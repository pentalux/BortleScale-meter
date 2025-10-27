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
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        const response = await fetch(`/api/light-pollution?lat=${lat}&lon=${lon}`, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const err = await response.json().catch(() => null);
            throw new Error(err?.error || `Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Логируем в консоль информацию о запросе
        console.log(`Light pollution data for ${data.location}:`);
        console.log(`- Bortle Level: ${data.bortle_level}/9`);
        console.log(`- Description: ${bortleDescriptions[data.bortle_level]}`);
        console.log(`- Coordinates: ${data.location}`);
        
        showResults(data);
        
    } catch (error) {
        console.error("API Error:", error);
        if (error.name === 'AbortError') {
            showError("Request timeout - service is taking too long to respond");
        } else {
            showError(error.message);
        }
    }
}

function showLoading() {
    document.getElementById("result").innerHTML = `
        <div class="loading-container">
            <div class="loading-spinner-large"></div>
            <div class="loading-text">Analyzing light pollution data...</div>
            <div class="loading-subtext">Querying scientific databases</div>
        </div>
    `;
    document.getElementById("description").textContent = "";
    
    const btn = document.getElementById("check-btn");
    btn.innerHTML = '<div class="button-loading-spinner"></div> Processing...';
    btn.disabled = true;
}

function showResults(data) {
    const btn = document.getElementById("check-btn");
    btn.innerHTML = 'Check Light Pollution';
    btn.disabled = false;
    
    // Создаем HTML с общей шкалой
    document.getElementById("result").innerHTML = `
        <div class="result-animation">
            <span class="bortle-level">Bortle Scale: ${data.bortle_level}/9</span>
            <div class="bortle-meter">
                <div class="level" style="width: ${(data.bortle_level / 9) * 100}%"></div>
                <div class="current-level" style="left: ${(data.bortle_level / 9) * 100}%"></div>
            </div>
        </div>
    `;
    
    document.getElementById("description").textContent = 
        bortleDescriptions[data.bortle_level] || "No description available";
    
    // Запускаем анимацию шкалы после небольшой задержки
    setTimeout(() => {
        const meter = document.querySelector('.bortle-meter');
        if (meter) {
            meter.classList.add('animate');
        }
    }, 100);
    
    if (marker) {
        marker.setPopupContent(`
            <strong>Location:</strong> ${data.location}<br>
            <strong>Bortle Scale:</strong> ${data.bortle_level}/9<br>
            <strong>Description:</strong> ${bortleDescriptions[data.bortle_level]}
        `);
    }
}

function showError(message) {
    const btn = document.getElementById("check-btn");
    btn.innerHTML = 'Check Light Pollution';
    btn.disabled = false;
    
    document.getElementById("result").innerHTML = `
        <div class="error-container result-animation">
            <span class="error-icon">⚠️</span>
            <span class="error-message">${message}</span>
        </div>
    `;
    document.getElementById("description").textContent = "Please try again or select a different location.";
}

document.addEventListener('DOMContentLoaded', () => {
    map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        updateCoordinates(lat, lng);
    });

    document.getElementById('check-btn').addEventListener('click', getBortleLevel);
});