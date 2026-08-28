import asyncio
import json
import random
import uuid
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ============================================
# КОНФИГУРАЦИЯ
# ============================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ОТ_BOTFATHER")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://ВАШ_ДОМЕН.bothost.tech")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
games = {}
CARDS = None

# ============================================
# HTML СТРАНИЦА (встроена в Python)
# ============================================

HTML_PAGE = '''<!DOCTYPE html>
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
    <script src="/app.js"></script>
</body>
</html>'''

# ============================================
# CSS СТИЛИ (встроены в Python)
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
    text-shadow: 
        0 0 10px #ff6b35,
        0 0 20px #ff6b35,
        0 0 40px #ff6b35,
        0 0 80px #ff6b35;
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
# JAVASCRIPT КОД (встроен в Python!)
# ============================================

JS_CODE = '''// ============================================
// КАФЕ ОАЗИС - Mini App Logic
// ============================================

const tg = window.Telegram.WebApp;
tg.expand();
tg.enableClosingConfirmation();

const gameState = {
    playerId: null,
    gameId: null,
    players: [],
    myCards: [],
    revealedCards: [],
    currentRound: 0,
    maxRounds: 5,
    status: 'lobby',
    isHost: false,
};

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🤠 Кафе ОАЗИС загружено!');
    
    const initData = tg.initDataUnsafe;
    if (initData && initData.user) {
        gameState.playerId = initData.user.id;
        console.log(`👤 Игрок: ${initData.user.first_name} (ID: ${gameState.playerId})`);
    }
    
    // Получаем game_id из URL
    const urlParams = new URLSearchParams(window.location.search);
    gameState.gameId = urlParams.get('game_id');
    
    if (!gameState.gameId) {
        tg.showPopup({
            title: '❌ Ошибка',
            message: 'Не найден ID игры. Начните игру заново.',
            buttons: [{text: 'OK', type: 'default'}]
        });
        return;
    }
    
    connectToGame();
    
    document.getElementById('start-game')?.addEventListener('click', startGame);
    document.getElementById('reveal-card')?.addEventListener('click', revealCard);
    document.getElementById('vote-btn')?.addEventListener('click', submitVote);
});

// ============================================
// ПОДКЛЮЧЕНИЕ К ИГРЕ
// ============================================

async function connectToGame() {
    try {
        const response = await fetch('/api/game/state', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                player_id: gameState.playerId,
                game_id: gameState.gameId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            gameState.players = data.players || [];
            gameState.status = data.status || 'lobby';
            gameState.isHost = data.is_host || false;
            
            // Если игрока нет в игре - присоединяемся
            const playerExists = gameState.players.some(p => p.id === gameState.playerId);
            if (!playerExists && gameState.status === 'waiting') {
                await joinGame();
            }
            
            updateUI();
            
            if (gameState.status !== 'lobby') {
                await getMyCards();
            }
        } else {
            console.error('❌ Ошибка:', data.message);
            tg.showPopup({
                title: '❌ Ошибка',
                message: data.message || 'Не удалось подключиться',
                buttons: [{text: 'OK', type: 'default'}]
            });
        }
    } catch (error) {
        console.error('❌ Network error:', error);
    }
}

async function joinGame() {
    try {
        const initData = tg.initDataUnsafe;
        const userName = initData?.user?.first_name || 'Игрок';
        
        const response = await fetch('/api/game/join', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                player_id: gameState.playerId,
                player_name: userName,
                game_id: gameState.gameId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            gameState.players = data.players;
            updateUI();
            tg.showPopup({
                title: '✅ Присоединились!',
                message: `Добро пожаловать, ${userName}!`,
                buttons: [{text: 'OK', type: 'default'}]
            });
        }
    } catch (error) {
        console.error('❌ Ошибка присоединения:', error);
    }
}

// ============================================
// ПОЛУЧЕНИЕ КАРТ
// ============================================

async function getMyCards() {
    try {
        const response = await fetch('/api/game/cards', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                player_id: gameState.playerId,
                game_id: gameState.gameId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            gameState.myCards = data.cards || [];
            gameState.revealedCards = data.revealed || [];
            renderCards();
        }
    } catch (error) {
        console.error('❌ Ошибка получения карт:', error);
    }
}

// ============================================
// НАЧАЛО ИГРЫ
// ============================================

async function startGame() {
    if (!gameState.isHost) {
        tg.showPopup({
            title: '⛔',
            message: 'Только ведущий может начать игру!',
            buttons: [{text: 'OK', type: 'default'}]
        });
        return;
    }
    
    if (gameState.players.length < 4) {
        tg.showPopup({
            title: '👥',
            message: 'Нужно минимум 4 игрока!',
            buttons: [{text: 'OK', type: 'default'}]
        });
        return;
    }
    
    try {
        const response = await fetch('/api/game/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                game_id: gameState.gameId,
                player_id: gameState.playerId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            gameState.status = 'playing';
            gameState.currentRound = 0;
            updateUI();
            await getMyCards();
            tg.showPopup({
                title: '🔥',
                message: 'Игра началась! Всем разданы карты.',
                buttons: [{text: 'OK', type: 'default'}]
            });
        } else {
            tg.showPopup({
                title: '❌',
                message: data.message || 'Не удалось начать игру',
                buttons: [{text: 'OK', type: 'default'}]
            });
        }
    } catch (error) {
        console.error('❌ Ошибка старта:', error);
    }
}

// ============================================
// ОТКРЫТИЕ КАРТЫ
// ============================================

async function revealCard() {
    const cardIndex = gameState.myCards.findIndex(c => !c.isRevealed);
    
    if (cardIndex === -1) {
        tg.showPopup({
            title: '🃏',
            message: 'Все карты уже открыты!',
            buttons: [{text: 'OK', type: 'default'}]
        });
        return;
    }
    
    try {
        const response = await fetch('/api/game/reveal', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                game_id: gameState.gameId,
                player_id: gameState.playerId,
                card_index: cardIndex,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            gameState.myCards[cardIndex].isRevealed = true;
            gameState.revealedCards = data.revealed_cards || [];
            renderCards();
            
            const cardName = gameState.myCards[cardIndex].name;
            const cardType = gameState.myCards[cardIndex].type;
            tg.showPopup({
                title: '🎴',
                message: `Открыто: ${cardType} - ${cardName}`,
                buttons: [{text: 'OK', type: 'default'}]
            });
            
            if (gameState.myCards.every(c => c.isRevealed)) {
                setTimeout(() => startVoting(), 1500);
            }
        } else {
            tg.showPopup({
                title: '❌',
                message: data.message || 'Не удалось открыть карту',
                buttons: [{text: 'OK', type: 'default'}]
            });
        }
    } catch (error) {
        console.error('❌ Ошибка открытия карты:', error);
    }
}

// ============================================
// ГОЛОСОВАНИЕ
// ============================================

async function startVoting() {
    gameState.status = 'voting';
    updateUI();
    
    try {
        const response = await fetch('/api/game/voting/players', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                game_id: gameState.gameId,
                player_id: gameState.playerId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            renderVotingList(data.players);
            tg.showPopup({
                title: '🗳️',
                message: 'Началось голосование! Выберите, кто не попадёт в убежище.',
                buttons: [{text: 'OK', type: 'default'}]
            });
        }
    } catch (error) {
        console.error('❌ Ошибка голосования:', error);
    }
}

function renderVotingList(players) {
    const container = document.getElementById('voting-list');
    container.innerHTML = '';
    
    players.forEach(player => {
        const card = document.createElement('div');
        card.className = 'character-card voting-card';
        card.dataset.playerId = player.id;
        
        card.innerHTML = `
            <div class="card-type">Игрок</div>
            <div class="card-name">${player.name}</div>
            <div class="card-effect">${player.role || 'Без роли'}</div>
            <input type="radio" name="vote" value="${player.id}" id="vote-${player.id}">
            <label for="vote-${player.id}">Голосовать за этого</label>
        `;
        
        container.appendChild(card);
    });
}

async function submitVote() {
    const selected = document.querySelector('input[name="vote"]:checked');
    
    if (!selected) {
        tg.showPopup({
            title: '⚠️',
            message: 'Выберите игрока для голосования!',
            buttons: [{text: 'OK', type: 'default'}]
        });
        return;
    }
    
    const targetId = parseInt(selected.value);
    
    try {
        const response = await fetch('/api/game/vote', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                game_id: gameState.gameId,
                player_id: gameState.playerId,
                target_id: targetId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            document.getElementById('vote-btn').disabled = true;
            tg.showPopup({
                title: '✅',
                message: 'Ваш голос учтён! Ожидаем остальных...',
                buttons: [{text: 'OK', type: 'default'}]
            });
            
            if (data.all_voted) {
                setTimeout(() => {
                    tg.sendData(JSON.stringify({
                        action: 'game_finished',
                        game_id: gameState.gameId,
                    }));
                }, 2000);
            }
        } else {
            tg.showPopup({
                title: '❌',
                message: data.message || 'Ошибка голосования',
                buttons: [{text: 'OK', type: 'default'}]
            });
        }
    } catch (error) {
        console.error('❌ Ошибка отправки голоса:', error);
    }
}

// ============================================
// UI ОБНОВЛЕНИЯ
// ============================================

function updateUI() {
    const lobby = document.getElementById('lobby');
    const gameArea = document.getElementById('game-area');
    const votingArea = document.getElementById('voting-area');
    
    if (gameState.status === 'lobby') {
        lobby.style.display = 'block';
        gameArea.style.display = 'none';
        renderPlayersList();
    } else if (gameState.status === 'voting') {
        lobby.style.display = 'none';
        gameArea.style.display = 'block';
        document.getElementById('character-cards').style.display = 'none';
        document.getElementById('voting-area').style.display = 'block';
    } else if (gameState.status === 'playing') {
        lobby.style.display = 'none';
        gameArea.style.display = 'block';
        document.getElementById('character-cards').style.display = 'block';
        document.getElementById('voting-area').style.display = 'none';
    }
}

function renderPlayersList() {
    const container = document.getElementById('players-list');
    container.innerHTML = '';
    
    gameState.players.forEach(player => {
        const div = document.createElement('div');
        div.className = 'player-item';
        div.innerHTML = `
            <span>👤 ${player.name}</span>
            ${player.isHost ? '<span class="host-badge">⭐ Ведущий</span>' : ''}
        `;
        container.appendChild(div);
    });
    
    const startBtn = document.getElementById('start-game');
    if (gameState.players.length >= 4 && gameState.isHost) {
        startBtn.style.display = 'block';
        startBtn.textContent = `🔥 Начать игру (${gameState.players.length} игроков)`;
        startBtn.disabled = false;
    } else if (gameState.isHost) {
        startBtn.style.display = 'block';
        startBtn.textContent = `👥 Нужно ещё ${4 - gameState.players.length} игроков`;
        startBtn.disabled = true;
    } else {
        startBtn.style.display = 'none';
    }
}

function renderCards() {
    const container = document.getElementById('cards-container');
    container.innerHTML = '';
    
    gameState.myCards.forEach((card, index) => {
        const div = document.createElement('div');
        div.className = 'character-card';
        
        if (card.isRevealed) {
            div.style.borderColor = '#ff6b35';
            div.style.opacity = '1';
        } else {
            div.style.borderColor = '#666';
            div.style.opacity = '0.7';
        }
        
        div.innerHTML = `
            <div class="card-type">${card.type || 'Карта'}</div>
            <div class="card-name">${card.isRevealed ? card.name : '❓ Скрыто'}</div>
            <div class="card-effect">${card.isRevealed ? (card.effect || card.description || '') : 'Нажмите "Открыть карту"'}</div>
            ${card.isRevealed ? `<div class="card-rarity">⭐ ${card.rarity || 'Обычная'}</div>` : ''}
        `;
        
        container.appendChild(div);
    });
    
    const remaining = gameState.myCards.filter(c => !c.isRevealed).length;
    document.getElementById('reveal-card').textContent = 
        `🃏 Открыть карту (осталось: ${remaining})`;
}

// ============================================
// ПЕРИОДИЧЕСКОЕ ОБНОВЛЕНИЕ
// ============================================

setInterval(async () => {
    if (gameState.status !== 'finished' && gameState.status !== 'voting') {
        try {
            const response = await fetch('/api/game/state', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    player_id: gameState.playerId,
                    game_id: gameState.gameId,
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success' && data.status !== gameState.status) {
                gameState.status = data.status;
                updateUI();
                
                if (data.status === 'voting') {
                    await startVoting();
                }
            }
        } catch (error) {
            // Игнорируем ошибки при фоновом обновлении
        }
    }
}, 3000);

console.log('✅ Mini App "Кафе ОАЗИС" готов к работе!')'''

