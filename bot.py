import asyncio
import json
import random
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiohttp import web, ClientSession
import sys
import os

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_BOTFATHER")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://ВАШ_ДОМЕН.bothost.tech")

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище игр (в памяти)
games = {}
players = {}

# ============================================
# ЗАГРУЗКА КАРТ
# ============================================

def load_cards():
    try:
        with open('cards.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Если файла нет, создаём дефолтные карты
        return {
            "roles": [
                {"name": "Шериф", "description": "Владеет револьвером и авторитетом", "rarity": "редкий"},
                {"name": "Продавец мороженого", "description": "Всегда носит с собой вафельный стаканчик", "rarity": "обычный"},
                {"name": "Таксист", "description": "Знает все дороги в городе", "rarity": "обычный"},
                {"name": "Инфлюенсер", "description": "Снимает всё на телефон, даже зомби", "rarity": "легендарный"},
                {"name": "Повар", "description": "Может приготовить что угодно, даже зомби-стейк", "rarity": "редкий"},
            ],
            "health": [
                {"name": "Здоров как бык", "bonus": "+2 к выживанию"},
                {"name": "Ранен (царапина)", "bonus": "-1 к выживанию"},
                {"name": "Под кайфом", "bonus": "Иногда галлюцинации"},
            ],
            "skills": [
                {"name": "Метание ножей", "effect": "Может убить зомби с 20 метров"},
                {"name": "Игра на гитаре", "effect": "Успокаивает зомби"},
                {"name": "Взлом автоматов", "effect": "Всегда есть еда"},
            ],
            "items": [
                {"name": "Кольт .45", "effect": "6 патронов"},
                {"name": "Фляга с виски", "effect": "Повышает настроение"},
                {"name": "Библия", "effect": "Отгоняет зомби крестом"},
            ],
            "secrets": [
                {"name": "Торговал с зомби", "effect": "Все будут недовольны"},
                {"name": "Убил напарника", "effect": "Больше никому не доверяют"},
            ]
        }

CARDS = load_cards()

# ============================================
# КОМАНДЫ БОТА
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🤠 Добро пожаловать в КАФЕ ОАЗИС!\n\n"
        "Это игра на выживание во время зомби-апокалипсиса.\n"
        "Ты должен убедить других, что ты достоин места в убежище.\n\n"
        "🔫 Чтобы начать игру в канале, используй команду /oasis"
    )

@dp.message(Command("oasis"))
async def cmd_oasis(message: Message):
    """Создание игры в канале"""
    chat_id = str(message.chat.id)
    
    # Проверяем, не идёт ли уже игра
    if chat_id in games:
        await message.answer("⚠️ Игра уже идёт! Дождись окончания.")
        return
    
    # Создаём игру
    game_id = str(uuid.uuid4())[:8]
    games[chat_id] = {
        'game_id': game_id,
        'chat_id': chat_id,
        'players': [],
        'status': 'waiting',  # waiting, playing, voting, finished
        'round': 0,
        'max_rounds': 5,
        'host_id': message.from_user.id,
        'created_at': datetime.now().isoformat(),
        'votes': {},
        'eliminated': [],
        'revealed_cards': [],
    }
    
    # Кнопка для присоединения
    webapp_url = f"{WEBAPP_URL}?game_id={game_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔫 Присоединиться к игре",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton(text="📖 Правила игры", callback_data="rules")]
    ])
    
    await message.answer(
        "🧟 ЗОМБИ-АПОКАЛИПСИС!\n\n"
        "Группа выживших нашла убежище в придорожном кафе 'ОАЗИС'.\n"
        "Но мест хватит только на половину из вас.\n\n"
        "👥 Соберите от 4 до 6 игроков и нажмите кнопку, чтобы присоединиться.\n"
        "Когда все готовы, ведущий нажмёт 'Начать игру' в приложении.",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "rules")
