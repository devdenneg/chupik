import logging
from smart_ai import SmartLocalAI
from knowledge_manager import KnowledgeManager
from bot import is_complex_task, needs_web_search

# Mock setup
logging.basicConfig(level=logging.INFO)
km = KnowledgeManager("bot_knowledge.json")
ai = SmartLocalAI(km)

def test_local_ai(text, user_id=123, username="Tester"):
    print(f"\n--- Testing: '{text}' ---")
    
    # 1. Routing check
    is_search = needs_web_search(text)
    is_complex = is_complex_task(text)
    print(f"Routing: Search={is_search}, Complex={is_complex}")
    
    # 2. Local AI Generation
    response, confidence = ai.generate_smart_response(text, user_id, username)
    print(f"Local AI: Confidence={confidence}, Response='{response}'")
    
    # 3. Decision simulation
    if is_search:
        print("Decision: -> WEB SEARCH (GLM)")
    elif is_complex:
        print("Decision: -> COMPLEX TASK (GLM)")
    elif confidence > 0.8:
        print("Decision: -> LOCAL AI (Fast)")
    else:
        print("Decision: -> GLM (Chat Fallback)")

print("=== VERIFICATION STARTED ===")

# Test Cases
tests = [
    "Привет, как дела?",
    "Привет!", # Это должно сработать как cooldown
    "Я купил хлеб", # Не должно быть приветствия (ку)
    "Я так сегодня устал", # Не должно быть знакомства (я)
    "Меня зовут Дмитрий", # Должно быть знакомство
    "Кто твой создатель?",
    "Что ты умеешь?",
    "Развлеки меня", # Скука
    "Пошути", # Шутка
    "Кто я?",
]

for t in tests:
    test_local_ai(t)
    
print("\n=== VERIFICATION FINISHED ===")