# ============================================
# ЗАГРУЗКА КАРТ
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
            {"name": "Бармен", "description": "Знает все коктейли", "rarity": "редкий"},
            {"name": "Менеджер", "description": "Управляет людьми", "rarity": "обычный"},
        ],
        "health": [
            {"name": "Здоров как бык", "bonus": "+2 к выживанию"},
            {"name": "Ранен (царапина)", "bonus": "-1 к выживанию"},
            {"name": "Под кайфом", "bonus": "Иногда галлюцинации"},
            {"name": "При смерти", "bonus": "Требует лекарства"},
            {"name": "Не выспался", "bonus": "-1 к харизме"},
            {"name": "Голоден", "bonus": "Съел бы зомби"},
        ],
        "skills": [
            {"name": "Метание ножей", "effect": "Убивает зомби с 20 метров"},
            {"name": "Игра на гитаре", "effect": "Успокаивает зомби"},
            {"name": "Взлом автоматов", "effect": "Всегда есть еда"},
            {"name": "Теннисный удар", "effect": "Отбивает головы зомби"},
            {"name": "Разговор с животными", "effect": "Собаки помогают"},
            {"name": "Паркур", "effect": "Убегает от зомби"},
            {"name": "Кулинария", "effect": "Вкусно кормит группу"},
        ],
        "items": [
            {"name": "Кольт .45", "effect": "6 патронов"},
            {"name": "Фляга с виски", "effect": "Повышает настроение"},
            {"name": "Библия", "effect": "Отгоняет зомби"},
            {"name": "Запасные носки", "effect": "Всегда пригодятся"},
            {"name": "Бензопила", "effect": "Громкая, но эффективная"},
            {"name": "Магический кристалл", "effect": "Работает или нет"},
            {"name": "Кулинарная книга", "effect": "Как съесть зомби"},
        ],
        "secrets": [
            {"name": "Торговал с зомби", "effect": "Все недовольны"},
            {"name": "Убил напарника", "effect": "Не доверяют"},
            {"name": "Был информатором", "effect": "Предатель"},
            {"name": "Украл еду", "effect": "Недоверие"},
            {"name": "Сделал фальшивку", "effect": "Все подозревают"},
        ]
    }
    print("✅ Используются дефолтные карты")

