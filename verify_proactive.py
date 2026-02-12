import asyncio
import random
from history_manager import HistoryManager
from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager

async def test_proactive_hooks():
    print("=== TESTING PROACTIVE ENLIVENER ===")
    
    km = KnowledgeManager()
    smart_ai = SmartLocalAI(km)
    hm = HistoryManager(max_history=10, expiration_minutes=20)
    chat_id = 777
    
    # Имитируем диалог про пиццу
    messages = [
        ("User1", "Привет, как дела?"),
        ("User2", "Норм, вот думаю пиццу заказать"),
        ("User1", "О, какую?"),
        ("User2", "Наверное пепперони, она классика"),
        ("User1", "А мне больше нравится с грибами"),
        ("User2", "Грибы это скучно, пепперони топ!"),
        ("User1", "Сам ты скучный, грибы это жизнь")
    ]
    
    for sender, text in messages:
        hm.add_message(chat_id, "user", text, sender)
        
    print(f"\nMessages in history: {len(hm.get_history(chat_id))}")
    
    # Проверяем вмешательство (ставим вероятность 1.0 для теста)
    if hm.should_intervene(chat_id, probability=1.0, min_delay=5):
        print("✅ Intervention triggered!")
        history = hm.get_history(chat_id)
        
        # Генерируем несколько разных хуков для проверки разнообразия
        print("\nGenerating 5 different hooks to check variety:")
        for i in range(5):
            hook = smart_ai.generate_proactive_hook(history)
            print(f"Hook {i+1}: {hook}")
            
        print("\n✅ Verification of hook generation complete!")
    else:
        print("❌ Intervention NOT triggered!")

if __name__ == "__main__":
    asyncio.run(test_proactive_hooks())
