from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from geopy.geocoders import Nominatim
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

geolocator = Nominatim(user_agent="light_pollution_app_v11")

def get_urbanization_level(lat, lon):
    """Определяем уровень урбанизации на основе OSM данных"""
    try:
        # Overpass API запрос для анализа плотности объектов
        overpass_url = "http://overpass-api.de/api/interpreter"
        
        overpass_query = f"""
        [out:json];
        (
          // Городские объекты в радиусе 10км
          node["place"~"city|town|village|hamlet"](around:10000,{lat},{lon});
          way["landuse"~"industrial|commercial|residential|retail"](around:10000,{lat},{lon});
          node["amenity"~"university|hospital|school|college"](around:10000,{lat},{lon});
          way["building"](around:5000,{lat},{lon});
          
          // Природные объекты в радиусе 20км
          relation["boundary"="national_park"](around:20000,{lat},{lon});
          way["landuse"~"forest|meadow|farmland|grass"](around:20000,{lat},{lon});
          way["natural"~"wood|water|coastline"](around:20000,{lat},{lon});
        );
        out count;
        """
        
        response = requests.post(overpass_url, data=overpass_query, timeout=10)
        
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
                      tags.get('natural')):
                    natural_count += 1
            
            print(f"Objects count - Cities: {city_count}, Towns: {town_count}, Villages: {village_count}, "
                  f"Industrial: {industrial_count}, Buildings: {building_count}, Natural: {natural_count}")
            
            # НОВАЯ ЛОГИКА: Приоритет природных зон
            if natural_count >= 10 and city_count == 0 and town_count == 0:
                return 1  # Дикая природа, национальные парки
            elif natural_count >= 5 and town_count == 0:
                return 2  # Природные зоны с минимальной населенкой
            
            # Городская логика
            if city_count >= 2 or (city_count >= 1 and industrial_count >= 3):
                return 9  # Крупный город с промышленностью
            elif city_count >= 1:
                return 8  # Город
            elif town_count >= 2 or (town_count >= 1 and industrial_count >= 2):
                return 7  # Несколько городов или город с промышленностью
            elif town_count >= 1:
                return 6  # Небольшой город
            elif village_count >= 3:
                return 5  # Несколько деревень
            elif village_count >= 1:
                return 4  # Деревня
            elif natural_count >= 3:
                return 2  # Природная зона
            elif natural_count >= 1:
                return 3  # Сельская местность
            else:
                return 1  # Океан, пустыня, удаленные территории
                
        return 3  # По умолчанию - сельская местность
        
    except Exception as e:
        print(f"Overpass API error: {str(e)}")
        return get_fallback_estimation(lat, lon)

def get_fallback_estimation(lat, lon):
    """Резервный метод на основе геолокации"""
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, language='en', timeout=10)
        if location:
            address = location.raw.get('address', {})
            
            # Проверяем на океан/море
            if any(key in str(address).lower() for key in ['ocean', 'sea', 'pacific', 'atlantic']):
                return 1
            
            # Проверяем на национальные парки и заповедники
            if any(key in str(address).lower() for key in ['national_park', 'nature_reserve', 'wilderness']):
                return 1
            
            # Проверяем городские признаки
            if 'city' in address:
                return 8
            elif 'town' in address:
                return 6
            elif 'village' in address:
                return 4
            elif any(key in str(address).lower() for key in ['forest', 'mountain', 'lake']):
                return 2
            else:
                return 3
                
        # Если не можем определить - проверяем координаты
        # Удаленные океанские координаты
        if (abs(lat) < 30 and (abs(lon) > 150 or abs(lon) < 30)):
            return 1
        # Пустыни и удаленные территории
        elif (abs(lat) < 30 and (100 < abs(lon) < 150)):
            return 1
            
        return 3
        
    except Exception as e:
        print(f"Geolocation fallback error: {e}")
        return 3

def get_light_pollution_data(lat, lon):
    """Основная функция получения данных о световом загрязнении"""
    
    # Используем анализ урбанизации через Overpass API
    print("Analyzing urbanization level...")
    bortle_level = get_urbanization_level(lat, lon)
    
    # Логируем детали
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