# ============================================
# КОМАНДЫ БОТА
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤠 Добро пожаловать в КАФЕ ОАЗИС!\n\n"
        "Игра на выживание во время зомби-апокалипсиса.\n"
        "Ты должен убедить других, что достоин места в убежище.\n\n"
        "🔫 Чтобы начать игру, используй команду /oasis"
    )

@dp.message(Command("oasis"))
async def cmd_oasis(message: types.Message):
    chat_id = str(message.chat.id)
    
    if chat_id in games:
        await message.answer("⚠️ Игра уже идёт!")
        return
    
    game_id = str(uuid.uuid4())[:8]
    games[chat_id] = {
        'game_id': game_id,
        'chat_id': chat_id,
        'players': [],
        'status': 'waiting',
        'round': 0,
        'max_rounds': 5,
        'host_id': message.from_user.id,
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
        "🧟 ЗОМБИ-АПОКАЛИПСИС!\n\n"
        "Группа выживших нашла убежище в кафе 'ОАЗИС'.\n"
        "Мест хватит только на половину из вас.\n\n"
        "👥 Соберите от 4 до 6 игроков и нажмите кнопку.",
        reply_markup=keyboard
    )

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

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    chat_id = str(message.chat.id)
    if chat_id in games:
        del games[chat_id]
        await message.answer("⛔ Игра остановлена.")
    else:
        await message.answer("❌ Активной игры нет.")

# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
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
# API ОБРАБОТЧИКИ
# ============================================

async def api_get_state(request):
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
        
        player = next((p for p in game['players'] if p['id'] == player_id), None)
        if not player and game['status'] != 'waiting':
            return web.json_response({'status': 'error', 'message': 'Игрок не найден'}, status=404)
        
        return web.json_response({
            'status': 'success',
            'game_id': game['game_id'],
            'status': game['status'],
            'players': game['players'],
            'round': game['round'],
            'max_rounds': game['max_rounds'],
            'is_host': game['host_id'] == player_id if player else False,
        })
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_join_game(request):
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
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_start_game(request):
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
        
        if game['host_id'] != player_id:
            return web.json_response({'status': 'error', 'message': 'Только ведущий'}, status=403)
        
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
        
        player = next((p for p in game['players'] if p['id'] == player_id), None)
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
        
        player = next((p for p in game['players'] if p['id'] == player_id), None)
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
                'id': p['id'],
                'name': p['name'],
                'role': next((c['name'] for c in p['cards'] if c.get('isRevealed') and c.get('type') == 'Роль'), 'Неизвестно')
            }
            for p in game['players']
            if p['id'] != player_id
        ]
        
        return web.json_response({'status': 'success', 'players': players_for_vote})
    except Exception as e:
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def api_submit_vote(request):
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
        
        game['votes'][player_id] = target_id
        
        all_voted = len(game['votes']) == len(game['players'])
        
        if all_voted:
            vote_results = {}
            for voter, target in game['votes'].items():
                vote_results[target] = vote_results.get(target, 0) + 1
            
            max_votes = max(vote_results.values())
            eliminated = [p for p in game['players'] if p['id'] in vote_results and vote_results[p['id']] == max_votes]
            
            if eliminated:
                eliminated_player = eliminated[0]
                game['eliminated'].append(eliminated_player)
                game['players'] = [p for p in game['players'] if p['id'] != eliminated_player['id']]
                
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
# СТАТИЧЕСКИЕ ФАЙЛЫ (все в Python!)
# ============================================

