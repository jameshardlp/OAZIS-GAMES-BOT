import sys
import os
import logging
import asyncio
import json
import random
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackGame
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from dotenv import load_dotenv

# ============================================
# ИМПОРТ МОДУЛЕЙ
# ============================================

from debug_manager import (
    is_debug_enabled,
    toggle_debug,
    get_debug_status,
    log_debug,
    get_debug_panel_html,
    get_debug_js,
    get_debug_command_response,
    api_debug_status,
    init_debug
)

from cards_generator import (
    generate_full_character,
    generate_character_with_specific_role,
    format_card_for_display,
    get_full_biography,
    get_card_emoji_for_display,
    ROLES,
    get_random_disaster,
)

from game_engine import (
    GameEngine,
    GamePhase,
    PlayerStatus,
    create_game,
)

from biography_builder import (
    BiographyBuilder,
    get_player_biography,
    get_player_biography_html,
    get_final_title_sheet,
    generate_biography_preview,
)

from sound_manager import (
    SoundManager,
    SoundType,
    create_sound_manager,
)

# ============================================
# 1. ЗАГРУЖАЕМ .env ФАЙЛ
# ============================================
load_dotenv()

# ============================================
# 2. НАСТРОЙКИ ЛОГИРОВАНИЯ
# ============================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

print("=" * 60)
print("🚀 КАФЕ ОАЗИС 2.0 - БОТ ЗАПУСКАЕТСЯ!")
print("=" * 60)
print("📋 Логирование включено на уровень DEBUG")
print("=" * 60)

# ============================================
# 2.5. ИНИЦИАЛИЗАЦИЯ ОТЛАДКИ И ЗВУКОВ
# ============================================
init_debug(True)
print("📡 Модуль отладки инициализирован")

sound_manager = create_sound_manager()
print("🔊 Модуль звуков инициализирован")

# ============================================
# 3. КОНФИГУРАЦИЯ
# ============================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
PORT = int(os.getenv("PORT", 8082))

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в .env файле!")
    sys.exit(1)

if not WEBAPP_URL:
    print("❌ ОШИБКА: WEBAPP_URL не найден в .env файле!")
    sys.exit(1)

print(f"🔌 Порт: {PORT}")
print(f"🤖 Токен: ✅ Загружен из .env")
print(f"🌐 URL: {WEBAPP_URL}")
print(f"🎮 Game Short Name: oaziscaffee")

# ============================================
# 4. ИНИЦИАЛИЗАЦИЯ
# ============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
games = {}
CARDS = None

BOT_NAMES = [
    "🤖 Бот-Шериф", "🤖 Бот-Бармен", "🤖 Бот-Повар",
    "🤖 Бот-Механик", "🤖 Бот-Доктор", "🤖 Бот-Инженер",
    "🤖 Бот-Учёный", "🤖 Бот-Солдат", "🤖 Бот-Разведчик",
    "🤖 Бот-Снайпер", "🤖 Бот-Сапёр", "🤖 Бот-Медик",
    "🤖 Бот-Клоун", "🤖 Бот-Фокусник", "🤖 Бот-Таксист",
]

# ============================================
# 5. ТЕКСТЫ
# ============================================
RULES_TEXT = """📖 **ПРАВИЛА ИГРЫ «КАФЕ ОАЗИС 2.0»**

🎯 **Цель:** Выжить 5 раундов и получить симпатию других игроков!

🃏 **Карты:** Каждый раунд вы открываете по 5 новых карт:
• **Раунд 1:** Роль + Навык + 3 черты характера
• **Раунд 2:** Оружие + Предмет + 3 факта
• **Раунд 3:** История из прошлого + 4 черты
• **Раунд 4:** Союзник/Враг + Здоровье + 3 черты
• **Раунд 5:** План на жизнь + Секрет + 3 бонусные черты

❤️ **Здоровье:** У каждого 3 жизни. При вылете вы теряете 1 жизнь. 
Если жизни закончились — вы полностью выбываете.

⚡ **Способности:** У каждой роли есть уникальная способность, 
которую можно использовать 1 раз за раунд.

📜 **Финал:** В конце игры вы сможете увидеть полную биографию 
каждого игрока и проголосовать за того, кто вам нравится!

🏆 **Победа:** Игрок, набравший больше всех симпатий в финале!"""

