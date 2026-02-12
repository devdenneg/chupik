import re
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math
from persona import FALLBACK_RESPONSES, SENTIMENT_RESPONSES, COMPLEX_MARKERS, SEARCH_MARKERS

class SmartLocalAI:
    """Умная локальная AI с продвинутыми алгоритмами и персоной"""

    def __init__(self, knowledge_manager):
        self.km = knowledge_manager
        
        # Состояние разговора (topic tracking)
        # {user_id: {"topic": "unknown", "last_intent": "greeting", "timestamp": ...}}
        self.conversation_states = {}

        # Классификация вопросов по типам
        self.question_patterns = {
            'who': r'\b(кто|кого|кому|кем|чей|чья)\b',
            'what': r'\b(что|чего|чему|чем|какой|какая|какое|какие)\b',
            'where': r'\b(где|куда|откуда|в каком|в какой)\b',
            'when': r'\b(когда|в какое время|во сколько)\b',
            'why': r'\b(почему|зачем|отчего|из-за чего)\b',
            'how': r'\b(как|каким образом|каким способом)\b',
            'yes_no': r'\b(это|есть|является|будет|может|можешь|ты)\s.*\?'
        }

        # Паттерны извлечения фактов
        self.extraction_patterns = {
            'name': [
                # Только явные формулировки с большой буквы или в начале предложения
                r'^(?:меня зовут|зови\s+меня)\s+([А-Я][а-яё]*)',
                r'^(?:my name is|call me)\s+([A-Z][a-z]+)',
                # Без "я" т.к. это дает слишком много ложных срабатываний
            ],
            'age': [
                r'(?:мне|я)\s+(\d+)\s+(?:год|лет)',
                r'(?:age|aged?)\s*(?:is|:)?\s*(\d+)',
                r'(\d+)\s*(?:лет|год)(?:\s+старого)?'
            ],
            'city': [
                r'(?:я из|живу в|горой|город)\s+([А-Яа-яA-Za-z\s]+)',
                r'(?:i am from|i live in)\s+([A-Za-z\s]+)'
            ],
            'work': [
                r'(?:работаю|профессия|специальность)\s+(?:как\s+)?([А-Яа-яA-Za-z\s]+)',
                r'(?:i work as|i am a)\s+([A-Za-z\s]+)'
            ],
            'likes': [
                r'(?:люблю|обожаю|нравится)\s+([А-Яа-яA-Za-z\s]+)',
                r'(?:i love|i like|my favorite)\s+([A-Za-z\s]+)'
            ]
        }

        # Шаблоны для математических выражений
        self.math_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*([\+\-\*\/x÷])\s*(\d+(?:\.\d+)?)')

        # Паттерны сентимента (упрощенные)
        self.sentiment_patterns = {
            'joy': [r'крут', r'супер', r'класс', r'радост', r'счастлив', r'кайф', r'огонь', r'успех', r'получилось'],
            'sadness': [r'груст', r'печаль', r'жаль', r'плохо', r'беда', r'уныл', r'обидно', r'слез'],
            'anger': [r'бесит', r'зло', r'ненавижу', r'черт', r'блин', r'раздраж', r'ужас', r'отстой']
        }

        self.stop_words = {
            'это', 'как', 'так', 'уже', 'был', 'была', 'быстро', 'плохо', 'хорошо', 
            'нормально', 'честно', 'просто', 'блин', 'устал', 'хочу', 'делаю', 'тоже',
            'из', 'в', 'на', 'с', 'у', 'к', 'от', 'до', 'через', 'около', 'работаю', 
            'живу', 'люблю', 'пошел', 'иду', 'вчера', 'сегодня', 'сейчас', 'здесь', 'тут'
        }

    def detect_persona_change(self, text: str) -> Tuple[Optional[str], bool]:
        """
        Определить, хочет ли пользователь сменить личность бота.
        Возвращает: (описание_личности, это_сброс)
        """
        text = text.lower().strip()
        
        # Паттерны сброса
        reset_patterns = [
            r'верни(?:сь)?\s+(?:в\s+)?(?:норм|обычн|стандарт|базов)',
            r'стань\s+(?:собой|обычным|как\s+раньше)',
            r'хватит\s+притворяться'
        ]
        
        for p in reset_patterns:
            if re.search(p, text):
                return None, True
                
        # Паттерны смены
        switch_patterns = [
            r'будь\s+([а-яА-ЯёЁ\s]+)',
            r'стань\s+([а-яА-ЯёЁ\s]+)',
            r'отвечай\s+как\s+([а-яА-ЯёЁ\s]+)',
            r'говори\s+как\s+([а-яА-ЯёЁ\s]+)',
            r'теперь\s+ты\s+([а-яА-ЯёЁ\s]+)'
        ]
        
        for p in switch_patterns:
            match = re.search(p, text)
            if match:
                persona_desc = match.group(1).strip()
                # Игнорируем слишком короткие или чисто пустые
                if len(persona_desc) > 2:
                    return persona_desc, False
                    
        return None, False

    def tokenize(self, text: str) -> List[str]:
        """Токенизация текста"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if len(t) > 2]

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Вычислить сходство двух текстов с использованием TF-IDF"""
        tokens1 = self.tokenize(text1)
        tokens2 = self.tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        all_tokens = list(set(tokens1 + tokens2))
        tf1 = {t: tokens1.count(t) / len(tokens1) for t in all_tokens}
        tf2 = {t: tokens2.count(t) / len(tokens2) for t in all_tokens}

        dot_product = sum(tf1[t] * tf2[t] for t in all_tokens)
        norm1 = math.sqrt(sum(v**2 for v in tf1.values()))
        norm2 = math.sqrt(sum(v**2 for v in tf2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def classify_question(self, text: str) -> str:
        """Классифицировать тип вопроса"""
        text_lower = text.lower()
        for q_type, pattern in self.question_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return q_type
        return 'general'

    def extract_entities(self, text: str) -> Dict[str, str]:
        """Извлечь сущности из текста"""
        entities = {}

        # Только ищем сущности если текст начинается с явного обращения к боту
        # Это предотвращает извлечение случайных имен из обычного текста
        text_start = text[:50].lower()
        is_direct_address = any(
            text_start.startswith(phrase)
            for phrase in ['меня зовут', 'зови меня', 'my name is', 'call me', 'я из', 'живу в', 'работаю', 'мне']
        )

        for entity_type, patterns in self.extraction_patterns.items():
            # Для имен - требуем явное обращение в начале
            if entity_type == 'name' and not is_direct_address:
                continue

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    # Проверка на стоп-слова и длину для имен
                    if entity_type == 'name':
                        # Игнорируем стоп-слова и короткие значения
                        if value.lower() in self.stop_words or len(value) < 2:
                            continue
                        # Имя должно начинаться с большой буквы
                        if not value[0].isupper():
                            continue
                    if value:
                        entities[entity_type] = value
                        break
        return entities

    def detect_sentiment(self, text: str) -> Optional[str]:
        """Определить сентимент сообщения"""
        text_lower = text.lower()
        for sentiment, patterns in self.sentiment_patterns.items():
            if any(re.search(p, text_lower) for p in patterns):
                return sentiment
        return None
    def track_topic(self, user_id: int, text: str, intent: Optional[str] = None):
        """Отслеживать тему разговора"""
        if user_id not in self.conversation_states:
            self.conversation_states[user_id] = {
                "topics": [],
                "last_intent": "none",
                "timestamp": datetime.now(),
                "last_greeting_time": None
            }
        
        state = self.conversation_states[user_id]
        if intent:
            state["last_intent"] = str(intent)
            if intent == 'greeting':
                state["last_greeting_time"] = datetime.now()
        state["timestamp"] = datetime.now()
        
        # Простой поиск темы по ключевым словам
        tokens = self.tokenize(text)
        if tokens:
            # Берем самое длинное слово как потенциальную тему
            potential_topic = max(tokens, key=len)
            topics = state.get("topics")
            if isinstance(topics, list):
                if potential_topic not in topics:
                    topics.append(potential_topic)
                    if len(topics) > 5:
                        topics.pop(0)

    def solve_math(self, text: str) -> Optional[str]:
        """Решить математическую задачу"""
        match = self.math_pattern.search(text)
        if match:
            try:
                n1 = match.group(1)
                op = match.group(2)
                n2 = match.group(3)
                if not n1 or not op or not n2:
                    return None
                
                num1 = float(n1)
                num2 = float(n2)

                if op == '+':
                    result = num1 + num2
                elif op == '-':
                    result = num1 - num2
                elif op in ['*', 'x', '·']:
                    result = num1 * num2
                elif op in ['/', '÷']:
                    if num2 != 0:
                        result = num1 / num2
                        if result == int(result):
                            result = int(result)
                    else:
                        return "Делить на ноль нельзя, даже мне! 🚫"
                else:
                    return None

                if isinstance(result, float) and result != int(result):
                    return f"Это легко: {num1:g} {op} {num2:g} = {result:g} 🤓"
                else:
                    return f"Изи: {int(num1)} {op} {int(num2)} = {int(result)} 😎"

            except Exception as e:
                return None
        return None

    def find_relevant_responses(self, query: str, user_id: int, limit: int = 5) -> List[Dict]:
        """Найти релевантные ответы из истории"""
        relevant = []
        all_facts = self.km.get_all_facts()

        for key, fact_list in all_facts.items():
            for fact in fact_list:
                if fact.get('added_by') == user_id:
                    continue

                message_text = fact['fact']
                similarity = self.calculate_similarity(query, message_text)

                if similarity > 0.2:
                    relevant.append({
                        'text': message_text,
                        'similarity': similarity,
                        'user': fact.get('username', 'Unknown'),
                        'timestamp': fact.get('timestamp', '')
                    })

        relevant.sort(key=lambda x: x['similarity'], reverse=True)
        return relevant[:limit]

    def detect_conversational_intent(self, text: str) -> Optional[str]:
        """Определить намерение разговора"""
        text_lower = text.lower().strip()
        # Очистка от знаков препинания для поиска ключевых слов
        clean_text = re.sub(r'[^\w\s]', '', text_lower)
        tokens = set(clean_text.split())

        # Приветствия - только если это явное приветствие
        # ИСПРАВЛЕНО: убраны короткие слова которые могут быть частью других слов
        first_word = clean_text.split()[0] if clean_text.split() else ""
        greeting_words = ['привет', 'здравствуй', 'здравствуйте', 'хай', 'хаю', 'дарова', 'салют', 'йоу', 'здарова']

        # Проверяем только если:
        # 1. Первое слово - приветствие
        # 2. ИЛИ это одно слово и оно точно приветствие (не часть другого слова)
        if first_word in greeting_words:
            return 'greeting'

        # Для коротких приветствий проверяем точное совпадение
        if len(tokens) == 1:
            short_greetings = ['привет', 'хай', 'салют', 'йоу', 'дарова', 'здарова']
            if any(w == token for token in tokens for w in short_greetings):
                return 'greeting'
        
        # Прощания
        if any(w in tokens for w in ['пока', 'прощай', 'бб', 'сладких', 'сновидений']):
            return 'farewell'

        # Благодарность
        if any(w in tokens for w in ['спасибо', 'благодарю', 'спс', 'thx', 'от души', 'пасиб']):
            return 'gratitude'

        # Как дела
        if any(phrase in clean_text for phrase in ['как дела', 'как ты', 'как сам', 'че как', 'как жизнь']):
            return 'how_are_you'

        # Вопрос о создателе
        if any(phrase in clean_text for phrase in ['кто твой создатель', 'кто тебя создал', 'чей ты', 'кто автор']):
            return 'creator'

        # Что ты умеешь
        if any(phrase in clean_text for phrase in ['что умеешь', 'что ты можешь', 'твои функции', 'че умеешь']):
            return 'capabilities'

        # Шутка
        if any(w in tokens for w in ['шутка', 'анекдот', 'пошути', 'рассмеши', 'прикол']):
            return 'joke'

        # Скука
        if any(phrase in clean_text for phrase in ['скучно', 'мне скучно', 'нечем заняться']):
            return 'boredom'

        # Кто ты
        if any(phrase in clean_text for phrase in ['кто ты', 'ты кто', 'как тебя зовут', 'твое имя']):
            if 'кто я' not in clean_text:
                return 'bot_identity'
            
        return None

    def get_user_contextual_response(self, user_id: int, intent: str) -> Optional[str]:
        """Получить контекстный ответ для пользователя, используя FALLBACK_RESPONSES"""
        user_name = self.km.get_user_name(user_id) or "друг"
        
        # Если такого интента нет в наших шаблонах (например, farewell нет в импортированном), добавим дефолт
        responses = FALLBACK_RESPONSES.get(intent)
        
        if not responses:
            return None

        response = random.choice(responses)
        return response.format(name=user_name)

    def generate_smart_response(self, message: str, user_id: int, username: str = None) -> Tuple[str, float]:
        """
        Сгенерировать умный ответ локально
        Returns: (ответ, уверенность)
        """
        message_lower = message.lower().strip()

        # 1. Сентимент/Эмоции (всегда в приоритете)
        sentiment = self.detect_sentiment(message)
        if sentiment:
            user_name = self.km.get_user_name(user_id) or "друг"
            responses = SENTIMENT_RESPONSES.get(sentiment)
            if responses:
                # Если сообщение короткое (эмоция), уверенность выше
                confidence = 0.85 if len(message_lower.split()) < 4 else 0.4
                res = random.choice(responses).format(name=user_name)
                # Добавляем "человечности" (опечатки или казуальность)
                if random.random() < 0.1: # 10% шанс на опечатку в конце
                    res = res[:-1] + (res[-1] * 2) if res[-1].isalpha() else res
                return res, confidence

        # 2. Математика
        math_result = self.solve_math(message)
        if math_result:
            return math_result, 1.0

        # 3. Интент (Приветствие, как дела и т.д.)
        intent = self.detect_conversational_intent(message)
        if intent:
            if intent == 'greeting':
                state = self.conversation_states.get(user_id)
                if isinstance(state, dict):
                    last_greet = state.get("last_greeting_time")
                    if isinstance(last_greet, datetime):
                        diff = (datetime.now() - last_greet).total_seconds()
                        if diff < 1800: # 30 минут кулдаун на приветствие
                            return "", 0.0 

            self.track_topic(user_id, message, intent)
            response = self.get_user_contextual_response(user_id, intent)
            if response:
                return response, 0.95

        # 4. Извлечение и сохранение инфо о пользователе
        entities = self.extract_entities(message)
        if entities:
            username_display = username or f"User_{user_id}"
            user_name = self.km.get_user_name(user_id) or "друг"

            if 'name' in entities:
                name = entities['name']
                # Дополнительная проверка: имя должно быть разумной длины и не содержать много цифр
                digit_count = sum(1 for char in name if char.isdigit())
                if len(name) >= 2 and len(name) <= 30 and digit_count <= 2:
                    existing_name = self.km.get_user_name(user_id)
                    # Запоминаем только если имя еще не сохранено или если это другое имя
                    if not existing_name or existing_name.lower() != name.lower():
                        self.km.save_user_info(user_id, 'name', name, username_display)
                        return f"Приятно познакомиться, {name}! 👋 Запомнил!", 0.95

            # Сохраняем другие сущности (город, работа и т.д.)
            for entity_type, value in entities.items():
                if entity_type != 'name':  # Имя уже обработано выше
                    self.km.save_user_info(user_id, entity_type, value, username_display)

            if 'age' in entities:
                return f"Ого, {entities['age']}! {user_name}, крутой возраст! 😊", 0.9
            elif 'city' in entities:
                return f"{entities['city']}? {user_name}, слышал, там красиво! 🏙", 0.9
            elif 'likes' in entities:
                return f"Ммм, {entities['likes']}... {user_name}, у тебя хороший вкус! 😋", 0.9

        # 5. Поиск похожих ответов в истории (цитирование)
        relevant = self.find_relevant_responses(message, user_id)
        if isinstance(relevant, list) and len(relevant) > 0:
            best = relevant[0]
            if isinstance(best, dict) and best.get('similarity', 0) > 0.45:
                user_name = self.km.get_user_name(user_id) or "Слушай"
                at_user = best.get('user', 'Unknown')
            
                # Разнообразим и добавим "личности"
                templates = [
                    f"Помню, @{at_user} говорил: \"{best['text'][:100]}...\"",
                    f"Кажется, @{at_user} уже упоминал это: \"{best['text'][:100]}...\"",
                    f"{user_name}, вот что я нашел в памяти от @{at_user}: \"{best['text'][:100]}...\"",
                    f"Ага! Вспомнил слова @{at_user}: \"{best['text'][:100]}...\" 🧐"
                ]
                return random.choice(templates), 0.7

        # 6. Вопросы о пользователе (Кто я?)
        user_info = self.km.get_user_info(user_id)
        if user_info:
            if any(p in message_lower for p in ['кто я', 'как меня зовут']):
                if 'name' in user_info:
                    return f"Ты - {user_info['name']['value']}! Я своих никогда не забываю! 😉", 1.0
                return "Мы вроде знакомы, но имя я не записал. Напомнишь?", 0.8
                
            if any(p in message_lower for p in ['откуда я', 'где я живу']):
                if 'city' in user_info:
                    return f"Слушай, ты же из города {user_info['city']['value']}! Я всё помню! 🏙", 1.0
        
        # 7. Если ничего не подошло - возвращаем низкую уверенность
        return "", 0.0

    def generate_proactive_hook(self, history: List[Dict]) -> Optional[str]:
        """Сгенерировать живой и неожиданный вопрос или комментарий для оживления беседы"""
        if not history:
            return None

        # Собираем активных пользователей
        users = list(set([m.get('sender', 'Unknown') for m in history if m['role'] == 'user']))
        if not users:
            return None
        
        target_user = random.choice(users)
        users_list = ", ".join([f"@{u}" for u in users[:3]])
        
        all_text = " ".join([m['content'] for m in history if m['role'] == 'user'])
        tokens = [t for t in self.tokenize(all_text) if t not in self.stop_words]
        
        if not tokens:
            return None

        # Топ ключевое слово
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        main_topic = sorted_freq[0][0]

        # Типы хуков
        hook_types = ['question', 'memory', 'pivot', 'short_comment']
        weights = [0.4, 0.2, 0.2, 0.2]
        hook_type = random.choices(hook_types, weights=weights)[0]

        if hook_type == 'question':
            questions = [
                f"Слушайте, а что вы реально думаете про {main_topic}? 😉",
                f"@{target_user}, а как тебе вообще {main_topic}? Есть мысли?",
                f"Кстати, {main_topic} — это же реально база или кринж? Что скажете?",
                f"Интересно про {main_topic}... А как это влияет на вашу жизнь? 🤔"
            ]
            return random.choice(questions)

        elif hook_type == 'memory':
            # Пытаемся вспомнить что-то связанное с топиком из базы знаний (упрощенно)
            return f"Хм, {main_topic}... Помню, кто-то тут обмолвился про что-то похожее. Совпадение? 😉"

        elif hook_type == 'pivot':
            pivots = [
                "Так, с этим понятно. А что там по планам на выхи? 🍻",
                "Ладненько, проехали. Есть новости поинтереснее? 🔥",
                "Кстати, а вы видели, что сейчас в трендах? Обсудим?",
                f"Ладно, {main_topic} — это круто, но я тут подумал о другом..."
            ]
            return random.choice(pivots)

        else: # short_comment
            sentiments = [self.detect_sentiment(m['content']) for m in history if m['role'] == 'user']
            sent_counts = {s: sentiments.count(s) for s in set(sentiments) if s}
            dominant = max(sent_counts, key=lambda k: sent_counts[k]) if sent_counts else 'neutral'
            
            comments = {
                'joy': [f"Радует ваш движ! {users_list}, вы огонь! 🔥", "Позитивно тут у вас! ✨"],
                'sadness': ["Что-то грустно стало... Ребят, всё будет ок! 🫂", "Не кисните! 😉"],
                'anger': ["Ух, жара! Поспокойнее, ребят. 😤", "Давайте без агрессии, мир-дружба! ✌️"],
                'neutral': [f"Вижу, {main_topic} вас не отпускает! 😎", "Интересно наблюдать за вами..."]
            }
            return random.choice(comments.get(dominant, comments['neutral']))