async def serve_html(request):
    return web.Response(text=HTML_PAGE, content_type='text/html')

async def serve_css(request):
    return web.Response(text=CSS_STYLES, content_type='text/css')

async def serve_js(request):
    return web.Response(text=JS_CODE, content_type='application/javascript')

async def health_check(request):
    return web.Response(text="OK")

# ============================================
# ЗАПУСК
# ============================================

async def main():
    load_cards()
    asyncio.create_task(dp.start_polling(bot))
    
    app = web.Application()
    
    # Статические файлы (все из Python)
    app.router.add_get('/', serve_html)
    app.router.add_get('/index.html', serve_html)
    app.router.add_get('/style.css', serve_css)
    app.router.add_get('/app.js', serve_js)
    
    # API
    app.router.add_post('/api/game/state', api_get_state)
    app.router.add_post('/api/game/join', api_join_game)
    app.router.add_post('/api/game/start', api_start_game)
    app.router.add_post('/api/game/cards', api_get_cards)
    app.router.add_post('/api/game/reveal', api_reveal_card)
    app.router.add_post('/api/game/voting/players', api_get_voting_players)
    app.router.add_post('/api/game/vote', api_submit_vote)
    
    app.router.add_get('/health', health_check)
    
    port = int(os.getenv('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    
    print(f"🤠 Бот 'Кафе ОАЗИС' запущен!")
    print(f"📱 Mini App: {WEBAPP_URL}")
    print(f"🔌 Порт: {port}")
    
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
