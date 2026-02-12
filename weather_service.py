import httpx
import logging
from typing import Optional, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class WeatherAPIService:
    """Сервис для получения погоды из WeatherAPI.com (бесплатный, точный, до 1M запросов/месяц)"""

    def __init__(self, api_key: str = None):
        # Бесплатный API ключ WeatherAPI.com
        self.api_key = api_key or "d4f3c7e8a4a64d54bed145851241102"
        self.base_url = "https://api.weatherapi.com/v1"

    async def get_weather(self, lat: float = 47.2094, lon: float = 38.9281) -> Optional[Dict]:
        """
        Получить текущую погоду
        Координаты Таганрога: 47.2094, 38.9281
        """
        try:
            params = {
                "key": self.api_key,
                "q": f"{lat},{lon}",
                "lang": "ru",
                "aqi": "no"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/current.json",
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"WeatherAPI.com error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching WeatherAPI.com weather: {e}")
            return None

    def format_weather_message(self, weather_data: Dict) -> str:
        """
        Форматировать сообщение о погоде в стиле Чупапи
        """
        if not weather_data or 'current_condition' not in weather_data:
            return "😅 Эх, не смог узнать погоду... Сервис молчит 😴"

        try:
            current = weather_data['current_condition'][0]
            forecast = weather_data.get('weather', [{}])[0]

            # Текущая погода
            temp = int(current['temp_C'])
            feels_like = int(current['FeelsLikeC'])
            condition = current['lang_ru'][0]['value'] if current.get('lang_ru') else current['weatherDesc'][0]['value']
            humidity = int(current['humidity'])
            wind_speed = int(current['windspeedKmph']) // 3.6  # км/ч в м/с
            wind_dir = current['winddir16Point']
            pressure = int(current['pressure'])

            # Эмодзи погоды
            weather_code = int(current['weatherCode'])
            emoji = self._get_weather_emoji(weather_code)

            # Направление ветра на русском
            wind_dir_text = self._get_wind_dir_text(wind_dir)

            # Совет как одеваться
            clothing_advice = self._get_clothing_advice(temp, weather_code, wind_speed)

            # Формируем сообщение в стиле Чупапи
            message = f"🌅 <b>Доброе утро, Таганрог!</b>\n\n"
            message += f"{emoji} <b>Погода сейчас:</b>\n"
            message += f"🌡 Температура: <b>{temp}°C</b> (ощущается как {feels_like}°C)\n"
            message += f"☁️ {condition}\n"
            message += f"💨 Ветер: {wind_speed} м/с, {wind_dir_text}\n"
            message += f"💧 Влажность: {humidity}%\n"
            message += f"🔽 Давление: {pressure} мм рт.ст.\n\n"

            # Прогноз по часам если есть
            if forecast and 'hourly' in forecast:
                message += "📊 <b>Прогноз на день:</b>\n"
                current_hour = datetime.now().hour

                for hour_data in forecast['hourly']:
                    hour = int(hour_data['time']) // 100
                    if hour >= current_hour:
                        temp_h = int(hour_data['tempC'])
                        cond_h = hour_data['lang_ru'][0]['value'] if hour_data.get('lang_ru') else hour_data['weatherDesc'][0]['value']
                        message += f"• {hour:02d}:00 — {temp_h}°C, {cond_h}\n"

                message += "\n"

            # Совет от Чупапи
            message += f"👕 <b>Совет по одежде:</b>\n{clothing_advice}\n\n"

            # Добавляем характерную фразу
            if temp <= -10:
                message += "🥶 Ну типа жесткий мороз! Одевайся как капуста!"
            elif temp <= 0:
                message += "🥶 На минусе! Шапка надень, уши застудишь!"
            elif temp <= 10:
                message += "🧥 Прохладненько! Куртку не забудь, а то сопли потекут!"
            elif temp <= 20:
                message += "😎 Нормальная погодка! В самый раз для прогулок!"
            elif temp <= 30:
                message += "☀️ Тепло! Можно в шортах, но не перегрейся!"
            else:
                message += "🔥 Жарища! Только в воду и ни шагу дальше!"

            return message

        except Exception as e:
            logger.error(f"Error formatting weather message: {e}")
            logger.error(f"Weather data: {weather_data}")
            return "😵 Чет с погодой разобраться не могу... Глянь в окно! 🪟"

    def _get_weather_emoji(self, code: int) -> str:
        """Получить эмодзи по коду погоды wttr.in (WMO Weather codes)"""
        emoji_map = {
            113: '☀️',  # Ясно
            116: '🌤️',  # Малооблачно
            119: '☁️',  # Облачно
            122: '☁️',  # Пасмурно
            143: '🌫️',  # Туман
            176: '🌧️',  # Местами дождь
            179: '🌨️',  # Местами снег
            182: '🌨️',  # Местами мокрый снег
            185: '🌧️',  # Местами морось
            200: '⛈️',  # Местами грозы
            227: '❄️',  # Метель
            230: '❄️',  # Сильная метель
            248: '🌫️',  # Туман
            260: '🌫️',  # Густой туман
            263: '🌧️',  # Местами морось
            266: '🌧️',  # Лёгкая морось
            281: '🌧️',  # Морось с заморозками
            284: '🌧️',  # Сильная морось с заморозками
            293: '🌧️',  # Местами небольшой дождь
            296: '🌧️',  # Небольшой дождь
            299: '🌧️',  # Местами умеренный дождь
            302: '🌧️',  # Умеренный дождь
            305: '🌧️',  # Местами сильный дождь
            308: '⛈️',  # Сильный дождь
            311: '🌧️',  # Небольшой ледяной дождь
            314: '🌧️',  # Умеренный или сильный ледяной дождь
            317: '🌨️',  # Небольшой мокрый снег
            320: '🌨️',  # Умеренный или сильный мокрый снег
            323: '🌨️',  # Местами небольшой снег
            326: '❄️',  # Небольшой снег
            329: '❄️',  # Местами умеренный снег
            332: '❄️',  # Умеренный снег
            335: '❄️',  # Местами сильный снег
            338: '❄️',  # Сильный снег
            350: '🌨️',  # Град
            353: '🌧️',  # Небольшой ливень
            356: '🌧️',  # Умеренный или сильный ливень
            359: '⛈️',  # Проливной дождь
            362: '🌨️',  # Небольшой снег с дождём
            365: '🌨️',  # Умеренный или сильный снег с дождём
            368: '🌨️',  # Небольшой снег
            371: '❄️',  # Умеренный или сильный снег
            374: '🌨️',  # Небольшой град
            377: '🌨️',  # Умеренный или сильный град
            386: '⛈️',  # Местами гроза с небольшим дождём
            389: '⛈️',  # Местами гроза с умеренным или сильным дождём
            392: '⛈️',  # Местами гроза с небольшим снегом
            395: '⛈️',  # Местами гроза с умеренным или сильным снегом
        }
        return emoji_map.get(code, '🌈')

    def _get_wind_dir_text(self, wind_dir: str) -> str:
        """Получить текст направления ветра"""
        dir_map = {
            'N': 'северный',
            'NNE': 'северо-северо-восточный',
            'NE': 'северо-восточный',
            'ENE': 'восточно-северо-восточный',
            'E': 'восточный',
            'ESE': 'восточно-юго-восточный',
            'SE': 'юго-восточный',
            'SSE': 'южно-юго-восточный',
            'S': 'южный',
            'SSW': 'южно-юго-западный',
            'SW': 'юго-западный',
            'WSW': 'западно-юго-западный',
            'W': 'западный',
            'WNW': 'западно-северо-западный',
            'NW': 'северо-западный',
            'NNW': 'северо-северо-западный',
        }
        return dir_map.get(wind_dir, wind_dir.lower())

    def _get_clothing_advice(self, temp: float, weather_code: int, wind_speed: float) -> str:
        """Получить совет по одежде"""
        advice = []

        # По температуре
        if temp <= -15:
            advice.append("🧥 Теплую зимнюю куртку обязательно!")
            advice.append("🧤 Шапка, шарф, перчатки - всё надень!")
            advice.append("👖 Термобелье не помешает")
        elif temp <= -5:
            advice.append("🧥 Зимняя куртка")
            advice.append("🧣 Шапка и шарф")
        elif temp <= 0:
            advice.append("🧥 Тёплая куртка")
            advice.append("🧣 Шарф не помешает")
        elif temp <= 10:
            advice.append("🧥 Куртка или толстовка")
            advice.append("👖 Джинсы самое то")
        elif temp <= 20:
            advice.append("👕 Кофта или лёгкая куртка")
        elif temp <= 25:
            advice.append("👕 Футболка, джинсы")
        else:
            advice.append("👕 Футболка и шорты")
            advice.append("🕶 Очки от солнца")
            advice.append("🧴 Крем от солнца")

        # По осадкам (коды дождя и гроз)
        rain_codes = [176, 185, 263, 266, 281, 284, 293, 296, 299, 302, 305, 308,
                     311, 314, 353, 356, 359, 386, 389]
        if weather_code in rain_codes:
            advice.append("☂️ Зонтик обязательно!")
            advice.append("👟 Резиновые сапоги или непромокаемую обувь")

        # По снегу
        snow_codes = [179, 182, 227, 230, 317, 320, 323, 326, 329, 332, 335, 338,
                     362, 365, 368, 371, 392, 395]
        if weather_code in snow_codes:
            advice.append("👟 Тёплую и непромокаемую обувь")
            advice.append("🧣 Шапку носи, а то уши замёрзнут")

        # По ветру
        if wind_speed > 10:
            advice.append("💨 Ветрено! Что-то непродуваемое надень")
        elif wind_speed > 5:
            advice.append("💨 Легкий ветерок, куртка с капюшоном в самый раз")

        return "\n".join([f"  {a}" for a in advice])


