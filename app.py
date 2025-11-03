from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
import numpy as np
import logging
import threading
import time
import os
import math
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import atexit


app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Глобальные переменные ---
executor = ThreadPoolExecutor(max_workers=1)
browser_lock = threading.Lock()
driver = None

def init_browser():
    """Инициализация браузера"""
    global driver
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1400,1000")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Добавляем опции для лучшего управления
        chrome_options.add_argument("--remote-debugging-port=0")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.set_page_load_timeout(30)
        logger.info("Browser initialized")
        
    except Exception as e:
        logger.error(f"Browser init failed: {e}")
        raise

def cleanup_browser():
    """Завершаем только наш браузер"""
    global driver
    try:
        if driver:
            logger.info("Closing our browser instance...")
            driver.quit()
            driver = None
            logger.info("Browser closed successfully")
    except Exception as e:
        logger.error(f"Error closing browser: {e}")
        driver = None

def ensure_browser_ready():
    global driver
    if driver is None:
        init_browser()
    return driver is not None

def cleanup_screenshots():
    """Очищаем скриншоты"""
    screenshots_dir = "debug_screenshots"
    if not os.path.exists(screenshots_dir):
        return
        
    for filename in os.listdir(screenshots_dir):
        if filename.endswith('.png'):
            try:
                os.remove(os.path.join(screenshots_dir, filename))
            except:
                pass

def save_screenshot(name, description, bortle_level):
    """Сохраняем скриншот"""
    screenshots_dir = "debug_screenshots"
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
    
    timestamp = int(time.time())
    filename = f"map_{name}_{description}_bortle{bortle_level}_{timestamp}.png"
    return os.path.join(screenshots_dir, filename)

def navigate_to_coordinates(lat, lon):
    """Простая навигация к координатам"""
    try:
        # Простая очистка кэша
        driver.delete_all_cookies()
        
        url = f"https://www.lightpollutionmap.info/#zoom=10&lat={lat}&lon={lon}&layers=B0FFFFFFTFFFF"
        logger.info(f"Opening URL: {url}")
        
        driver.get(url)
        time.sleep(10)  # Даем больше времени на загрузку
        
        return True
            
    except Exception as e:
        logger.error(f"Navigation failed: {e}")
        return False

def set_max_opacity():
    """Устанавливаем максимальную прозрачность"""
    try:
        js_code = """
        setTimeout(function() {
            // Пробуем найти слайдеры opacity
            const sliders = document.querySelectorAll('input[type="range"]');
            sliders.forEach(slider => {
                if (slider.min === '0' && slider.max === '100') {
                    slider.value = '100';
                    slider.dispatchEvent(new Event('input', { bubbles: true }));
                    slider.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        }, 2000);
        """
        
        driver.execute_script(js_code)
        time.sleep(3)
        logger.info("Opacity set to 100%")
        
    except Exception as e:
        logger.warning(f"Opacity setting failed: {e}")

def click_multiple_locations():
    """Кликаем в нескольких местах - ТОЧНЫЕ КЛИКИ В ЦЕНТР"""
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )
        
        canvas = driver.find_element(By.TAG_NAME, "canvas")
        action = ActionChains(driver)
        
        # БОЛЕЕ ТОЧНЫЕ КЛИКИ В ЦЕНТР И БЛИЗКИЕ ТОЧКИ
        click_points = [
            (400, 300),  # Точно центр
            (395, 295),  # Слегка смещено
            (405, 305),  # Слегка смещено
            (390, 290),  # Еще немного
            (410, 310),  # Еще немного
        ]
        
        for i, (x, y) in enumerate(click_points):
            try:
                logger.info(f"Click attempt {i+1} at ({x}, {y})")
                action.move_to_element_with_offset(canvas, x, y).click().perform()
                time.sleep(2)
                
                # Проверяем popup
                popup_data = get_popup_data()
                if popup_data:
                    logger.info(f"Found popup data on attempt {i+1}")
                    return popup_data
                    
            except Exception as e:
                logger.warning(f"Click {i+1} failed: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Multiple clicks failed: {e}")
        return None

def get_popup_data():
    """Получаем данные из всплывающего окна"""
    try:
        # Сначала делаем скриншот всей страницы
        page_screenshot = save_screenshot("debug", "page", "check")
        driver.save_screenshot(page_screenshot)
        logger.info(f"Page screenshot saved: {page_screenshot}")
        
        # Ищем popup элементы
        popup_selectors = [
            "div.leaflet-popup",
            ".leaflet-popup-content", 
            "[class*='popup']",
            "[class*='tooltip']"
        ]
        
        for selector in popup_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
                
                for i, element in enumerate(elements):
                    try:
                        if element.is_displayed():
                            popup_text = element.text
                            logger.info(f"Popup {i} text: {popup_text}")
                            
                            if popup_text.strip():
                                parsed_data = parse_popup_text(popup_text)
                                if parsed_data:
                                    return parsed_data
                    except Exception as e:
                        logger.warning(f"Element {i} check failed: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Popup data extraction failed: {e}")
        return None

