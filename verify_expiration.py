import asyncio
from history_manager import HistoryManager
from datetime import datetime, timedelta
import time

async def test_expiration():
    print("=== TESTING CONTEXT EXPIRATION ===")
    
    # Ставим 1 минуту для теста
    hm = HistoryManager(max_history=10, expiration_minutes=1)
    chat_id = 999
    
    print("\n1. Adding message...")
    hm.add_message(chat_id, "user", "Первое сообщение", "User1")
    history = hm.get_history(chat_id)
    print(f"History size: {len(history)}")
    assert len(history) == 1
    
    print("\n2. Waiting 65 seconds (simulating 1+ minute inactivity)...")
    # Манипулируем временем для быстрого теста
    hm.last_interactions[chat_id] = datetime.now() - timedelta(seconds=70)
    
    print("Checking history after 'inactivity'...")
    history_after = hm.get_history(chat_id)
    print(f"History size after expiration: {len(history_after)}")
    
    if len(history_after) == 0:
        print("✅ SUCCESS: History cleared automatically due to inactivity!")
    else:
        print("❌ FAILURE: History NOT cleared!")

    print("\n3. Testing add_message with expiration...")
    # Снова ставим старое время
    hm.add_message(chat_id, "user", "Второе сообщение", "User1")
    hm.last_interactions[chat_id] = datetime.now() - timedelta(seconds=70)
    
    # Триггерим add_message которое должно сбросить старый контекст
    hm.add_message(chat_id, "user", "Третье сообщение", "User1")
    history_final = hm.get_history(chat_id)
    print(f"History size: {len(history_final)}")
    # Должно остаться только "Третье сообщение"
    for m in history_final:
        print(f"Content: {m['content']}")
        
    if len(history_final) == 1 and history_final[0]['content'] == "Третье сообщение":
        print("✅ SUCCESS: add_message cleared old context before adding new!")
    else:
        print("❌ FAILURE: Context not cleared properly in add_message!")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_expiration())