class OpenWeatherMapService:
    """Сервис для получения погоды из OpenWeatherMap API"""

    def __init__(self, api_key: str = None):
        # Бесплатный API ключ (до 1 млн запросов/месяц)
        self.api_key = api_key or "66dbfd4a02b0b83af6f61d7e5bdbc3b0"
        self.base_url = "https://api.openweathermap.org/data/2.5"

    async def get_weather(self, lat: float = 47.2094, lon: float = 38.9281) -> Optional[Dict]:
        """
        Получить текущую погоду и прогноз
        Координаты Таганрога: 47.2094, 38.9281
        """
        try:
            # Текущая погода
            current_params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "ru"
            }

            # Прогноз по часам
            forecast_params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "lang": "ru",
                "cnt": 8  # 8 часов вперед
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Получаем текущую погоду
                current_response = await client.get(
                    f"{self.base_url}/weather",
                    params=current_params
                )

                # Получаем прогноз
                forecast_response = await client.get(
                    f"{self.base_url}/forecast",
                    params=forecast_params
                )

                if current_response.status_code == 200 and forecast_response.status_code == 200:
                    return {
                        "current": current_response.json(),
                        "forecast": forecast_response.json()
                    }
                else:
                    logger.error(f"OpenWeatherMap API error: {current_response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching OpenWeatherMap weather: {e}")
            return None

    def format_weather_message(self, weather_data: Dict) -> str:
        """
        Форматировать сообщение о погоде в стиле Чупапи
        """
        if not weather_data or 'current' not in weather_data:
            return "😅 Эх, не смог узнать погоду... Сервис молчит 😴"

        try:
            current = weather_data['current']
            forecast = weather_data.get('forecast', {})

            # Текущая погода
            temp = round(current['main']['temp'])
            feels_like = round(current['main']['feels_like'])
            condition = current['weather'][0]['description'].capitalize()
            humidity = current['main']['humidity']
            wind_speed = round(current['wind']['speed'])
            wind_deg = current['wind'].get('deg', 0)
            pressure = round(current['main']['pressure'] * 0.75)  # гПа в мм рт.ст.

            # Эмодзи погоды
            weather_id = current['weather'][0]['id']
            emoji = self._get_weather_emoji(weather_id)

            # Направление ветра
            wind_dir_text = self._get_wind_dir_text(wind_deg)

            # Совет как одеваться
            clothing_advice = self._get_clothing_advice(temp, weather_id, wind_speed)

            # Формируем сообщение в стиле Чупапи
            message = f"🌅 <b>Доброе утро, Таганрог!</b>\n\n"
            message += f"{emoji} <b>Погода сейчас:</b>\n"
            message += f"🌡 Температура: <b>{temp}°C</b> (ощущается как {feels_like}°C)\n"
            message += f"☁️ {condition}\n"
            message += f"💨 Ветер: {wind_speed} м/с, {wind_dir_text}\n"
            message += f"💧 Влажность: {humidity}%\n"
            message += f"🔽 Давление: {pressure} мм рт.ст.\n\n"

            # Прогноз по часам если есть
            if forecast and 'list' in forecast:
                message += "📊 <b>Прогноз на день:</b>\n"
                for item in forecast['list'][:8]:
                    dt = datetime.fromtimestamp(item['dt'])
                    temp_h = round(item['main']['temp'])
                    cond_h = item['weather'][0]['description']
                    message += f"• {dt.hour:02d}:00 — {temp_h}°C, {cond_h}\n"
                message += "\n"

            # Совет от Чупапи
            message += f"👕 <b>Совет по одежде:</b>\n{clothing_advice}\n\n"

            # Добавляем характерную фразу
            if temp <= -10:
                message += "🥶 Ну типа жесткий мороз! Одевайся как капуста!"
            elif temp <= 0:
                message += "🥶 На минусе! Шапка надень, уши застудишь!"
            elif temp <= 10:
                message += "🧥 Прохладненько! Куртку не забудь, а то сопли потекут!"
            elif temp <= 20:
                message += "😎 Нормальная погодка! В самый раз для прогулок!"
            elif temp <= 30:
                message += "☀️ Тепло! Можно в шортах, но не перегрейся!"
            else:
                message += "🔥 Жарища! Только в воду и ни шагу дальше!"

            return message

        except Exception as e:
            logger.error(f"Error formatting weather message: {e}")
            return "😵 Чет с погодой разобраться не могу... Глянь в окно! 🪟"

    def _get_weather_emoji(self, weather_id: int) -> str:
        """Получить эмодзи по коду погоды OpenWeatherMap"""
        if weather_id >= 200 and weather_id < 300:
            return '⛈️'  # Гроза
        elif weather_id >= 300 and weather_id < 400:
            return '🌧️'  # Морось
        elif weather_id >= 500 and weather_id < 600:
            return '🌧️'  # Дождь
        elif weather_id >= 600 and weather_id < 700:
            return '❄️'  # Снег
        elif weather_id >= 700 and weather_id < 800:
            return '🌫️'  # Атмосферные явления (туман и т.д.)
        elif weather_id == 800:
            return '☀️'  # Ясно
        elif weather_id == 801:
            return '🌤️'  # Малооблачно
        elif weather_id == 802:
            return '⛅'  # Переменная облачность
        elif weather_id >= 803:
            return '☁️'  # Облачно/Пасмурно
        return '🌈'

    def _get_wind_dir_text(self, degrees: float) -> str:
        """Получить текст направления ветра по градусам"""
        if degrees is None:
            return 'штиль'

        directions = [
            'северный', 'северо-восточный', 'восточный', 'юго-восточный',
            'южный', 'юго-западный', 'западный', 'северо-западный'
        ]
        index = round(degrees / 45) % 8
        return directions[index]

    def _get_clothing_advice(self, temp: float, weather_id: int, wind_speed: float) -> str:
        """Получить совет по одежде"""
        advice = []

        # По температуре
        if temp <= -15:
            advice.append("🧥 Теплую зимнюю куртку обязательно!")
            advice.append("🧤 Шапка, шарф, перчатки - всё надень!")
            advice.append("👖 Термобелье не помешает")
        elif temp <= -5:
            advice.append("🧥 Зимняя куртка")
            advice.append("🧣 Шапка и шарф")
        elif temp <= 0:
            advice.append("🧥 Тёплая куртка")
            advice.append("🧣 Шарф не помешает")
        elif temp <= 10:
            advice.append("🧥 Куртка или толстовка")
            advice.append("👖 Джинсы самое то")
        elif temp <= 20:
            advice.append("👕 Кофта или лёгкая куртка")
        elif temp <= 25:
            advice.append("👕 Футболка, джинсы")
        else:
            advice.append("👕 Футболка и шорты")
            advice.append("🕶 Очки от солнца")
            advice.append("🧴 Крем от солнца")

        # По осадкам (дождь: 300-599, гроза: 200-299)
        if (weather_id >= 200 and weather_id < 600):
            advice.append("☂️ Зонтик обязательно!")
            advice.append("👟 Резиновые сапоги или непромокаемую обувь")

        # По снегу (600-699)
        if weather_id >= 600 and weather_id < 700:
            advice.append("👟 Тёплую и непромокаемую обувь")
            advice.append("🧣 Шапку носи, а то уши замёрзнут")

        # По ветру
        if wind_speed > 10:
            advice.append("💨 Ветрено! Что-то непродуваемое надень")
        elif wind_speed > 5:
            advice.append("💨 Легкий ветерок, куртка с капюшоном в самый раз")

        return "\n".join([f"  {a}" for a in advice])