def parse_popup_text(popup_text):
    """Парсим текст для извлечения уровня Бортля - ФИКС ДИАПАЗОНОВ"""
    try:
        logger.info(f"Parsing text: {popup_text}")
        
        # СНАЧАЛА ИЩЕМ ДИАПАЗОНЫ (например: "3-4", "8-9")
        range_patterns = [
            r'Bortle[:\s]*(\d+)[-\s]+(\d+)',
            r'Class[:\s]*(\d+)[-\s]+(\d+)',
            r'Level[:\s]*(\d+)[-\s]+(\d+)',
            r'Scale[:\s]*(\d+)[-\s]+(\d+)',
            r'(\d+)[-\s]+(\d+)/9'
        ]
        
        for pattern in range_patterns:
            matches = re.findall(pattern, popup_text, re.IGNORECASE)
            if matches:
                min_level = int(matches[0][0])
                max_level = int(matches[0][1])
                if 1 <= min_level <= 9 and 1 <= max_level <= 9:
                    # БЕРЕМ НАИБОЛЬШЕЕ ЗНАЧЕНИЕ (худший случай)
                    bortle_level = max(min_level, max_level)
                    logger.info(f"Found Bortle range {min_level}-{max_level}, using worst case: {bortle_level}")
                    return {
                        'bortle_level': bortle_level,
                        'source': 'Bortle Range',
                        'confidence': 'high',
                        'range': f"{min_level}-{max_level}"
                    }
        
        # ЕСЛИ НЕТ ДИАПАЗОНА, ИЩЕМ ОДИНОЧНЫЕ ЗНАЧЕНИЯ (как раньше)
        bortle_patterns = [
            r'Bortle[:\s]*(\d+)',
            r'Class[:\s]*(\d+)',
            r'Level[:\s]*(\d+)', 
            r'Scale[:\s]*(\d+)',
            r'(\d)/9'
        ]
        
        for pattern in bortle_patterns:
            matches = re.findall(pattern, popup_text, re.IGNORECASE)
            if matches:
                bortle_level = int(matches[0])
                if 1 <= bortle_level <= 9:
                    logger.info(f"Found single Bortle level: {bortle_level}")
                    return {
                        'bortle_level': bortle_level,
                        'source': 'Direct Bortle',
                        'confidence': 'high'
                    }
        
        # ОСТАЛЬНАЯ ЛОГИКА БЕЗ ИЗМЕНЕНИЙ...
        value_patterns = [
            r'(\d+\.?\d*)\s*[µµ]cd/m²',
            r'(\d+\.?\d*)\s*nW/cm²/sr',
            r'Radiance[:\s]*(\d+\.?\d*)',
            r'Value[:\s]*(\d+\.?\d*)'
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, popup_text, re.IGNORECASE)
            if matches:
                value = float(matches[0])
                bortle_level = value_to_bortle(value)
                logger.info(f"Found value {value} -> Bortle {bortle_level}")
                return {
                    'bortle_level': bortle_level,
                    'raw_value': value,
                    'source': 'Numeric Value',
                    'confidence': 'high'
                }
        
        numbers = re.findall(r'\d+\.?\d*', popup_text)
        for num in numbers:
            try:
                value = float(num)
                if 0.01 <= value <= 100:
                    bortle_level = value_to_bortle(value)
                    logger.info(f"Found potential value {value} -> Bortle {bortle_level}")
                    return {
                        'bortle_level': bortle_level,
                        'raw_value': value,
                        'source': 'Auto-detected Value',
                        'confidence': 'medium'
                    }
            except:
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"Popup parsing failed: {e}")
        return None

def value_to_bortle(value):
    """Конвертируем значение в шкалу Бортля"""
    if value <= 0.1: return 1
    elif value <= 0.3: return 2
    elif value <= 0.5: return 3
    elif value <= 1.0: return 4
    elif value <= 3.0: return 5
    elif value <= 6.0: return 6
    elif value <= 10.0: return 7
    elif value <= 20.0: return 8
    else: return 9

