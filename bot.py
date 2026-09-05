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

# Отладка
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

# Генератор карт
from cards_generator import (
    generate_full_character,
    generate_character_with_specific_role,
    format_card_for_display,
    get_full_biography,
    get_card_emoji_for_display,
    ROLES,
    get_random_disaster,
)

# Игровой движок
from game_engine import (
    GameEngine,
    GamePhase,
    PlayerStatus,
    create_game,
)

# Биографии
from biography_builder import (
    BiographyBuilder,
    get_player_biography,
    get_player_biography_html,
    get_final_title_sheet,
    generate_biography_preview,
)

# Звуки
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
games = {}  # chat_id -> GameEngine
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
# 6. HTML СТРАНИЦА (с интеграцией звуков и отладки)
# ============================================
DEBUG_PANEL_HTML = get_debug_panel_html()
DEBUG_JS = get_debug_js()
SOUND_JS = sound_manager.get_sound_html()

HTML_PAGE = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Кафе ОАЗИС 2.0</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div id="app">
        <div class="neon-sign">
            <h1 class="neon-text">ОАЗИС</h1>
            <p class="neon-sub">Бар на окраине • Техас 1998</p>
        </div>
        
        {DEBUG_PANEL_HTML}
        
        <div id="game-container">
            <!-- Лобби -->
            <div id="lobby">
                <h2>👥 Лобби</h2>
                <div id="players-list"></div>
                <button id="start-game" class="btn-neon">🔥 Начать игру</button>
            </div>
            
            <!-- Игровая область -->
            <div id="game-area" style="display:none;">
                <!-- Информация о раунде -->
                <div id="round-info" style="text-align:center;padding:10px;background:#1a0a00;border-radius:8px;border:1px solid #FFB000;margin-bottom:15px;">
                    <span id="round-number" style="color:#FFB000;font-size:1.5rem;">Раунд 1</span>
                    <span id="round-phase" style="color:#f5e6d3;opacity:0.7;margin-left:15px;">Открытие карт</span>
                    <div id="current-turn" style="color:#FFB000;font-size:0.9rem;margin-top:5px;"></div>
                </div>
                
                <!-- Карты персонажа -->
                <div id="character-cards">
                    <h2>🎴 Твои карты</h2>
                    <div id="cards-container"></div>
                    <button id="reveal-card" class="btn-neon">🃏 Открыть карту</button>
                    <button id="continue-btn" class="btn-neon" style="display:none;background:#FFB000;color:#0a0a0a;">▶️ Продолжить</button>
                </div>
                
                <!-- Голосование -->
                <div id="voting-area" style="display:none;">
                    <h2>🗳️ Голосование</h2>
                    <div id="voting-list"></div>
                    <button id="vote-btn" class="btn-neon">✅ Проголосовать</button>
                </div>
                
                <!-- Способности -->
                <div id="skill-area" style="display:none;margin-top:15px;">
                    <h2>⚡ Способность</h2>
                    <div id="skill-info"></div>
                    <div id="skill-targets"></div>
                    <button id="use-skill-btn" class="btn-neon" style="border-color:#00FF88;color:#00FF88;">⚡ Использовать способность</button>
                </div>
            </div>
        </div>
        
        <!-- Результаты -->
        <div id="results" style="display:none;">
            <h2>🏆 Итоги</h2>
            <div id="results-list"></div>
        </div>
    </div>
    
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script>
        const API_BASE = '{WEBAPP_URL}';
        
        // ★★★ ВСТРАИВАЕМ МОДУЛЬ ОТЛАДКИ ★★★
        {DEBUG_JS}
        
        // ★★★ ВСТРАИВАЕМ МОДУЛЬ ЗВУКОВ ★★★
        {SOUND_JS}
        
        const gameState = {{
            playerId: null,
            chatId: null,
            gameId: null,
            players: [],
            myCards: [],
            revealedCards: [],
            currentRound: 0,
            maxRounds: 5,
            status: 'waiting',
            isHost: false,
            isObserver: false,
            isEliminated: false,
            health: 3,
            maxHealth: 3,
            role: 'Неизвестно',
            roleSkill: 'Нет способности',
            skillUsed: false,
            canUseSkill: false,
            gameLog: [],
            disaster: null,
            finalBiographies: {{}},
        }};

        // ============================================
        // ОСНОВНЫЕ ФУНКЦИИ
        // ============================================

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
                        chat_id: gameState.chatId,
                    }})
                }});
                
                if (!response.ok) {{
                    throw new Error('HTTP ' + response.status);
                }}
                
                var data = await response.json();
                debugLog('📦 Состояние: ' + JSON.stringify(data));
                
                if (data.chat_id) {{
                    gameState.players = data.players || [];
                    gameState.status = data.phase || 'waiting';
                    gameState.isHost = data.is_host || false;
                    gameState.isObserver = data.is_observer || false;
                    gameState.isEliminated = data.is_eliminated || false;
                    gameState.currentRound = data.round || 0;
                    gameState.maxRounds = data.max_rounds || 5;
                    gameState.gameLog = data.game_log || [];
                    gameState.disaster = data.disaster || null;
                    
                    // Обновляем данные игрока
                    var myData = gameState.players.find(p => String(p.id) === String(gameState.playerId));
                    if (myData) {{
                        gameState.health = myData.health || 3;
                        gameState.maxHealth = myData.max_health || 3;
                        gameState.role = myData.role || 'Неизвестно';
                        gameState.roleSkill = myData.role_skill || 'Нет способности';
                        gameState.skillUsed = myData.skill_used || false;
                        gameState.myCards = myData.cards || [];
                        gameState.revealedCards = myData.revealed_cards || [];
                    }}
                    
                    updateUI();
                    
                    if (gameState.status === 'voting') {{
                        debugLog('🗳️ Статус "voting" — запускаем голосование');
                        await startVoting();
                    }}
                    
                    if (gameState.status === 'playing' || gameState.status === 'ready') {{
                        debugLog('🃏 Статус "' + gameState.status + '" — загружаем карты');
                        renderCards();
                    }}
                    
                    if (gameState.status === 'final_ready') {{
                        debugLog('📜 Финальная фаза!');
                        await showFinalTitleSheet();
                    }}
                    
                    if (gameState.status === 'final_voting') {{
                        debugLog('🗳️ Финальное голосование!');
                        await startFinalVoting();
                    }}
                    
                    if (gameState.status === 'finished') {{
                        debugLog('🏆 Игра завершена!');
                        showResults();
                    }}
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка обновления: ' + error.message);
                if (retryCount < 3) {{
                    setTimeout(function() {{
                        refreshGameState(retryCount + 1);
                    }}, 1000);
                }}
            }}
        }}

        // ============================================
        // ИНИЦИАЛИЗАЦИЯ
        // ============================================

        document.addEventListener('DOMContentLoaded', function() {{
            initDebug().then(function() {{
                debugLog('✅ Отладка инициализирована');
            }});
            
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
            var userIdFromUrl = urlParams.get('user_id');
            var userNameFromUrl = urlParams.get('user_name');
            var chatIdFromUrl = urlParams.get('chat_id');
            
            // Получаем chat_id из Telegram WebApp Data
            var chatIdFromInitData = null;
            try {{
                var initData = window.Telegram.WebApp.initDataUnsafe;
                if (initData && initData.chat) {{
                    chatIdFromInitData = initData.chat.id;
                    debugLog('💬 Chat из initData: ' + chatIdFromInitData);
                }}
            }} catch(e) {{
                debugLog('⚠️ Не удалось получить chat из initData');
            }}
            
            gameState.chatId = chatIdFromUrl || chatIdFromInitData || null;
            
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
            
            // Запасной вариант для chat_id
            if (!gameState.chatId && gameState.playerId) {{
                gameState.chatId = gameState.playerId;
                debugLog('⚠️ chat_id не найден, используем player_id: ' + gameState.chatId);
            }}
            
            if (!gameState.chatId) {{
                debugLog('❌ Нет chat_id!');
                return;
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
            
            gameState.userName = userName;
            debugLog('👤 Итоговое имя: ' + userName);
            debugLog('💬 Итоговый chat_id: ' + gameState.chatId);
            
            connectToGame();
            
            // Кнопки
            document.getElementById('start-game')?.addEventListener('click', startGame);
            document.getElementById('reveal-card')?.addEventListener('click', revealCard);
            document.getElementById('continue-btn')?.addEventListener('click', continueGame);
            document.getElementById('vote-btn')?.addEventListener('click', submitVote);
            document.getElementById('use-skill-btn')?.addEventListener('click', useSkill);
            
            debugLog('✅ Инициализация завершена');
        }});

        // ============================================
        // ПОДКЛЮЧЕНИЕ К ИГРЕ
        // ============================================

        async function connectToGame() {{
            debugLog('🔄 Подключение к API...');
            try {{
                var response = await fetch(API_BASE + '/api/game/state', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        chat_id: gameState.chatId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ: ' + JSON.stringify(data));
                
                if (data.chat_id) {{
                    gameState.players = data.players || [];
                    gameState.status = data.phase || 'waiting';
                    gameState.isHost = data.is_host || false;
                    gameState.isObserver = data.is_observer || false;
                    gameState.isEliminated = data.is_eliminated || false;
                    gameState.currentRound = data.round || 0;
                    gameState.maxRounds = data.max_rounds || 5;
                    gameState.gameLog = data.game_log || [];
                    gameState.disaster = data.disaster || null;
                    
                    var playerExists = gameState.players.some(function(p) {{
                        return String(p.id) === String(gameState.playerId);
                    }});
                    
                    if (!playerExists && gameState.status === 'waiting') {{
                        await joinGame();
                        await refreshGameState();
                    }}
                    
                    updateUI();
                    
                    if (gameState.status === 'playing' || gameState.status === 'ready') {{
                        renderCards();
                    }}
                    
                    if (gameState.status === 'voting') {{
                        await startVoting();
                    }}
                    
                    if (gameState.status === 'final_ready') {{
                        await showFinalTitleSheet();
                    }}
                    
                    if (gameState.status === 'final_voting') {{
                        await startFinalVoting();
                    }}
                    
                    if (gameState.status === 'finished') {{
                        showResults();
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
                        chat_id: gameState.chatId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.players = data.players || [];
                    updateUI();
                    debugLog('✅ Присоединился: ' + userName);
                    playSound('click');
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка присоединения: ' + error.message);
            }}
        }}

        // ============================================
        // УПРАВЛЕНИЕ ИГРОЙ
        // ============================================

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
                playSound('voting_start');
                var response = await fetch(API_BASE + '/api/game/start', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.status = 'playing';
                    gameState.disaster = data.disaster || null;
                    updateUI();
                    await refreshGameState();
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка: ' + error.message);
            }}
        }}

        async function revealCard() {{
            debugLog('🃏 Открытие карты...');
            
            if (gameState.isObserver || gameState.isEliminated) {{
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '👀',
                    message: 'Вы в режиме наблюдения и не можете открывать карты',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            // Находим первую неоткрытую карту
            var cardIndex = -1;
            for (var i = 0; i < gameState.myCards.length; i++) {{
                if (!gameState.myCards[i].isRevealed) {{
                    cardIndex = i;
                    break;
                }}
            }}
            
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
                playSound('card_flip');
                var response = await fetch(API_BASE + '/api/game/reveal', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
                        player_id: gameState.playerId,
                        card_index: cardIndex,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ открытия карты: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.myCards[cardIndex].isRevealed = true;
                    renderCards();
                    debugLog('✅ Карта открыта, осталось: ' + gameState.myCards.filter(function(c) {{ return !c.isRevealed; }}).length);
                    
                    setTimeout(function() {{
                        refreshGameState();
                    }}, 1000);
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
                playSound('click');
                var response = await fetch(API_BASE + '/api/game/continue', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        player_id: gameState.playerId,
                        chat_id: gameState.chatId,
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
                        document.getElementById('continue-btn').textContent = '⏳ Ожидание (' + data.ready_count + '/' + data.total_players + ')';
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

        // ============================================
        // ГОЛОСОВАНИЕ
        // ============================================

        async function startVoting() {{
            debugLog('🗳️ ЗАПУСК ГОЛОСОВАНИЯ...');
            playSound('voting_start');
            gameState.status = 'voting';
            updateUI();
            
            try {{
                var response = await fetch(API_BASE + '/api/game/voting/players', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                var data = await response.json();
                
                if (data.status === 'success') {{
                    renderVotingList(data.players);
                    document.getElementById('vote-btn').disabled = false;
                    
                    // Показываем кнопку способности
                    if (gameState.roleSkill && gameState.roleSkill !== 'Нет способности' && !gameState.skillUsed) {{
                        document.getElementById('skill-area').style.display = 'block';
                        document.getElementById('skill-info').innerHTML = 
                            '⚡ <strong>' + gameState.roleSkill + '</strong> — ' + 
                            (gameState.players.find(p => String(p.id) === String(gameState.playerId))?.role_desc || '');
                        gameState.canUseSkill = true;
                    }}
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
                // Показываем открытые карты игрока (кроме секретов)
                var cardsHtml = '';
                if (player.revealed_cards && player.revealed_cards.length > 0) {{
                    var shownCards = player.revealed_cards.filter(c => c.type !== 'secret');
                    if (shownCards.length > 0) {{
                        cardsHtml = '<div style="font-size:0.7rem;opacity:0.6;margin-top:5px;">' +
                            shownCards.map(c => '🃏 ' + c.name).join(' ') +
                            '</div>';
                    }}
                }}
                card.innerHTML = `
                    <div class="card-type">Игрок</div>
                    <div class="card-name">${{player.name}}</div>
                    <div class="card-effect">🎴 ${{roleText}}</div>
                    ${{cardsHtml}}
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
                playSound('click');
                var response = await fetch(API_BASE + '/api/game/vote', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
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
                            playSound('win');
                            var tg = window.Telegram.WebApp;
                            tg.showPopup({{
                                title: '🏆 ПОБЕДА!',
                                message: '🎉 ' + data.winner_name + ' выжил в кафе ОАЗИС!',
                                buttons: [{{text: '🎊 Ура!', type: 'default'}}]
                            }});
                        }} else if (data.winner === 'bots') {{
                            playSound('elimination');
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
                        if (data.eliminated) {{
                            playSound('elimination');
                        }}
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

        // ============================================
        // СПОСОБНОСТИ
        // ============================================

        async function useSkill() {{
            debugLog('⚡ ИСПОЛЬЗОВАНИЕ СПОСОБНОСТИ');
            
            if (!gameState.canUseSkill || gameState.skillUsed) {{
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '⚡',
                    message: 'Вы уже использовали способность в этом раунде',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            // Показываем список игроков для выбора цели
            var alivePlayers = gameState.players.filter(p => 
                String(p.id) !== String(gameState.playerId) && 
                !p.is_observer && 
                !p.is_eliminated
            );
            
            if (alivePlayers.length === 0) {{
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '⚡',
                    message: 'Нет доступных целей для способности',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            // Создаём кнопки для выбора цели
            var buttons = alivePlayers.map(function(p) {{
                return {{text: p.name, id: p.id}};
            }});
            
            var tg = window.Telegram.WebApp;
            tg.showPopup({{
                title: '⚡ Выберите цель',
                message: 'Кого вы хотите использовать способность?',
                buttons: buttons.map(function(b) {{
                    return {{text: b.text, id: b.id, type: 'default'}};
                }}).concat([{{text: 'Отмена', type: 'cancel'}}])
            }}, function(result) {{
                if (result && result.id) {{
                    executeSkill(result.id);
                }}
            }});
        }}

        async function executeSkill(targetId) {{
            debugLog('⚡ Применение способности к ' + targetId);
            
            try {{
                playSound('skill');
                var response = await fetch(API_BASE + '/api/game/skill', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
                        player_id: gameState.playerId,
                        target_id: parseInt(targetId),
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ способности: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    gameState.skillUsed = true;
                    gameState.canUseSkill = false;
                    document.getElementById('skill-area').style.display = 'none';
                    
                    var tg = window.Telegram.WebApp;
                    tg.showPopup({{
                        title: '⚡ Способность использована',
                        message: data.message || 'Способность применена!',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                    
                    setTimeout(function() {{
                        refreshGameState();
                    }}, 1500);
                }} else {{
                    var tg = window.Telegram.WebApp;
                    tg.showPopup({{
                        title: '❌',
                        message: data.message || 'Ошибка использования способности',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка способности: ' + error.message);
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '❌',
                    message: 'Ошибка: ' + error.message,
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
            }}
        }}

        // ============================================
        // ФИНАЛЬНАЯ ФАЗА
        // ============================================

        async function showFinalTitleSheet() {{
            debugLog('📜 ПОКАЗ ФИНАЛЬНОГО ТИТУЛЬНОГО ЛИСТА');
            playSound('final');
            
            try {{
                var response = await fetch(API_BASE + '/api/game/final/title', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
                        player_id: gameState.playerId,
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ финала: ' + JSON.stringify(data));
                
                if (data.status === 'success' && data.html) {{
                    // Открываем титульный лист в новом окне или в iframe
                    var tg = window.Telegram.WebApp;
                    tg.showPopup({{
                        title: '📜 ФИНАЛ',
                        message: 'Изучите биографии игроков и проголосуйте за того, кто вам нравится!',
                        buttons: [{{text: '📖 Смотреть биографии', id: 'view', type: 'default'}}]
                    }}, function(result) {{
                        if (result && result.id === 'view') {{
                            // Открываем титульный лист
                            var win = window.open('', '_blank');
                            win.document.write(data.html);
                            win.document.close();
                        }}
                    }});
                    
                    // Также сохраняем биографии для отображения
                    gameState.finalBiographies = data.biographies || {{}};
                    gameState.status = 'final_ready';
                    updateUI();
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка финального листа: ' + error.message);
            }}
        }}

        async function startFinalVoting() {{
            debugLog('🗳️ ФИНАЛЬНОЕ ГОЛОСОВАНИЕ');
            playSound('voting_start');
            gameState.status = 'final_voting';
            updateUI();
            
            // Показываем список игроков для финального голосования
            var alivePlayers = gameState.players.filter(p => !p.is_observer && !p.is_eliminated);
            
            if (alivePlayers.length === 0) {{
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '👀',
                    message: 'Нет игроков для голосования',
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
                return;
            }}
            
            // Создаём кнопки для финального голосования
            var buttons = alivePlayers.map(function(p) {{
                return {{text: p.name + ' (' + (p.role || 'Неизвестно') + ')', id: p.id}};
            }});
            
            var tg = window.Telegram.WebApp;
            tg.showPopup({{
                title: '🗳️ ФИНАЛЬНОЕ ГОЛОСОВАНИЕ',
                message: 'Кто из игроков вам нравится больше всего?',
                buttons: buttons.map(function(b) {{
                    return {{text: b.text, id: b.id, type: 'default'}};
                }})
            }}, function(result) {{
                if (result && result.id) {{
                    submitFinalVote(result.id);
                }}
            }});
        }}

        async function submitFinalVote(targetId) {{
            debugLog('🗳️ Отправка финального голоса за ' + targetId);
            
            try {{
                playSound('click');
                var response = await fetch(API_BASE + '/api/game/final/vote', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        chat_id: gameState.chatId,
                        player_id: gameState.playerId,
                        target_id: parseInt(targetId),
                    }})
                }});
                
                var data = await response.json();
                debugLog('📦 Ответ финального голоса: ' + JSON.stringify(data));
                
                if (data.status === 'success') {{
                    if (data.game_finished) {{
                        playSound('win');
                        var tg = window.Telegram.WebApp;
                        tg.showPopup({{
                            title: '🏆 ПОБЕДА!',
                            message: '🎉 ' + data.winner_name + ' победил в финальном голосовании!',
                            buttons: [{{text: '🎊 Ура!', type: 'default'}}]
                        }});
                        await refreshGameState();
                        showResults();
                    }} else {{
                        var tg = window.Telegram.WebApp;
                        tg.showPopup({{
                            title: '✅',
                            message: 'Ваш голос принят! Ожидаем остальных игроков...',
                            buttons: [{{text: 'OK', type: 'default'}}]
                        }});
                        setTimeout(function() {{
                            refreshGameState();
                        }}, 3000);
                    }}
                }} else {{
                    var tg = window.Telegram.WebApp;
                    tg.showPopup({{
                        title: '❌',
                        message: data.message || 'Ошибка голосования',
                        buttons: [{{text: 'OK', type: 'default'}}]
                    }});
                }}
            }} catch (error) {{
                debugLog('❌ Ошибка финального голоса: ' + error.message);
                var tg = window.Telegram.WebApp;
                tg.showPopup({{
                    title: '❌',
                    message: 'Ошибка: ' + error.message,
                    buttons: [{{text: 'OK', type: 'default'}}]
                }});
            }}
        }}

        // ============================================
        // ОТОБРАЖЕНИЕ
        // ============================================

        function updateUI() {{
            var lobby = document.getElementById('lobby');
            var gameArea = document.getElementById('game-area');
            var votingArea = document.getElementById('voting-area');
            var results = document.getElementById('results');
            var skillArea = document.getElementById('skill-area');
            
            // Обновляем информацию о раунде
            document.getElementById('round-number').textContent = 'Раунд ' + (gameState.currentRound || 0) + '/' + gameState.maxRounds;
            
            var phaseText = {{
                'waiting': 'Ожидание',
                'playing': 'Открытие карт',
                'ready': 'Готов к голосованию',
                'voting': 'Голосование',
                'skill': 'Способность',
                'final_ready': 'Финальная фаза',
                'final_voting': 'Финальное голосование',
                'finished': 'Завершена'
            }};
            document.getElementById('round-phase').textContent = phaseText[gameState.status] || gameState.status;
            
            // Показываем катастрофу
            if (gameState.disaster) {{
                document.getElementById('current-turn').innerHTML = '💀 ' + gameState.disaster;
            }}
            
            if (gameState.status === 'waiting' || gameState.status === 'lobby') {{
                lobby.style.display = 'block';
                gameArea.style.display = 'none';
                votingArea.style.display = 'none';
                results.style.display = 'none';
                skillArea.style.display = 'none';
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
                skillArea.style.display = 'none';
                renderCards();
            }} else if (gameState.status === 'final_ready' || gameState.status === 'final_voting') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'block';
                document.getElementById('character-cards').style.display = 'none';
                votingArea.style.display = 'none';
                results.style.display = 'none';
                skillArea.style.display = 'none';
            }} else if (gameState.status === 'finished') {{
                lobby.style.display = 'none';
                gameArea.style.display = 'none';
                votingArea.style.display = 'none';
                results.style.display = 'block';
                skillArea.style.display = 'none';
                showResults();
            }}
        }}

        function renderPlayersList() {{
            var container = document.getElementById('players-list');
            container.innerHTML = '';
            
            gameState.players.forEach(function(player) {{
                var div = document.createElement('div');
                div.className = 'player-item';
                var hostBadge = player.is_host ? '<span class="host-badge">⭐ Ведущий</span>' : '';
                var isBot = player.is_bot ? '🤖 ' : '';
                var observerBadge = player.is_observer ? '👀 ' : '';
                var healthStr = '❤️'.repeat(player.health || 3) + '🖤'.repeat((player.max_health || 3) - (player.health || 3));
                div.innerHTML = `
                    <span>${{observerBadge}}${{isBot}}👤 ${{player.name}}</span>
                    <span style="margin-left:10px;">${{healthStr}}</span>
                    ${{hostBadge}}
                `;
                container.appendChild(div);
            }});
            
            var startBtn = document.getElementById('start-game');
            var alive = gameState.players.filter(p => !p.is_observer && !p.is_eliminated);
            if (alive.length >= 4 && gameState.isHost && gameState.status === 'waiting') {{
                startBtn.style.display = 'block';
                startBtn.textContent = '🔥 Начать игру (' + alive.length + ' игроков)';
                startBtn.disabled = false;
            }} else if (gameState.isHost && gameState.status === 'waiting') {{
                startBtn.style.display = 'block';
                startBtn.textContent = '👥 Нужно ещё ' + (4 - alive.length) + ' игроков';
                startBtn.disabled = true;
            }} else {{
                startBtn.style.display = 'none';
            }}
        }}

        function renderCards() {{
            var container = document.getElementById('cards-container');
            container.innerHTML = '';
            
            // Проверяем, в режиме ли наблюдения игрок
            if (gameState.isObserver || gameState.isEliminated) {{
                container.innerHTML = `
                    <div style="text-align:center;padding:30px;background:#1a0a00;border-radius:12px;border:2px solid #FFB000;">
                        <h2 style="color:#FFB000;font-size:2rem;">👀 РЕЖИМ НАБЛЮДЕНИЯ</h2>
                        <p style="opacity:0.8;margin-top:10px;font-size:1.1rem;">Вы выбыли из игры</p>
                        <p style="opacity:0.5;margin-top:5px;">Следите за игрой!</p>
                        <button id="refresh-btn" class="btn-neon" style="margin-top:20px;border-color:#FFB000;color:#FFB000;">🔄 Обновить</button>
                    </div>
                `;
                document.getElementById('reveal-card').style.display = 'none';
                document.getElementById('continue-btn').style.display = 'none';
                document.getElementById('refresh-btn')?.addEventListener('click', function() {{
                    refreshGameState();
                }});
                return;
            }}
            
            if (!gameState.myCards || gameState.myCards.length === 0) {{
                container.innerHTML = '<p style="opacity:0.7;">Карты не загружены</p>';
                return;
            }}
            
            // Отображаем карты
            gameState.myCards.forEach(function(card) {{
                var div = document.createElement('div');
                div.className = 'character-card';
                
                if (card.isRevealed) {{
                    div.style.borderColor = '#FFB000';
                    div.style.opacity = '1';
                }} else {{
                    div.style.borderColor = '#666';
                    div.style.opacity = '0.7';
                }}
                
                var icon = card.icon || '🃏';
                var cardName = card.isRevealed ? card.name : '❓ Скрыто';
                var cardDesc = card.isRevealed ? (card.desc || '') : 'Нажмите "Открыть карту"';
                var roundBadge = card.round ? '📌 Раунд ' + card.round : '';
                
                div.innerHTML = `
                    <div class="card-type">${{icon}} ${{card.type || 'Карта'}}</div>
                    <div class="card-name">${{cardName}}</div>
                    <div class="card-effect">${{cardDesc}}</div>
                    <div style="font-size:0.6rem;opacity:0.4;margin-top:5px;">${{roundBadge}}</div>
                `;
                container.appendChild(div);
            }});
            
            var remaining = gameState.myCards.filter(function(c) {{ return !c.isRevealed; }}).length;
            
            var revealBtn = document.getElementById('reveal-card');
            var continueBtn = document.getElementById('continue-btn');
            
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

        function showResults() {{
            var container = document.getElementById('results-list');
            container.innerHTML = '';
            
            var alive = gameState.players.filter(p => !p.is_observer && !p.is_eliminated);
            var eliminated = gameState.players.filter(p => p.is_observer || p.is_eliminated);
            
            var html = '';
            
            if (alive.length > 0) {{
                html += '<h3 style="color:#00FF00;">🏆 ВЫЖИВШИЕ</h3>';
                alive.forEach(function(p) {{
                    var healthStr = '❤️'.repeat(p.health || 3) + '🖤'.repeat((p.max_health || 3) - (p.health || 3));
                    html += `
                        <div class="result-card survivors">
                            <strong>${{p.name}}</strong> (${{p.role || 'Неизвестно'}})
                            <span style="margin-left:10px;">${{healthStr}}</span>
                        </div>
                    `;
                }});
            }}
            
            if (eliminated.length > 0) {{
                html += '<h3 style="color:#FF0000;margin-top:20px;">💀 ВЫБЫВШИЕ</h3>';
                eliminated.forEach(function(p) {{
                    html += `
                        <div class="result-card eliminated">
                            <strong>${{p.name}}</strong> (${{p.role || 'Неизвестно'}})
                            <span style="margin-left:10px;">👀 Наблюдатель</span>
                        </div>
                    `;
                }});
            }}
            
            container.innerHTML = html;
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
                            chat_id: gameState.chatId,
                        }})
                    }});
                    
                    var data = await response.json();
                    
                    if (data.chat_id && data.phase && data.phase !== gameState.status) {{
                        debugLog('🔄 Статус изменился: ' + gameState.status + ' -> ' + data.phase);
                        gameState.status = data.phase;
                        gameState.players = data.players || [];
                        gameState.isHost = data.is_host || false;
                        gameState.isObserver = data.is_observer || false;
                        gameState.isEliminated = data.is_eliminated || false;
                        gameState.currentRound = data.round || 0;
                        gameState.gameLog = data.game_log || [];
                        updateUI();
                        
                        if (data.phase === 'voting') {{
                            await startVoting();
                        }}
                        
                        if (data.phase === 'playing' || data.phase === 'ready') {{
                            var myData = gameState.players.find(p => String(p.id) === String(gameState.playerId));
                            if (myData) {{
                                gameState.myCards = myData.cards || [];
                                gameState.revealedCards = myData.revealed_cards || [];
                            }}
                            renderCards();
                        }}
                        
                        if (data.phase === 'final_ready') {{
                            await showFinalTitleSheet();
                        }}
                        
                        if (data.phase === 'final_voting') {{
                            await startFinalVoting();
                        }}
                        
                        if (data.phase === 'finished') {{
                            showResults();
                        }}
                    }}
                }} catch (error) {{
                    // Игнорируем ошибки фонового обновления
                }}
            }}
        }}, 1500);

        debugLog('✅ Mini App 2.0 готов!');
        debugLog('🔄 Автообновление каждые 1.5 секунды');
    </script>
</body>
</html>'''

# ============================================
# 7. CSS СТИЛИ (обновлённые)
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
    color: #FFB000;
    text-shadow: 0 0 10px #FFB000, 0 0 20px #FFB000, 0 0 40px #FFB000, 0 0 80px #FFB000;
    animation: neon-pulse 2s infinite;
}
@keyframes neon-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}
.neon-sub {
    color: #FFB000;
    opacity: 0.7;
    letter-spacing: 4px;
}
.character-card {
    background: linear-gradient(145deg, #1a0a00, #2a1a0a);
    border: 2px solid #FFB000;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 0 20px rgba(255, 176, 0, 0.2);
    transition: transform 0.3s;
}
.character-card:hover {
    transform: scale(1.02);
    box-shadow: 0 0 40px rgba(255, 176, 0, 0.4);
}
.card-type {
    color: #FFB000;
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
    border-top: 1px solid #FFB000;
    padding-top: 10px;
}
.btn-neon {
    background: transparent;
    color: #FFB000;
    border: 2px solid #FFB000;
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
    background: #FFB000;
    color: #0a0a0a;
    box-shadow: 0 0 30px rgba(255, 176, 0, 0.6);
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
    border-left: 3px solid #FFB000;
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
#round-info {
    background: linear-gradient(145deg, #1a0a00, #0a0500);
    border: 1px solid #FFB000;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 15px;
}
#round-info span {
    display: inline-block;
}
.skill-area {
    border: 1px solid #00FF88;
    border-radius: 8px;
    padding: 15px;
    margin-top: 15px;
    background: rgba(0, 255, 136, 0.05);
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
# 9. КОМАНДЫ БОТА
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
    """Включить/выключить панель отладки в Mini App"""
    chat_id = str(message.chat.id)
    
    if chat_id not in games:
        await message.answer("❌ Нет активной игры в этом чате.")
        return
    
    toggle_debug()
    await message.answer(get_debug_command_response(), parse_mode="Markdown")
    log_debug(f"Команда /logs выполнена в чате {chat_id}")

@dp.message(Command("play"))
async def cmd_play(message: types.Message):
    """Создать игру и отправить ссылку"""
    
    print("=" * 60)
    print("🎮 КОМАНДА /play")
    print(f"👤 Пользователь: {message.from_user.id} ({message.from_user.first_name})")
    print(f"💬 Chat ID: {message.chat.id}")
    print("=" * 60)
    
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or message.from_user.username or 'Игрок'
    
    # Проверяем, есть ли уже игра в этом чате
    if chat_id in games:
        game = games[chat_id]
        if game.phase != GamePhase.FINISHED:
            # Игра уже существует
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
    
    # Создаём новую игру
    game = create_game(chat_id, user_id, user_name)
    games[chat_id] = game
    
    # Отправляем игру
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
    """Добавить ботов в игру (только ведущий)"""
    
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
    
    # Проверяем, существует ли игра
    if chat_id not in games:
        # Создаём новую игру
        game = create_game(chat_id, str(user_id), user_name)
        games[chat_id] = game
        print(f"🆕 Создана новая игра: {game.game_id}")
    
    game_url = f"{WEBAPP_URL}?chat_id={chat_id}&user_id={user_id}&user_name={user_name_encoded}"
    print(f"🔗 URL игры: {game_url}")
    
    await callback.answer(url=game_url)
    print("✅ Ответ отправлен с URL игры!")
    print("=" * 60)

# ============================================
# 11. API ОБРАБОТЧИКИ
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
        
        # Собираем данные для титульного листа
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
        
        # Генерируем HTML титульного листа
        html = get_final_title_sheet(players_data)
        
        # Сохраняем биографии
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
        
        # Если финальное голосование ещё не началось — запускаем
        if game.phase == GamePhase.FINAL_READY:
            game.start_final_voting()
        
        result = game.submit_final_vote(str(player_id), str(target_id))
        return web.json_response(result)
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

# ============================================
# 12. CORS MIDDLEWARE
# ============================================
@web.middleware
async def cors_middleware(request, handler):
    response = await handler(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
    return response

# ============================================
# 13. СТАТИЧЕСКИЕ ФАЙЛЫ
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
# 14. ЗАПУСК
# ============================================
async def main():
    load_cards()
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application(middlewares=[cors_middleware])
    
    # Убедитесь, что каждый путь добавляется ТОЛЬКО ОДИН РАЗ
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