# ============================================
# 6. ЗАГРУЗКА КАРТ
# ============================================
def load_cards():
    global CARDS
    try:
        with open('cards.json', 'r', encoding='utf-8') as f:
            CARDS = json.load(f)
            print("✅ Карты загружены из cards.json")
            return
    except:
        pass
    
    CARDS = {
        "roles": [
            {"name": "Шериф", "description": "Владеет револьвером и авторитетом", "rarity": "редкий"},
            {"name": "Продавец мороженого", "description": "Всегда носит с собой вафельный стаканчик", "rarity": "обычный"},
            {"name": "Таксист", "description": "Знает все дороги в городе", "rarity": "обычный"},
            {"name": "Инфлюенсер", "description": "Снимает всё на телефон, даже зомби", "rarity": "легендарный"},
            {"name": "Повар", "description": "Может приготовить что угодно, даже зомби-стейк", "rarity": "редкий"},
            {"name": "Фокусник", "description": "Умеет делать предметы исчезать", "rarity": "редкий"},
            {"name": "Медиум", "description": "Разговаривает с духами умерших", "rarity": "эпический"},
            {"name": "Клоун-убийца", "description": "Смешит и убивает одновременно", "rarity": "легендарный"},
            {"name": "Сантехник", "description": "Может починить что угодно", "rarity": "обычный"},
            {"name": "Ютубер", "description": "Снимает влог о выживании", "rarity": "обычный"}
        ],
        "health": [
            {"name": "Здоров как бык", "bonus": "+2 к выживанию"},
            {"name": "Ранен (царапина)", "bonus": "-1 к выживанию"},
            {"name": "Под кайфом", "bonus": "Иногда галлюцинации"},
            {"name": "При смерти", "bonus": "Требует лекарства"},
            {"name": "Не выспался", "bonus": "-1 к харизме"}
        ],
        "skills": [
            {"name": "Метание ножей", "effect": "Может убить зомби с 20 метров"},
            {"name": "Игра на гитаре", "effect": "Успокаивает зомби"},
            {"name": "Взлом автоматов", "effect": "Всегда есть еда"},
            {"name": "Теннисный удар", "effect": "Отбивает головы зомби"},
            {"name": "Разговор с животными", "effect": "Собаки и кошки помогают"}
        ],
        "items": [
            {"name": "Кольт .45", "effect": "6 патронов"},
            {"name": "Фляга с виски", "effect": "Повышает настроение"},
            {"name": "Библия", "effect": "Отгоняет зомби крестом"},
            {"name": "Запасные носки", "effect": "Чистые, всегда пригодятся"},
            {"name": "Бензопила", "effect": "Очень громкая, но эффективная"}
        ],
        "secrets": [
            {"name": "Торговал с зомби", "effect": "Все будут недовольны"},
            {"name": "Убил напарника", "effect": "Больше никому не доверяют"},
            {"name": "Был информатором", "effect": "Предатель"},
            {"name": "Украл еду у других", "effect": "Недоверие"}
        ]
    }
    print("✅ Используются дефолтные карты")

# ============================================
# 7. КОМАНДЫ БОТА
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤠 Добро пожаловать в КАФЕ ОАЗИС 2.0!\n\n"
        "🎮 **Как играть:**\n"
        "1️⃣ Напиши /play в этом чате\n"
        "2️⃣ Нажми кнопку «Играть»\n"
        "3️⃣ Присоединяйся к игре!\n\n"
        "📋 **Команды:**\n"
        "/play - Начать игру в этом чате\n"
        "/addbots N - Добавить N ботов (1-3, только ведущий)\n"
        "/status - Показать статус игры\n"
        "/host - Назначить ведущего\n"
        "/whohost - Показать ведущего\n"
        "/stop - Остановить игру\n"
        "/rules - Показать правила игры\n"
        "/logs - Включить/выключить панель отладки",
        parse_mode="Markdown"
    )

