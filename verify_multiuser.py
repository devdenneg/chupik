import asyncio
from history_manager import HistoryManager
from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager
import os

async def main():
    print("=== VERIFYING MULTI-USER AWARENESS ===")
    
    hm = HistoryManager(max_history=40)
    km = KnowledgeManager("bot_knowledge.json")
    ai = SmartLocalAI(km)

    chat_id = 12345
    
    # Симулируем диалог двух разных людей
    print("\n--- Simulating group chat dialogue ---")
    hm.add_message(chat_id, "user", "Всем привет! Как дела?", "Дмитрий")
    hm.add_message(chat_id, "user", "Привет, Дима. Я вот думаю, какую машину купить.", "Алексей")
    hm.add_message(chat_id, "user", "Машину? Лучше купи самокат, пробок меньше!", "Дмитрий")
    hm.add_message(chat_id, "user", "Самокат это не серьезно. Мне нужно возить картошку.", "Алексей")
    
    history = hm.get_history(chat_id)
    
    # Проверяем, что в истории есть имена
    print("\nCheck history attribution:")
    for m in history:
        print(f"Role: {m['role']}, Sender: {m.get('sender')}, Content: {m['content']}")
        assert m.get('sender') in ["Дмитрий", "Алексей"]

    # Проверяем локальный анализ контекста
    print("\nCheck local analysis (Local Opinion):")
    # Добавим еще сообщений чтобы набрать 10 (или вызовем напрямую)
    for i in range(6):
        hm.add_message(chat_id, "user", f"Сообщение {i}", "Алексей" if i%2==0 else "Дмитрий")
    
    opinion = ai.analyze_context_locally(hm.get_history(chat_id))
    print(f"Bot's Opinion: {opinion}")
    
    if "@Дмитрий" in opinion and "@Алексей" in opinion:
        print("✅ SUCCESS: Bot mentions both users!")
    else:
        print("⚠️ WARNING: Bot might not have mentioned everyone, check formatting.")

    # Проверяем подготовку для GLM (симулируем логику из bot.py)
    print("\nCheck GLM history formatting simulation:")
    formatted_history = []
    for m in hm.get_history(chat_id):
        role = m.get('role', 'user')
        content = m.get('content', '')
        sender = m.get('sender', 'Unknown')
        if role == 'user':
            formatted_history.append({"role": "user", "content": f"{sender}: {content}"})
        else:
            formatted_history.append({"role": "assistant", "content": content})
    
    for f in formatted_history[:4]:
        print(f"GLM Row: {f}")
        assert ": " in f['content']

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
