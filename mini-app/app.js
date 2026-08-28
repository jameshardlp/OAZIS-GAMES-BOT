// ============================================
// КАФЕ ОАЗИС - Mini App Logic
// ============================================

// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand(); // Растягиваем на весь экран
tg.enableClosingConfirmation(); // Спрашиваем при закрытии

// Глобальное состояние игры
const gameState = {
    playerId: null,
    gameId: null,
    players: [],
    myCards: [],
    revealedCards: [],
    currentRound: 0,
    maxRounds: 5,
    status: 'lobby', // lobby, playing, voting, finished
    isHost: false,
};

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🤠 Кафе ОАЗИС загружено!');
    
    // Получаем данные игрока от Telegram
    const initData = tg.initDataUnsafe;
    if (initData && initData.user) {
        gameState.playerId = initData.user.id;
        console.log(`👤 Игрок: ${initData.user.first_name} (ID: ${gameState.playerId})`);
    }
    
    // Подключаемся к игре через WebSocket (или через HTTP запросы)
    connectToGame();
    
    // Обработчики кнопок
    document.getElementById('start-game')?.addEventListener('click', startGame);
    document.getElementById('reveal-card')?.addEventListener('click', revealCard);
    document.getElementById('vote-btn')?.addEventListener('click', submitVote);
});

// ============================================
// ПОДКЛЮЧЕНИЕ К ИГРЕ (через HTTP запросы к боту)
// ============================================

async function connectToGame() {
    try {
        // Получаем текущее состояние игры
        const response = await fetch('/api/game/state', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                player_id: gameState.playerId,
                // initData: tg.initData // Для верификации
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            gameState.gameId = data.game_id;
            gameState.players = data.players || [];
            gameState.status = data.status || 'lobby';
            
            updateUI();
            
            // Если игра уже идёт, получаем карты
            if (gameState.status !== 'lobby') {
                await getMyCards();
            }
        } else {
            console.error('❌ Ошибка подключения:', data.message);
            showError('Не удалось подключиться к игре');
        }
    } catch (error) {
        console.error('❌ Network error:', error);
        showError('Ошибка сети. Проверьте подключение.');
    }
}

// ============================================
// ПОЛУЧЕНИЕ КАРТ ИГРОКА
// ============================================

