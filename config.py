import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# GLM settings
GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_API_URL = os.getenv("GLM_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions")

# Weather API - Open-Meteo (бесплатный, не требует ключа)
# Оставляем переменную для обратной совместимости, но она больше не используется
YANDEX_WEATHER_API_KEY = os.getenv("YANDEX_WEATHER_API_KEY", "")
WEATHER_API_KEY = YANDEX_WEATHER_API_KEY

# Чаты для ежедневной отправки погоды (через запятую)
WEATHER_CHAT_IDS = [
    int(chat_id.strip()) for chat_id in os.getenv("WEATHER_CHAT_IDS", "").split(",")
    if chat_id.strip()
] if os.getenv("WEATHER_CHAT_IDS") else []

# Время отправки погоды (по умолчанию 8:00)
WEATHER_SEND_TIME = os.getenv("WEATHER_SEND_TIME", "08:00")

# Список разрешенных чатов (через запятую)
ALLOWED_CHAT_IDS = [
    int(chat_id.strip()) for chat_id in os.getenv("ALLOWED_CHAT_IDS", "").split(",")
    if chat_id.strip()
] if os.getenv("ALLOWED_CHAT_IDS") else None

# Настройки модели
DEFAULT_MODEL = os.getenv("GLM_MODEL", "glm-4.6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
