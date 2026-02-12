#!/usr/bin/env python3
"""
Тест конкретной фразы пользователя
"""
import sys
sys.path.insert(0, '/Users/negodyaev-dn/Documents/bot')

from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager

# Инициализация
km = KnowledgeManager()
ai = SmartLocalAI(km)

# Тестируем конкретную фразу пользователя
test_phrase = "Чупик, напомни через 10 секунд что Юра гей"

print(f"🧪 Тестирование фразы: '{test_phrase}'\n")

result = ai.detect_reminder_request(test_phrase)

if result:
    print(f"✅ РАСПОЗНАНО!")
    print(f"   Секунд: {result['seconds']}")
    print(f"   Количество: {result['amount']}")
    print(f"   Единица: {result['unit']}")
    print(f"   Текст напоминания: '{result['text']}'")
else:
    print(f"❌ НЕ РАСПОЗНАНО")
    print(f"\nПопробуем понять почему...")
    
    # Тестируем упрощенные варианты
    variants = [
        "напомни через 10 секунд что Юра гей",
        "напомни через 10 секунд про Юра гей",
        "напомни через 10 секунд Юра гей",
    ]
    
    for variant in variants:
        res = ai.detect_reminder_request(variant)
        status = "✅" if res else "❌"
        print(f"{status} '{variant}'")
        if res:
            print(f"    → Текст: '{res['text']}'")
