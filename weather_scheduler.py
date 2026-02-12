"""
Планировщик ежедневной отправки погоды в чаты
"""
import logging
import asyncio
from datetime import datetime, time
from telegram.ext import Application

logger = logging.getLogger(__name__)


class WeatherScheduler:
    """Планировщик отправки погоды по расписанию"""

    def __init__(self, weather_service, weather_chat_ids, send_time_str="08:00", glm_client=None, system_persona=""):
        """
        Инициализация планировщика

        Args:
            weather_service: Сервис погоды (WeatherService или MockWeatherService)
            weather_chat_ids: Список chat_id для отправки погоды
            send_time_str: Время отправки в формате "HH:MM"
            glm_client: Клиент для генерации сообщений через AI
            system_persona: Персона бота для генерации сообщений
        """
        self.weather_service = weather_service
        self.weather_chat_ids = weather_chat_ids
        self.send_time = self._parse_time(send_time_str)
        self.glm_client = glm_client
        self.system_persona = system_persona
        self._last_sent_date = None
        self._running = False

    def _parse_time(self, time_str: str) -> time:
        """Парсит строку времени в объект time"""
        try:
            hours, minutes = map(int, time_str.split(":"))
            return time(hour=hours, minute=minutes)
        except Exception as e:
            logger.warning(f"Ошибка парсинга времени {time_str}: {e}. Используем 08:00")
            return time(hour=8, minute=0)

    def _should_send_weather(self) -> bool:
        """Проверяет, пора ли отправлять погоду"""
        now = datetime.now()
        current_time = now.time()

        # Проверяем, что наступило нужное время (с точностью до минуты)
        time_match = (
            current_time.hour == self.send_time.hour and
            current_time.minute == self.send_time.minute
        )

        # Проверяем, что еще не отправляли сегодня
        today_str = now.strftime("%Y-%m-%d")
        already_sent = self._last_sent_date == today_str

        return time_match and not already_sent

    async def send_weather_to_chats(self, application: Application, glm_client, system_persona: str):
        """Отправляет погоду во все настроенные чаты"""
        if not self.weather_chat_ids:
            logger.info("Нет чатов для отправки погоды")
            return

        # Получаем данные погоды
        weather_data = await self.weather_service.get_weather()

        if not weather_data or 'current' not in weather_data:
            logger.error("Не удалось получить данные погоды")
            return

        # Извлекаем данные погоды (формат Open-Meteo)
        current = weather_data['current']
        temp = round(current['temperature_2m'])
        feels_like = round(current['apparent_temperature'])
        humidity = current['relative_humidity_2m']
        wind_speed = round(current['wind_speed_10m'], 1)
        pressure = round(current['pressure_msl'] * 0.75)

        # Формируем промпт для AI для утренней сводки
        weather_prompt = f"""Пришло время утренней сводки погоды для Таганрога! Вот данные:

Температура: {temp}°C (ощущается как {feels_like}°C)
Влажность: {humidity}%
Ветер: {wind_speed} м/с
Давление: {pressure} мм рт.ст.

Сделай утреннее приветствие и расскажи про погоду В СВОЕМ СТИЛЕ Чупапи - с эмодзи, прикольно, дай совет как одеться. Это утренняя рассылка, поэтому начни с приветствия!"""

        try:
            # Получаем сообщение от AI
            message = await glm_client.chat_completion(
                weather_prompt,
                system_prompt=system_persona,
                max_tokens=500,
                temperature=0.8
            )

            if not message:
                logger.error("AI не сгенерировал сообщение о погоде")
                return

            # Отправляем в каждый чат
            success_count = 0
            for chat_id in self.weather_chat_ids:
                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=message
                    )
                    success_count += 1
                    logger.info(f"Погода отправлена в чат {chat_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки погоды в чат {chat_id}: {e}")

            # Обновляем дату последней отправки
            if success_count > 0:
                now = datetime.now()
                self._last_sent_date = now.strftime("%Y-%m-%d")
                logger.info(f"Погода отправлена в {success_count}/{len(self.weather_chat_ids)} чатов")

        except Exception as e:
            logger.error(f"Ошибка при генерации/отправке погоды: {e}")

    async def run(self, application: Application):
        """
        Основной цикл планировщика
        Запускается как фоновая задача
        """
        if not self.weather_chat_ids:
            logger.info("Планировщик погоды не запущен: нет настроенных чатов")
            return

        self._running = True
        logger.info(f"Планировщик погоды запущен. Время отправки: {self.send_time}")
        logger.info(f"Чаты для отправки: {self.weather_chat_ids}")

        while self._running:
            try:
                # Проверяем каждую секунду
                await asyncio.sleep(1)

                # Проверяем, пора ли отправить погоду
                if self._should_send_weather():
                    await self.send_weather_to_chats(application, self.glm_client, self.system_persona)

            except Exception as e:
                logger.error(f"Ошибка в цикле планировщика: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке

    def stop(self):
        """Останавливает планировщик"""
        self._running = False
        logger.info("Планировщик погоды остановлен")
