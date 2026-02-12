import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class KnowledgeManager:
    """Менеджер знаний для обучения бота"""

    MAX_FACTS = 5500  # Максимальное количество сохранённых фактов

    def __init__(self, data_file: str = "bot_knowledge.json"):
        self.data_file = data_file
        self.facts: Dict[str, List[Dict]] = {}
        self.user_info: Dict[int, Dict] = {}  # Персональная информация по user_id
        self.behavioral_rules: Dict[int, List[Dict]] = {}  # Поведенческие правила по chat_id
        self.load_knowledge()

    def load_knowledge(self):
        """Загрузка знаний из файла"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.facts = data.get('facts', {})
                    self.user_info = data.get('user_info', {})
                    # Загружаем поведенческие правила, конвертируя ключи обратно в int
                    behavioral_rules_raw = data.get('behavioral_rules', {})
                    self.behavioral_rules = {int(k): v for k, v in behavioral_rules_raw.items()}
            except Exception as e:
                print(f"Ошибка загрузки знаний: {e}")
                self.facts = {}
                self.user_info = {}
                self.behavioral_rules = {}

    def save_knowledge(self):
        """Сохранение знаний в файл"""
        try:
            data = {
                'facts': self.facts,
                'user_info': self.user_info,
                'behavioral_rules': self.behavioral_rules,
                'last_updated': datetime.now().isoformat(),
                'total_facts': self.get_total_count()
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения знаний: {e}")

    def get_total_count(self) -> int:
        """Получить общее количество фактов"""
        return sum(len(facts) for facts in self.facts.values())

    def cleanup_old_facts(self):
        """Удалить самые старые факты при достижении лимита"""
        total = self.get_total_count()

        if total > self.MAX_FACTS:
            # Собираем все факты с датами
            all_facts = []
            for key, fact_list in self.facts.items():
                for fact in fact_list:
                    all_facts.append({
                        'key': key,
                        'fact': fact,
                        'timestamp': fact.get('timestamp', '')
                    })

            # Сортируем по дате (самые старые первые)
            all_facts.sort(key=lambda x: x['timestamp'])

            # Удаляем самые старые факты
            to_remove = total - self.MAX_FACTS
            removed = 0

            for item in all_facts:
                if removed >= to_remove:
                    break

                key = item['key']
                fact_to_remove = item['fact']

                if key in self.facts and fact_to_remove in self.facts[key]:
                    self.facts[key].remove(fact_to_remove)
                    if not self.facts[key]:
                        del self.facts[key]
                    removed += 1

            print(f"Удалено {removed} старых фактов для соблюдения лимита")
            self.save_knowledge()

    def add_fact(self, key: str, fact: str, user_id: int, username: str = None):
        """
        Добавить новый факт

        Args:
            key: Ключевое слово или фраза для поиска
            fact: Сам факт или информация
            user_id: ID пользователя, который добавил факт
            username: Имя пользователя
        """
        key = key.lower().strip()

        if key not in self.facts:
            self.facts[key] = []

        fact_data = {
            'fact': fact,
            'added_by': user_id,
            'username': username,
            'timestamp': datetime.now().isoformat()
        }

        # Добавляем факт (дубликаты тоже сохраняем)
        self.facts[key].append(fact_data)

        # Проверяем лимит и удаляем старые при необходимости
        self.cleanup_old_facts()

        self.save_knowledge()
        return True

    def add_raw_message(self, message: str, user_id: int, username: str = None):
        """
        Добавить необработанное сообщение

        Args:
            message: Текст сообщения
            user_id: ID пользователя
            username: Имя пользователя
        """
        # Используем первые слова как ключ
        words = message.split()[:5]
        key = ' '.join(words).lower()

        return self.add_fact(key, message, user_id, username)

    def get_fact(self, key: str) -> Optional[str]:
        """Получить факт по ключу"""
        key = key.lower().strip()

        if key in self.facts and self.facts[key]:
            # Возвращаем самый свежий факт
            return self.facts[key][-1]['fact']

        # Пытаемся найти частичное совпадение
        for k, facts in self.facts.items():
            if key in k or k in key:
                return facts[-1]['fact']

        return None

    def search_facts(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск фактов по запросу с ранжированием по релевантности
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список словарей с ключами, фактами и релевантностью
        """
        query = query.lower().strip()
        results = []

        for key, facts in self.facts.items():
            key_lower = key.lower()
            relevance = 0
            
            # Точное совпадение ключа
            if query == key_lower:
                relevance = 100
            # Ключ содержит запрос
            elif query in key_lower:
                relevance = 50
            # Запрос содержит ключ
            elif key_lower in query:
                relevance = 30
            
            # Проверяем совпадения в фактах
            for fact in facts:
                fact_text = fact.get('fact', '').lower()
                if query in fact_text:
                    relevance += 10
            
            if relevance > 0:
                results.append({
                    'key': key,
                    'facts': facts,
                    'relevance': relevance
                })

        # Сортируем по релевантности
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results[:limit]

    def get_all_facts(self) -> Dict[str, List[Dict]]:
        """Получить все факты"""
        return self.facts

    def delete_fact(self, key: str, user_id: int) -> bool:
        """Удалить факт (только для администраторов или автора)"""
        key = key.lower().strip()

        if key in self.facts:
            # Проверяем, является ли пользователь автором
            for fact in self.facts[key]:
                if fact['added_by'] == user_id:
                    self.facts[key].remove(fact)
                    if not self.facts[key]:
                        del self.facts[key]
                    self.save_knowledge()
                    return True

        return False

    def get_context_for_prompt(self, query: str = "") -> str:
        """Получить контекст из фактов для добавления в промпт
        
        Args:
            query: Поисковый запрос для фильтрации релевантных фактов
        """
        if not self.facts:
            return ""

        # Собираем все факты и сортируем по времени
        all_facts = []
        for key, fact_list in self.facts.items():
            for fact in fact_list[-3:]:  # Берем последние 3 для каждого ключа
                all_facts.append({
                    'key': key,
                    'fact': fact,
                    'relevance': 0
                })

        # Если есть запрос, ищем релевантные факты
        if query:
            query_lower = query.lower()
            for item in all_facts:
                key_lower = item['key'].lower()
                fact_text_lower = item['fact']['fact'].lower()
                
                # Подсчитываем релевантность
                relevance = 0
                for word in query_lower.split():
                    if len(word) > 2:  # Игнорируем короткие слова
                        if word in key_lower:
                            relevance += 3  # Ключ более важен
                        if word in fact_text_lower:
                            relevance += 1
                
                item['relevance'] = relevance
            
            # Сортируем по релевантности, затем по времени
            all_facts.sort(key=lambda x: (x['relevance'], x['fact'].get('timestamp', '')), reverse=True)
            # Берем топ 50 релевантных + 50 последних
            relevant_facts = [f for f in all_facts if f['relevance'] > 0][:50]
            recent_facts = sorted(all_facts, key=lambda x: x['fact'].get('timestamp', ''), reverse=True)[:50]
            
            # Объединяем и убираем дубликаты
            combined = {id(f): f for f in relevant_facts + recent_facts}
            facts_to_show = list(combined.values())[:100]
        else:
            # Сортируем по времени (самые свежие первые)
            all_facts.sort(key=lambda x: x['fact'].get('timestamp', ''), reverse=True)
            facts_to_show = all_facts[:100]

        if not facts_to_show:
            return ""

        context = "\n\n=== ВАЖНО: СОХРАНЕННЫЕ ФАКТЫ И ПАМЯТЬ ===\n"
        context += "Ниже находится информация, которую пользователи СПЕЦИАЛЬНО попросили тебя запомнить через команду /learn.\n"
        context += "ТЫ ОБЯЗАН использовать эти факты при ответах на вопросы!\n"
        context += "Если пользователь спрашивает о чем-то из этого списка - отвечай на основе ЭТИХ данных.\n\n"

        # Группируем по ключам для лучшей читаемости
        facts_by_key = {}
        for item in facts_to_show:
            key = item['key']
            if key not in facts_by_key:
                facts_by_key[key] = []
            facts_by_key[key].append(item['fact'])

        for key, fact_list in facts_by_key.items():
            context += f"📌 Ключ: '{key}'\n"
            for fact in fact_list:
                username = fact.get('username', 'Unknown')
                timestamp = fact.get('timestamp', '')[:10]
                fact_text = fact['fact']
                context += f"   └─ [{timestamp}] @{username}: {fact_text}\n"
            context += "\n"

        context += "=== КОНЕЦ СОХРАНЕННЫХ ФАКТОВ ===\n"
        return context

    def save_user_info(self, user_id: int, info_type: str, value: str, username: str = None):
        """
        Сохранить персональную информацию о пользователе

        Args:
            user_id: ID пользователя
            info_type: Тип информации (name, age, city, etc.)
            value: Значение
            username: Имя пользователя
        """
        if user_id not in self.user_info:
            self.user_info[user_id] = {}

        self.user_info[user_id][info_type] = {
            'value': value,
            'username': username,
            'timestamp': datetime.now().isoformat()
        }

        self.save_knowledge()
        return True

    def get_user_info(self, user_id: int) -> Dict:
        """Получить всю информацию о пользователе"""
        return self.user_info.get(user_id, {})

    def get_user_name(self, user_id: int) -> Optional[str]:
        """Получить имя пользователя для обращения"""
        if user_id in self.user_info and 'name' in self.user_info[user_id]:
            return self.user_info[user_id]['name']['value']
        return None

    def get_user_context(self, user_id: int) -> str:
        """Получить контекст о пользователе для промпта"""
        if user_id not in self.user_info:
            return ""

        info = self.user_info[user_id]
        context_parts = []

        for info_type, data in info.items():
            type_names = {
                'name': 'Имя',
                'age': 'Возраст',
                'city': 'Город',
                'work': 'Работа',
                'hobby': 'Хобби',
                'favorite_food': 'Любимая еда',
                'favorite_music': 'Любимая музыка',
                'favorite_movie': 'Любимый фильм'
            }

            type_name = type_names.get(info_type, info_type)
            context_parts.append(f"{type_name}: {data['value']}")

        if context_parts:
            return "\nИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:\n" + "\n".join(f"  - {p}" for p in context_parts)

        return ""


    def get_stats(self) -> Dict:
        """Получить статистику по знаниям"""
        total_facts = self.get_total_count()
        top_contributors = {}

        for facts in self.facts.values():
            for fact in facts:
                user_id = fact['added_by']
                username = fact.get('username', f'User_{user_id}')
                if username not in top_contributors:
                    top_contributors[username] = 0
                top_contributors[username] += 1

        # Сортируем по количеству добавленных фактов
        top_contributors = sorted(
            top_contributors.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'total_keys': len(self.facts),
            'total_facts': total_facts,
            'max_facts': self.MAX_FACTS,
            'usage_percent': round((total_facts / self.MAX_FACTS) * 100, 2),
            'top_contributors': top_contributors
        }

    def add_behavioral_rule(self, chat_id: int, rule: str, user_id: int, username: str = None) -> bool:
        """Добавить поведенческое правило для чата
        
        Args:
            chat_id: ID чата
            rule: Текст правила (например, 'начинай сообщения со слов Абудаби')
            user_id: ID пользователя, который добавил правило
            username: Имя пользователя
            
        Returns:
            True если правило добавлено успешно
        """
        if chat_id not in self.behavioral_rules:
            self.behavioral_rules[chat_id] = []
        
        rule_data = {
            'rule': rule,
            'added_by': user_id,
            'username': username,
            'timestamp': datetime.now().isoformat(),
            'active': True
        }
        
        self.behavioral_rules[chat_id].append(rule_data)
        self.save_knowledge()
        return True
    
    def get_behavioral_rules(self, chat_id: int) -> List[Dict]:
        """Получить активные поведенческие правила для чата
        
        Args:
            chat_id: ID чата
            
        Returns:
            Список активных правил
        """
        if chat_id not in self.behavioral_rules:
            return []
        
        # Возвращаем только активные правила
        return [rule for rule in self.behavioral_rules[chat_id] if rule.get('active', True)]
    
    def remove_behavioral_rule(self, chat_id: int, rule_index: int) -> bool:
        """Удалить поведенческое правило
        
        Args:
            chat_id: ID чата
            rule_index: Индекс правила (начиная с 0)
            
        Returns:
            True если правило удалено успешно
        """
        if chat_id not in self.behavioral_rules:
            return False
        
        if 0 <= rule_index < len(self.behavioral_rules[chat_id]):
            self.behavioral_rules[chat_id][rule_index]['active'] = False
            self.save_knowledge()
            return True
        
        return False
    
    def get_behavioral_context(self, chat_id: int) -> str:
        """Получить контекст с поведенческими правилами для промпта
        
        Args:
            chat_id: ID чата
            
        Returns:
            Строка с правилами для добавления в промпт
        """
        rules = self.get_behavioral_rules(chat_id)
        
        if not rules:
            return ""
        
        context = "\n\n=== КРИТИЧЕСКИ ВАЖНО: ПОВЕДЕНЧЕСКИЕ ПРАВИЛА ===\n"
        context += "Пользователи ПРИКАЗАЛИ тебе следовать этим правилам при КАЖДОМ ответе:\n\n"
        
        for i, rule_data in enumerate(rules, 1):
            rule = rule_data['rule']
            username = rule_data.get('username', 'Unknown')
            timestamp = rule_data.get('timestamp', '')[:10]
            context += f"{i}. [{timestamp}] @{username} приказал: {rule}\n"
        
        context += "\nТЫ ОБЯЗАН СЛЕДОВАТЬ ЭТИМ ПРАВИЛАМ В КАЖДОМ СВОЕМ ОТВЕТЕ!\n"
        context += "=== КОНЕЦ ПОВЕДЕНЧЕСКИХ ПРАВИЛ ===\n"
        
        return context