def analyze_map_colors(lat, lon):
    """Анализируем цвета карты как последний вариант"""
    try:
        screenshot_path = save_screenshot(str(lat), str(lon), "color_analysis")
        driver.save_screenshot(screenshot_path)
        logger.info(f"Color analysis screenshot: {screenshot_path}")
        
        image = Image.open(screenshot_path)
        img_array = np.array(image)
        
        height, width = img_array.shape[:2]
        margin = 0.3
        start_y = int(height * margin)
        end_y = int(height * (1 - margin))
        start_x = int(width * margin)
        end_x = int(width * (1 - margin))
        
        map_area = img_array[start_y:end_y, start_x:end_x]
        
        if map_area.size == 0:
            return 4
        
        # Простой анализ по средней яркости
        pixels = map_area.reshape(-1, 3)
        avg_brightness = np.mean(pixels) / 255.0
        
        if avg_brightness < 0.1: return 1
        elif avg_brightness < 0.2: return 2
        elif avg_brightness < 0.3: return 3
        elif avg_brightness < 0.4: return 4
        elif avg_brightness < 0.5: return 5
        elif avg_brightness < 0.6: return 6
        elif avg_brightness < 0.7: return 7
        elif avg_brightness < 0.8: return 8
        else: return 9
        
    except Exception as e:
        logger.error(f"Color analysis failed: {e}")
        return 4

def get_light_pollution_from_map(lat, lon):
    """Основная функция с гарантированным завершением ТОЛЬКО нашего браузера"""
    global driver
    
    with browser_lock:
        try:
            # Очищаем предыдущий браузер если есть
            cleanup_browser()
            cleanup_screenshots()
            
            # Создаем новый браузер для этого запроса
            init_browser()
            
            # УВЕЛИЧИВАЕМ ZOOM ДЛЯ ТОЧНОСТИ КООРДИНАТ
            zoom_level = 14
            url = f"https://www.lightpollutionmap.info/#zoom={zoom_level}&lat={lat}&lon={lon}&layers=B0FFFFFFTFFFF"
            logger.info(f"Fresh browser opening: {lat}, {lon} (zoom: {zoom_level})")
            
            driver.get(url)
            time.sleep(10)
            
            set_max_opacity()
            
            # ТОЧНЫЕ КЛИКИ В ЦЕНТР КАРТЫ
            popup_data = click_multiple_locations()
            
            if popup_data and 'bortle_level' in popup_data:
                bortle_level = popup_data['bortle_level']
                logger.info(f"Success with popup data: Bortle {bortle_level}")
            else:
                # Запасной вариант
                logger.warning("Popup data not found, using color analysis")
                bortle_level = analyze_map_colors(lat, lon)
                popup_data = {
                    'bortle_level': bortle_level,
                    'source': 'Color Analysis',
                    'confidence': 'low'
                }
            
            # Финальный скриншот
            final_screenshot = save_screenshot(str(lat), str(lon), str(bortle_level))
            driver.save_screenshot(final_screenshot)
            logger.info(f"Final screenshot saved: {final_screenshot}")
            
            return popup_data
            
        except Exception as e:
            logger.error(f"Map processing failed: {e}")
            raise
        finally:
            # ГАРАНТИРОВАННО ЗАКРЫВАЕМ ТОЛЬКО НАШ БРАУЗЕР
            cleanup_browser()
            logger.info("Our browser instance closed successfully")


@app.route("/api/light-pollution", methods=["GET"])
def get_light_pollution():
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        
        if lat is None or lon is None:
            return jsonify({"error": "Missing coordinates"}), 400
            
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
            
        logger.info(f"Processing: {lat}, {lon}")
        
        try:
            future = executor.submit(get_light_pollution_from_map, lat, lon)
            result = future.result(timeout=120)
            
            response = {
                "bortle_level": result['bortle_level'],
                "location": f"{lat:.4f}, {lon:.4f}",
                "source": result['source'],
                "confidence": result.get('confidence', 'medium'),
                "raw_value": result.get('raw_value')
            }
            
            logger.info(f"Success: Bortle {result['bortle_level']}")
            return jsonify(response)
            
        except FutureTimeoutError:
            logger.error("Timeout")
            cleanup_browser()  # Закрываем браузер при таймауте
            return jsonify({
                "error": "Request timeout",
                "bortle_level": None
            }), 408
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            cleanup_browser()  # Закрываем браузер при ошибке
            return jsonify({
                "error": f"Failed to get light pollution data: {str(e)}",
                "bortle_level": None
            }), 500
        
    except Exception as e:
        logger.error(f"API error: {e}")
        cleanup_browser()  # Закрываем браузер при любой ошибке
        return jsonify({
            "error": "Internal server error",
            "bortle_level": None
        }), 500

@app.route("/")
def index():
    return render_template("index.html")

@atexit.register
def cleanup():
    """Очистка при завершении приложения"""
    logger.info("Application shutdown - cleaning up...")
    cleanup_browser()
    cleanup_screenshots()
    executor.shutdown(wait=False)

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)
    finally:
        # Дополнительная гарантия очистки
        cleanup_browser()