@dp.message(Command("logs"))
async def cmd_toggle_debug(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры в этом чате.")
        return
    
    toggle_debug()
    await message.answer(get_debug_command_response(), parse_mode="Markdown")
    log_debug(f"Команда /logs выполнена в чате {chat_id}")

@dp.message(Command("play"))
async def cmd_play(message: types.Message):
    print("=" * 60)
    print("🎮 КОМАНДА /play")
    print(f"👤 Пользователь: {message.from_user.id} ({message.from_user.first_name})")
    print(f"💬 Chat ID: {message.chat.id}")
    print("=" * 60)
    
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or message.from_user.username or 'Игрок'
    
    if chat_id in games:
        game = games[chat_id]
        if game.phase != GamePhase.FINISHED:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🎮 Играть",
                    callback_game=CallbackGame()
                )]
            ])
            await bot.send_game(
                chat_id=message.chat.id,
                game_short_name="oaziscaffee",
                reply_markup=keyboard
            )
            return
    
    game = create_game(chat_id, user_id, user_name)
    games[chat_id] = game
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 Играть",
            callback_game=CallbackGame()
        )]
    ])
    
    await bot.send_game(
        chat_id=message.chat.id,
        game_short_name="oaziscaffee",
        reply_markup=keyboard
    )
    
    print(f"✅ Игра создана: {game.game_id}")
    print("=" * 60)

