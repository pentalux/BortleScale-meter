from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from geopy.geocoders import Nominatim
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

geolocator = Nominatim(user_agent="light_pollution_app_v13")

def get_urbanization_level(lat, lon):
    """Определяем уровень урбанизации на основе OSM данных"""
    try:
        # Overpass API запрос для анализа плотности объектов
        overpass_url = "http://overpass-api.de/api/interpreter"
        
        overpass_query = f"""
        [out:json];
        (
          // Все возможные объекты в радиусе 50км
          node["place"~"city|town|village|hamlet|island"](around:50000,{lat},{lon});
          way["landuse"~"industrial|commercial|residential|retail"](around:50000,{lat},{lon});
          node["amenity"~"university|hospital|school|college"](around:50000,{lat},{lon});
          way["building"](around:50000,{lat},{lon});
          relation["boundary"="national_park"](around:50000,{lat},{lon});
          way["landuse"~"forest|meadow|farmland|grass"](around:50000,{lat},{lon});
          way["natural"~"wood|water|coastline|beach"](around:50000,{lat},{lon});
          node["natural"~"bay|cape|cliff"](around:50000,{lat},{lon});
        );
        out count;
        """
        
        response = requests.post(overpass_url, data=overpass_query, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            
            # Считаем объекты по типам
            city_count = 0
            town_count = 0
            village_count = 0
            industrial_count = 0
            building_count = 0
            natural_count = 0
            water_count = 0
            total_objects = len(elements)
            
            for element in elements:
                tags = element.get('tags', {})
                
                if tags.get('place') == 'city':
                    city_count += 1
                elif tags.get('place') == 'town':
                    town_count += 1
                elif tags.get('place') in ['village', 'hamlet']:
                    village_count += 1
                elif tags.get('landuse') in ['industrial', 'commercial', 'retail']:
                    industrial_count += 1
                elif tags.get('building'):
                    building_count += 1
                elif (tags.get('boundary') == 'national_park' or 
                      tags.get('landuse') in ['forest', 'meadow', 'farmland'] or
                      tags.get('natural') in ['wood', 'beach']):
                    natural_count += 1
                elif tags.get('natural') in ['water', 'bay', 'cape', 'cliff']:
                    water_count += 1
            
            print(f"Total objects: {total_objects}")
            print(f"Cities: {city_count}, Towns: {town_count}, Villages: {village_count}")
            print(f"Industrial: {industrial_count}, Buildings: {building_count}")
            print(f"Natural: {natural_count}, Water: {water_count}")
            
            # ПРОВЕРКА НА ОКЕАН: если очень мало объектов вообще
            if total_objects <= 2:
                print("Very few objects - likely ocean/remote area")
                return 1
            
            # ПРОВЕРКА НА ВОДНЫЕ ОБЪЕКТЫ
            if water_count >= 5 and total_objects <= 10:
                print("Many water objects, few others - likely ocean")
                return 1
            
            # 1. Крупные городские объекты
            if city_count >= 2 or (city_count >= 1 and industrial_count >= 3):
                return 9
            elif city_count >= 1:
                return 8
            
            # 2. Средние городские объекты
            elif town_count >= 2 or (town_count >= 1 and industrial_count >= 2):
                return 7
            elif town_count >= 1:
                return 6
            
            # 3. Малые населенные пункты
            elif village_count >= 3 or building_count >= 10:
                return 5
            elif village_count >= 1 or building_count >= 5:
                return 4
            
            # 4. Природные зоны
            elif natural_count >= 10 and total_objects <= 20:
                return 1  # Дикая природа
            elif natural_count >= 5:
                return 2  # Природная зона
            elif natural_count >= 2:
                return 3  # Сельская местность
            
            # 5. Если дошли сюда и объектов мало - скорее всего вода/пустыня
            elif total_objects <= 5:
                return 1
            else:
                return 3
                
        else:
            print(f"Overpass API error: Status {response.status_code}")
            return get_fallback_estimation(lat, lon)
        
    except Exception as e:
        print(f"Overpass API error: {str(e)}")
        return get_fallback_estimation(lat, lon)

def get_fallback_estimation(lat, lon):
    """Резервный метод на основе геолокации и координат"""
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, language='en', timeout=10)
        if location:
            address = location.raw.get('address', {})
            address_str = str(address).lower()
            
            print(f"Fallback address: {address}")
            
            # Проверяем на океан/море
            ocean_keywords = ['ocean', 'sea', 'pacific', 'atlantic', 'indian', 'arctic', 'gulf', 'bay']
            if any(keyword in address_str for keyword in ocean_keywords):
                return 1
            
            # Проверяем на национальные парки и заповедники
            if any(keyword in address_str for keyword in ['national_park', 'nature_reserve', 'wilderness']):
                return 1
            
            # Проверяем городские признаки
            if 'city' in address:
                return 8
            elif 'town' in address:
                return 6
            elif 'village' in address:
                return 4
            elif any(keyword in address_str for keyword in ['forest', 'mountain', 'lake', 'river']):
                return 2
            else:
                return 3
                
        # ГЕОГРАФИЧЕСКАЯ ПРОВЕРКА по координатам
        # Удаленные океанские координаты
        if is_ocean_coordinate(lat, lon):
            return 1
        # Пустыни и удаленные территории
        elif is_desert_coordinate(lat, lon):
            return 1
        # Горные и лесные районы
        elif is_mountain_forest_coordinate(lat, lon):
            return 2
            
        return 3
        
    except Exception as e:
        print(f"Geolocation fallback error: {e}")
        # Последняя проверка - чисто по координатам
        if is_ocean_coordinate(lat, lon):
            return 1
        return 3

