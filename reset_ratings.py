#!/usr/bin/env python3
"""
Скрипт для обнуления всех рейтингов и уровней
"""
import json
import os
from datetime import datetime

def reset_ratings():
    """Обнулить все рейтинги"""
    ratings_file = "ratings.json"

    if os.path.exists(ratings_file):
        # Создаем backup перед обнулением
        backup_file = f"ratings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(ratings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Сохраняем backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ Backup создан: {backup_file}")

            # Обнуляем рейтинги
            new_data = {
                'ratings': {},
                'history': {}
            }

            with open(ratings_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            print(f"✅ Все рейтинги обнулены!")
            print(f"📊 Старые данные сохранены в: {backup_file}")

        except Exception as e:
            print(f"❌ Ошибка при обнулении: {e}")
    else:
        print(f"⚠️  Файл {ratings_file} не найден")

if __name__ == "__main__":
    print("🔄 Обнуление всех рейтингов и уровней...")
    print()

    confirm = input("❗ Вы уверены? Это удалит все рейтинги! (yes/no): ")

    if confirm.lower() in ['yes', 'y', 'да']:
        reset_ratings()
    else:
        print("❌ Операция отменена")
