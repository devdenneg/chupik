import json
import os
from typing import Dict

class SettingsManager:
    """Менеджер настроек бота для различных чатов"""
    
    def __init__(self, settings_file: str = "bot_settings.json"):
        self.settings_file = settings_file
        self.settings: Dict[str, Dict] = self._load_settings()
        
    def _load_settings(self) -> Dict:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_chat_settings(self, chat_id: int) -> Dict:
        chat_id_str = str(chat_id)
        if chat_id_str not in self.settings:
            # Дефолтные настройки
            self.settings[chat_id_str] = {
                "response_style": "concise",
                "intervention_level": "low",  # По умолчанию низкая активность, чтобы не спамить
                "proactive_hooks": True,
                "silence_revival": True,
                "silence_timeout": 45, # минут (увеличено до 45, чтобы не часто вмешивался)
                "custom_persona": None
            }
            self._save_settings()
        return self.settings[chat_id_str]

    def update_setting(self, chat_id: int, key: str, value):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.settings:
            self.get_chat_settings(chat_id)
        
        self.settings[chat_id_str][key] = value
        self._save_settings()

    def get_intervention_params(self, chat_id: int) -> Dict:
        settings = self.get_chat_settings(chat_id)
        level = settings.get("intervention_level", "medium")

        # Настроены так, чтобы бот не спамил, но изредка оживлял беседу
        mapping = {
            "none": {"probability": 0.0, "min_delay": 9999},
            "low": {"probability": 0.03, "min_delay": 15},     # Очень редко, минимум 15 сообщений
            "medium": {"probability": 0.08, "min_delay": 10},  # Иногда, минимум 10 сообщений
            "high": {"probability": 0.15, "min_delay": 7}      # Чаще, минимум 7 сообщений
        }

        return mapping.get(level, mapping["medium"])