def is_ocean_coordinate(lat, lon):
    """Проверяем, находится ли точка в океане по координатам"""
    # Тихий океан
    if (-60 <= lat <= 60) and (120 <= abs(lon) <= 180):
        return True
    # Атлантический океан
    if (-60 <= lat <= 60) and (30 <= abs(lon) <= 80):
        return True
    # Индийский океан
    if (-60 <= lat <= 30) and (40 <= lon <= 120):
        return True
    # Арктика/Антарктика
    if abs(lat) > 70:
        return True
    return False

def is_desert_coordinate(lat, lon):
    """Проверяем пустынные регионы"""
    # Сахара
    if (15 <= lat <= 30) and (-20 <= lon <= 50):
        return True
    # Аравийская пустыня
    if (15 <= lat <= 30) and (35 <= lon <= 60):
        return True
    # Гоби
    if (35 <= lat <= 45) and (90 <= lon <= 120):
        return True
    # Австралийские пустыни
    if (-30 <= lat <= -20) and (120 <= lon <= 140):
        return True
    return False

def is_mountain_forest_coordinate(lat, lon):
    """Проверяем горные и лесные регионы"""
    # Сибирь
    if (50 <= lat <= 70) and (60 <= lon <= 180):
        return True
    # Канадская тайга
    if (50 <= lat <= 70) and (-140 <= lon <= -60):
        return True
    # Амазония
    if (-20 <= lat <= 10) and (-80 <= lon <= -50):
        return True
    # Гималаи
    if (25 <= lat <= 35) and (75 <= lon <= 100):
        return True
    return False

def get_light_pollution_data(lat, lon):
    """Основная функция получения данных о световом загрязнении"""
    
    print("Analyzing urbanization level...")
    bortle_level = get_urbanization_level(lat, lon)
    
    print(f"Final Bortle level: {bortle_level}")
    
    source = "Environmental Analysis"
    return bortle_level, source

@app.route("/api/light-pollution", methods=["GET"])
def get_light_pollution():
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        
        if lat is None or lon is None:
            return jsonify({"error": "Missing coordinates"}), 400
            
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
            
        print(f"Processing coordinates: {lat}, {lon}")
        
        # Получаем данные
        bortle_level, source = get_light_pollution_data(lat, lon)
        
        # Логируем в консоль
        print(f"Bortle Level: {bortle_level}, Source: {source}")
        
        return jsonify({
            "bortle_level": bortle_level,
            "location": f"{lat:.4f}, {lon:.4f}"
        })
        
    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)