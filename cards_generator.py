"""
Модуль генерации карт для игры "Кафе ОАЗИС 2.0"
Генерирует 25 карт на игрока: 5 раундов × 5 карт
"""

import random
import json
from typing import List, Dict, Any, Optional

# ============================================
# БАЗА ДАННЫХ КАРТ
# ============================================

# 1. РОЛИ (с уникальными способностями)
ROLES = [
    {"name": "Шериф", "skill": "Проверка факта", "desc": "Узнаёт один случайный факт о любом игроке"},
    {"name": "Проститутка", "skill": "Соблазнение", "desc": "Узнаёт секрет одного игрока"},
    {"name": "Блогер", "skill": "Страйк", "desc": "Если кто-то голосует против → пишет в лог 'Я на тебя страйк кину!'"},
    {"name": "Инфлюенсер", "skill": "Страйк", "desc": "Если кто-то голосует против → пишет в лог 'Я на тебя страйк кину!'"},
    {"name": "Продавец мороженого", "skill": "Мороженое", "desc": "Может угостить игрока → тот теряет голос в этом раунде"},
    {"name": "Таксист", "skill": "Быстрый выезд", "desc": "Может избежать вылета 1 раз за игру"},
    {"name": "Повар", "skill": "Вкусный ужин", "desc": "Выбранный игрок получает +1 голос в свою пользу"},
    {"name": "Фокусник", "skill": "Иллюзия", "desc": "Может скрыть одну свою карту от голосования"},
    {"name": "Медиум", "skill": "Голос духов", "desc": "Узнаёт, кто голосовал против него в прошлом раунде"},
    {"name": "Клоун-убийца", "skill": "Смех", "desc": "Заставляет одного игрока смеяться → тот не может голосовать"},
    {"name": "Сантехник", "skill": "Починка", "desc": "Может починить одну жизнь себе или другому"},
    {"name": "Ютубер", "skill": "Монетизация", "desc": "Если за него голосуют → получает +1 голос в свой счёт"},
    {"name": "Доктор", "skill": "Лечение", "desc": "Восстанавливает 1 жизнь выбранному игроку"},
    {"name": "Инженер", "skill": "Баррикада", "desc": "Защищает одного игрока от вылета в этом раунде"},
    {"name": "Учёный", "skill": "Анализ", "desc": "Узнаёт профессию любого игрока"},
    {"name": "Солдат", "skill": "Огневая поддержка", "desc": "Даёт +2 голоса выбранному игроку"},
    {"name": "Разведчик", "skill": "Разведка", "desc": "Узнаёт, кто голосовал за кого в прошлом раунде"},
    {"name": "Снайпер", "skill": "Точный выстрел", "desc": "Убирает 1 голос у выбранного игрока"},
    {"name": "Сапёр", "skill": "Мина", "desc": "Если против него голосуют → голосующий теряет голос"},
    {"name": "Медик", "skill": "Полевая аптечка", "desc": "Восстанавливает 2 жизни себе"},
]

# 2. НАВЫКИ (для 1 раунда)
SKILLS = [
    "Метание ножей",
    "Игра на гитаре",
    "Взлом автоматов",
    "Теннисный удар",
    "Разговор с животными",
    "Стрельба из лука",
    "Выживание в пустыне",
    "Первая помощь",
    "Кулинария",
    "Шахматы",
    "Медитация",
    "Йога",
    "Паркур",
    "Скалолазание",
    "Плавание",
    "Бег на длинные дистанции",
    "Сила",
    "Ловкость",
    "Харизма",
    "Интеллект",
]

# 3. ОРУЖИЕ (для 2 раунда)
WEAPONS = [
    {"name": "Кольт .45", "desc": "6 патронов, надёжный"},
    {"name": "Дробовик Winchester", "desc": "Мощный, но шумный"},
    {"name": "Винтовка", "desc": "Точная, дальнобойная"},
    {"name": "Бензопила", "desc": "Громкая, страшная для зомби"},
    {"name": "Мачете", "desc": "Острое, тихое"},
    {"name": "Топор", "desc": "Тяжёлый, но эффективный"},
    {"name": "Арбалет", "desc": "Бесшумный, смертельный"},
    {"name": "Лук", "desc": "Древнее оружие, требует навыка"},
    {"name": "Кастет", "desc": "Ближний бой"},
    {"name": "Молоток", "desc": "Инструмент и оружие"},
]