class OpenMeteoWeatherService:
    """Сервис для получения погоды из Open-Meteo API (бесплатный, без ключа)"""

    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    async def get_weather(self, lat: float = 47.2094, lon: float = 38.9281) -> Optional[Dict]:
        """
        Получить текущую погоду и прогноз
        Координаты Таганрога: 47.2094, 38.9281
        """
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
                          "weather_code,wind_speed_10m,wind_direction_10m,pressure_msl",
                "hourly": "temperature_2m,weather_code",
                "forecast_days": 1,
                "timezone": "Europe/Moscow"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Open-Meteo API error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching Open-Meteo weather: {e}")
            return None

    def format_weather_message(self, weather_data: Dict) -> str:
        """
        Форматировать сообщение о погоде в стиле Чупапи
        """
        if not weather_data or 'current' not in weather_data:
            return "😅 Эх, не смог узнать погоду... Сервис молчит 😴"

        try:
            current = weather_data['current']
            hourly = weather_data.get('hourly', {})

            # Текущая погода
            temp = round(current['temperature_2m'])
            feels_like = round(current['apparent_temperature'])
            weather_code = current['weather_code']
            humidity = current['relative_humidity_2m']
            wind_speed = round(current['wind_speed_10m'])
            wind_dir = current['wind_direction_10m']
            pressure = round(current['pressure_msl'] * 0.75)  # Конвертируем гПа в мм рт.ст.

            # Эмодзи и описание погоды
            emoji, condition_text = self._get_weather_info(weather_code)

            # Направление ветра
            wind_dir_text = self._get_wind_dir_text(wind_dir)

            # Совет как одеваться
            clothing_advice = self._get_clothing_advice(temp, weather_code, wind_speed)

            # Формируем сообщение в стиле Чупапи
            message = f"🌅 <b>Доброе утро, Таганрог!</b>\n\n"
            message += f"{emoji} <b>Погода сейчас:</b>\n"
            message += f"🌡 Температура: <b>{temp}°C</b> (ощущается как {feels_like}°C)\n"
            message += f"☁️ {condition_text}\n"
            message += f"💨 Ветер: {wind_speed} м/с, {wind_dir_text}\n"
            message += f"💧 Влажность: {humidity}%\n"
            message += f"🔽 Давление: {pressure} мм рт.ст.\n\n"

            # Прогноз по часам если есть
            if hourly and 'time' in hourly and 'temperature_2m' in hourly:
                message += "📊 <b>Прогноз на день:</b>\n"
                current_hour = datetime.now().hour
                times = hourly['time']
                temps = hourly['temperature_2m']
                codes = hourly['weather_code']

                count = 0
                for i, time_str in enumerate(times):
                    hour = int(time_str.split('T')[1].split(':')[0])
                    if hour >= current_hour and count < 8:
                        temp_h = round(temps[i])
                        _, cond_h = self._get_weather_info(codes[i])
                        message += f"• {hour:02d}:00 — {temp_h}°C, {cond_h}\n"
                        count += 1

                message += "\n"

            # Совет от Чупапи
            message += f"👕 <b>Совет по одежде:</b>\n{clothing_advice}\n\n"

            # Добавляем характерную фразу
            if temp <= -10:
                message += "🥶 Ну типа жесткий мороз! Одевайся как капуста!"
            elif temp <= 0:
                message += "🥶 На минусе! Шапка надень, уши застудишь!"
            elif temp <= 10:
                message += "🧥 Прохладненько! Куртку не забудь, а то сопли потекут!"
            elif temp <= 20:
                message += "😎 Нормальная погодка! В самый раз для прогулок!"
            elif temp <= 30:
                message += "☀️ Тепло! Можно в шортах, но не перегрейся!"
            else:
                message += "🔥 Жарища! Только в воду и ни шагу дальше!"

            return message

        except Exception as e:
            logger.error(f"Error formatting weather message: {e}")
            return "😵 Чет с погодой разобраться не могу... Глянь в окно! 🪟"

    def _get_weather_info(self, code: int) -> tuple[str, str]:
        """Получить эмодзи и описание по WMO Weather Code"""
        weather_map = {
            0: ('☀️', 'Ясно'),
            1: ('🌤️', 'Преимущественно ясно'),
            2: ('⛅', 'Переменная облачность'),
            3: ('☁️', 'Пасмурно'),
            45: ('🌫️', 'Туман'),
            48: ('🌫️', 'Изморозь'),
            51: ('🌧️', 'Лёгкая морось'),
            53: ('🌧️', 'Морось'),
            55: ('🌧️', 'Сильная морось'),
            56: ('🌧️', 'Лёгкая морось с заморозками'),
            57: ('🌧️', 'Морось с заморозками'),
            61: ('🌧️', 'Небольшой дождь'),
            63: ('🌧️', 'Дождь'),
            65: ('🌧️', 'Сильный дождь'),
            66: ('🌧️', 'Лёгкий ледяной дождь'),
            67: ('🌧️', 'Ледяной дождь'),
            71: ('🌨️', 'Небольшой снег'),
            73: ('❄️', 'Снег'),
            75: ('❄️', 'Сильный снег'),
            77: ('🌨️', 'Снежная крупа'),
            80: ('🌧️', 'Небольшой ливень'),
            81: ('🌧️', 'Ливень'),
            82: ('⛈️', 'Сильный ливень'),
            85: ('🌨️', 'Небольшой снегопад'),
            86: ('❄️', 'Снегопад'),
            95: ('⛈️', 'Гроза'),
            96: ('⛈️', 'Гроза с градом'),
            99: ('⛈️', 'Гроза с сильным градом'),
        }
        return weather_map.get(code, ('🌈', 'Неизвестно'))

    def _get_wind_dir_text(self, degrees: float) -> str:
        """Получить текст направления ветра по градусам"""
        if degrees is None:
            return 'штиль'

        directions = [
            'северный', 'северо-восточный', 'восточный', 'юго-восточный',
            'южный', 'юго-западный', 'западный', 'северо-западный'
        ]
        index = round(degrees / 45) % 8
        return directions[index]

    def _get_clothing_advice(self, temp: float, weather_code: int, wind_speed: float) -> str:
        """Получить совет по одежде"""
        advice = []

        # По температуре
        if temp <= -15:
            advice.append("🧥 Теплую зимнюю куртку обязательно!")
            advice.append("🧤 Шапка, шарф, перчатки - всё надень!")
            advice.append("👖 Термобелье не помешает")
        elif temp <= -5:
            advice.append("🧥 Зимняя куртка")
            advice.append("🧣 Шапка и шарф")
        elif temp <= 0:
            advice.append("🧥 Тёплая куртка")
            advice.append("🧣 Шарф не помешает")
        elif temp <= 10:
            advice.append("🧥 Куртка или толстовка")
            advice.append("👖 Джинсы самое то")
        elif temp <= 20:
            advice.append("👕 Кофта или лёгкая куртка")
        elif temp <= 25:
            advice.append("👕 Футболка, джинсы")
        else:
            advice.append("👕 Футболка и шорты")
            advice.append("🕶 Очки от солнца")
            advice.append("🧴 Крем от солнца")

        # По осадкам (коды дождя: 51-67, 80-82)
        if weather_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
            advice.append("☂️ Зонтик обязательно!")
            advice.append("👟 Резиновые сапоги или непромокаемую обувь")

        # По снегу (коды снега: 71-77, 85-86)
        if weather_code in [71, 73, 75, 77, 85, 86]:
            advice.append("👟 Тёплую и непромокаемую обувь")
            advice.append("🧣 Шапку носи, а то уши замёрзнут")

        # По ветру
        if wind_speed > 10:
            advice.append("💨 Ветрено! Что-то непродуваемое надень")
        elif wind_speed > 5:
            advice.append("💨 Легкий ветерок, куртка с капюшоном в самый раз")

        return "\n".join([f"  {a}" for a in advice])


