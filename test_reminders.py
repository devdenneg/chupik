#!/usr/bin/env python3
"""
Простой тест системы напоминаний
"""
import asyncio
import sys
sys.path.insert(0, '/Users/negodyaev-dn/Documents/bot')

from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager

# Инициализация
km = KnowledgeManager()
ai = SmartLocalAI(km)

# Тестовые запросы
test_requests = [
    "напомни через 5 секунд",
    "напомни через 10 секунд про встречу",
    "через 15 секунд напомни позвонить",
    "поставь напоминание на 20 секунд",
    "напомни через 1 минуту",
]

print("🧪 Тестирование распознавания напоминаний:\n")

for req in test_requests:
    result = ai.detect_reminder_request(req)
    if result:
        print(f"✅ '{req}'")
        print(f"   → Секунд: {result['seconds']}, Текст: {result['text']}")
    else:
        print(f"❌ '{req}' - не распознано")
    print()

print("\n✅ Тест завершен!")
