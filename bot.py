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
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from dotenv import load_dotenv

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
print("🚀 КАФЕ ОАЗИС - БОТ ЗАПУСКАЕТСЯ!")
print("=" * 60)

# ============================================
# 3. КОНФИГУРАЦИЯ
# ============================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")
PORT = int(os.getenv("PORT", 8082))

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в .env файле!")
    print("📝 Создай файл .env с содержимым:")
    print("   BOT_TOKEN=твой_токен_от_BotFather")
    print("   WEBAPP_URL=https://твой_домен.bothost.tech")
    print("   PORT=8082")
    sys.exit(1)

if not WEBAPP_URL:
    print("❌ ОШИБКА: WEBAPP_URL не найден в .env файле!")
    sys.exit(1)

print(f"🔌 Порт: {PORT}")
print(f"🤖 Токен: ✅ Загружен из .env")
print(f"🌐 URL: {WEBAPP_URL}")

# ============================================
# 4. ИНИЦИАЛИЗАЦИЯ
# ============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
games = {}
CARDS = None

# ============================================
# 5. HTML СТРАНИЦА
# ============================================
HTML_PAGE = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Кафе ОАЗИС</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div id="app">
        <div class="neon-sign">
            <h1 class="neon-text">ОАЗИС</h1>
            <p class="neon-sub">Зомби-убежище • Техас 1999</p>
        </div>
        <div id="game-container">
            <div id="lobby">
                <h2>👥 Лобби</h2>
                <div id="players-list"></div>
                <button id="start-game" class="btn-neon">🔥 Начать игру</button>
                <p id="debug-info" style="font-size:0.8rem;opacity:0.5;margin-top:10px;"></p>
            </div>
            <div id="game-area" style="display:none;">
                <div id="character-cards">
                    <h2>🎴 Твои карты</h2>
                    <div id="cards-container"></div>
                    <button id="reveal-card" class="btn-neon">🃏 Открыть карту</button>
                </div>
                <div id="voting-area" style="display:none;">
                    <h2>🗳️ Голосование</h2>
                    <div id="voting-list"></div>
                    <button id="vote-btn" class="btn-neon">✅ Проголосовать</button>
                </div>
            </div>
        </div>
        <div id="results" style="display:none;">
            <h2>🏆 Итоги</h2>
            <div id="results-list"></div>
        </div>
    </div>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script>
        const API_BASE = '{WEBAPP_URL}';
        console.log('📍 API_BASE:', API_BASE);
        
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.enableClosingConfirmation();

        const gameState = {{
            playerId: null,
            gameId: null,
            players: [],
            myCards: [],
            revealedCards: [],
            currentRound: 0,
            maxRounds: 5,
            status: 'lobby',
            isHost: false,
        }};

        document.addEventListener('DOMContentLoaded', () => {{
            console.log('🤠 Кафе ОАЗИС загружено!');
            console.log('📡 API URL:', API_BASE);
            
            const initData = tg.initDataUnsafe;
            if (initData && initData.user) {{
                gameState.playerId = initData.user.id;
                console.log(`👤 Игрок: ${{initData.user.first_name}} (ID: ${{gameState.playerId}})`);
                document.getElementById('debug-info').textContent = 
                    `Игрок: ${{initData.user.first_name}} | ID: ${{gameState.playerId}}`;
            }}
            
            const urlParams = new URLSearchParams(window.location.search);
            gameState.gameId = urlParams.get('game_id');
            
            if (!gameState.gameId) {{
                tg.showPopup({{
                    title: '❌ Ошибка',
                    message: 'Не найден ID игры. Начните игру заново.',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            console.log('🎮 Game ID:', gameState.gameId);
            document.getElementById('debug-info').textContent += ` | Game: ${{gameState.gameId}}`;
            
            connectToGame();
            
            document.getElementById('start-game')?.addEventListener('click', startGame);
            document.getElementById('reveal-card')?.addEventListener('click', revealCard);
            document.getElementById('vote-btn')?.addEventListener('click', submitVote);
        }});

        async function connectToGame() {{
            try {{
                console.log('🔄 Подключение к API...');
                const url = API_BASE + '/api/game/state';
                console.log('📍 URL:', url);
                
                const response = await fetch(url, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        game_id: gameState.gameId,
                    }})
                }});
                
                console.log('📡 Статус:', response.status);
                const data = await response.json();
                console.log('📦 Данные:', data);
                
                if (data.status === 'success') {{
                    gameState.players = data.players || [];
                    gameState.status = data.status || 'lobby';
                    gameState.isHost = data.is_host || false;
                    console.log('👑 isHost:', gameState.isHost);
                    
                    const playerExists = gameState.players.some(p => p.id == gameState.playerId);
                    if (!playerExists && gameState.status === 'waiting') {{
                        await joinGame();
                    }}
                    
                    updateUI();
                    
                    if (gameState.status !== 'lobby') {{
                        await getMyCards();
                    }}
                }} else {{
                    console.error('❌ Ошибка API:', data);
                    tg.showPopup({{
                        title: '❌ Ошибка',
                        message: data.message || 'Не удалось подключиться к игре',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                console.error('❌ Ошибка сети:', error);
                console.error('❌ Stack:', error.stack);
                tg.showPopup({{
                    title: '❌ Ошибка сети',
                    message: 'Не удалось подключиться к серверу. Проверьте консоль (F12).',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
            }}
        }}

        async function joinGame() {{
            try {{
                const initData = tg.initDataUnsafe;
                const userName = initData?.user?.first_name || 'Игрок';
                
                const response = await fetch(API_BASE + '/api/game/join', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        player_name: userName,
                        game_id: gameState.gameId,
                    }})
                }});
                
                const data = await response.json();
                
                if (data.status === 'success') {{
                    gameState.players = data.players;
                    updateUI();
                    tg.showPopup({{
                        title: '✅ Присоединились!',
                        message: `Добро пожаловать, ${{userName}}!`,
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                console.error('❌ Ошибка присоединения:', error);
            }}
        }}

        async function getMyCards() {{
            try {{
                const response = await fetch(API_BASE + '/api/game/cards', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        game_id: gameState.gameId,
                    }})
                }});
                
                const data = await response.json();
                
                if (data.status === 'success') {{
                    gameState.myCards = data.cards || [];
                    gameState.revealedCards = data.revealed || [];
                    renderCards();
                }}
            }} catch (error) {{
                console.error('❌ Ошибка получения карт:', error);
            }}
        }}

        async function startGame() {{
            if (!gameState.isHost) {{
                tg.showPopup({{
                    title: '⛔',
                    message: 'Только ведущий может начать игру!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            if (gameState.players.length < 4) {{
                tg.showPopup({{
                    title: '👥',
                    message: 'Нужно минимум 4 игрока!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            try {{
                const response = await fetch(API_BASE + '/api/game/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                const data = await response.json();
                
                if (data.status === 'success') {{
                    gameState.status = 'playing';
                    updateUI();
                    await getMyCards();
                    tg.showPopup({{
                        title: '🔥',
                        message: 'Игра началась!',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }} else {{
                    tg.showPopup({{
                        title: '❌',
                        message: data.message || 'Ошибка старта',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                console.error('❌ Ошибка:', error);
            }}
        }}

        async function revealCard() {{
            const cardIndex = gameState.myCards.findIndex(c => !c.isRevealed);
            
            if (cardIndex === -1) {{
                tg.showPopup({{
                    title: '🃏',
                    message: 'Все карты уже открыты!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            try {{
                const response = await fetch(API_BASE + '/api/game/reveal', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                        card_index: cardIndex,
                    }})
                }});
                
                const data = await response.json();
                
                if (data.status === 'success') {{
                    gameState.myCards[cardIndex].isRevealed = true;
                    gameState.revealedCards = data.revealed_cards || [];
                    renderCards();
                    
                    if (gameState.myCards.every(c => c.isRevealed)) {{
                        setTimeout(() => startVoting(), 1500);
                    }}
                }}
            }} catch (error) {{
                console.error('❌ Ошибка:', error);
            }}
        }}

        async function startVoting() {{
            gameState.status = 'voting';
            updateUI();
            
            try {{
                const response = await fetch(API_BASE + '/api/game/voting/players', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                const data = await response.json();
                
                if (data.status === 'success') {{
                    renderVotingList(data.players);
                }}
            }} catch (error) {{
                console.error('❌ Ошибка:', error);
            }}
        }}

        function renderVotingList(players) {{
            const container = document.getElementById('voting-list');
            container.innerHTML = '';
            
            players.forEach(player => {{
                const card = document.createElement('div');
                card.className = 'character-card voting-card';
                card.innerHTML = `
                    <div class="card-type">Игрок</div>
                    <div class="card-name">${{player.name}}</div>
                    <div class="card-effect">${{player.role || 'Без роли'}}</div>
                    <input type="radio" name="vote" value="${{player.id}}" id="vote-${{player.id}}">
                    <label for="vote-${{player.id}}">Голосовать</label>
                `;
                container.appendChild(card);
            }});
        }}

        async function submitVote() {{
            const selected = document.querySelector('input[name="vote"]:checked');
            
            if (!selected) {{
                tg.showPopup({{
                    title: '⚠️',
                    message: 'Выберите игрока!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            const targetId = parseInt(selected.value);
            
            try {{
                const response = await fetch(API_BASE + '/api/game/vote', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                        target_id: targetId,
                    }})
                }});
                
                const data = await response.json();
                
                if (data.status === 'success') {{
                    document.getElementById('vote-btn').disabled = true;
                    tg.showPopup({{
                        title: '✅',
                        message: 'Голос учтён!',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                console.error('❌ Ошибка:', error);
            }}
        }}

        function updateUI() {{
            const lobby = document.getElementById('lobby');
            const gameArea = document.getElementById('game-area');
            const votingArea = document.getElementById('voting-area');
            
            if (gameState.status === 'lobby') {{
                lobby.style.display = 'block';
                gameArea.style.display = 'none';
                renderPlayersList();
            }} else if (gameState.status === 'voting') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'block';
                document.getElementById('character-cards').style.display = 'none';
                document.getElementById('voting-area').style.display = 'block';
            }} else if (gameState.status === 'playing') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'block';
                document.getElementById('character-cards').style.display = 'block';
                document.getElementById('voting-area').style.display = 'none';
            }}
        }}

        function renderPlayersList() {{
            const container = document.getElementById('players-list');
            container.innerHTML = '';
            
            gameState.players.forEach(player => {{
                const div = document.createElement('div');
                div.className = 'player-item';
                div.innerHTML = `
                    <span>👤 ${{player.name}}</span>
                    ${{player.isHost ? '<span class="host-badge">⭐ Ведущий</span>' : ''}}
                `;
                container.appendChild(div);
            }});
            
            const startBtn = document.getElementById('start-game');
            if (gameState.players.length >= 4 && gameState.isHost) {{
                startBtn.style.display = 'block';
                startBtn.textContent = `🔥 Начать игру (${{gameState.players.length}} игроков)`;
                startBtn.disabled = false;
            }} else if (gameState.isHost) {{
                startBtn.style.display = 'block';
                startBtn.textContent = `👥 Нужно ещё ${{4 - gameState.players.length}} игроков`;
                startBtn.disabled = true;
            }} else {{
                startBtn.style.display = 'none';
            }}
        }}

        function renderCards() {{
            const container = document.getElementById('cards-container');
            container.innerHTML = '';
            
            gameState.myCards.forEach((card) => {{
                const div = document.createElement('div');
                div.className = 'character-card';
                
                if (card.isRevealed) {{
                    div.style.borderColor = '#ff6b35';
                    div.style.opacity = '1';
                }} else {{
                    div.style.borderColor = '#666';
                    div.style.opacity = '0.7';
                }}
                
                div.innerHTML = `
                    <div class="card-type">${{card.type || 'Карта'}}</div>
                    <div class="card-name">${{card.isRevealed ? card.name : '❓ Скрыто'}}</div>
                    <div class="card-effect">${{card.isRevealed ? (card.effect || card.description || '') : 'Нажмите "Открыть карту"'}}</div>
                    ${{card.isRevealed ? `<div class="card-rarity">⭐ ${{card.rarity || 'Обычная'}}</div>` : ''}}
                `;
                container.appendChild(div);
            }});
            
            const remaining = gameState.myCards.filter(c => !c.isRevealed).length;
            document.getElementById('reveal-card').textContent = 
                `🃏 Открыть карту (осталось: ${{remaining}})`;
        }}

        console.log('✅ Mini App готов!');
        console.log('📡 API URL:', API_BASE);
    </script>
</body>
</html>'''

# ============================================
# 6. CSS СТИЛИ
# ============================================
CSS_STYLES = '''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
body {
    background: #0a0a0a;
    color: #f5e6d3;
    font-family: 'Courier New', monospace;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}
.neon-sign {
    text-align: center;
    margin-bottom: 40px;
}
.neon-text {
    font-size: 4rem;
    color: #ff6b35;
    text-shadow: 0 0 10px #ff6b35, 0 0 20px #ff6b35, 0 0 40px #ff6b35, 0 0 80px #ff6b35;
    animation: neon-pulse 2s infinite;
}
@keyframes neon-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
.neon-sub {
    color: #ff6b35;
    opacity: 0.7;
    letter-spacing: 4px;
}
.character-card {
    background: linear-gradient(145deg, #1a0a00, #2a1a0a);
    border: 2px solid #ff6b35;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 0 20px rgba(255, 107, 53, 0.2);
    transition: transform 0.3s;
}
.character-card:hover {
    transform: scale(1.02);
    box-shadow: 0 0 40px rgba(255, 107, 53, 0.4);
}
.card-type {
    color: #ff6b35;
    font-weight: bold;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 2px;
}
.card-name {
    font-size: 1.5rem;
    margin: 10px 0;
}
.card-effect {
    font-style: italic;
    opacity: 0.8;
    border-top: 1px solid #ff6b35;
    padding-top: 10px;
}
.btn-neon {
    background: transparent;
    color: #ff6b35;
    border: 2px solid #ff6b35;
    padding: 15px 30px;
    font-size: 1.2rem;
    font-family: 'Courier New', monospace;
    cursor: pointer;
    transition: all 0.3s;
    border-radius: 8px;
    width: 100%;
    margin: 10px 0;
}
.btn-neon:hover {
    background: #ff6b35;
    color: #0a0a0a;
    box-shadow: 0 0 30px rgba(255, 107, 53, 0.6);
}
.player-item {
    padding: 10px;
    margin: 5px 0;
    background: #1a0a00;
    border-radius: 8px;
    border-left: 3px solid #ff6b35;
}
.host-badge {
    color: #ffd700;
    margin-left: 10px;
}
.voting-card {
    cursor: pointer;
}
.voting-card input[type="radio"] {
    margin-top: 10px;
}
.result-card {
    padding: 20px;
    margin: 10px 0;
    border-radius: 12px;
}
.result-card.eliminated {
    background: #2a0a0a;
    border: 2px solid #ff0000;
}
.result-card.survivors {
    background: #0a2a0a;
    border: 2px solid #00ff00;
}
.survivor-item {
    padding: 5px;
    margin: 5px 0;
}'''

# ============================================
# 7. ЗАГРУЗКА КАРТ
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
            {"name": "Шериф", "description": "Владеет револьвером", "rarity": "редкий"},
            {"name": "Продавец мороженого", "description": "Всегда носит мороженое", "rarity": "обычный"},
            {"name": "Таксист", "description": "Знает все дороги", "rarity": "обычный"},
            {"name": "Инфлюенсер", "description": "Снимает всё на телефон", "rarity": "легендарный"},
            {"name": "Повар", "description": "Готовит зомби-стейк", "rarity": "редкий"},
            {"name": "Фокусник", "description": "Делает предметы исчезать", "rarity": "редкий"},
            {"name": "Медиум", "description": "Разговаривает с духами", "rarity": "эпический"},
            {"name": "Клоун-убийца", "description": "Смешит и убивает", "rarity": "легендарный"},
            {"name": "Сантехник", "description": "Чинит что угодно", "rarity": "обычный"},
            {"name": "Ютубер", "description": "Влог о выживании", "rarity": "обычный"},
        ],
        "health": [
            {"name": "Здоров как бык", "bonus": "+2 к выживанию"},
            {"name": "Ранен (царапина)", "bonus": "-1 к выживанию"},
            {"name": "Под кайфом", "bonus": "Иногда галлюцинации"},
            {"name": "При смерти", "bonus": "Требует лекарства"},
        ],
        "skills": [
            {"name": "Метание ножей", "effect": "Убивает зомби с 20 метров"},
            {"name": "Игра на гитаре", "effect": "Успокаивает зомби"},
            {"name": "Взлом автоматов", "effect": "Всегда есть еда"},
        ],
        "items": [
            {"name": "Кольт .45", "effect": "6 патронов"},
            {"name": "Фляга с виски", "effect": "Повышает настроение"},
            {"name": "Библия", "effect": "Отгоняет зомби"},
        ],
        "secrets": [
            {"name": "Торговал с зомби", "effect": "Все недовольны"},
            {"name": "Убил напарника", "effect": "Не доверяют"},
        ]
    }
    print("✅ Используются дефолтные карты")

# ============================================
# 8. КОМАНДЫ БОТА
# ============================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤠 Добро пожаловать в КАФЕ ОАЗИС!\n\n"
        "Игра на выживание во время зомби-апокалипсиса.\n"
        "🔫 Чтобы начать игру, используй команду /oasis\n\n"
        "📋 Команды:\n"
        "/oasis - Создать игру\n"
        "/host @username - Назначить ведущего\n"
        "/whohost - Показать ведущего\n"
        "/stop - Остановить игру (только ведущий)"
    )

@dp.message(Command("oasis"))
async def cmd_oasis(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id in games:
        await message.answer("⚠️ Игра уже идёт! Используй /stop чтобы остановить.")
        return
    
    game_id = str(uuid.uuid4())[:8]
    games[chat_id] = {
        'game_id': game_id,
        'chat_id': chat_id,
        'players': [],
        'status': 'waiting',
        'round': 0,
        'max_rounds': 5,
        'host_id': str(message.from_user.id),
        'host_name': message.from_user.first_name or message.from_user.username or 'Ведущий',
        'created_at': datetime.now().isoformat(),
        'votes': {},
        'eliminated': [],
    }
    
    webapp_url = f"{WEBAPP_URL}?game_id={game_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔫 Присоединиться к игре",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton(text="📖 Правила игры", callback_data="rules")]
    ])
    
    await message.answer(
        f"🧟 ЗОМБИ-АПОКАЛИПСИС!\n\n"
        f"Группа выживших нашла убежище в кафе 'ОАЗИС'.\n"
        f"Мест хватит только на половину из вас.\n\n"
        f"👑 Ведущий: {games[chat_id]['host_name']}\n"
        f"👥 Соберите от 4 до 6 игроков и нажмите кнопку.",
        reply_markup=keyboard
    )

@dp.message(Command("host"))
async def cmd_host(message: types.Message):
    """Назначить ведущего (/host @username)"""
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Создай игру через /oasis")
        return
    
    if str(message.from_user.id) != str(games[chat_id]['host_id']):
        await message.answer("⛔ Только текущий ведущий может назначить нового!")
        return
    
    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.answer("❌ Использование: /host @username")
        return
    
    username = command_parts[1].replace('@', '')
    
    try:
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            games[chat_id]['host_id'] = str(target_user.id)
            games[chat_id]['host_name'] = target_user.first_name or target_user.username or 'Ведущий'
            
            for player in games[chat_id]['players']:
                player['is_host'] = str(player['id']) == str(target_user.id)
            
            await message.answer(f"👑 Ведущий передан {games[chat_id]['host_name']}")
            return
        
        found = False
        for player in games[chat_id]['players']:
            if player.get('username') == username or player.get('name') == username:
                games[chat_id]['host_id'] = str(player['id'])
                games[chat_id]['host_name'] = player['name']
                player['is_host'] = True
                found = True
                await message.answer(f"👑 Ведущий передан {player['name']}")
                break
        
        if not found:
            await message.answer(f"❌ Игрок @{username} не найден в игре")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command("whohost"))
async def cmd_whohost(message: types.Message):
    """Показать ведущего"""
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры")
        return
    
    host_name = games[chat_id].get('host_name', 'Неизвестно')
    host_id = games[chat_id].get('host_id', 'Нет ID')
    
    host_in_game = False
    for player in games[chat_id]['players']:
        if str(player['id']) == str(host_id):
            host_in_game = True
            host_name = player['name']
            break
    
    await message.answer(
        f"👑 Текущий ведущий:\n"
        f"Имя: {host_name}\n"
        f"Статус: {'✅ В игре' if host_in_game else '❌ Не в игре'}"
    )

@dp.message(Command("stop"))
async def cmd_stop_game(message: types.Message):
    """Остановить игру (только ведущий)"""
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры")
        return
    
    if str(message.from_user.id) != str(games[chat_id]['host_id']):
        await message.answer("⛔ Только ведущий может остановить игру!")
        return
    
    del games[chat_id]
    await message.answer("⛔ Игра остановлена ведущим!")

@dp.callback_query(lambda c: c.data == "rules")
async def show_rules(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📖 ПРАВИЛА ИГРЫ 'КАФЕ ОАЗИС'\n\n"
        "1️⃣ Каждый получает 5 карт: Роль, Здоровье, Навык, Предмет, Секрет\n"
        "2️⃣ За 5 раундов нужно убедить других, что ты достоин остаться\n"
        "3️⃣ В каждом раунде игроки по очереди открывают карту\n"
        "4️⃣ После обсуждения - тайное голосование\n"
        "5️⃣ Кто набрал больше голосов - выбывает\n"
        "6️⃣ Побеждают те, кто остался в живых\n\n"
        "🎯 Главное - харизма и убеждение!"
    )

# ============================================
# 9. ГЕНЕРАЦИЯ КАРТ
# ============================================
def generate_cards_for_player():
    cards = []
    
    role = random.choice(CARDS['roles'])
    cards.append({
        'type': 'Роль',
        'name': role['name'],
        'description': role['description'],
        'rarity': role.get('rarity', 'обычный'),
        'isRevealed': False,
    })
    
    health = random.choice(CARDS['health'])
    cards.append({
        'type': 'Здоровье',
        'name': health['name'],
        'effect': health.get('bonus', ''),
        'isRevealed': False,
    })
    
    skill = random.choice(CARDS['skills'])
    cards.append({
        'type': 'Навык',
        'name': skill['name'],
        'effect': skill.get('effect', ''),
        'isRevealed': False,
    })
    
    item = random.choice(CARDS['items'])
    cards.append({
        'type': 'Предмет',
        'name': item['name'],
        'effect': item.get('effect', ''),
        'isRevealed': False,
    })
    
    secret = random.choice(CARDS['secrets'])
    cards.append({
        'type': 'Секрет',
        'name': secret['name'],
        'effect': secret.get('effect', ''),
        'isRevealed': False,
    })
    
    return cards

# ============================================
# 10. API ОБРАБОТЧИКИ
# ============================================
async def api_test(request):
    print("🧪 Тестовый API вызван!")
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
        game_id = data.get('game_id')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        player = next((p for p in game['players'] if str(p['id']) == str(player_id)), None)
        
        return web.json_response({
            'status': 'success',
            'game_id': game['game_id'],
            'status': game['status'],
            'players': game['players'],
            'round': game['round'],
            'max_rounds': game['max_rounds'],
            'is_host': str(game['host_id']) == str(player_id) if player else False,
        })
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_join_game(request):
    print(f"📨 JOIN GAME запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        player_name = data.get('player_name')
        game_id = data.get('game_id')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        if game['status'] != 'waiting':
            return web.json_response({'status': 'error', 'message': 'Игра уже началась'}, status=400)
        
        if len(game['players']) >= 6:
            return web.json_response({'status': 'error', 'message': 'Игра заполнена'}, status=400)
        
        if any(str(p['id']) == str(player_id) for p in game['players']):
            return web.json_response({
                'status': 'success',
                'message': 'Игрок уже в игре',
                'players': game['players'],
            })
        
        player = {
            'id': str(player_id),
            'name': player_name,
            'is_host': str(game['host_id']) == str(player_id),
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
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_start_game(request):
    print(f"📨 START GAME запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        if str(game['host_id']) != str(player_id):
            print(f"❌ Ошибка: игрок {player_id} не ведущий (хост: {game['host_id']})")
            return web.json_response({'status': 'error', 'message': 'Только ведущий может начать игру'}, status=403)
        
        if len(game['players']) < 4:
            return web.json_response({'status': 'error', 'message': 'Нужно минимум 4 игрока'}, status=400)
        
        for player in game['players']:
            player['cards'] = generate_cards_for_player()
            player['revealed'] = []
        
        game['status'] = 'playing'
        game['round'] = 1
        
        await bot.send_message(
            game['chat_id'],
            f"🔥 ИГРА НАЧАЛАСЬ!\n\n👥 Игроков: {len(game['players'])}\n📝 Раунд 1 из {game['max_rounds']}"
        )
        
        return web.json_response({'status': 'success', 'message': 'Игра началась'})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_get_cards(request):
    print(f"📨 GET CARDS запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        player = next((p for p in game['players'] if str(p['id']) == str(player_id)), None)
        if not player:
            return web.json_response({'status': 'error', 'message': 'Игрок не найден'}, status=404)
        
        return web.json_response({
            'status': 'success',
            'cards': player['cards'],
            'revealed': player['revealed'],
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_reveal_card(request):
    print(f"📨 REVEAL CARD запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        card_index = data.get('card_index')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        player = next((p for p in game['players'] if str(p['id']) == str(player_id)), None)
        if not player:
            return web.json_response({'status': 'error', 'message': 'Игрок не найден'}, status=404)
        
        if card_index >= len(player['cards']):
            return web.json_response({'status': 'error', 'message': 'Неверный индекс'}, status=400)
        
        card = player['cards'][card_index]
        card['isRevealed'] = True
        player['revealed'].append(card)
        
        all_revealed = True
        for p in game['players']:
            if len(p['revealed']) < len(p['cards']):
                all_revealed = False
                break
        
        if all_revealed and game['status'] == 'playing':
            game['status'] = 'voting'
            await bot.send_message(
                game['chat_id'],
                f"🗳️ ГОЛОСОВАНИЕ!\n\nВсе игроки открыли карты. Голосуйте в приложении!"
            )
        
        return web.json_response({
            'status': 'success',
            'card': card,
            'revealed_cards': player['revealed'],
            'all_revealed': all_revealed,
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_get_voting_players(request):
    print(f"📨 GET VOTING PLAYERS запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        players_for_vote = [
            {
                'id': str(p['id']),
                'name': p['name'],
                'role': next((c['name'] for c in p['cards'] if c.get('isRevealed') and c.get('type') == 'Роль'), 'Неизвестно')
            }
            for p in game['players']
            if str(p['id']) != str(player_id)
        ]
        
        return web.json_response({'status': 'success', 'players': players_for_vote})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_submit_vote(request):
    print(f"📨 SUBMIT VOTE запрос")
    try:
        data = await request.json()
        player_id = data.get('player_id')
        game_id = data.get('game_id')
        target_id = data.get('target_id')
        
        game = None
        for g in games.values():
            if g['game_id'] == game_id:
                game = g
                break
        
        if not game:
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        game['votes'][str(player_id)] = str(target_id)
        
        all_voted = len(game['votes']) == len(game['players'])
        
        if all_voted:
            vote_results = {}
            for voter, target in game['votes'].items():
                vote_results[target] = vote_results.get(target, 0) + 1
            
            max_votes = max(vote_results.values())
            eliminated = [p for p in game['players'] if str(p['id']) in vote_results and vote_results[str(p['id'])] == max_votes]
            
            if eliminated:
                eliminated_player = eliminated[0]
                game['eliminated'].append(eliminated_player)
                game['players'] = [p for p in game['players'] if str(p['id']) != str(eliminated_player['id'])]
                
                await bot.send_message(
                    game['chat_id'],
                    f"🧟 ВЫБЫВАЕТ: {eliminated_player['name']}\n\nГолосов: {max_votes} из {len(game['votes'])}\nОсталось: {len(game['players'])} игроков"
                )
            
            if len(game['players']) <= len(game['players']) / 2 + 1:
                game['status'] = 'finished'
                survivors = [p['name'] for p in game['players']]
                await bot.send_message(
                    game['chat_id'],
                    f"🏆 ВЫЖИВШИЕ!\n\n{', '.join(survivors)} заперлись в кафе.\nЗомби не прошли! 🎉"
                )
            else:
                game['round'] += 1
                game['status'] = 'playing'
                game['votes'] = {}
                
                for p in game['players']:
                    p['revealed'] = []
                    for card in p['cards']:
                        card['isRevealed'] = False
                
                await bot.send_message(
                    game['chat_id'],
                    f"📝 РАУНД {game['round']}\n\nНовый раунд! Открывайте карты."
                )
        
        return web.json_response({
            'status': 'success',
            'all_voted': all_voted,
            'vote_count': len(game['votes']),
            'total_players': len(game['players']),
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

# ============================================
# 11. СТАТИЧЕСКИЕ ФАЙЛЫ
# ============================================
async def serve_html(request):
    return web.Response(text=HTML_PAGE, content_type='text/html')

async def serve_css(request):
    return web.Response(text=CSS_STYLES, content_type='text/css')

# ============================================
# 12. ЗАПУСК
# ============================================
async def main():
    load_cards()
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application()
    
    # Статика
    app.router.add_get('/', serve_html)
    app.router.add_get('/style.css', serve_css)
    
    # API
    app.router.add_get('/api/test', api_test)
    app.router.add_post('/api/game/state', api_get_state)
    app.router.add_post('/api/game/join', api_join_game)
    app.router.add_post('/api/game/start', api_start_game)
    app.router.add_post('/api/game/cards', api_get_cards)
    app.router.add_post('/api/game/reveal', api_reveal_card)
    app.router.add_post('/api/game/voting/players', api_get_voting_players)
    app.router.add_post('/api/game/vote', api_submit_vote)
    
    app.router.add_get('/health', lambda r: web.Response(text="OK"))
    
    # Запуск
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=PORT)
    
    print(f"✅ Сервер запущен на порту {PORT}")
    print(f"📱 Mini App: {WEBAPP_URL}")
    print(f"🧪 Тестовый API: {WEBAPP_URL}/api/test")
    
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
