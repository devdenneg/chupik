import httpx
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GLMClient:
    """Клиент для работы с GLM API (ZhipuAI / ChatGLM)"""

    def __init__(self, api_key: str, api_url: str, model: str = "glm-4"):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Optional[str]:
        """
        Отправить запрос к GLM API

        Args:
            messages: Список сообщений в формате [{"role": "user", "content": "..."}]
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура (креативность) от 0 до 1
            stream: Потоковая передача ответа

        Returns:
            Текст ответа или None в случае ошибки
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"GLM API request to {self.api_url}")
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                logger.info(f"GLM API response status: {response.status_code}")
                response.raise_for_status()

                response_text = response.text
                logger.info(f"GLM API raw response: {response_text[:500]}")

                data = response.json()
                logger.info(f"GLM API parsed response: {data}")

                # Проверяем структуру ответа
                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0]["message"]
                    # Берем ТОЛЬКО actual content, не reasoning_content
                    content = message.get("content", "").strip()

                    logger.info(f"GLM API returned content length: {len(content)} chars")
                    return content if content else None

                logger.warning(f"GLM API response has no choices: {data}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при запросе к GLM API: {e}", exc_info=True)
            return None

    async def chat_completion_with_history(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]] = None,
        system_prompt: str = None
    ) -> Optional[str]:
        """
        Отправить запрос с историей диалога

        Args:
            user_message: Сообщение от пользователя
            chat_history: История предыдущих сообщений
            system_prompt: Системный промпт для настройки поведения

        Returns:
            Текст ответа или None в случае ошибки
        """
        messages = []

        # Добавляем системный промпт если указан
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Добавляем историю сообщений
        if chat_history:
            messages.extend(chat_history)

        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": user_message})

        return await self.chat_completion(messages)

    async def web_search(
        self,
        query: str,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Веб-поиск через GLM API

        Args:
            query: Поисковый запрос
            max_tokens: Максимальное количество токенов в ответе
            temperature: Температура (креативность) от 0 до 1

        Returns:
            Текст ответа с результатами поиска или None в случае ошибки
        """
        # Формируем промпт для веб-поиска
        search_prompt = f"""Найди информацию в интернете и ответь на вопрос: {query}

Предоставь подробный и точный ответ на основе найденной информации.
Если не можешь найти информацию, так и скажи."""

        messages = [
            {"role": "user", "content": search_prompt}
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()

                # Проверяем структуру ответа
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]

                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при поиске: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при веб-поиске: {e}", exc_info=True)
            return None