# 4. ПРЕДМЕТЫ (для 2 раунда)
ITEMS = [
    {"name": "Старая фотография семьи", "desc": "Напоминание о прошлом"},
    {"name": "Фляга с виски", "desc": "Согревает в холодные ночи"},
    {"name": "Библия", "desc": "Даёт надежду"},
    {"name": "Запасные носки", "desc": "Чистые, всегда пригодятся"},
    {"name": "Компас", "desc": "Помогает не заблудиться"},
    {"name": "Карта пустыни", "desc": "Знание всех троп"},
    {"name": "Спички", "desc": "Огонь — это жизнь"},
    {"name": "Зеркальце", "desc": "Можно подавать сигналы"},
    {"name": "Нож", "desc": "Многофункциональный"},
    {"name": "Верёвка", "desc": "Всегда нужна"},
]

# 5. ФАКТЫ (для 3 раунда)
FACTS = [
    "Был лучшим стрелком в округе",
    "Никогда не пьёт виски",
    "Держит руку на кобуре",
    "Умеет читать следы",
    "Знает все тропы в пустыне",
    "Помнит имена всех погибших",
    "Боится темноты",
    "Верит в знаки",
    "Ночью не спит",
    "Нервно постукивает пальцами",
    "Всегда носит с собой монетку",
    "Умеет играть на губной гармошке",
    "Не доверяет незнакомцам",
    "Носит старый шерифский значок",
    "Боится собак",
    "Любит кофе с корицей",
    "Не умеет плавать",
    "Знает несколько языков",
]

# 6. ИСТОРИИ ИЗ ПРОШЛОГО (для 4 раунда)
HISTORIES = [
    "Потерял семью при нападении зомби",
    "Был на войне, видел ужасы",
    "Сбежал из города, охваченного зомби",
    "Потерял лучшего друга",
    "Был заключённым, но сбежал",
    "Служил в армии, был награждён",
    "Работал в морге, видел много смертей",
    "Путешествовал по миру до катастрофы",
    "Был успешным бизнесменом",
    "Играл в театре, был актёром",
    "Был учителем, любил детей",
    "Работал на нефтяной вышке",
    "Был охотником на зомби с самого начала",
    "Потерял ногу в аварии, теперь протез",
    "Спас ребёнка из горящего здания",
    "Был свидетелем первого появления зомби",
]

# 7. ПЛАНЫ НА ЖИЗНЬ (для 5 раунда)
PLANS = [
    "Мечтал открыть свой бар в Техасе",
    "Хотел стать писателем",
    "Планировал путешествовать по миру",
    "Мечтал о семье и доме",
    "Хотел научиться играть на гитаре",
    "Планировал открыть ресторан",
    "Мечтал стать миллионером",
    "Хотел покорить Эверест",
    "Планировал выучить 10 языков",
    "Мечтал о мире во всём мире",
    "Хотел стать фермером",
    "Планировал построить дом своими руками",
]

# 8. СОСТОЯНИЯ ЗДОРОВЬЯ
HEALTH_STATES = [
    {"name": "Здоров как бык", "hearts": 3},
    {"name": "Ранен (царапина)", "hearts": 2},
    {"name": "Под кайфом", "hearts": 2},
    {"name": "При смерти", "hearts": 1},
    {"name": "Не выспался", "hearts": 2},
    {"name": "Бодр", "hearts": 3},
    {"name": "Уставший", "hearts": 2},
    {"name": "Травмирован", "hearts": 1},
    {"name": "Здоров", "hearts": 3},
]

# 9. ТРАЙТЫ (характерные черты)
TRAITS = [
    "Мстителен, но справедлив",
    "Добрый и отзывчивый",
    "Циничный и саркастичный",
    "Оптимист до последнего",
    "Пессимист, но борется",
    "Любит рисковать",
    "Осторожный до паранойи",
    "Харизматичный лидер",
    "Тихий и наблюдательный",
    "Громкий и весёлый",
    "Странный, но милый",
    "Умный и хитрый",
    "Сильный и смелый",
    "Быстрый и ловкий",
    "Верный и надёжный",
]

