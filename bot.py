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
print("📋 Логирование включено на уровень DEBUG")
print("=" * 60)

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
    "🤖 Бот-Снайпер", "🤖 Бот-Сапёр", "🤖 Бот-Медик"
]

# ============================================
# 5. ТЕКСТЫ
# ============================================
RULES_TEXT = """📖 **ПРАВИЛА ИГРЫ «КАФЕ ОАЗИС»**

🎯 **Цель:** Убедить других, что ты достоин попасть в убежище.

🃏 **Карты:** Каждый игрок получает 5 карт:
• Роль (профессия)
• Здоровье (физическое состояние)
• Навык (умение выживать)
• Предмет (полезная вещь)
• Секрет (личная тайна)

📋 **Ход игры:**
1️⃣ Каждый раунд игроки открывают по одной карте
2️⃣ После открытия всех карт — нажмите «Продолжить»
3️⃣ Когда все готовы — начинается голосование
4️⃣ Кто набрал больше голосов — выбывает и становится наблюдателем
5️⃣ Игра длится до последнего выжившего

🏆 **Победа:** Последний выживший получает кубок!
👀 **Наблюдатели:** Выбывшие игроки следят за игрой."""

# ============================================
# 6. HTML СТРАНИЦА
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
        
        <div id="debug-panel" style="background:#1a0a00;border:2px solid #ff6b35;border-radius:8px;padding:10px;margin-bottom:10px;font-size:0.7rem;font-family:monospace;min-height:120px;max-height:200px;overflow-y:auto;">
            <div style="color:#ff6b35;font-weight:bold;">📡 ОТЛАДКА:</div>
            <div id="debug-log" style="color:#f5e6d3;white-space:pre-wrap;word-break:break-all;"></div>
        </div>
        
        <div id="game-container">
            <div id="lobby">
                <h2>👥 Лобби</h2>
                <div id="players-list"></div>
                <button id="start-game" class="btn-neon">🔥 Начать игру</button>
            </div>
            <div id="game-area" style="display:none;">
                <div id="character-cards">
                    <h2>🎴 Твои карты</h2>
                    <div id="cards-container"></div>
                    <button id="reveal-card" class="btn-neon">🃏 Открыть карту</button>
                    <button id="continue-btn" class="btn-neon" style="display:none;background:#ff6b35;color:#0a0a0a;">▶️ Продолжить</button>
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
        
        function debugLog(message) {{
            var logEl = document.getElementById('debug-log');
            if (logEl) {{
                var timestamp = new Date().toLocaleTimeString();
                logEl.innerHTML += '[' + timestamp + '] ' + message + '\\n';
                logEl.scrollTop = logEl.scrollHeight;
            }}
            console.log(message);
        }}
        
        const gameState = {{
            playerId: null,
            gameId: null,
            players: [],
            myCards: [],
            revealedCards: [],
            currentRound: 0,
            maxRounds: 5,
            status: 'waiting',
            isHost: false,
        }};

        async function refreshGameState(retryCount) {{
            if (retryCount === undefined) retryCount = 0;
            debugLog('🔄 Обновление состояния (попытка ' + (retryCount + 1) + ')...');
            try {{
                var url = API_BASE + '/api/game/state';
                var response = await fetch(url, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        game_id: gameState.gameId,
                    }})
                }});
                
                if (!response.ok) {{
                    throw new Error('HTTP ' + response.status);
                }}
                
                var data = await response.json();
                debugLog('📦 Состояние: ' + JSON.stringify(data));
                
                if (data.game_id) {{
                    gameState.players = data.players || [];
                    gameState.status = data.status || 'waiting';
                    gameState.isHost = data.is_host || false;
                    gameState.currentRound = data.round || 0;
                    gameState.maxRounds = data.max_rounds || 5;
                    
                    updateUI();
                    
                    if (gameState.status === 'voting') {{
                        debugLog('🗳️ Статус "voting" — запускаем голосование');
                        await startVoting();
                    }}
                    
                    if (gameState.status === 'playing' || gameState.status === 'ready') {{
                        debugLog('🃏 Статус "' + gameState.status + '" — загружаем карты');
                        await getMyCards();
                    }}
                    
                    if (gameState.status === 'finished') {{
                        debugLog('🏆 Игра завершена!');
                        updateUI();
                    }}
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка обновления: ' + error.message);
                if (retryCount < 2) {{
                    setTimeout(function() {{
                        refreshGameState(retryCount + 1);
                    }}, 1000);
                }}
            }}
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            debugLog('✅ JS скрипт загружен!');
            
            const tg = window.Telegram.WebApp;
            tg.expand();
            tg.enableClosingConfirmation();
            
            if (typeof window.Telegram !== 'undefined' && window.Telegram.WebApp) {{
                debugLog('✅ Telegram WebApp найден!');
            }} else {{
                debugLog('❌ Telegram WebApp НЕ НАЙДЕН!');
                return;
            }}
            
            debugLog('🚀 DOM загружен!');
            
            var urlParams = new URLSearchParams(window.location.search);
            gameState.gameId = urlParams.get('game_id');
            var userIdFromUrl = urlParams.get('user_id');
            var userNameFromUrl = urlParams.get('user_name');
            
            if (userIdFromUrl) {{
                gameState.playerId = parseInt(userIdFromUrl);
                debugLog('👤 ID из URL: ' + gameState.playerId);
            }} else {{
                try {{
                    var initData = window.Telegram.WebApp.initDataUnsafe;
                    if (initData && initData.user) {{
                        gameState.playerId = initData.user.id;
                        debugLog('👤 ID из initData: ' + gameState.playerId);
                    }}
                }} catch(e) {{
                    debugLog('⚠️ Не удалось получить ID из initData');
                }}
                
                if (!gameState.playerId) {{
                    try {{
                        var hashParams = new URLSearchParams(window.location.hash.substring(1));
                        var tgWebAppData = hashParams.get('tgWebAppData');
                        if (tgWebAppData) {{
                            var parsed = JSON.parse(decodeURIComponent(tgWebAppData));
                            if (parsed && parsed.user && parsed.user.id) {{
                                gameState.playerId = parsed.user.id;
                                debugLog('👤 ID из hash: ' + gameState.playerId);
                            }}
                        }}
                    }} catch(e) {{
                        debugLog('⚠️ Не удалось распарсить tgWebAppData');
                    }}
                }}
            }}
            
            var userName = 'Игрок';
            if (userNameFromUrl) {{
                userName = decodeURIComponent(userNameFromUrl);
                debugLog('👤 Имя из URL: ' + userName);
            }} else {{
                try {{
                    var initData = window.Telegram.WebApp.initDataUnsafe;
                    if (initData && initData.user) {{
                        userName = initData.user.first_name || 'Игрок';
                        debugLog('👤 Имя из initData: ' + userName);
                    }}
                }} catch(e) {{
                    debugLog('⚠️ Не удалось получить имя из initData');
                }}
            }}
            
            if (!gameState.playerId) {{
                debugLog('⚠️ Нет данных пользователя!');
            }}
            
            if (gameState.gameId) {{
                debugLog('🎮 Game ID: ' + gameState.gameId);
            }} else {{
                debugLog('❌ Нет Game ID!');
                return;
            }}
            
            gameState.userName = userName;
            debugLog('👤 Итоговое имя: ' + userName);
            
            connectToGame();
            
            var startBtn = document.getElementById('start-game');
            if (startBtn) {{
                debugLog('✅ Кнопка "Начать" найдена');
                startBtn.addEventListener('click', function() {{
                    debugLog('🔄 НАЖАТА КНОПКА "НАЧАТЬ"!');
                    startGame();
                }});
            }}
            
            var revealBtn = document.getElementById('reveal-card');
            if (revealBtn) {{
                revealBtn.addEventListener('click', function() {{
                    debugLog('🔄 НАЖАТА КНОПКА "ОТКРЫТЬ КАРТУ"!');
                    revealCard();
                }});
            }}
            
            var continueBtn = document.getElementById('continue-btn');
            if (continueBtn) {{
                continueBtn.addEventListener('click', function() {{
                    debugLog('🔄 НАЖАТА КНОПКА "ПРОДОЛЖИТЬ"!');
                    continueGame();
                }});
            }}
            
            var voteBtn = document.getElementById('vote-btn');
            if (voteBtn) {{
                voteBtn.addEventListener('click', function() {{
                    debugLog('🔄 НАЖАТА КНОПКА "ПРОГОЛОСОВАТЬ"!');
                    submitVote();
                }});
            }}
            
            debugLog('✅ Инициализация завершена');
        }});

        async function connectToGame() {{
            debugLog('🔄 Подключение к API...');
            try {{
                var url = API_BASE + '/api/game/state';
                var response = await fetch(url, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        game_id: gameState.gameId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ: ' + JSON.stringify(data));
                
                if (data.game_id) {{
                    gameState.players = data.players || [];
                    gameState.status = data.status || 'waiting';
                    gameState.isHost = data.is_host || false;
                    gameState.currentRound = data.round || 0;
                    gameState.maxRounds = data.max_rounds || 5;
                    
                    var playerExists = gameState.players.some(function(p) {{
                        return String(p.id) === String(gameState.playerId);
                    }});
                    
                    if (!playerExists && gameState.status === 'waiting') {{
                        await joinGame();
                        await refreshGameState();
                    }}
                    
                    updateUI();
                    
                    if (gameState.status === 'playing' || gameState.status === 'ready') {{
                        await getMyCards();
                    }}
                    
                    if (gameState.status === 'voting') {{
                        await startVoting();
                    }}
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка: ' + error.message);
            }}
        }}

        async function joinGame() {{
            try {{
                var userName = gameState.userName || 'Игрок';
                var response = await fetch(API_BASE + '/api/game/join', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        player_name: userName,
                        username: '',
                        game_id: gameState.gameId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.players = data.players || [];
                    updateUI();
                    debugLog('✅ Присоединился: ' + userName);
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка присоединения: ' + error.message);
            }}
        }}

        async function startGame() {{
            debugLog('🔄 ЗАПУСК startGame()');
            
            if (!gameState.isHost) {{
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '⛔',
                    message: 'Только ведущий может начать игру!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            if (gameState.players.length < 4) {{
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '👥',
                    message: 'Нужно минимум 4 игрока! Сейчас: ' + gameState.players.length,
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            try {{
                var response = await fetch(API_BASE + '/api/game/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.status = 'playing';
                    updateUI();
                    await refreshGameState();
                    await getMyCards();
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка: ' + error.message);
            }}
        }}

        async function getMyCards() {{
            try {{
                var response = await fetch(API_BASE + '/api/game/cards', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        game_id: gameState.gameId,
                    }})
                }});
                
                var data = await response.json();
                
                if (data.status === 'success') {{
                    gameState.myCards = data.cards || [];
                    gameState.revealedCards = data.revealed || [];
                    renderCards();
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка получения карт: ' + error.message);
            }}
        }}

        async function revealCard() {{
            debugLog('🃏 Открытие карты...');
            var cardIndex = gameState.myCards.findIndex(function(c) {{
                return !c.isRevealed;
            }});
            
            if (cardIndex === -1) {{
                debugLog('⚠️ Все карты уже открыты');
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '🃏',
                    message: 'Все карты уже открыты!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            try {{
                var response = await fetch(API_BASE + '/api/game/reveal', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                        card_index: cardIndex,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ открытия карты: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.myCards[cardIndex].isRevealed = true;
                    gameState.revealedCards = data.revealed_cards || [];
                    renderCards();
                    debugLog('✅ Карта открыта, осталось: ' + gameState.myCards.filter(function(c) {{ return !c.isRevealed; }}).length);
                    
                    setTimeout(function() {{
                        refreshGameState();
                    }}, 1500);
                }} else {{
                    debugLog('❌ Ошибка открытия карты: ' + (data.message || 'неизвестно'));
                    var tg = window.Telegram.WebApp;
                    tg.showPopup({{
                        title: '❌',
                        message: data.message || 'Ошибка открытия карты',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка открытия карты: ' + error.message);
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '❌',
                    message: 'Ошибка: ' + error.message,
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
            }}
        }}

        async function continueGame() {{
            debugLog('▶️ КНОПКА "ПРОДОЛЖИТЬ" НАЖАТА!');
            
            document.getElementById('continue-btn').style.display = 'none';
            document.getElementById('continue-btn').disabled = true;
            
            try {{
                var response = await fetch(API_BASE + '/api/game/continue', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        game_id: gameState.gameId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ continue: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    if (data.all_ready) {{
                        debugLog('🔥 Все готовы! Начинаем голосование!');
                        await refreshGameState();
                        updateUI();
                        await startVoting();
                    }} else {{
                        debugLog('⏳ Ожидаем остальных игроков... (' + data.ready_count + '/' + data.total_players + ')');
                        document.getElementById('continue-btn').textContent = '⏳ Ожидание остальных (' + data.ready_count + '/' + data.total_players + ')';
                        document.getElementById('continue-btn').style.display = 'block';
                        document.getElementById('continue-btn').disabled = true;
                        
                        setTimeout(function() {{
                            refreshGameState();
                        }}, 2000);
                    }}
                }} else {{
                    debugLog('❌ Ошибка: ' + (data.message || 'неизвестно'));
                    document.getElementById('continue-btn').style.display = 'block';
                    document.getElementById('continue-btn').textContent = '▶️ Продолжить';
                    document.getElementById('continue-btn').disabled = false;
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка продолжения: ' + error.message);
                document.getElementById('continue-btn').style.display = 'block';
                document.getElementById('continue-btn').textContent = '▶️ Продолжить';
                document.getElementById('continue-btn').disabled = false;
            }}
        }}

        async function startVoting() {{
            debugLog('🗳️ ЗАПУСК ГОЛОСОВАНИЯ...');
            gameState.status = 'voting';
            updateUI();
            
            try {{
                var response = await fetch(API_BASE + '/api/game/voting/players', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                var data = await response.json();
                
                if (data.status === 'success') {{
                    renderVotingList(data.players);
                    document.getElementById('vote-btn').disabled = false;
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка голосования: ' + error.message);
            }}
        }}

        function renderVotingList(players) {{
            var container = document.getElementById('voting-list');
            container.innerHTML = '';
            
            if (!players || players.length === 0) {{
                container.innerHTML = '<p style="opacity:0.7;">Нет игроков для голосования</p>';
                return;
            }}
            
            players.forEach(function(player) {{
                var card = document.createElement('div');
                card.className = 'character-card voting-card';
                var roleText = player.role || 'Без роли';
                card.innerHTML = `
                    <div class="card-type">Игрок</div>
                    <div class="card-name">${{player.name}}</div>
                    <div class="card-effect">${{roleText}}</div>
                    <input type="radio" name="vote" value="${{player.id}}" id="vote-${{player.id}}">
                    <label for="vote-${{player.id}}">Голосовать</label>
                `;
                container.appendChild(card);
            }});
            
            document.getElementById('vote-btn').disabled = false;
        }}

        async function submitVote() {{
            debugLog('🗳️ ОТПРАВКА ГОЛОСА...');
            var selected = document.querySelector('input[name="vote"]:checked');
            
            if (!selected) {{
                debugLog('⚠️ Не выбран игрок');
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '⚠️',
                    message: 'Выберите игрока!',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            var targetId = parseInt(selected.value);
            debugLog('🎯 Голос за ID: ' + targetId);
            
            try {{
                var response = await fetch(API_BASE + '/api/game/vote', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        game_id: gameState.gameId,
                        player_id: gameState.playerId,
                        target_id: targetId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ голосования: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    document.getElementById('vote-btn').disabled = true;
                    debugLog('✅ Голос учтён!');
                    
                    if (data.game_finished) {{
                        debugLog('🏆 Игра завершена!');
                        if (data.winner === 'human') {{
                            var tg = window.Telegram.WebApp;
                            tg.showPopup({{
                                title: '🏆 ПОБЕДА!',
                                message: '🎉 ' + data.winner_name + ' выжил в кафе ОАЗИС!',
                                buttons: [{{text: '🎊 Ура!', type: 'default'}}]
                            }});
                        }} else if (data.winner === 'bots') {{
                            var tg = window.Telegram.WebApp;
                            tg.showPopup({{
                                title: '🤖',
                                message: 'Боты захватили кафе! Люди проиграли.',
                                buttons: [{{text: '😢 OK', type: 'default'}}]
                            }});
                        }}
                        await refreshGameState();
                    }} else if (data.all_voted) {{
                        debugLog('🔥 Все проголосовали!');
                        setTimeout(function() {{
                            refreshGameState();
                        }}, 1500);
                    }} else {{
                        debugLog('⏳ Ожидаем остальных игроков...');
                        setTimeout(function() {{
                            refreshGameState();
                        }}, 2500);
                    }}
                }} else {{
                    debugLog('❌ Ошибка голосования: ' + (data.message || 'неизвестно'));
                    var tg = window.Telegram.WebApp;
                    tg.showPopup({{
                        title: '❌',
                        message: data.message || 'Ошибка голосования',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка отправки голоса: ' + error.message);
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '❌',
                    message: 'Ошибка: ' + error.message,
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
            }}
        }}

        function updateUI() {{
            var lobby = document.getElementById('lobby');
            var gameArea = document.getElementById('game-area');
            var votingArea = document.getElementById('voting-area');
            var results = document.getElementById('results');
            
            if (gameState.status === 'waiting' || gameState.status === 'lobby') {{
                lobby.style.display = 'block';
                gameArea.style.display = 'none';
                votingArea.style.display = 'none';
                results.style.display = 'none';
                renderPlayersList();
            }} else if (gameState.status === 'voting') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'block';
                document.getElementById('character-cards').style.display = 'none';
                votingArea.style.display = 'block';
                results.style.display = 'none';
            }} else if (gameState.status === 'playing' || gameState.status === 'ready') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'block';
                document.getElementById('character-cards').style.display = 'block';
                votingArea.style.display = 'none';
                results.style.display = 'none';
            }} else if (gameState.status === 'finished') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'none';
                votingArea.style.display = 'none';
                results.style.display = 'block';
            }}
        }}

        function renderPlayersList() {{
            var container = document.getElementById('players-list');
            container.innerHTML = '';
            
            gameState.players.forEach(function(player) {{
                var div = document.createElement('div');
                div.className = 'player-item';
                var hostBadge = player.isHost ? '<span class="host-badge">⭐ Ведущий</span>' : '';
                var isBot = player.is_bot ? '🤖 ' : '';
                var observerBadge = player.is_observer ? '👀 ' : '';
                div.innerHTML = `
                    <span>${{observerBadge}}${{isBot}}👤 ${{player.name}}</span>
                    ${{hostBadge}}
                `;
                container.appendChild(div);
            }});
            
            var startBtn = document.getElementById('start-game');
            if (gameState.players.length >= 4 && gameState.isHost) {{
                startBtn.style.display = 'block';
                startBtn.textContent = '🔥 Начать игру (' + gameState.players.length + ' игроков)';
                startBtn.disabled = false;
            }} else if (gameState.isHost) {{
                startBtn.style.display = 'block';
                startBtn.textContent = '👥 Нужно ещё ' + (4 - gameState.players.length) + ' игроков';
                startBtn.disabled = true;
            }} else {{
                startBtn.style.display = 'none';
            }}
        }}

        function renderCards() {{
            var container = document.getElementById('cards-container');
            container.innerHTML = '';
            
            // Проверяем, в режиме ли наблюдения игрок
            var isObserver = false;
            for (var i = 0; i < gameState.players.length; i++) {{
                if (String(gameState.players[i].id) === String(gameState.playerId)) {{
                    if (gameState.players[i].is_observer) {{
                        isObserver = true;
                    }}
                    break;
                }}
            }}
            
            // ★★★ ЕСЛИ ИГРОК В РЕЖИМЕ НАБЛЮДЕНИЯ ★★★
            if (isObserver) {{
                var activePlayers = gameState.players.filter(function(p) {{ return !p.is_observer; }});
                var humanPlayers = activePlayers.filter(function(p) {{ return !p.is_bot; }});
                var botPlayers = activePlayers.filter(function(p) {{ return p.is_bot; }});
                
                var statusText = '';
                if (activePlayers.length === 0) {{
                    statusText = '💀 Все игроки выбыли. Игра завершена.';
                }} else if (humanPlayers.length === 0 && botPlayers.length > 0) {{
                    statusText = '🤖 Остались только боты. Игра скоро завершится.';
                }} else if (humanPlayers.length === 1 && botPlayers.length === 0) {{
                    statusText = '🏆 Остался 1 игрок! Скоро будет победитель!';
                }} else {{
                    statusText = '👥 Активных игроков: ' + activePlayers.length + ' (людей: ' + humanPlayers.length + ', ботов: ' + botPlayers.length + ')';
                }}
                
                container.innerHTML = `
                    <div style="text-align:center;padding:30px;background:#1a0a00;border-radius:12px;border:2px solid #ff6b35;">
                        <h2 style="color:#ff6b35;font-size:2rem;">👀 РЕЖИМ НАБЛЮДЕНИЯ</h2>
                        <p style="opacity:0.8;margin-top:10px;font-size:1.1rem;">${{statusText}}</p>
                        <p style="opacity:0.5;margin-top:5px;">Следите за игрой в реальном времени!</p>
                        <button id="refresh-btn" class="btn-neon" style="margin-top:20px;border-color:#ff6b35;color:#ff6b35;">🔄 Обновить</button>
                    </div>
                `;
                
                document.getElementById('reveal-card').style.display = 'none';
                document.getElementById('continue-btn').style.display = 'none';
                
                document.getElementById('refresh-btn')?.addEventListener('click', function() {{
                    refreshGameState();
                }});
                
                return;
            }}
            
            // ★★★ ЕСЛИ КАРТЫ НЕ ЗАГРУЖЕНЫ ★★★
            if (!gameState.myCards || gameState.myCards.length === 0) {{
                container.innerHTML = '<p style="opacity:0.7;">Карты не загружены</p>';
                return;
            }}
            
            // Отображаем карты
            gameState.myCards.forEach(function(card) {{
                var div = document.createElement('div');
                div.className = 'character-card';
                
                if (card.isRevealed) {{
                    div.style.borderColor = '#ff6b35';
                    div.style.opacity = '1';
                }} else {{
                    div.style.borderColor = '#666';
                    div.style.opacity = '0.7';
                }}
                
                var cardName = card.isRevealed ? card.name : '❓ Скрыто';
                var cardEffect = card.isRevealed ? (card.effect || card.description || '') : 'Нажмите "Открыть карту"';
                var cardRarity = card.isRevealed ? '<div class="card-rarity">⭐ ' + (card.rarity || 'Обычная') + '</div>' : '';
                
                div.innerHTML = `
                    <div class="card-type">${{card.type || 'Карта'}}</div>
                    <div class="card-name">${{cardName}}</div>
                    <div class="card-effect">${{cardEffect}}</div>
                    ${{cardRarity}}
                `;
                container.appendChild(div);
            }});
            
            var remaining = gameState.myCards.filter(function(c) {{ return !c.isRevealed; }}).length;
            
            var revealBtn = document.getElementById('reveal-card');
            var continueBtn = document.getElementById('continue-btn');
            
            // ★★★ УПРАВЛЕНИЕ КНОПКАМИ ★★★
            if (gameState.status === 'ready') {{
                revealBtn.style.display = 'none';
                continueBtn.style.display = 'block';
                continueBtn.textContent = '▶️ Продолжить';
                continueBtn.disabled = false;
            }} else if (remaining === 0) {{
                revealBtn.style.display = 'none';
                continueBtn.style.display = 'block';
                continueBtn.textContent = '▶️ Продолжить';
                continueBtn.disabled = false;
            }} else {{
                revealBtn.style.display = 'block';
                revealBtn.textContent = '🃏 Открыть карту (осталось: ' + remaining + ')';
                revealBtn.disabled = false;
                continueBtn.style.display = 'none';
            }}
        }}

        // ★★★ АВТООБНОВЛЕНИЕ КАЖДЫЕ 1.5 СЕКУНДЫ ★★★
        setInterval(async function() {{
            if (gameState.status !== 'finished') {{
                try {{
                    var response = await fetch(API_BASE + '/api/game/state', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            player_id: gameState.playerId,
                            game_id: gameState.gameId,
                        }})
                    }});
                    
                    var data = await response.json();
                    
                    if (data.game_id && data.status && data.status !== gameState.status) {{
                        debugLog('🔄 Статус изменился: ' + gameState.status + ' -> ' + data.status);
                        gameState.status = data.status;
                        gameState.players = data.players || [];
                        gameState.isHost = data.is_host || false;
                        updateUI();
                        
                        if (data.status === 'voting') {{
                            await startVoting();
                        }}
                        
                        if (data.status === 'playing' || data.status === 'ready') {{
                            await getMyCards();
                        }}
                    }}
                }} catch (error) {{
                    // Игнорируем ошибки фонового обновления
                }}
            }}
        }}, 1500);

        debugLog('✅ Mini App готов!');
        debugLog('🔄 Автообновление каждые 1.5 секунды');
    </script>
</body>
</html>'''

# ============================================
# 7. CSS СТИЛИ
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
.btn-neon:hover:not(:disabled) {
    background: #ff6b35;
    color: #0a0a0a;
    box-shadow: 0 0 30px rgba(255, 107, 53, 0.6);
}
.btn-neon:disabled {
    opacity: 0.4;
    cursor: not-allowed;
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
# 8. ЗАГРУЗКА КАРТ
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
# 9. КОМАНДЫ БОТА
# ============================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤠 Добро пожаловать в КАФЕ ОАЗИС!\n\n"
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
        "/rules - Показать правила игры",
        parse_mode="Markdown"
    )

@dp.message(Command("play"))
async def cmd_play(message: types.Message):
    """Отправить игру в чат через send_game"""
    
    print("=" * 60)
    print("🎮 КОМАНДА /play")
    print(f"👤 Пользователь: {message.from_user.id} ({message.from_user.first_name})")
    print(f"💬 Chat ID: {message.chat.id}")
    print("=" * 60)
    
    chat_id = str(message.chat.id)
    user_id = message.from_user.id
    user_name = message.from_user.first_name or message.from_user.username or 'Игрок'
    
    if chat_id in games:
        game = games[chat_id]
        game_id = game['game_id']
        print(f"✅ Найдена существующая игра: {game_id}")
        
        if game['status'] == 'finished':
            print("⚠️ Игра завершена, создаём новую")
            del games[chat_id]
            game_id = str(uuid.uuid4())[:8]
            games[chat_id] = {
                'game_id': game_id,
                'chat_id': chat_id,
                'players': [],
                'status': 'waiting',
                'round': 0,
                'max_rounds': 5,
                'host_id': str(user_id),
                'host_name': user_name,
                'created_at': datetime.now().isoformat(),
                'votes': {},
                'eliminated': [],
                'players_ready': [],
            }
            print(f"🆕 Создана новая игра: {game_id}")
    else:
        game_id = str(uuid.uuid4())[:8]
        print(f"🆕 Создаём новую игру: {game_id}")
        games[chat_id] = {
            'game_id': game_id,
            'chat_id': chat_id,
            'players': [],
            'status': 'waiting',
            'round': 0,
            'max_rounds': 5,
            'host_id': str(user_id),
            'host_name': user_name,
            'created_at': datetime.now().isoformat(),
            'votes': {},
            'eliminated': [],
            'players_ready': [],
        }
        print(f"✅ Игра создана: {games[chat_id]}")
    
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
    
    print("✅ Игра отправлена в чат!")
    print("=" * 60)

@dp.message(Command("addbots"))
async def cmd_add_bots(message: types.Message):
    """Добавить ботов в игру (только ведущий)"""
    
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Сначала создай игру через /play")
        return
    
    game = games[chat_id]
    
    if str(message.from_user.id) != str(game['host_id']):
        await message.answer("⛔ Только ведущий может добавлять ботов!")
        return
    
    if game['status'] != 'waiting':
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
    
    current_players = len(game['players'])
    max_players = 6
    available = max_players - current_players
    
    if count > available:
        await message.answer(f"❌ Можно добавить максимум {available} ботов (сейчас {current_players} игроков)")
        return
    
    bot_count = 0
    added_names = []
    used_names = [p['name'] for p in game['players']]
    
    for i in range(count):
        available_names = [n for n in BOT_NAMES if n not in used_names]
        if not available_names:
            break
        
        bot_name = available_names[0]
        used_names.append(bot_name)
        bot_id = f"bot_{uuid.uuid4().hex[:6]}"
        
        player = {
            'id': bot_id,
            'name': bot_name,
            'username': '',
            'is_host': False,
            'is_bot': True,
            'is_observer': False,
            'cards': [],
            'revealed': [],
        }
        game['players'].append(player)
        added_names.append(bot_name)
        bot_count += 1
    
    await message.answer(
        f"🤖 Добавлено {bot_count} ботов:\n"
        f"{', '.join(added_names)}\n\n"
        f"👥 Всего игроков: {len(game['players'])} из 6\n"
        f"🎮 Статус: {game['status']}"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Напиши /play чтобы начать")
        return
    
    game = games[chat_id]
    bot_count = sum(1 for p in game['players'] if p.get('is_bot', False))
    human_count = len(game['players']) - bot_count
    observer_count = sum(1 for p in game['players'] if p.get('is_observer', False))
    active_count = len(game['players']) - observer_count
    
    await message.answer(
        f"📊 **Статус игры:**\n"
        f"🎮 Game ID: `{game['game_id']}`\n"
        f"👑 Ведущий: {game['host_name']}\n"
        f"👥 Всего игроков: {len(game['players'])}\n"
        f"👤 Активных: {active_count}\n"
        f"👀 Наблюдателей: {observer_count}\n"
        f"🤖 Ботов: {bot_count}\n"
        f"📝 Статус: {game['status']}\n"
        f"📊 Раунд: {game['round']} из {game['max_rounds']}",
        parse_mode="Markdown"
    )

@dp.message(Command("host"))
async def cmd_host(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры. Напиши /play чтобы начать")
        return
    
    game = games[chat_id]
    
    if str(message.from_user.id) != str(game['host_id']):
        await message.answer("⛔ Только текущий ведущий может назначить нового!")
        return
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_id = str(target_user.id)
        target_name = target_user.first_name or target_user.username or f"User {target_id}"
        
        player_in_game = False
        for player in game['players']:
            if str(player['id']) == target_id:
                player_in_game = True
                break
        
        if not player_in_game:
            await message.answer(f"❌ Игрок {target_name} не в игре!")
            return
        
        game['host_id'] = target_id
        game['host_name'] = target_name
        
        for player in game['players']:
            player['is_host'] = str(player['id']) == target_id
        
        await message.answer(f"👑 Ведущий передан {target_name}")
        return
    
    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.answer(
            "❌ Использование:\n"
            "/host - ответь на сообщение игрока\n"
            "/host 123456789 - по Telegram ID\n"
            "/host @username - по username"
        )
        return
    
    target_input = command_parts[1].strip()
    
    if target_input.isdigit():
        target_id = target_input
        found_player = None
        for player in game['players']:
            if str(player['id']) == target_id:
                found_player = player
                break
        
        if found_player:
            game['host_id'] = target_id
            game['host_name'] = found_player['name']
            for player in game['players']:
                player['is_host'] = str(player['id']) == target_id
            await message.answer(f"👑 Ведущий передан {found_player['name']}")
            return
        else:
            await message.answer(f"❌ Игрок с ID {target_id} не найден в игре")
            return
    
    username = target_input.replace('@', '').lower()
    found_player = None
    for player in game['players']:
        if player.get('name', '').lower() == username:
            found_player = player
            break
        if player.get('username', '').lower() == username:
            found_player = player
            break
    
    if found_player:
        target_id = str(found_player['id'])
        game['host_id'] = target_id
        game['host_name'] = found_player['name']
        for player in game['players']:
            player['is_host'] = str(player['id']) == target_id
        await message.answer(f"👑 Ведущий передан {found_player['name']}")
        return
    
    await message.answer(f"❌ Игрок {target_input} не найден в игре")

@dp.message(Command("whohost"))
async def cmd_whohost(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры")
        return
    
    game = games[chat_id]
    host_name = game.get('host_name', 'Неизвестно')
    host_id = game.get('host_id', 'Нет ID')
    
    host_in_game = False
    for player in game['players']:
        if str(player['id']) == str(host_id):
            host_in_game = True
            host_name = player['name']
            break
    
    await message.answer(
        f"👑 **Текущий ведущий:**\n"
        f"Имя: {host_name}\n"
        f"Статус: {'✅ В игре' if host_in_game else '❌ Не в игре'}\n"
        f"👥 Всего игроков: {len(game['players'])}",
        parse_mode="Markdown"
    )

@dp.message(Command("stop"))
async def cmd_stop_game(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры")
        return
    
    game = games[chat_id]
    
    if str(message.from_user.id) != str(game['host_id']):
        await message.answer("⛔ Только ведущий может остановить игру!")
        return
    
    del games[chat_id]
    await message.answer("⛔ Игра остановлена ведущим!")

@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    await message.answer(RULES_TEXT, parse_mode="Markdown")

# ============================================
# 10. ОБРАБОТЧИК ДЛЯ TELEGRAM GAMES
# ============================================
@dp.callback_query(lambda c: c.game_short_name is not None)
async def game_callback(callback: types.CallbackQuery):
    """Обработка нажатия на кнопку Play в игре"""
    
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
    
    if chat_id in games:
        game = games[chat_id]
        game_id = game['game_id']
        print(f"✅ Найдена существующая игра: {game_id}")
    else:
        game_id = str(uuid.uuid4())[:8]
        print(f"🆕 Создаём новую игру: {game_id}")
        games[chat_id] = {
            'game_id': game_id,
            'chat_id': chat_id,
            'players': [],
            'status': 'waiting',
            'round': 0,
            'max_rounds': 5,
            'host_id': str(user_id),
            'host_name': user_name,
            'created_at': datetime.now().isoformat(),
            'votes': {},
            'eliminated': [],
            'players_ready': [],
        }
        print(f"✅ Игра создана: {games[chat_id]}")
    
    game_url = f"{WEBAPP_URL}?game_id={game_id}&user_id={user_id}&user_name={user_name_encoded}"
    print(f"🔗 URL игры: {game_url}")
    
    await callback.answer(url=game_url)
    print("✅ Ответ отправлен с URL игры!")
    print("=" * 60)

# ============================================
# 11. ГЕНЕРАЦИЯ КАРТ
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
# 12. ФУНКЦИИ ДЛЯ БОТОВ
# ============================================

def bot_reveal_all_cards(game):
    """Боты открывают все свои карты"""
    if not game:
        return
    
    for player in game['players']:
        if player.get('is_bot', False):
            for card in player['cards']:
                card['isRevealed'] = True
            player['revealed'] = player['cards'].copy()
            print(f"🤖 Бот {player['name']} открыл все карты")

def bot_decide_vote(game, player_id):
    """Бот выбирает, за кого голосовать (случайно)"""
    if not game or not game['players']:
        return None
    
    # Боты голосуют только за активных игроков (не наблюдателей)
    available = [p for p in game['players'] if str(p['id']) != str(player_id) and not p.get('is_observer', False)]
    if available:
        return random.choice(available)['id']
    return None

# ============================================
# 12.5. ФУНКЦИЯ ПРОВЕРКИ ОТКРЫТИЯ ВСЕХ КАРТ
# ============================================
def check_all_cards_revealed(game):
    """Проверяет, открыли ли все живые игроки все карты"""
    if not game:
        return False
    
    # Только игроки, которые ещё в игре (не выбыли)
    active_players = [p for p in game['players'] if not p.get('is_observer', False)]
    
    if not active_players:
        return False
    
    all_revealed = True
    for player in active_players:
        cards = player.get('cards', [])
        revealed = player.get('revealed', [])
        if len(revealed) < len(cards):
            all_revealed = False
            break
    
    if all_revealed:
        game['status'] = 'ready'
        game['players_ready'] = []
        return True
    
    return False

# ============================================
# 13. API ОБРАБОТЧИКИ
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
            print(f"❌ Игра не найдена: {game_id}")
            return web.json_response({'status': 'error', 'message': 'Игра не найдена'}, status=404)
        
        print(f"✅ Игра найдена")
        
        player = None
        is_observer = False
        if player_id:
            player = next((p for p in game['players'] if str(p['id']) == str(player_id)), None)
            if player:
                is_observer = player.get('is_observer', False)
        
        return web.json_response({
            'game_id': game['game_id'],
            'status': game['status'],
            'players': game['players'],
            'round': game['round'],
            'max_rounds': game['max_rounds'],
            'is_host': str(game['host_id']) == str(player_id) if player_id else False,
            'is_observer': is_observer,
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
        username = data.get('username', '')
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
        
        if player_id and any(str(p['id']) == str(player_id) for p in game['players']):
            return web.json_response({
                'status': 'success',
                'message': 'Игрок уже в игре',
                'players': game['players'],
            })
        
        is_host = str(game['host_id']) == str(player_id) if player_id else False
        
        player = {
            'id': str(player_id) if player_id else 'unknown',
            'name': player_name,
            'username': username,
            'is_host': is_host,
            'is_bot': False,
            'is_observer': False,
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
            return web.json_response({'status': 'error', 'message': 'Только ведущий может начать игру'}, status=403)
        
        if len(game['players']) < 4:
            return web.json_response({'status': 'error', 'message': 'Нужно минимум 4 игрока'}, status=400)
        
        # ★★★ ПРОВЕРКА: если в игре только боты ★★★
        if all(p.get('is_bot', False) for p in game['players']):
            game['status'] = 'finished'
            await bot.send_message(
                game['chat_id'],
                f"🤖 **ПОБЕДА БОТОВ!**\n\n"
                f"В игре не было людей. Боты захватили кафе ОАЗИС!"
            )
            return web.json_response({'status': 'success', 'message': 'Игра завершена (только боты)'})
        
        for player in game['players']:
            player['cards'] = generate_cards_for_player()
            player['revealed'] = []
            player['is_observer'] = False
        
        game['players_ready'] = []
        bot_reveal_all_cards(game)
        
        game['status'] = 'playing'
        game['round'] = 1
        
        await bot.send_message(
            game['chat_id'],
            f"🔥 ИГРА НАЧАЛАСЬ!\n\n👥 Игроков: {len(game['players'])}\n📝 Раунд 1 из {game['max_rounds']}\n\n🤖 Боты уже открыли свои карты!"
        )
        
        await check_all_revealed(game)
        
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
        
        # ★★★ ПРОВЕРКА: если игрок в режиме наблюдения ★★★
        if player.get('is_observer', False):
            return web.json_response({
                'status': 'error', 
                'message': 'Вы в режиме наблюдения и не можете открывать карты'
            }, status=403)
        
        if card_index >= len(player['cards']):
            return web.json_response({'status': 'error', 'message': 'Неверный индекс'}, status=400)
        
        card = player['cards'][card_index]
        if card.get('isRevealed', False):
            return web.json_response({'status': 'error', 'message': 'Эта карта уже открыта'}, status=400)
        
        card['isRevealed'] = True
        player['revealed'].append(card)
        
        # Боты всегда открывают все карты сразу
        bot_reveal_all_cards(game)
        
        # ★★★ ПРОВЕРЯЕМ, ВСЕ ЛИ ОТКРЫЛИ КАРТЫ (БЕЗ ПЕРЕВОДА В НАБЛЮДАТЕЛИ) ★★★
        all_revealed = check_all_cards_revealed(game)
        
        if all_revealed:
            await bot.send_message(
                game['chat_id'],
                f"📢 Все игроки открыли карты!\n\nНажмите **«Продолжить»** в приложении, чтобы перейти к голосованию.",
                parse_mode="Markdown"
            )
        
        return web.json_response({
            'status': 'success',
            'card': card,
            'revealed_cards': player['revealed'],
            'all_revealed': all_revealed,
            'is_observer': player.get('is_observer', False),
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_continue(request):
    """Обработчик нажатия кнопки 'Продолжить'"""
    print(f"📨 CONTINUE запрос")
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
        
        # ★★★ ПРОВЕРЯЕМ, В ИГРЕ ЛИ ИГРОК (НЕ НАБЛЮДАТЕЛЬ) ★★★
        player = next((p for p in game['players'] if str(p['id']) == str(player_id)), None)
        if not player:
            return web.json_response({
                'status': 'success',
                'all_ready': False,
                'message': 'Игрок выбыл, не участвует',
                'ready_count': len(game.get('players_ready', [])),
                'total_players': len(game['players']),
                'is_observer': True,
            })
        
        # Если игрок в режиме наблюдения — он не может нажимать "Продолжить"
        if player.get('is_observer', False):
            return web.json_response({
                'status': 'success',
                'all_ready': False,
                'message': 'Вы в режиме наблюдения',
                'ready_count': len(game.get('players_ready', [])),
                'total_players': len(game['players']),
                'is_observer': True,
            })
        
        if game['status'] != 'ready':
            return web.json_response({'status': 'error', 'message': 'Игра не в состоянии готовности'}, status=400)
        
        if 'players_ready' not in game:
            game['players_ready'] = []
        
        if str(player_id) not in game['players_ready']:
            game['players_ready'].append(str(player_id))
            print(f"✅ Игрок {player_id} готов продолжить")
        
        # Боты всегда готовы
        for p in game['players']:
            if p.get('is_bot', False) and str(p['id']) not in game['players_ready']:
                game['players_ready'].append(str(p['id']))
                print(f"🤖 Бот {p['name']} готов продолжить")
        
        all_ready = len(game['players_ready']) >= len([p for p in game['players'] if not p.get('is_observer', False)])
        
        if all_ready:
            game['status'] = 'voting'
            game['players_ready'] = []
            print(f"🗳️ Все игроки готовы! Начинаем голосование")
            await bot.send_message(
                game['chat_id'],
                f"🗳️ **ГОЛОСОВАНИЕ!**\n\nВсе игроки готовы. Голосуйте в приложении!\n👀 Наблюдатели следят за голосованием."
            )
        
        return web.json_response({
            'status': 'success',
            'all_ready': all_ready,
            'ready_count': len(game['players_ready']),
            'total_players': len([p for p in game['players'] if not p.get('is_observer', False)]),
            'is_observer': player.get('is_observer', False),
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
        
        # Только активные игроки (не наблюдатели) могут голосовать
        players_for_vote = [
            {
                'id': str(p['id']),
                'name': p['name'],
                'role': next((c['name'] for c in p['cards'] if c.get('isRevealed') and c.get('type') == 'Роль'), 'Неизвестно')
            }
            for p in game['players']
            if str(p['id']) != str(player_id) and not p.get('is_observer', False)
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
        
        # Проверяем, не наблюдатель ли игрок
        voter = next((p for p in game['players'] if str(p['id']) == str(player_id)), None)
        if voter and voter.get('is_observer', False):
            return web.json_response({
                'status': 'error', 
                'message': 'Вы в режиме наблюдения и не можете голосовать'
            }, status=403)
        
        game['votes'][str(player_id)] = str(target_id)
        
        # Боты голосуют автоматически
        for p in game['players']:
            if p.get('is_bot', False) and str(p['id']) not in game['votes']:
                target = bot_decide_vote(game, p['id'])
                if target:
                    game['votes'][str(p['id'])] = str(target)
                    print(f"🤖 Бот {p['name']} проголосовал за {target}")
        
        all_voted = len(game['votes']) >= len([p for p in game['players'] if not p.get('is_observer', False)])
        
        if all_voted:
            vote_results = {}
            for voter_id, target in game['votes'].items():
                vote_results[target] = vote_results.get(target, 0) + 1
            
            max_votes = max(vote_results.values())
            eliminated = [p for p in game['players'] if str(p['id']) in vote_results and vote_results[str(p['id'])] == max_votes]
            
            if eliminated:
                eliminated_player = eliminated[0]
                
                # ★★★ ВЫБЫВШИЙ СТАНОВИТСЯ НАБЛЮДАТЕЛЕМ ★★★
                eliminated_player['is_observer'] = True
                
                # Удаляем из активных игроков (но оставляем в списке для истории)
                game['players'] = [p for p in game['players'] if str(p['id']) != str(eliminated_player['id'])]
                game['eliminated'].append(eliminated_player)
                
                await bot.send_message(
                    game['chat_id'],
                    f"🧟 **ВЫБЫВАЕТ:** {eliminated_player['name']}\n\n"
                    f"Голосов: {max_votes} из {len(game['votes'])}\n"
                    f"Осталось: {len([p for p in game['players'] if not p.get('is_observer', False)])} игроков\n\n"
                    f"👀 {eliminated_player['name']} теперь наблюдает за игрой!"
                )
                
                # ★★★ ОТПРАВЛЯЕМ ЛИЧНОЕ СООБЩЕНИЕ ВЫБЫВШЕМУ ★★★
                try:
                    await bot.send_message(
                        int(eliminated_player['id']) if str(eliminated_player['id']).isdigit() else eliminated_player['id'],
                        f"💀 **Вас выгнали из игры!**\n\n"
                        f"Но вы можете наблюдать за её продолжением.\n"
                        f"Откройте игру снова, чтобы увидеть, что происходит.",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"⚠️ Не удалось отправить сообщение выбывшему: {e}")
            
            # ★★★ ПРОВЕРЯЕМ, КТО ОСТАЛСЯ ★★★
            active_players = [p for p in game['players'] if not p.get('is_observer', False)]
            human_players = [p for p in active_players if not p.get('is_bot', False)]
            bot_players = [p for p in active_players if p.get('is_bot', False)]
            
            # Сценарий 1: Остались только боты → победа ботов
            if len(human_players) == 0 and len(bot_players) > 0:
                game['status'] = 'finished'
                await bot.send_message(
                    game['chat_id'],
                    f"🤖 **ПОБЕДА БОТОВ!**\n\n"
                    f"Все люди выбыли. Боты захватили кафе ОАЗИС!\n"
                    f"🧟‍♂️ Зомби и боты теперь правят миром..."
                )
                return web.json_response({
                    'status': 'success',
                    'all_voted': True,
                    'game_finished': True,
                    'winner': 'bots',
                })
            
            # Сценарий 2: Остался 1 человек → победа человека
            if len(human_players) == 1 and len(bot_players) == 0:
                game['status'] = 'finished'
                winner = human_players[0]
                winner_name = winner['name']
                
                # Отправляем сообщение с кубком в чат
                await bot.send_message(
                    game['chat_id'],
                    f"🏆 **ПОБЕДА!** 🏆\n\n"
                    f"🎉 {winner_name} выжил в кафе ОАЗИС!\n"
                    f"🌟 Единственный человек, переживший зомби-апокалипсис!\n\n"
                    f"💪 **{winner_name} — легенда!**"
                )
                
                # ★★★ ОТПРАВЛЯЕМ КРАСИВОЕ СООБЩЕНИЕ ПОБЕДИТЕЛЮ ★★★
                try:
                    await bot.send_message(
                        int(winner['id']) if str(winner['id']).isdigit() else winner['id'],
                        f"🏆 **ТЫ ПОБЕДИЛ!** 🏆\n\n"
                        f"🎊 Поздравляем! Ты единственный выживший в кафе ОАЗИС!\n"
                        f"🌟 Ты пережил зомби-апокалипсис и стал легендой!\n\n"
                        f"💀 {len(game['eliminated'])} игроков не смогли пройти твой путь...\n\n"
                        f"🔥 Ты — настоящий герой Техаса!",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"⚠️ Не удалось отправить сообщение победителю: {e}")
                
                return web.json_response({
                    'status': 'success',
                    'all_voted': True,
                    'game_finished': True,
                    'winner': 'human',
                    'winner_name': winner_name,
                })
            
            # Сценарий 3: Игра продолжается
            game['round'] += 1
            game['status'] = 'playing'
            game['votes'] = {}
            game['players_ready'] = []
            
            # Сбрасываем карты для живых игроков
            for p in game['players']:
                if not p.get('is_observer', False):
                    p['revealed'] = []
                    for card in p['cards']:
                        card['isRevealed'] = False
            
            # Боты снова открывают карты
            bot_reveal_all_cards(game)
            
            await bot.send_message(
                game['chat_id'],
                f"📝 **РАУНД {game['round']}**\n\n"
                f"Новый раунд! Открывайте карты.\n"
                f"🤖 Боты уже открыли свои карты!\n"
                f"👀 Наблюдатели следят за игрой.\n"
                f"👥 Активных игроков: {len([p for p in game['players'] if not p.get('is_observer', False)])}"
            )
            
            # Проверяем, все ли открыли карты
            check_all_cards_revealed(game)
        
        return web.json_response({
            'status': 'success',
            'all_voted': all_voted,
            'vote_count': len(game['votes']),
            'total_players': len([p for p in game['players'] if not p.get('is_observer', False)]),
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

# ============================================
# 14. CORS MIDDLEWARE
# ============================================
@web.middleware
async def cors_middleware(request, handler):
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
    return response

# ============================================
# 15. СТАТИЧЕСКИЕ ФАЙЛЫ
# ============================================
async def serve_html(request):
    return web.Response(text=HTML_PAGE, content_type='text/html')

async def serve_css(request):
    return web.Response(text=CSS_STYLES, content_type='text/css')

async def handle_options(request):
    return web.Response(headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Accept',
    })

# ============================================
# 16. ЗАПУСК
# ============================================
async def main():
    load_cards()
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application(middlewares=[cors_middleware])
    
    app.router.add_get('/', serve_html)
    app.router.add_get('/style.css', serve_css)
    app.router.add_options('/api/{path:.*}', handle_options)
    
    app.router.add_get('/api/test', api_test)
    app.router.add_post('/api/game/state', api_get_state)
    app.router.add_post('/api/game/join', api_join_game)
    app.router.add_post('/api/game/start', api_start_game)
    app.router.add_post('/api/game/cards', api_get_cards)
    app.router.add_post('/api/game/reveal', api_reveal_card)
    app.router.add_post('/api/game/continue', api_continue)
    app.router.add_post('/api/game/voting/players', api_get_voting_players)
    app.router.add_post('/api/game/vote', api_submit_vote)
    
    app.router.add_get('/health', lambda r: web.Response(text="OK"))
    
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
