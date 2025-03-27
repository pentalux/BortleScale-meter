from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from geopy.geocoders import Nominatim
import os
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image
import numpy as np

load_dotenv()

app = Flask(__name__)
CORS(app)

geolocator = Nominatim(user_agent="light_pollution_app_v5")
NASA_API_KEY = os.getenv('NASA_API_KEY', 'DEMO_KEY')

def analyze_nasa_image(image_url):
    try:
        response = requests.get(image_url, timeout=10)
        if not response.headers.get('Content-Type', '').startswith('image/'):
            print("Response is not an image")
            return None
            
        try:
            img = Image.open(BytesIO(response.content))
            gray_img = img.convert('L')
            np_img = np.array(gray_img)
            masked_img = np_img[np_img > 0]
            if len(masked_img) == 0:
                return 1
            
            avg_brightness = np.mean(masked_img)
            bortle = min(9, max(1, round(avg_brightness / 28)))
            return bortle
        except Exception as img_error:
            print(f"Image processing error: {str(img_error)}")
            return None
            
    except Exception as e:
        print(f"Image download error: {str(e)}")
        return None

def get_nasa_viirs_data(lat, lon):
    try:
        url = f"https://api.nasa.gov/planetary/earth/imagery?lon={lon}&lat={lat}&date=2022-12-01&dim=0.1&api_key={NASA_API_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'url' in data:
                print(f"Fetching image from: {data['url']}")
                return analyze_nasa_image(data['url'])
        return None
    except Exception as e:
        print(f"NASA API error: {str(e)}")
        return None

def get_osm_estimation(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location:
            address = location.raw.get('address', {})
            place_type = (
                'city' if 'city' in address else
                'town' if 'town' in address else
                'village' if 'village' in address else
                'country'
            )
            return {
                'city': 8,
                'town': 6,
                'village': 4,
                'country': 2
            }.get(place_type, 5)
        return 5
    except Exception as e:
        print(f"OSM error: {str(e)}")
        return 5

@app.route("/api/light-pollution", methods=["GET"])
def get_light_pollution():
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        nasa_result = get_nasa_viirs_data(lat, lon)
        if nasa_result is not None:
            return jsonify({
                "bortle_level": nasa_result,
                "source": "NASA VIIRS",
                "location": f"{lat:.4f}, {lon:.4f}"
            })
        osm_result = get_osm_estimation(lat, lon)
        return jsonify({
            "bortle_level": osm_result,
            "source": "OpenStreetMap",
            "location": f"{lat:.4f}, {lon:.4f}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

