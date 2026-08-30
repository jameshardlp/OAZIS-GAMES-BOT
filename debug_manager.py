"""
Модуль управления отладкой для игры "Кафе ОАЗИС"
Позволяет включать/выключать панель отладки в Mini App через команду /logs
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

# Глобальное состояние отладки
_debug_enabled: bool = True
_debug_history: list = []  # Хранит последние 100 сообщений для истории
_MAX_HISTORY: int = 100


# ============================================
# ОСНОВНЫЕ ФУНКЦИИ
# ============================================

def is_debug_enabled() -> bool:
    """Возвращает текущее состояние отладки"""
    return _debug_enabled


def toggle_debug() -> bool:
    """Переключает состояние отладки. Возвращает новое состояние."""
    global _debug_enabled
    _debug_enabled = not _debug_enabled
    
    # Логируем переключение в историю
    _add_to_history(f"🔄 Отладка переключена: {'ВКЛ' if _debug_enabled else 'ВЫКЛ'}")
    
    return _debug_enabled


def set_debug(enabled: bool) -> bool:
    """Устанавливает конкретное состояние отладки"""
    global _debug_enabled
    _debug_enabled = enabled
    _add_to_history(f"📡 Отладка установлена: {'ВКЛ' if enabled else 'ВЫКЛ'}")
    return _debug_enabled


def get_debug_status() -> Dict[str, Any]:
    """Возвращает полный статус отладки для API"""
    return {
        'enabled': _debug_enabled,
        'timestamp': datetime.now().isoformat(),
        'history_count': len(_debug_history),
        'history': _debug_history[-10:]  # Последние 10 записей
    }


def log_debug(message: str, level: str = 'INFO') -> None:
    """
    Добавляет сообщение в историю отладки.
    Используется для сохранения важных событий.
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    entry = f"[{timestamp}] [{level}] {message}"
    _add_to_history(entry)


def _add_to_history(message: str) -> None:
    """Внутренняя функция для добавления записи в историю"""
    global _debug_history
    _debug_history.append(message)
    
    # Ограничиваем размер истории
    if len(_debug_history) > _MAX_HISTORY:
        _debug_history = _debug_history[-_MAX_HISTORY:]


def get_debug_panel_html() -> str:
    """
    Возвращает HTML-код панели отладки для вставки в Mini App.
    """
    if _debug_enabled:
        return '''<div id="debug-panel" style="background:#1a0a00;border:2px solid #ff6b35;border-radius:8px;padding:10px;margin-bottom:10px;font-size:0.7rem;font-family:monospace;min-height:120px;max-height:200px;overflow-y:auto;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="color:#ff6b35;font-weight:bold;">📡 ОТЛАДКА:</div>
        <button id="toggle-debug-btn" style="background:transparent;border:1px solid #ff6b35;color:#ff6b35;padding:2px 10px;border-radius:4px;cursor:pointer;font-size:0.7rem;">🔄 Обновить</button>
    </div>
    <div id="debug-log" style="color:#f5e6d3;white-space:pre-wrap;word-break:break-all;"></div>
</div>'''
    else:
        return '''<div id="debug-panel" style="display:none;"></div>'''


def get_debug_js() -> str:
    """
    Возвращает JavaScript-код для управления отладкой в Mini App.
    """
    return '''
// ★★★ МОДУЛЬ УПРАВЛЕНИЯ ОТЛАДКОЙ ★★★
var debugEnabled = true;

async function checkDebugStatus() {
    try {
        var response = await fetch(API_BASE + '/api/debug/status', {
            method: 'GET',
            headers: {'Content-Type': 'application/json'}
        });
        var data = await response.json();
        debugEnabled = data.enabled;
        return data.enabled;
    } catch (error) {
        console.error('Ошибка получения статуса отладки:', error);
        debugEnabled = true; // По умолчанию включена
        return true;
    }
}

async function initDebug() {
    await checkDebugStatus();
    var panel = document.getElementById('debug-panel');
    if (panel) {
        panel.style.display = debugEnabled ? 'block' : 'none';
    }
    if (debugEnabled) {
        debugLog('✅ Отладка включена');
    } else {
        console.log('🔇 Отладка выключена');
    }
}

function debugLog(message) {
    if (!debugEnabled) {
        console.log('[DEBUG OFF]', message);
        return;
    }
    var logEl = document.getElementById('debug-log');
    if (logEl) {
        var timestamp = new Date().toLocaleTimeString();
        logEl.innerHTML += '[' + timestamp + '] ' + message + '\\n';
        logEl.scrollTop = logEl.scrollHeight;
    }
    console.log(message);
}

// Функция для принудительного обновления состояния отладки
async function refreshDebug() {
    await initDebug();
    debugLog('🔄 Панель отладки обновлена');
}

// Добавляем обработчик для кнопки обновления, если она есть
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        document.getElementById('toggle-debug-btn')?.addEventListener('click', function() {
            refreshDebug();
        });
    }, 500);
});
'''


def get_debug_command_response() -> str:
    """Возвращает текст ответа для команды /logs"""
    status = "🟢 ВКЛЮЧЕНА" if _debug_enabled else "🔴 ВЫКЛЮЧЕНА"
    return (
        f"📡 **Панель отладки:** {status}\n\n"
        f"{'Теперь игроки видят отладочную информацию.' if _debug_enabled else 'Отладочная панель скрыта.'}\n\n"
        f"🔄 Чтобы применить изменения, игрокам нужно обновить страницу (закрыть и открыть игру заново).\n\n"
        f"📊 Всего записей в истории: {len(_debug_history)}"
    )


# ============================================
# API-ОБРАБОТЧИК ДЛЯ Aiohttp
# ============================================

async def api_debug_status(request):
    """
    API-эндпоинт для получения статуса отладки.
    Используется Mini App для проверки, нужно ли показывать панель.
    """
    from aiohttp import web
    return web.json_response({
        'enabled': _debug_enabled,
        'timestamp': datetime.now().isoformat()
    })


# ============================================
# ИНИЦИАЛИЗАЦИЯ МОДУЛЯ
# ============================================

def init_debug(enabled: bool = True) -> None:
    """Инициализирует модуль отладки с начальным состоянием"""
    global _debug_enabled
    _debug_enabled = enabled
    _add_to_history(f"🚀 Модуль отладки инициализирован (статус: {'ВКЛ' if enabled else 'ВЫКЛ'})")
    print(f"📡 Модуль отладки инициализирован: {'ВКЛЮЧЕН' if enabled else 'ВЫКЛЮЧЕН'}")


# ============================================
# ТЕСТИРОВАНИЕ (если запустить файл напрямую)
# ============================================

if __name__ == "__main__":
    # Простой тест модуля
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ МОДУЛЯ ОТЛАДКИ")
    print("=" * 60)
    
    init_debug(True)
    
    print(f"Состояние: {is_debug_enabled()}")
    print(f"Статус: {get_debug_status()}")
    
    toggle_debug()
    print(f"После переключения: {is_debug_enabled()}")
    
    log_debug("Тестовое сообщение", "TEST")
    print(f"История: {_debug_history[-1]}")
    
    print("\n✅ Модуль работает корректно!")