async function getMyCards() {
    try {
        const response = await fetch('/api/game/cards', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
// НАЧАЛО ИГРЫ (только для хоста)
// ============================================

async function startGame() {
    if (!gameState.isHost) {
        showError('Только ведущий может начать игру!');
        return;
    }
    
    if (gameState.players.length < 4) {
        showError('Нужно минимум 4 игрока!');
        return;
    }
    
    try {
        const response = await fetch('/api/game/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
            showNotification('🔥 Игра началась! Всем разданы карты.');
        } else {
            showError(data.message || 'Не удалось начать игру');
        }
    } catch (error) {
        console.error('❌ Ошибка старта:', error);
    }
}

// ============================================
// ОТКРЫТИЕ КАРТЫ
// ============================================

async function revealCard() {
    // Находим первую неоткрытую карту
    const cardIndex = gameState.myCards.findIndex(c => !c.isRevealed);
    
    if (cardIndex === -1) {
        showError('Все карты уже открыты!');
        return;
    }
    
    // Проверяем, очередь ли этого игрока
    // В реальной игре тут будет проверка через сервер
    
    try {
        const response = await fetch('/api/game/reveal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
            
            // Отправляем уведомление в чат через бота
            const cardName = gameState.myCards[cardIndex].name;
            const cardType = gameState.myCards[cardIndex].type;
            showNotification(`🎴 Вы открыли: ${cardType} - ${cardName}`);
            
            // Если все карты открыты, переходим к голосованию
            if (gameState.myCards.every(c => c.isRevealed)) {
                setTimeout(() => startVoting(), 1500);
            }
        } else {
            showError(data.message || 'Не удалось открыть карту');
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
    
    // Получаем список игроков для голосования
    try {
        const response = await fetch('/api/game/voting/players', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: gameState.gameId,
                player_id: gameState.playerId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            renderVotingList(data.players);
            showNotification('🗳️ Началось голосование! Выберите, кто не попадёт в убежище.');
        }
    } catch (error) {
        console.error('❌ Ошибка голосования:', error);
    }
}

function renderVotingList(players) {
    const container = document.getElementById('voting-list');
    container.innerHTML = '';
    
    players.forEach(player => {
        // Нельзя голосовать за себя
        if (player.id === gameState.playerId) return;
        
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
        showError('Выберите игрока для голосования!');
        return;
    }
    
    const targetId = parseInt(selected.value);
    
    try {
        const response = await fetch('/api/game/vote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: gameState.gameId,
                player_id: gameState.playerId,
                target_id: targetId,
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('✅ Ваш голос учтён! Ожидаем остальных игроков...');
            
            // Проверяем, все ли проголосовали
            if (data.all_voted) {
                showResults(data.results);
            }
            
            // Блокируем кнопку
            document.getElementById('vote-btn').disabled = true;
        } else {
            showError(data.message || 'Ошибка голосования');
        }
    } catch (error) {
        console.error('❌ Ошибка отправки голоса:', error);
    }
}

// ============================================
// РЕЗУЛЬТАТЫ
// ============================================

function showResults(results) {
    gameState.status = 'finished';
    updateUI();
    
    const container = document.getElementById('results-list');
    container.innerHTML = '';
    
    // Показываем, кто выбыл
    const eliminated = results.eliminated;
    const eliminatedDiv = document.createElement('div');
    eliminatedDiv.className = 'result-card eliminated';
    eliminatedDiv.innerHTML = `
        <h3>🧟 ВЫБЫВАЕТ</h3>
        <div class="card-name">${eliminated.name}</div>
        <div class="card-effect">${eliminated.role || 'Без роли'}</div>
        <p>Причина: ${eliminated.reason || 'Большинство голосов'}</p>
    `;
    container.appendChild(eliminatedDiv);
    
    // Показываем выживших
    const survivors = results.survivors || [];
    const survivorsDiv = document.createElement('div');
    survivorsDiv.className = 'result-card survivors';
    survivorsDiv.innerHTML = `
        <h3>🏆 ВЫЖИВШИЕ</h3>
        ${survivors.map(s => `
            <div class="survivor-item">✅ ${s.name}</div>
        `).join('')}
    `;
    container.appendChild(survivorsDiv);
    
    // Показываем блок результатов
    document.getElementById('game-area').style.display = 'none';
    document.getElementById('results').style.display = 'block';
    
    // Отправляем результат в чат через бота
    tg.sendData(JSON.stringify({
        action: 'game_finished',
        game_id: gameState.gameId,
        results: results
    }));
}

// ============================================
// UI ОБНОВЛЕНИЯ
// ============================================

function updateUI() {
    const lobby = document.getElementById('lobby');
    const gameArea = document.getElementById('game-area');
    const votingArea = document.getElementById('voting-area');
    
    // Обновляем лобби
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
    
    // Если игроков достаточно и он хост, показываем кнопку старта
    const startBtn = document.getElementById('start-game');
    if (gameState.players.length >= 4 && gameState.isHost) {
        startBtn.style.display = 'block';
        startBtn.textContent = `🔥 Начать игру (${gameState.players.length} игроков)`;
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
    
    // Показываем, сколько карт осталось открыть
    const remaining = gameState.myCards.filter(c => !c.isRevealed).length;
    document.getElementById('reveal-card').textContent = 
        `🃏 Открыть карту (осталось: ${remaining})`;
}

// ============================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// ============================================

function showNotification(message) {
    // Используем нативный Toast из Telegram
    tg.showPopup({
        title: '📢 Уведомление',
        message: message,
        buttons: [{text: 'OK', type: 'default'}]
    });
}

function showError(message) {
    tg.showPopup({
        title: '❌ Ошибка',
        message: message,
        buttons: [{text: 'OK', type: 'default'}]
    });
}

// ============================================
// ОБРАБОТКА ВХОДЯЩИХ ДАННЫХ ОТ БОТА
// ============================================

// Если бот отправляет данные в Mini App через sendData
tg.onEvent('mainButtonClicked', () => {
    console.log('Главная кнопка нажата');
});

// Обработка данных от бота
tg.onEvent('dataReceived', (data) => {
    console.log('📨 Данные от бота:', data);
    // Здесь можно обрабатывать обновления от бота
});

// ============================================
// ПЕРИОДИЧЕСКОЕ ОБНОВЛЕНИЕ СОСТОЯНИЯ
// ============================================

// Каждые 3 секунды проверяем статус игры
setInterval(async () => {
    if (gameState.status !== 'finished') {
        try {
            const response = await fetch('/api/game/state', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
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

// ============================================
// ЗАВЕРШЕНИЕ
// ============================================

console.log('✅ Mini App "Кафе ОАЗИС" готов к работе!');