# 10. СЕКРЕТЫ
SECRETS = [
    {"name": "Торговал с зомби", "effect": "Все будут недовольны"},
    {"name": "Убил напарника", "effect": "Больше никому не доверяют"},
    {"name": "Был информатором", "effect": "Предатель"},
    {"name": "Украл еду у других", "effect": "Недоверие"},
    {"name": "Воровал медикаменты", "effect": "Ненависть"},
    {"name": "Лгал о своей профессии", "effect": "Все разозлены"},
    {"name": "Продал друзей", "effect": "Нет друзей"},
    {"name": "Был шпионом зомби", "effect": "Полное недоверие"},
    {"name": "Спал с врагом", "effect": "Позор"},
]

# 11. СОЮЗНИКИ/ВРАГИ (для 4 раунда)
RELATIONSHIPS = [
    {"name": "Союзник: Барменша Салли", "type": "ally"},
    {"name": "Союзник: Старый шериф Боб", "type": "ally"},
    {"name": "Союзник: Доктор Эмили", "type": "ally"},
    {"name": "Враг: Грабитель Джек", "type": "enemy"},
    {"name": "Враг: Торговец зомби", "type": "enemy"},
    {"name": "Союзник: Снайпер Том", "type": "ally"},
    {"name": "Враг: Мэр города", "type": "enemy"},
    {"name": "Союзник: Инженер Марк", "type": "ally"},
    {"name": "Враг: Бандит Виктор", "type": "enemy"},
]

# 12. КАТАСТРОФЫ (общие для всех)
DISASTERS = [
    "Нападение зомби-волков",
    "Землетрясение разрушило убежище",
    "Заражение воды в колодце",
    "Пожар в кафе",
    "Нашествие зомби-птиц",
    "Обрушение крыши",
    "Грабители украли припасы",
    "Нападение диких животных",
]

# 13. БОНУСНЫЕ ЧЕРТЫ (для финального раунда)
BONUS_TRAITS = [
    "Герой дня",
    "Выживший-одиночка",
    "Легенда кафе",
    "Тот, кто никогда не сдаётся",
    "Лучший друг зомби",
    "Хранитель очага",
    "Пустынный волк",
    "Последний человек на Земле",
]


# ============================================
# ОСНОВНЫЕ ФУНКЦИИ ГЕНЕРАЦИИ
# ============================================

def get_random_role() -> Dict[str, Any]:
    """Возвращает случайную роль с её способностью"""
    return random.choice(ROLES).copy()


def get_random_skill() -> str:
    """Возвращает случайный навык"""
    return random.choice(SKILLS)


def get_random_weapon() -> Dict[str, str]:
    """Возвращает случайное оружие"""
    return random.choice(WEAPONS).copy()


def get_random_item() -> Dict[str, str]:
    """Возвращает случайный предмет"""
    return random.choice(ITEMS).copy()


def get_random_health() -> Dict[str, Any]:
    """Возвращает случайное состояние здоровья"""
    return random.choice(HEALTH_STATES).copy()


def get_random_fact() -> str:
    """Возвращает случайный факт"""
    return random.choice(FACTS)


def get_random_history() -> str:
    """Возвращает случайную историю"""
    return random.choice(HISTORIES)


def get_random_plan() -> str:
    """Возвращает случайный план на жизнь"""
    return random.choice(PLANS)


def get_random_trait() -> str:
    """Возвращает случайную черту характера"""
    return random.choice(TRAITS)


def get_random_secret() -> Dict[str, str]:
    """Возвращает случайный секрет"""
    return random.choice(SECRETS).copy()


def get_random_relationship() -> Dict[str, str]:
    """Возвращает случайного союзника или врага"""
    return random.choice(RELATIONSHIPS).copy()


def get_random_disaster() -> str:
    """Возвращает случайную катастрофу (общую)"""
    return random.choice(DISASTERS)


def get_random_bonus_trait() -> str:
    """Возвращает случайную бонусную черту"""
    return random.choice(BONUS_TRAITS)


# ============================================
# ГЕНЕРАЦИЯ КАРТ ПО РАУНДАМ
# ============================================

