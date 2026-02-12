import asyncio
from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager

async def test_ya_bug():
    print("=== TESTING 'Я' (I AM) HANDLING ===")
    
    km = KnowledgeManager()
    smart_ai = SmartLocalAI(km)
    user_id = 123
    username = "TestUser"
    
    test_cases = [
        "Я Дима",
        "Я из Москвы",
        "Я работаю программистом",
        "Я люблю пиццу",
        "я",
        "ясно",
        "яблоко"
    ]
    
    for text in test_cases:
        print(f"\nProcessing: '{text}'")
        
        # 1. Проверяем интенты
        intent = smart_ai.detect_conversational_intent(text)
        print(f"Intent: {intent}")
        
        # 2. Проверяем сущности
        entities = smart_ai.extract_entities(text)
        print(f"Entities: {entities}")
        
        # 3. Проверяем локальный ответ
        resp, conf = smart_ai.generate_smart_response(text, user_id, username)
        print(f"Smart Response: {resp} (Confidence: {conf})")
        
        if intent == 'greeting' and text.lower().startswith('я'):
            print("❌ BUG detected: 'я' classified as greeting!")
        elif entities:
            print(f"✅ Fact extracted: {entities}")
        else:
            print("ℹ️ No specific local action, will go to GLM (correct behavior for generic 'я ...')")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(test_ya_bug())