class YandexWeatherService:
    """Сервис для получения погоды из Яндекс Погоды API"""

    def __init__(self, api_key: str = None):
        # API ключ Яндекс Погоды
        self.api_key = api_key or "your_yandex_api_key"
        self.base_url = "https://api.weather.yandex.ru/v2/forecast"

    async def get_weather(self, lat: float = 47.2094, lon: float = 38.9281) -> Optional[Dict]:
        """
        Получить текущую погоду
        Координаты Таганрога: 47.2094, 38.9281
        """
        try:
            headers = {
                "X-Yandex-API-Key": self.api_key
            }
            params = {
                "lat": lat,
                "lon": lon,
                "lang": "ru_RU",
                "extra": "true"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    self.base_url,
                    headers=headers,
                    params=params
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Yandex Weather API error: {response.status_code} - {response.text}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching Yandex weather: {e}")
            return None

    def format_weather_message(self, weather_data: Dict) -> str:
        """
        Форматировать сообщение о погоде в стиле Чупапи
        """
        if not weather_data or 'fact' not in weather_data:
            return "😅 Эх, не смог узнать погоду... Яндекс молчит 😴"

        try:
            fact = weather_data['fact']
            forecast = weather_data.get('forecast', {})

            # Текущая погода
            temp = fact['temp']
            feels_like = fact['feels_like']
            condition = fact['condition']
            humidity = fact['humidity']
            wind_speed = fact['wind_speed']
            wind_dir = fact['wind_dir']
            pressure = fact['pressure_mm']

            # Эмодзи погоды
            emoji = self._get_weather_emoji(condition)

            # Описание условия на русском
            condition_text = self._get_condition_text(condition)

            # Направление ветра
            wind_dir_text = self._get_wind_dir_text(wind_dir)

            # Совет как одеваться
            clothing_advice = self._get_clothing_advice(temp, condition, wind_speed)

            # Формируем сообщение в стиле Чупапи
            message = f"🌅 <b>Доброе утро, Таганрог!</b>\n\n"
            message += f"{emoji} <b>Погода сейчас:</b>\n"
            message += f"🌡 Температура: <b>{temp}°C</b> (ощущается как {feels_like}°C)\n"
            message += f"☁️ {condition_text}\n"
            message += f"💨 Ветер: {wind_speed} м/с, {wind_dir_text}\n"
            message += f"💧 Влажность: {humidity}%\n"
            message += f"🔽 Давление: {pressure} мм рт.ст.\n\n"

            # Прогноз по часам если есть
            if forecast and 'hours' in forecast:
                message += "📊 <b>Прогноз на день:</b>\n"
                current_hour = datetime.now().hour
                hours = forecast['hours']

                # Берем прогноз на ближайшие 12 часов
                for hour in hours:
                    h = hour['hour']
                    if h >= current_hour and len(message.split('\n')) < 18:
                        temp_h = hour['temp']
                        cond_h = self._get_condition_text(hour['condition'])
                        message += f"• {h:02d}:00 — {temp_h}°C, {cond_h}\n"

                message += "\n"

            # Совет от Чупапи
            message += f"👕 <b>Совет по одежде:</b>\n{clothing_advice}\n\n"

            # Добавляем характерную фразу
            if temp <= -10:
                message += "🥶 Ну типа жесткий мороз! Одевайся как капуста!"
            elif temp <= 0:
                message += "🥶 На минусе! Шапка надень, уши застудишь!"
            elif temp <= 10:
                message += "🧥 Прохладненько! Куртку не забудь, а то сопли потекут!"
            elif temp <= 20:
                message += "😎 Нормальная погодка! В самый раз для прогулок!"
            elif temp <= 30:
                message += "☀️ Тепло! Можно в шортах, но не перегрейся!"
            else:
                message += "🔥 Жарища! Только в воду и ни шагу дальше!"

            return message

        except Exception as e:
            logger.error(f"Error formatting weather message: {e}")
            return "😵 Чет с погодой разобраться не могу... Глянь в окно! 🪟"

    def _get_weather_emoji(self, condition: str) -> str:
        """Получить эмодзи по условию погоды"""
        emoji_map = {
            'clear': '☀️',           # Ясно
            'partly-cloudy': '🌤️',  # Малооблачно
            'cloudy': '☁️',          # Облачно с прояснениями
            'overcast': '☁️',        # Пасмурно
            'drizzle': '🌧️',        # Морось
            'light-rain': '🌧️',     # Небольшой дождь
            'rain': '🌧️',           # Дождь
            'moderate-rain': '🌧️',  # Умеренно сильный дождь
            'heavy-rain': '⛈️',      # Сильный дождь
            'continuous-heavy-rain': '⛈️',  # Длительный сильный дождь
            'showers': '🌧️',        # Ливень
            'wet-snow': '🌨️',       # Мокрый снег
            'light-snow': '🌨️',     # Небольшой снег
            'snow': '❄️',           # Снег
            'snow-showers': '❄️',   # Снегопад
            'hail': '🌨️',           # Град
            'thunderstorm': '⛈️',    # Гроза
            'thunderstorm-with-rain': '⛈️',  # Гроза с дождем
            'thunderstorm-with-hail': '⛈️',  # Гроза с градом
        }
        return emoji_map.get(condition, '🌈')

    def _get_condition_text(self, condition: str) -> str:
        """Получить текстовое описание условия"""
        condition_map = {
            'clear': 'Ясно',
            'partly-cloudy': 'Малооблачно',
            'cloudy': 'Облачно с прояснениями',
            'overcast': 'Пасмурно',
            'drizzle': 'Морось',
            'light-rain': 'Небольшой дождь',
            'rain': 'Дождь',
            'moderate-rain': 'Умеренно сильный дождь',
            'heavy-rain': 'Сильный дождь',
            'continuous-heavy-rain': 'Длительный сильный дождь',
            'showers': 'Ливень',
            'wet-snow': 'Мокрый снег',
            'light-snow': 'Небольшой снег',
            'snow': 'Снег',
            'snow-showers': 'Снегопад',
            'hail': 'Град',
            'thunderstorm': 'Гроза',
            'thunderstorm-with-rain': 'Гроза с дождем',
            'thunderstorm-with-hail': 'Гроза с градом',
        }
        return condition_map.get(condition, 'Неизвестно')

    def _get_wind_dir_text(self, wind_dir: str) -> str:
        """Получить текст направления ветра"""
        dir_map = {
            'n': 'северный',
            'ne': 'северо-восточный',
            'e': 'восточный',
            'se': 'юго-восточный',
            's': 'южный',
            'sw': 'юго-западный',
            'w': 'западный',
            'nw': 'северо-западный',
            'c': 'штиль',
        }
        return dir_map.get(wind_dir, '')

    def _get_clothing_advice(self, temp: float, condition: str, wind_speed: float) -> str:
        """Получить совет по одежде"""
        advice = []

        # По температуре
        if temp <= -15:
            advice.append("🧥 Теплую зимнюю куртку обязательно!")
            advice.append("🧤 Шапка, шарф, перчатки - всё надень!")
            advice.append("👖 Термобелье не помешает")
        elif temp <= -5:
            advice.append("🧥 Зимняя куртка")
            advice.append("🧣 Шапка и шарф")
        elif temp <= 0:
            advice.append("🧥 Тёплая куртка")
            advice.append("🧣 Шарф не помешает")
        elif temp <= 10:
            advice.append("🧥 Куртка или толстовка")
            advice.append("👖 Джинсы самое то")
        elif temp <= 20:
            advice.append("👕 Кофта или лёгкая куртка")
        elif temp <= 25:
            advice.append("👕 Футболка, джинсы")
        else:
            advice.append("👕 Футболка и шорты")
            advice.append("🕶 Очки от солнца")
            advice.append("🧴 Крем от солнца")

        # По осадкам
        if condition in ['drizzle', 'light-rain', 'rain', 'moderate-rain', 'heavy-rain',
                       'continuous-heavy-rain', 'showers', 'thunderstorm-with-rain']:
            advice.append("☂️ Зонтик обязательно!")
            advice.append("👟 Резиновые сапоги или непромокаемую обувь")

        # По снегу
        if condition in ['wet-snow', 'light-snow', 'snow', 'snow-showers']:
            advice.append("👟 Тёплую и непромокаемую обувь")
            advice.append("🧣 Шапку носи, а то уши замёрзнут")

        # По ветру
        if wind_speed > 10:
            advice.append("💨 Ветрено! Что-то непродуваемое надень")
        elif wind_speed > 5:
            advice.append("💨 Легкий ветерок, куртка с капюшоном в самый раз")

        return "\n".join([f"  {a}" for a in advice])


# Заглушка для работы без API ключа
class MockWeatherService:
    """Моковый сервис погоды для тестирования"""

    async def get_weather(self, lat: float = 47.2094, lon: float = 38.9281) -> Optional[Dict]:
        return {
            'fact': {
                'temp': 15,
                'feels_like': 14,
                'condition': 'partly-cloudy',
                'humidity': 65,
                'wind_speed': 3,
                'wind_dir': 'ne',
                'pressure_mm': 760
            },
            'forecast': {
                'hours': [
                    {'hour': 9, 'temp': 16, 'condition': 'partly-cloudy'},
                    {'hour': 12, 'temp': 18, 'condition': 'clear'},
                    {'hour': 15, 'temp': 19, 'condition': 'clear'},
                    {'hour': 18, 'temp': 17, 'condition': 'partly-cloudy'},
                ]
            }
        }

    def format_weather_message(self, weather_data: Dict) -> str:
        return YandexWeatherService().format_weather_message(weather_data)


# Создаем правильный класс для обратной совместимости
# По умолчанию используем Open-Meteo (бесплатный, работает без API ключа)
WeatherService = OpenMeteoWeatherService