async def show_rules(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📖 ПРАВИЛА ИГРЫ 'КАФЕ ОАЗИС'\n\n"
        "1️⃣ Каждый игрок получает 5 карт: Роль, Здоровье, Навык, Предмет, Секрет\n"
        "2️⃣ За 5 раундов нужно убедить других, что ты достоин остаться в убежище\n"
        "3️⃣ В каждом раунде игроки по очереди открывают карту и рассказывают о себе\n"
        "4️⃣ После обсуждения проходит тайное голосование\n"
        "5️⃣ Тот, кто набрал больше всего голосов, выбывает навсегда\n"
        "6️⃣ Побеждают те, кто остался в живых после 5 раундов\n\n"
        "🎯 Главное — харизма и убеждение, а не логика!"
    )

@dp.message(Command("stop"))
async def cmd_stop(message: Message):
    """Принудительно остановить игру"""
    chat_id = str(message.chat.id)
    if chat_id in games:
        del games[chat_id]
        await message.answer("⛔ Игра остановлена.")
    else:
        await message.answer("❌ Активной игры нет.")

# ============================================
# API ОБРАБОТЧИКИ ДЛЯ MINI APP
# ============================================

async def api_get_state(request):
    """Получить состояние игры"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        # Ищем игру
        game = None
        chat_id = None
        for cid, g in games.items():
            if g['game_id'] == game_id:
                game = g
                chat_id = cid
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        # Проверяем, есть ли игрок
        player = next((p for p in game['players'] if p['id'] == player_id), None)
        if not player and game['status'] != 'waiting':
            return web.json_response({
                'status': 'error',
                'message': 'Игрок не найден'
            }, status=404)
        
        return web.json_response({
            'status': 'success',
            'game_id': game['game_id'],
            'status': game['status'],
            'players': game['players'],
            'round': game['round'],
            'max_rounds': game['max_rounds'],
            'is_host': game['host_id'] == player_id,
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

async def api_join_game(request):
    """Присоединиться к игре"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        player_name = data.get('player_name')
        game_id = data.get('game_id')
        
        # Ищем игру
        game = None
        chat_id = None
        for cid, g in games.items():
            if g['game_id'] == game_id:
                game = g
                chat_id = cid
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        if game['status'] != 'waiting':
            return web.json_response({
                'status': 'error',
                'message': 'Игра уже началась'
            }, status=400)
        
        if len(game['players']) >= 6:
            return web.json_response({
                'status': 'error',
                'message': 'Игра заполнена (максимум 6 игроков)'
            }, status=400)
        
        # Добавляем игрока
        player = {
            'id': player_id,
            'name': player_name,
            'is_host': game['host_id'] == player_id,
            'cards': [],
            'revealed': [],
        }
        game['players'].append(player)
        
        return web.json_response({
            'status': 'success',
            'message': f'Игрок {player_name} присоединился',
            'players': game['players'],
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

async def api_start_game(request):
    """Начать игру (только хост)"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        # Ищем игру
        game = None
        chat_id = None
        for cid, g in games.items():
            if g['game_id'] == game_id:
                game = g
                chat_id = cid
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        if game['host_id'] != player_id:
            return web.json_response({
                'status': 'error',
                'message': 'Только ведущий может начать игру'
            }, status=403)
        
        if len(game['players']) < 4:
            return web.json_response({
                'status': 'error',
                'message': 'Нужно минимум 4 игрока'
            }, status=400)
        
        # Раздаём карты каждому игроку
        for player in game['players']:
            player['cards'] = generate_cards_for_player()
            player['revealed'] = []
        
        game['status'] = 'playing'
        game['round'] = 1
        
        # Уведомление в чат
        await bot.send_message(
            chat_id,
            f"🔥 ИГРА НАЧАЛАСЬ!\n\n"
            f"👥 Игроков: {len(game['players'])}\n"
            f"📝 Раунд 1 из {game['max_rounds']}\n\n"
            f"Каждый игрок получил 5 карт. Открывайте их по очереди!"
        )
        
        return web.json_response({
            'status': 'success',
            'message': 'Игра началась',
            'game_id': game['game_id'],
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

async def api_get_cards(request):
    """Получить карты игрока"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        # Ищем игру
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        # Ищем игрока
        player = next((p for p in game['players'] if p['id'] == player_id), None)
        if not player:
            return web.json_response({
                'status': 'error',
                'message': 'Игрок не найден'
            }, status=404)
        
        return web.json_response({
            'status': 'success',
            'cards': player['cards'],
            'revealed': player['revealed'],
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

async def api_reveal_card(request):
    """Открыть карту"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        card_index = data.get('card_index')
        
        # Ищем игру
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        # Ищем игрока
        player = next((p for p in game['players'] if p['id'] == player_id), None)
        if not player:
            return web.json_response({
                'status': 'error',
                'message': 'Игрок не найден'
            }, status=404)
        
        if card_index >= len(player['cards']):
            return web.json_response({
                'status': 'error',
                'message': 'Неверный индекс карты'
            }, status=400)
        
        # Открываем карту
        card = player['cards'][card_index]
        card['isRevealed'] = True
        player['revealed'].append(card)
        
        # Проверяем, все ли карты открыты у всех игроков
        all_revealed = True
        for p in game['players']:
            if len(p['revealed']) < len(p['cards']):
                all_revealed = False
                break
        
        # Если все открыли карты, переходим к голосованию
        if all_revealed and game['status'] == 'playing':
            game['status'] = 'voting'
            await bot.send_message(
                game['chat_id'],
                f"🗳️ ГОЛОСОВАНИЕ!\n\n"
                f"Все игроки открыли карты. Теперь нужно выбрать, кто не попадёт в убежище.\n"
                f"Голосуйте в приложении!"
            )
        
        return web.json_response({
            'status': 'success',
            'card': card,
            'revealed_cards': player['revealed'],
            'all_revealed': all_revealed,
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

async def api_get_voting_players(request):
    """Получить список игроков для голосования"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        # Ищем игру
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        # Возвращаем всех игроков кроме самого голосующего
        players_for_vote = [
            {
                'id': p['id'],
                'name': p['name'],
                'role': next((c['name'] for c in p['cards'] if c.get('isRevealed') and c.get('type') == 'role'), 'Неизвестно')
            }
            for p in game['players']
            if p['id'] != player_id
        ]
        
        return web.json_response({
            'status': 'success',
            'players': players_for_vote,
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

async def api_submit_vote(request):
    """Отправить голос"""
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        target_id = data.get('target_id')
        
        # Ищем игру
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({
                'status': 'error',
                'message': 'Игра не найдена'
            }, status=404)
        
        # Сохраняем голос
        if 'votes' not in game:
            game['votes'] = {}
        game['votes'][player_id] = target_id
        
        # Проверяем, все ли проголосовали
        all_voted = len(game['votes']) == len(game['players'])
        
        if all_voted:
            # Подводим итоги голосования
            vote_results = {}
            for voter, target in game['votes'].items():
                vote_results[target] = vote_results.get(target, 0) + 1
            
            # Находим игрока с наибольшим количеством голосов
            max_votes = max(vote_results.values())
            eliminated = [p for p in game['players'] if p['id'] in vote_results and vote_results[p['id']] == max_votes]
            
            if eliminated:
                eliminated_player = eliminated[0]
                game['eliminated'].append(eliminated_player)
                game['players'] = [p for p in game['players'] if p['id'] != eliminated_player['id']]
                
                # Уведомление в чат
                await bot.send_message(
                    game['chat_id'],
                    f"🧟 ВЫБЫВАЕТ: {eliminated_player['name']}\n\n"
                    f"Причина: Большинство голосов ({max_votes} из {len(game['votes'])})\n"
                    f"Осталось игроков: {len(game['players'])}"
                )
            
            # Проверяем, осталось ли достаточно игроков
            if len(game['players']) <= len(game['players']) / 2:
                game['status'] = 'finished'
                await bot.send_message(
                    game['chat_id'],
                    f"🏆 ВЫЖИВШИЕ!\n\n"
                    f"Группа заперлась в подсобке кафе.\n"
                    f"Снаружи слышен вой зомби.\n"
                    f"Они выжили до рассвета! 🎉"
                )
            else:
                # Переходим к следующему раунду
                game['round'] += 1
                game['status'] = 'playing'
                game['votes'] = {}
                
                # Сбрасываем открытые карты у всех
                for p in game['players']:
                    p['revealed'] = []
                    for card in p['cards']:
                        card['isRevealed'] = False
                
                await bot.send_message(
                    game['chat_id'],
                    f"📝 РАУНД {game['round']}\n\n"
                    f"Новый раунд! Открывайте карты по очереди."
                )
        
        return web.json_response({
            'status': 'success',
            'all_voted': all_voted,
            'vote_count': len(game['votes']),
            'total_players': len(game['players']),
        })
        
    except Exception as e:
        return web.json_response({
            'status': 'error',
            'message': str(e)
        }, status=500)

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def generate_cards_for_player():
    """Генерирует случайный набор карт для игрока"""
    cards = []
    
    # Роль
    role = random.choice(CARDS['roles'])
    cards.append({
        'type': 'Роль',
        'name': role['name'],
        'description': role['description'],
        'rarity': role.get('rarity', 'обычный'),
        'isRevealed': False,
    })
    
    # Здоровье
    health = random.choice(CARDS['health'])
    cards.append({
        'type': 'Здоровье',
        'name': health['name'],
        'effect': health.get('bonus', ''),
        'isRevealed': False,
    })
    
    # Навык
    skill = random.choice(CARDS['skills'])
    cards.append({
        'type': 'Навык',
        'name': skill['name'],
        'effect': skill.get('effect', ''),
        'isRevealed': False,
    })
    
    # Предмет
    item = random.choice(CARDS['items'])
    cards.append({
        'type': 'Предмет',
        'name': item['name'],
        'effect': item.get('effect', ''),
        'isRevealed': False,
    })
    
    # Секрет
    secret = random.choice(CARDS['secrets'])
    cards.append({
        'type': 'Секрет',
        'name': secret['name'],
        'effect': secret.get('effect', ''),
        'isRevealed': False,
    })
    
    return cards

# ============================================
# ЗАПУСК HTTP СЕРВЕРА ДЛЯ MINI APP
# ============================================

async def handle_index(request):
    """Отдаём index.html"""
    try:
        with open('mini-app/index.html', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/html')
    except:
        return web.Response(text="<h1>Кафе ОАЗИС</h1><p>Mini App загружается...</p>", content_type='text/html')

async def handle_style(request):
    """Отдаём style.css"""
    try:
        with open('mini-app/style.css', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='text/css')
    except:
        return web.Response(text="/* CSS */", content_type='text/css')

async def handle_app_js(request):
    """Отдаём app.js"""
    try:
        with open('mini-app/app.js', 'r', encoding='utf-8') as f:
            return web.Response(text=f.read(), content_type='application/javascript')
    except:
        return web.Response(text="// JS", content_type='application/javascript')

async def handle_polling(request):
    """Для long polling или webhook"""
    return web.Response(text="OK")

# ============================================
# ЗАПУСК
# ============================================

async def main():
    # Запускаем бота в фоне
    asyncio.create_task(dp.start_polling(bot))
    
    # Создаём HTTP сервер для Mini App
    app = web.Application()
    
    # Статика
    app.router.add_get('/', handle_index)
    app.router.add_get('/style.css', handle_style)
    app.router.add_get('/app.js', handle_app_js)
    
    # API эндпоинты
    app.router.add_post('/api/game/state', api_get_state)
    app.router.add_post('/api/game/join', api_join_game)
    app.router.add_post('/api/game/start', api_start_game)
    app.router.add_post('/api/game/cards', api_get_cards)
    app.router.add_post('/api/game/reveal', api_reveal_card)
    app.router.add_post('/api/game/voting/players', api_get_voting_players)
    app.router.add_post('/api/game/vote', api_submit_vote)
    
    # Для health check
    app.router.add_get('/polling', handle_polling)
    
    # Запускаем HTTP сервер
    port = int(os.getenv('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    
    print(f"🤠 Бот и Mini App запущены на порту {port}")
    print(f"📱 Mini App доступен по адресу: {WEBAPP_URL}")
    
    await site.start()
    
    # Держим сервер запущенным
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())