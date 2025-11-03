// Инициализация карты с ограничениями
const map = L.map('map', {
    center: [30, 0],
    zoom: 2,
    zoomControl: false,
    fadeAnimation: true,
    zoomAnimation: true,
    // ОГРАНИЧЕНИЯ ПЕРЕМЕЩЕНИЯ КАРТЫ
    minZoom: 2,
    maxZoom: 18,
    maxBounds: [
        [-90, -180], // Юго-западный угол
        [90, 180]    // Северо-восточный угол
    ],
    maxBoundsViscosity: 1.0 // Жесткие границы
});

// Темные тайлы как было раньше
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '©OpenStreetMap, ©CartoDB',
    maxZoom: 20
}).addTo(map);

// ДОБАВЛЯЕМ ОГРАНИЧЕНИЯ НА ПАННИНГ (ПЕРЕМЕЩЕНИЕ)
map.setMaxBounds([
    [-85, -175], // Небольшой отступ от краев
    [85, 175]
]);

// Ограничиваем zoom для точности
map.options.minZoom = 2;
map.options.maxZoom = 15;

// Темные тайлы как было раньше
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '©OpenStreetMap, ©CartoDB',
    maxZoom: 20
}).addTo(map);

// Добавляем кастомные контролы
L.control.zoom({
    position: 'topright'
}).addTo(map);

// Кастомный маркер
const customIcon = L.divIcon({
    className: 'custom-marker',
    html: `
        <div class="marker-pulse">
            <div class="marker-glow"></div>
            <div class="marker-center"></div>
        </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

let currentMarker = null;

map.on('click', function(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    console.log('Map clicked at:', lat, lng); // Для отладки
    
    // Удаляем предыдущий маркер
    if (currentMarker) {
        map.removeLayer(currentMarker);
    }
    
    // Создаем маркер с нашим кастомным иконом
    currentMarker = L.marker([lat, lng], {
        icon: customIcon
    }).addTo(map);
    
    console.log('Marker created:', currentMarker); // Для отладки
    
    // Заполняем поля координат
    document.getElementById('latitude').value = lat.toFixed(6);
    document.getElementById('longitude').value = lng.toFixed(6);
});

// Проверяем что карта загрузилась
// Убираем title атрибуты после загрузки карты
map.whenReady(function() {
    setTimeout(() => {
        const zoomIn = document.querySelector('.leaflet-control-zoom-in');
        const zoomOut = document.querySelector('.leaflet-control-zoom-out');
        
        if (zoomIn) zoomIn.removeAttribute('title');
        if (zoomOut) zoomOut.removeAttribute('title');
        
        // Центрируем карту после загрузки
        map.invalidateSize();
    }, 100);
});

// Альтернативно - отключаем все title у контролов
map.on('load', function() {
    const controls = document.querySelectorAll('.leaflet-control-zoom a');
    controls.forEach(control => {
        control.removeAttribute('title');
    });
});

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
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 45 секунд
        
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
}

// Инициализируем карту по центру экрана
document.addEventListener('DOMContentLoaded', () => {
    // Добавляем обработчик клика на карту
    map.on('click', (e) => {
        const { lat, lng } = e.latlng;
        updateCoordinates(lat, lng);
    });

    // Добавляем обработчик для кнопки
    document.getElementById('check-btn').addEventListener('click', getBortleLevel);
    
    // Пересчитываем размер карты после загрузки DOM
    setTimeout(() => {
        map.invalidateSize();
    }, 100);
    
    // Проверяем видимость информационного раздела
    checkScroll();
});

// Анимация появления при скролле
function checkScroll() {
    const elements = document.querySelectorAll('.fade-in');
    elements.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        const windowHeight = window.innerHeight;
        
        if (elementTop < windowHeight - 100) {
            element.classList.add('visible');
        }
    });
}

// Проверяем при загрузке и скролле
window.addEventListener('load', checkScroll);
window.addEventListener('scroll', checkScroll);

// Аккордеон для информации о шкале Бортля
document.addEventListener('DOMContentLoaded', function() {
    const accordionToggle = document.getElementById('accordion-toggle');
    const accordionContent = document.getElementById('accordion-content');
    const accordionIcon = document.querySelector('.accordion-icon');

    if (accordionToggle && accordionContent) {
        accordionToggle.addEventListener('click', function() {
            const isExpanded = accordionContent.classList.contains('expanded');
            
            if (isExpanded) {
                accordionContent.classList.remove('expanded');
                accordionIcon.classList.remove('rotated');
            } else {
                accordionContent.classList.add('expanded');
                accordionIcon.classList.add('rotated');
                
                // Плавная прокрутка к развернутому контенту
                setTimeout(() => {
                    accordionContent.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'nearest' 
                    });
                }, 300);
            }
        });
    }
});

// Дополнительно: пересчитываем размер карты при изменении размера окна
window.addEventListener('resize', function() {
    setTimeout(() => {
        map.invalidateSize();
    }, 250);
});