@dp.message(Command("addbots"))
async def cmd_add_bots(message: types.Message):
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Сначала создай игру через /play")
        return
    
    game = games[chat_id]
    
    if game.host_id != user_id:
        await message.answer("⛔ Только ведущий может добавлять ботов!")
        return
    
    if game.phase != GamePhase.WAITING:
        await message.answer("❌ Игра уже началась! Ботов можно добавлять только в лобби.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /addbots N (где N от 1 до 3)")
        return
    
    try:
        count = int(parts[1])
        if count < 1 or count > 3:
            await message.answer("❌ Можно добавить от 1 до 3 ботов!")
            return
    except:
        await message.answer("❌ Введи число! Например: /addbots 2")
        return
    
    current_players = len(game.players)
    max_players = 6
    available = max_players - current_players
    
    if count > available:
        await message.answer(f"❌ Можно добавить максимум {available} ботов (сейчас {current_players} игроков)")
        return
    
    bot_count = 0
    added_names = []
    used_names = [p["name"] for p in game.players.values()]
    
    for i in range(count):
        available_names = [n for n in BOT_NAMES if n not in used_names]
        if not available_names:
            break
        
        bot_name = available_names[0]
        used_names.append(bot_name)
        
        if game.add_bot(bot_name):
            added_names.append(bot_name)
            bot_count += 1
    
    await message.answer(
        f"🤖 Добавлено {bot_count} ботов:\n"
        f"{', '.join(added_names)}\n\n"
        f"👥 Всего игроков: {len(game.players)} из 6\n"
        f"🎮 Статус: {game.phase.value}"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Напиши /play чтобы начать")
        return
    
    game = games[chat_id]
    
    alive = game.get_alive_players()
    eliminated = game.eliminated_players
    observers = list(game.observer_players)
    bots = game.get_bot_players()
    
    await message.answer(
        f"📊 **Статус игры:**\n"
        f"🎮 Game ID: `{game.game_id}`\n"
        f"👑 Ведущий: {game.host_name}\n"
        f"👥 Всего игроков: {len(game.players)}\n"
        f"👤 Активных: {len(alive)}\n"
        f"💀 Выбывших: {len(eliminated)}\n"
        f"👀 Наблюдателей: {len(observers)}\n"
        f"🤖 Ботов: {len(bots)}\n"
        f"📝 Фаза: {game.phase.value}\n"
        f"📊 Раунд: {game.round} из {game.max_rounds}",
        parse_mode="Markdown"
    )

@dp.message(Command("host"))
async def cmd_host(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Напиши /play чтобы начать")
        return
    
    game = games[chat_id]
    user_id = str(message.from_user.id)
    
    if user_id != game.host_id:
        await message.answer("⛔ Только текущий ведущий может назначить нового!")
        return
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_id = str(target_user.id)
        target_name = target_user.first_name or target_user.username or f"User {target_id}"
        
        if target_id not in game.players:
            await message.answer(f"❌ Игрок {target_name} не в игре!")
            return
        
        game.host_id = target_id
        game.host_name = target_name
        
        for player in game.players.values():
            player["is_host"] = player["id"] == target_id
        
        await message.answer(f"👑 Ведущий передан {target_name}")
        return
    
    await message.answer(
        "❌ Использование:\n"
        "/host - ответь на сообщение игрока"
    )

@dp.message(Command("whohost"))
async def cmd_whohost(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры")
        return
    
    game = games[chat_id]
    
    await message.answer(
        f"👑 **Текущий ведущий:**\n"
        f"Имя: {game.host_name}\n"
        f"👥 Всего игроков: {len(game.players)}",
        parse_mode="Markdown"
    )

@dp.message(Command("stop"))
async def cmd_stop_game(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры")
        return
    
    game = games[chat_id]
    user_id = str(message.from_user.id)
    
    if user_id != game.host_id:
        await message.answer("⛔ Только ведущий может остановить игру!")
        return
    
    del games[chat_id]
    await message.answer("⛔ Игра остановлена ведущим!")

@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    await message.answer(RULES_TEXT, parse_mode="Markdown")

# ============================================
# 8. ОБРАБОТЧИК ДЛЯ TELEGRAM GAMES
# ============================================

@dp.callback_query(lambda c: c.game_short_name is not None)
async def game_callback(callback: types.CallbackQuery):
    print("=" * 60)
    print("🎮 ПОЛУЧЕН CALLBACK ОТ ИГРЫ!")
    print(f"👤 Пользователь: {callback.from_user.id} ({callback.from_user.first_name})")
    print("=" * 60)
    
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or callback.from_user.username or 'Игрок'
    user_name_encoded = user_name.replace(' ', '%20')
    
    if callback.message and callback.message.chat:
        chat_id = str(callback.message.chat.id)
        print(f"💬 Chat ID: {chat_id}")
    else:
        chat_id = str(user_id)
        print(f"💬 Используем user_id как chat_id: {chat_id}")
    
    if chat_id not in games:
        game = create_game(chat_id, str(user_id), user_name)
        games[chat_id] = game
        print(f"🆕 Создана новая игра: {game.game_id}")
    
    game_url = f"{WEBAPP_URL}?chat_id={chat_id}&user_id={user_id}&user_name={user_name_encoded}"
    print(f"🔗 URL игры: {game_url}")
    
    await callback.answer(url=game_url)
    print("✅ Ответ отправлен с URL игры!")
    print("=" * 60)

# ============================================
# 9. API ОБРАБОТЧИКИ
# ============================================

async def api_test(request):
    return web.json_response({
        'status': 'success',
        'message': 'API работает!',
        'time': datetime.now().isoformat()
    })

async def api_get_state(request):
    print(f"📨 GET STATE запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': f'Игра не найдена для чата {chat_id}'
            }, status=404)
        
        state = game.get_game_state(player_id)
        return web.json_response(state)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_join_game(request):
    print(f"📨 JOIN GAME запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        player_name = data.get('player_name')
        username = data.get('username', '')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        if game.add_player(str(player_id), player_name):
            return web.json_response({
                'status': 'success',
                'message': f'Игрок {player_name} присоединился',
                'players': game.get_players_list(player_id),
            })
        else:
            return web.json_response({
                'status': 'error',
                'message': 'Не удалось присоединиться к игре'
            }, status=400)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_start_game(request):
    print(f"📨 START GAME запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        if str(game.host_id) != str(player_id):
            return web.json_response({'status': 'error', 'message': 'Только ведущий может начать игру'}, status=403)
        
        if game.start_game():
            return web.json_response({
                'status': 'success',
                'message': 'Игра началась!',
                'disaster': game.disaster,
                'round': game.round,
            })
        else:
            return web.json_response({
                'status': 'error',
                'message': 'Не удалось начать игру. Проверьте, что минимум 4 игрока.'
            }, status=400)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_get_cards(request):
    print(f"📨 GET CARDS запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        player = game.players.get(str(player_id))
        if not player:
            return web.json_response({'status': 'error', 'message': 'Игрок не найден'}, status=404)
        
        return web.json_response({
            'status': 'success',
            'cards': player.get('all_cards', []),
            'revealed': player.get('revealed_cards', []),
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_reveal_card(request):
    print(f"📨 REVEAL CARD запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        card_index = data.get('card_index')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        result = game.reveal_card(str(player_id), card_index)
        
        if result.get('success'):
            return web.json_response(result)
        else:
            return web.json_response({'status': 'error', 'message': result.get('message', 'Ошибка')}, status=400)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_continue(request):
    print(f"📨 CONTINUE запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        result = game.player_ready(str(player_id))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_get_voting_players(request):
    print(f"📨 GET VOTING PLAYERS запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        alive = game.get_alive_players()
        players_for_vote = []
        for pid in alive:
            if str(pid) == str(player_id):
                continue
            player = game.players.get(pid)
            if player:
                players_for_vote.append({
                    'id': pid,
                    'name': player.get('name', 'Игрок'),
                    'role': player.get('role', 'Неизвестно'),
                    'revealed_cards': player.get('revealed_cards', []),
                })
        
        return web.json_response({'status': 'success', 'players': players_for_vote})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_submit_vote(request):
    print(f"📨 SUBMIT VOTE запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        target_id = data.get('target_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        result = game.submit_vote(str(player_id), str(target_id))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_use_skill(request):
    print(f"📨 USE SKILL запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        target_id = data.get('target_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        result = game.use_skill(str(player_id), str(target_id) if target_id else None)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_final_title(request):
    print(f"📨 FINAL TITLE запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        players_data = []
        for pid, player in game.players.items():
            if pid in game.eliminated_players or pid in game.observer_players:
                continue
            players_data.append({
                'id': pid,
                'name': player.get('name', 'Игрок'),
                'role': player.get('role', 'Неизвестно'),
                'health': player.get('health', 3),
                'max_health': player.get('max_health', 3),
                'is_observer': False,
                'is_eliminated': False,
                'all_cards': player.get('all_cards', []),
                'rounds': player.get('rounds', {}),
                'revealed_cards': player.get('revealed_cards', []),
            })
        
        html = get_final_title_sheet(players_data)
        
        biographies = {}
        for player in players_data:
            builder = BiographyBuilder(player)
            biographies[player['id']] = builder.to_html(show_secrets=True)
        
        return web.json_response({
            'status': 'success',
            'html': html,
            'biographies': biographies,
        })
    except Exception as e:
        print(f"❌ Ошибка финального листа: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_final_vote(request):
    print(f"📨 FINAL VOTE запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        chat_id = data.get('chat_id')
        target_id = data.get('target_id')
        
        if not chat_id:
            return web.json_response({'status': 'error', 'message': 'chat_id не передан'}, status=400)
        
        game = games.get(str(chat_id))
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        if game.phase == GamePhase.FINAL_READY:
            game.start_final_voting()
        
        result = game.submit_final_vote(str(player_id), str(target_id))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

# ============================================
# 10. CORS MIDDLEWARE
# ============================================
@web.middleware
async def cors_middleware(request, handler):
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
    return response

# ============================================
# 11. СТАТИЧЕСКИЕ ФАЙЛЫ
# ============================================
async def serve_html(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return web.Response(text=html_content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text='<h1>404 - index.html не найден</h1>', content_type='text/html', status=404)

async def serve_css(request):
    return web.Response(text='', content_type='text/css')

async def handle_options(request):
    return web.Response(headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept',
    })

# ============================================
# 12. ЗАПУСК
# ============================================
async def main():
    load_cards()
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application(middlewares=[cors_middleware])
    
    app.router.add_get('/', serve_html)
    app.router.add_get('/style.css', serve_css)
    app.router.add_options('/api/{path:.*}', handle_options)
    
    app.router.add_get('/api/test', api_test)
    app.router.add_get('/api/debug/status', api_debug_status)
    app.router.add_post('/api/game/state', api_get_state)
    app.router.add_post('/api/game/join', api_join_game)
    app.router.add_post('/api/game/start', api_start_game)
    app.router.add_post('/api/game/cards', api_get_cards)
    app.router.add_post('/api/game/reveal', api_reveal_card)
    app.router.add_post('/api/game/continue', api_continue)
    app.router.add_post('/api/game/voting/players', api_get_voting_players)
    app.router.add_post('/api/game/vote', api_submit_vote)
    app.router.add_post('/api/game/skill', api_use_skill)
    app.router.add_post('/api/game/final/title', api_final_title)
    app.router.add_post('/api/game/final/vote', api_final_vote)
    
    app.router.add_get('/health', lambda r: web.Response(text="OK"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=PORT)
    
    print(f"✅ Сервер запущен на порту {PORT}")
    print(f"📱 Mini App: {WEBAPP_URL}")
    print(f"🧪 Тестовый API: {WEBAPP_URL}/api/test")
    print(f"📡 API отладки: {WEBAPP_URL}/api/debug/status")
    print(f"🔊 Звуки: {len(sound_manager._sounds)} звуков загружено")
    
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