def generate_round_1(role: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Раунд 1: Роль + Навык + 3 черты характера
    """
    if not role:
        role = get_random_role()
    
    return [
        {
            "type": "role",
            "name": role["name"],
            "desc": role["desc"],
            "skill": role["skill"],
            "icon": "🎴",
            "round": 1,
        },
        {
            "type": "skill",
            "name": get_random_skill(),
            "desc": "Навык выживания",
            "icon": "🔪",
            "round": 1,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 1,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 1,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 1,
        },
    ]


def generate_round_2() -> List[Dict[str, Any]]:
    """
    Раунд 2: Оружие + Предмет + 3 факта
    """
    weapon = get_random_weapon()
    item = get_random_item()
    
    return [
        {
            "type": "weapon",
            "name": weapon["name"],
            "desc": weapon["desc"],
            "icon": "🔫",
            "round": 2,
        },
        {
            "type": "item",
            "name": item["name"],
            "desc": item["desc"],
            "icon": "🎒",
            "round": 2,
        },
        {
            "type": "fact",
            "name": get_random_fact(),
            "desc": "Факт о персонаже",
            "icon": "📖",
            "round": 2,
        },
        {
            "type": "fact",
            "name": get_random_fact(),
            "desc": "Факт о персонаже",
            "icon": "📖",
            "round": 2,
        },
        {
            "type": "fact",
            "name": get_random_fact(),
            "desc": "Факт о персонаже",
            "icon": "📖",
            "round": 2,
        },
    ]


def generate_round_3() -> List[Dict[str, Any]]:
    """
    Раунд 3: История из прошлого + 4 черты
    """
    return [
        {
            "type": "history",
            "name": get_random_history(),
            "desc": "Событие из прошлого",
            "icon": "📜",
            "round": 3,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 3,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 3,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 3,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 3,
        },
    ]


def generate_round_4(role_name: str = None) -> List[Dict[str, Any]]:
    """
    Раунд 4: Союзник/Враг + Здоровье + 3 черты
    """
    relation = get_random_relationship()
    
    # Если есть роль, привязываем союзника к ней
    if role_name and random.random() > 0.5:
        relation["name"] = f"Союзник: {role_name} (связь)"
    
    health = get_random_health()
    
    return [
        {
            "type": "relationship",
            "name": relation["name"],
            "desc": f"{'🤝 Союзник' if relation['type'] == 'ally' else '👹 Враг'} в прошлом",
            "icon": "🤝" if relation['type'] == 'ally' else "👹",
            "round": 4,
        },
        {
            "type": "health",
            "name": health["name"],
            "desc": f"❤️❤️❤️ Жизни: {health['hearts']}/3",
            "hearts": health["hearts"],
            "icon": "❤️",
            "round": 4,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 4,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 4,
        },
        {
            "type": "trait",
            "name": get_random_trait(),
            "desc": "Черта характера",
            "icon": "🧠",
            "round": 4,
        },
    ]


def generate_round_5() -> List[Dict[str, Any]]:
    """
    Раунд 5: План на жизнь + Секрет + 3 бонусные черты
    """
    secret = get_random_secret()
    
    return [
        {
            "type": "plan",
            "name": get_random_plan(),
            "desc": "Мечта или план на жизнь",
            "icon": "🌟",
            "round": 5,
        },
        {
            "type": "secret",
            "name": secret["name"],
            "desc": secret["effect"],
            "icon": "🤫",
            "round": 5,
        },
        {
            "type": "bonus_trait",
            "name": get_random_bonus_trait(),
            "desc": "Особая черта",
            "icon": "⭐",
            "round": 5,
        },
        {
            "type": "bonus_trait",
            "name": get_random_bonus_trait(),
            "desc": "Особая черта",
            "icon": "⭐",
            "round": 5,
        },
        {
            "type": "bonus_trait",
            "name": get_random_bonus_trait(),
            "desc": "Особая черта",
            "icon": "⭐",
            "round": 5,
        },
    ]


# ============================================
# ПОЛНАЯ ГЕНЕРАЦИЯ ПЕРСОНАЖА
# ============================================

def generate_full_character(name: str, role: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Генерирует полного персонажа с 25 картами (5 раундов × 5 карт)
    """
    if not role:
        role = get_random_role()
    
    # Получаем роль для персонажа
    character_role = role["name"]
    
    rounds = {
        1: generate_round_1(role),
        2: generate_round_2(),
        3: generate_round_3(),
        4: generate_round_4(character_role),
        5: generate_round_5(),
    }
    
    # Собираем все карты в плоский список
    all_cards = []
    for round_num in range(1, 6):
        all_cards.extend(rounds[round_num])
    
    # Состояние здоровья (берётся из 4 раунда)
    health_card = None
    for card in rounds[4]:
        if card["type"] == "health":
            health_card = card
            break
    
    health_hearts = health_card["hearts"] if health_card else 3
    
    return {
        "name": name,
        "role": character_role,
        "role_skill": role["skill"],
        "role_desc": role["desc"],
        "rounds": rounds,
        "all_cards": all_cards,
        "health": health_hearts,
        "max_health": 3,
        "revealed_cards": [],  # Карты, открытые в текущем раунде
        "cards_by_round_revealed": {
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
        },
    }


def generate_character_with_specific_role(name: str, role_name: str) -> Dict[str, Any]:
    """
    Генерирует персонажа с конкретной ролью (для тестирования)
    """
    role = next((r for r in ROLES if r["name"] == role_name), None)
    if not role:
        role = get_random_role()
    return generate_full_character(name, role)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_card_icon(card_type: str) -> str:
    """Возвращает иконку для типа карты"""
    icons = {
        "role": "🎴",
        "skill": "🔪",
        "trait": "🧠",
        "weapon": "🔫",
        "item": "🎒",
        "fact": "📖",
        "history": "📜",
        "relationship": "🤝",
        "health": "❤️",
        "plan": "🌟",
        "secret": "🤫",
        "bonus_trait": "⭐",
    }
    return icons.get(card_type, "🃏")


def get_card_emoji_for_display(card: Dict[str, Any]) -> str:
    """Возвращает эмодзи для отображения карты"""
    return card.get("icon", get_card_icon(card["type"]))


def format_card_for_display(card: Dict[str, Any]) -> str:
    """Форматирует карту для отображения в чате"""
    icon = get_card_emoji_for_display(card)
    name = card.get("name", "???")
    desc = card.get("desc", "")
    
    if desc:
        return f"{icon} **{name}** — {desc}"
    return f"{icon} **{name}**"


def get_all_cards_by_type(character: Dict[str, Any], card_type: str) -> List[Dict[str, Any]]:
    """Возвращает все карты персонажа определённого типа"""
    return [c for c in character["all_cards"] if c["type"] == card_type]


def get_full_biography(character: Dict[str, Any]) -> str:
    """Формирует полную биографию персонажа для финального экрана"""
    lines = []
    lines.append(f"📜 **ПОЛНАЯ БИОГРАФИЯ: {character['name']}**")
    lines.append("=" * 40)
    
    # Группируем по раундам
    for round_num in range(1, 6):
        cards = character["rounds"][round_num]
        if not cards:
            continue
        
        lines.append(f"\n**Раунд {round_num}:**")
        for card in cards:
            lines.append(f"  {format_card_for_display(card)}")
    
    lines.append("\n" + "=" * 40)
    lines.append(f"❤️ Здоровье: {'❤️' * character['health']}{'🖤' * (3 - character['health'])}")
    lines.append(f"🎯 Роль: {character['role']}")
    lines.append(f"⚡ Способность: {character['role_skill']}")
    
    return "\n".join(lines)


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ГЕНЕРАТОРА КАРТ")
    print("=" * 60)
    
    # Тест 1: Генерация случайного персонажа
    print("\n📋 Тест 1: Случайный персонаж")
    character = generate_full_character("Матвей")
    print(f"Персонаж: {character['name']} ({character['role']})")
    print(f"Здоровье: {character['health']}/3")
    print(f"Всего карт: {len(character['all_cards'])}")
    
    # Тест 2: Биография
    print("\n📋 Тест 2: Полная биография")
    print(get_full_biography(character))
    
    # Тест 3: Конкретная роль
    print("\n📋 Тест 3: Персонаж с ролью 'Шериф'")
    sheriff = generate_character_with_specific_role("Джон", "Шериф")
    print(f"Роль: {sheriff['role']}")
    print(f"Способность: {sheriff['role_skill']}")
    
    # Тест 4: Статистика по типам карт
    print("\n📋 Тест 4: Статистика типов карт")
    types = {}
    for card in character["all_cards"]:
        card_type = card["type"]
        types[card_type] = types.get(card_type, 0) + 1
    
    for card_type, count in types.items():
        print(f"  {card_type}: {count} карт")
    
    print("\n✅ Тестирование завершено!")