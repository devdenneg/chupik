import asyncio
from history_manager import HistoryManager
from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager

async def test_commentary_flow():
    km = KnowledgeManager()
    ai = SmartLocalAI(km)
    hm = HistoryManager(max_history=40)
    
    chat_id = 12345
    
    # 1. Добавляем 9 сообщений о погоде
    print("--- Sending 9 messages about weather ---")
    for i in range(9):
        hm.add_message(chat_id, "user", f"Сегодня такая солнечная погода, уже {i} раз об этом говорю!")
        triggered = hm.should_comment(chat_id)
        print(f"Msg {i+1}: Triggered={triggered}")

    # 2. 10-е сообщение
    print("\n--- Sending 10th message ---")
    hm.add_message(chat_id, "user", "Да, погода класс!")
    if hm.should_comment(chat_id):
        history = hm.get_history(chat_id)
        opinion = ai.analyze_context_locally(history)
        print(f"BOT OPINION: {opinion}")
    else:
        print("FAILED: No trigger on 10th message")

if __name__ == "__main__":
    asyncio.run(test_commentary_flow())
