"""
Модуль игрового движка для "Кафе ОАЗИС 2.0"
Управляет логикой игры, ходами, голосованиями, способностями и жизнями
"""

import random
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from enum import Enum

# Импортируем генератор карт
from cards_generator import (
    generate_full_character,
    generate_character_with_specific_role,
    format_card_for_display,
    get_full_biography,
    get_card_emoji_for_display,
    ROLES,
)


# ============================================
# КЛАССЫ И СОСТОЯНИЯ
# ============================================

class GamePhase(Enum):
    """Фазы игры"""
    WAITING = "waiting"          # Ожидание игроков
    PLAYING = "playing"          # Игра идёт (открытие карт)
    READY = "ready"              # Все открыли карты, готовы к голосованию
    VOTING = "voting"            # Идёт голосование
    SKILL = "skill"              # Использование способности
    FINAL_READY = "final_ready"  # Все карты открыты, готов к финалу
    FINAL_VOTING = "final_voting"  # Финальное голосование "Кто нравится?"
    FINISHED = "finished"        # Игра завершена


class PlayerStatus(Enum):
    """Статус игрока"""
    ALIVE = "alive"              # Жив и активен
    ELIMINATED = "eliminated"    # Выбыл из игры
    OBSERVER = "observer"        # Наблюдатель (выбыл, но смотрит)
    BOT = "bot"                  # Бот


# ============================================
# КЛАСС ИГРОВОГО ДВИЖКА
# ============================================

class GameEngine:
    """Основной движок игры"""
    
    def __init__(self, chat_id: str, host_id: str, host_name: str):
        self.chat_id = chat_id
        self.host_id = host_id
        self.host_name = host_name
        self.game_id = self._generate_game_id()
        
        # Игроки
        self.players: Dict[str, Dict] = {}  # player_id -> player_data
        self.player_order: List[str] = []   # Порядок ходов
        
        # Состояние игры
        self.phase: GamePhase = GamePhase.WAITING
        self.round: int = 0
        self.max_rounds: int = 5
        self.current_player_index: int = 0
        
        # Голосования
        self.votes: Dict[str, str] = {}  # voter_id -> target_id
        self.final_votes: Dict[str, str] = {}  # voter_id -> target_id (финал)
        self.vote_history: List[Dict] = []  # История голосований
        
        # Способности
        self.skill_usage: Dict[str, bool] = {}  # player_id -> использовал ли способность
        self.skill_targets: Dict[str, str] = {}  # player_id -> target_id (для способности)
        self.skill_log: List[str] = []  # Лог способностей
        
        # Здоровье
        self.eliminated_players: List[str] = []  # ID выбывших (без жизней)
        self.observer_players: Set[str] = set()  # ID наблюдателей
        
        # Временные данные
        self.reveal_order: List[str] = []  # Очерёдность открытия карт
        self.players_ready: Set[str] = set()  # Кто нажал "Продолжить"
        
        # Финал
        self.final_biographies: Dict[str, str] = {}  # player_id -> биография
        self.final_results: Dict[str, int] = {}  # player_id -> голоса в финале
        self.winner_id: Optional[str] = None
        
        # Катастрофа (общая для всех)
        self.disaster: Optional[str] = None
        
        # Время создания
        self.created_at = datetime.now().isoformat()
        
        # Логи игры
        self.game_log: List[str] = []
        self._add_log("🎮 Игра создана!")
    
    # ============================================
    # БАЗОВЫЕ МЕТОДЫ
    # ============================================
    
    def _generate_game_id(self) -> str:
        """Генерирует уникальный ID игры"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _add_log(self, message: str) -> None:
        """Добавляет запись в лог игры"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.game_log.append(f"[{timestamp}] {message}")
    
    def get_game_state(self, player_id: Optional[str] = None) -> Dict[str, Any]:
        """Возвращает текущее состояние игры для клиента"""
        player = self.players.get(player_id) if player_id else None
        
        return {
            "game_id": self.game_id,
            "chat_id": self.chat_id,
            "phase": self.phase.value,
            "round": self.round,
            "max_rounds": self.max_rounds,
            "players": self.get_players_list(player_id),
            "is_host": self.host_id == player_id,
            "is_observer": player_id in self.observer_players if player_id else False,
            "is_eliminated": player_id in self.eliminated_players if player_id else False,
            "current_turn": self.get_current_player_id(),
            "vote_count": len(self.votes),
            "total_players": len(self.get_alive_players()),
            "game_log": self.game_log[-20:],  # Последние 20 записей
            "disaster": self.disaster,
        }
    
    def get_players_list(self, viewer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Возвращает список игроков для отображения"""
        result = []
        for player_id, player in self.players.items():
            data = {
                "id": player_id,
                "name": player.get("name", "Игрок"),
                "role": player.get("role", "Неизвестно"),
                "health": player.get("health", 3),
                "max_health": player.get("max_health", 3),
                "is_host": player_id == self.host_id,
                "is_bot": player.get("is_bot", False),
                "is_observer": player_id in self.observer_players,
                "is_eliminated": player_id in self.eliminated_players,
                "status": self._get_player_status(player_id),
                "revealed_count": len(player.get("revealed_cards", [])),
                "total_cards": len(player.get("all_cards", [])),
            }
            
            # Если игрок смотрит на себя — показываем все карты
            if viewer_id and viewer_id == player_id:
                data["cards"] = player.get("all_cards", [])
                data["revealed_cards"] = player.get("revealed_cards", [])
            
            # Если игрок наблюдатель — показываем открытые карты других
            elif viewer_id and viewer_id in self.observer_players:
                data["cards"] = player.get("revealed_cards", [])
            
            result.append(data)
        
        return result
    
    def _get_player_status(self, player_id: str) -> str:
        """Возвращает статус игрока"""
        if player_id in self.eliminated_players:
            return PlayerStatus.ELIMINATED.value
        if player_id in self.observer_players:
            return PlayerStatus.OBSERVER.value
        if self.players.get(player_id, {}).get("is_bot", False):
            return PlayerStatus.BOT.value
        return PlayerStatus.ALIVE.value
    
    def get_current_player_id(self) -> Optional[str]:
        """Возвращает ID текущего игрока (чей ход открывать карту)"""
        if not self.player_order or self.phase != GamePhase.PLAYING:
            return None
        if self.current_player_index >= len(self.player_order):
            return None
        return self.player_order[self.current_player_index]
    
    def get_alive_players(self) -> List[str]:
        """Возвращает список ID живых игроков"""
        return [
            pid for pid in self.players
            if pid not in self.eliminated_players
            and pid not in self.observer_players
        ]
    
    def get_human_players(self) -> List[str]:
        """Возвращает список ID живых людей (не ботов)"""
        return [
            pid for pid in self.get_alive_players()
            if not self.players[pid].get("is_bot", False)
        ]
    
    def get_bot_players(self) -> List[str]:
        """Возвращает список ID живых ботов"""
        return [
            pid for pid in self.get_alive_players()
            if self.players[pid].get("is_bot", False)
        ]
    
    # ============================================
    # УПРАВЛЕНИЕ ИГРОКАМИ
    # ============================================
    
    def add_player(self, player_id: str, name: str, is_bot: bool = False) -> bool:
        """Добавляет игрока в игру"""
        if player_id in self.players:
            return False
        
        if len(self.players) >= 6:
            return False
        
        self.players[player_id] = {
            "id": player_id,
            "name": name,
            "is_bot": is_bot,
            "is_host": player_id == self.host_id,
            "health": 3,
            "max_health": 3,
            "role": None,
            "role_skill": None,
            "role_desc": None,
            "rounds": {},
            "all_cards": [],
            "revealed_cards": [],
            "cards_by_round_revealed": {},
            "skill_used": False,
        }
        
        self.player_order.append(player_id)
        self._add_log(f"👤 {name} присоединился к игре")
        return True
    
    def add_bot(self, bot_name: str) -> bool:
        """Добавляет бота в игру"""
        bot_id = f"bot_{self._generate_game_id()}"
        return self.add_player(bot_id, bot_name, is_bot=True)
    
    def remove_player(self, player_id: str) -> bool:
        """Удаляет игрока из игры"""
        if player_id not in self.players:
            return False
        
        name = self.players[player_id]["name"]
        del self.players[player_id]
        if player_id in self.player_order:
            self.player_order.remove(player_id)
        self._add_log(f"🚪 {name} покинул игру")
        return True
    
    # ============================================
    # СТАРТ ИГРЫ
    # ============================================
    
    def start_game(self) -> bool:
        """Начинает игру"""
        if self.phase != GamePhase.WAITING:
            return False
        
        alive_players = self.get_alive_players()
        if len(alive_players) < 4:
            return False
        
        # Генерируем катастрофу
        from cards_generator import get_random_disaster
        self.disaster = get_random_disaster()
        self._add_log(f"💀 КАТАСТРОФА: {self.disaster}")
        
        # Генерируем персонажей для всех игроков
        for player_id in self.players:
            player = self.players[player_id]
            if player.get("is_bot", False):
                # Боты получают случайные роли
                character = generate_full_character(player["name"])
            else:
                # Люди — тоже случайные, но можно будет выбрать роль позже
                character = generate_full_character(player["name"])
            
            # Сохраняем данные персонажа
            player["role"] = character["role"]
            player["role_skill"] = character["role_skill"]
            player["role_desc"] = character["role_desc"]
            player["rounds"] = character["rounds"]
            player["all_cards"] = character["all_cards"]
            player["health"] = character["health"]
            player["max_health"] = character["max_health"]
            player["revealed_cards"] = []
            player["cards_by_round_revealed"] = {
                1: [], 2: [], 3: [], 4: [], 5: []
            }
            player["skill_used"] = False
        
        self.round = 1
        self.phase = GamePhase.PLAYING
        self.current_player_index = 0
        self.reveal_order = self.player_order.copy()
        
        self._add_log(f"🔥 ИГРА НАЧАЛАСЬ! Раунд {self.round}")
        self._add_log(f"👥 Игроков: {len(self.get_alive_players())}")
        self._add_log(f"💀 Катастрофа: {self.disaster}")
        
        return True
    
    # ============================================
    # ОТКРЫТИЕ КАРТ
    # ============================================
    
    def reveal_card(self, player_id: str, card_index: int) -> Dict[str, Any]:
        """
        Открывает карту игрока в текущем раунде
        """
        if self.phase != GamePhase.PLAYING:
            return {"success": False, "message": "Не время открывать карты"}
        
        if player_id in self.observer_players or player_id in self.eliminated_players:
            return {"success": False, "message": "Вы выбыли из игры"}
        
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "Игрок не найден"}
        
        # Проверяем, что это ход игрока
        current = self.get_current_player_id()
        if current and current != player_id:
            return {"success": False, "message": "Сейчас не ваш ход"}
        
        # Получаем карты текущего раунда
        round_cards = player["rounds"].get(self.round, [])
        if not round_cards:
            return {"success": False, "message": "Нет карт для открытия"}
        
        if card_index < 0 or card_index >= len(round_cards):
            return {"success": False, "message": "Неверный индекс карты"}
        
        card = round_cards[card_index]
        
        # Проверяем, не открыта ли уже эта карта
        if card in player["revealed_cards"] or card in player["cards_by_round_revealed"].get(self.round, []):
            return {"success": False, "message": "Эта карта уже открыта"}
        
        # Открываем карту
        player["revealed_cards"].append(card)
        player["cards_by_round_revealed"][self.round].append(card)
        
        self._add_log(f"🃏 {player['name']} открыл карту: {format_card_for_display(card)}")
        
        # Проверяем, открыты ли все карты у игрока
        all_revealed = len(player["cards_by_round_revealed"][self.round]) >= len(round_cards)
        
        # Переходим к следующему игроку
        if all_revealed:
            self._move_to_next_player()
        
        return {
            "success": True,
            "card": card,
            "all_revealed": all_revealed,
            "player_name": player["name"],
        }
    
    def _move_to_next_player(self) -> None:
        """Переходит к следующему игроку для открытия карт"""
        # Находим следующего живого игрока
        alive = self.get_alive_players()
        
        # Проверяем, все ли открыли карты
        all_done = True
        for pid in alive:
            player = self.players[pid]
            round_cards = player["rounds"].get(self.round, [])
            revealed = len(player["cards_by_round_revealed"].get(self.round, []))
            if revealed < len(round_cards):
                all_done = False
                break
        
        if all_done:
            # Все открыли карты → переходим в режим READY
            self.phase = GamePhase.READY
            self.players_ready = set()
            self._add_log(f"📢 Все игроки открыли карты в раунде {self.round}")
            self._add_log("⏳ Нажмите 'Продолжить' чтобы перейти к голосованию")
            return
        
        # Ищем следующего живого игрока, который не открыл все карты
        start_index = self.current_player_index
        for i in range(len(self.player_order)):
            idx = (start_index + i + 1) % len(self.player_order)
            pid = self.player_order[idx]
            
            if pid not in alive:
                continue
            
            player = self.players[pid]
            round_cards = player["rounds"].get(self.round, [])
            revealed = len(player["cards_by_round_revealed"].get(self.round, []))
            
            if revealed < len(round_cards):
                self.current_player_index = idx
                self._add_log(f"🔄 Следующий ход: {player['name']}")
                return
        
        # Если никого не нашли — переходим в READY
        self.phase = GamePhase.READY
        self.players_ready = set()
        self._add_log(f"📢 Все игроки открыли карты в раунде {self.round}")
    
    def player_ready(self, player_id: str) -> Dict[str, Any]:
        """Игрок нажал 'Продолжить'"""
        if self.phase != GamePhase.READY:
            return {"success": False, "message": "Игра не в режиме готовности"}
        
        if player_id in self.observer_players or player_id in self.eliminated_players:
            return {"success": False, "message": "Вы выбыли из игры"}
        
        self.players_ready.add(player_id)
        
        # Боты автоматически готовы
        for pid in self.get_bot_players():
            self.players_ready.add(pid)
        
        alive = len(self.get_alive_players())
        ready = len(self.players_ready)
        
        self._add_log(f"✅ {self.players[player_id]['name']} готов ({ready}/{alive})")
        
        if ready >= alive:
            # Все готовы → начинаем голосование
            return self.start_voting()
        
        return {
            "success": True,
            "ready_count": ready,
            "total_players": alive,
            "message": f"Ожидаем остальных игроков ({ready}/{alive})",
        }
    
    # ============================================
    # ГОЛОСОВАНИЕ
    # ============================================
    
    def start_voting(self) -> Dict[str, Any]:
        """Начинает голосование"""
        if self.phase == GamePhase.FINAL_VOTING:
            return self.start_final_voting()
        
        if self.phase != GamePhase.READY:
            return {"success": False, "message": "Игра не в режиме готовности"}
        
        self.phase = GamePhase.VOTING
        self.votes = {}
        self._add_log(f"🗳️ НАЧАЛО ГОЛОСОВАНИЯ! Раунд {self.round}")
        
        # Боты голосуют автоматически (позже)
        return {
            "success": True,
            "phase": "voting",
            "message": "Голосование началось!",
        }
    
    def submit_vote(self, voter_id: str, target_id: str) -> Dict[str, Any]:
        """Принимает голос от игрока"""
        if self.phase == GamePhase.FINAL_VOTING:
            return self.submit_final_vote(voter_id, target_id)
        
        if self.phase != GamePhase.VOTING:
            return {"success": False, "message": "Голосование не активно"}
        
        if voter_id in self.observer_players or voter_id in self.eliminated_players:
            return {"success": False, "message": "Вы выбыли из игры"}
        
        if voter_id in self.votes:
            return {"success": False, "message": "Вы уже проголосовали"}
        
        if target_id not in self.get_alive_players():
            return {"success": False, "message": "Цель не найдена или выбыла"}
        
        if target_id == voter_id:
            return {"success": False, "message": "Нельзя голосовать за себя"}
        
        self.votes[voter_id] = target_id
        self._add_log(f"🗳️ {self.players[voter_id]['name']} проголосовал")
        
        # Проверяем, все ли проголосовали
        alive = self.get_alive_players()
        if len(self.votes) >= len(alive):
            return self.process_voting_results()
        
        return {
            "success": True,
            "vote_count": len(self.votes),
            "total_players": len(alive),
            "message": f"Голос принят ({len(self.votes)}/{len(alive)})",
        }
    
    def process_voting_results(self) -> Dict[str, Any]:
        """Обрабатывает результаты голосования"""
        # Подсчёт голосов
        vote_results = {}
        for target in self.votes.values():
            vote_results[target] = vote_results.get(target, 0) + 1
        
        # Находим игрока с максимальным количеством голосов
        max_votes = max(vote_results.values())
        eliminated = [pid for pid, count in vote_results.items() if count == max_votes]
        
        # Если несколько игроков набрали максимум — выбираем случайного
        target_id = random.choice(eliminated)
        
        # Сохраняем историю голосования
        self.vote_history.append({
            "round": self.round,
            "votes": self.votes.copy(),
            "results": vote_results.copy(),
            "eliminated": target_id,
        })
        
        # Проверяем, не выбыл ли игрок из-за способности "Быстрый выезд" (Таксист)
        target_player = self.players.get(target_id)
        if target_player and target_player.get("role") == "Таксист" and target_player.get("skill_used", False) == False:
            # Таксист может избежать вылета 1 раз
            target_player["skill_used"] = True
            self._add_log(f"🚕 {target_player['name']} использовал 'Быстрый выезд' и избежал вылета!")
            
            # Выбираем следующего игрока для вылета
            candidates = [pid for pid in self.get_alive_players() if pid != target_id]
            if candidates:
                target_id = random.choice(candidates)
        
        # Обрабатываем выбывание
        return self.eliminate_player(target_id)
    
    def eliminate_player(self, player_id: str) -> Dict[str, Any]:
        """Обрабатывает выбывание игрока"""
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "Игрок не найден"}
        
        name = player["name"]
        
        # Снимаем 1 жизнь
        player["health"] -= 1
        self._add_log(f"💔 {name} теряет жизнь! Осталось: {player['health']}/3")
        
        if player["health"] <= 0:
            # Жизни закончились — игрок выбывает
            self.eliminated_players.append(player_id)
            self.observer_players.add(player_id)
            self._add_log(f"💀 {name} ПОЛНОСТЬЮ ВЫБЫЛ из игры!")
            
            # Уведомление в чат
            self._add_log(f"👀 {name} теперь наблюдатель")
        else:
            # Игрок остаётся, но с потерей жизни
            self._add_log(f"🔄 {name} остаётся в игре с {player['health']} жизнями")
        
        # Проверяем, остались ли живые игроки
        alive = self.get_alive_players()
        human_alive = self.get_human_players()
        bot_alive = self.get_bot_players()
        
        # Проверяем условия завершения игры
        if len(alive) == 0:
            # Все выбыли
            self.phase = GamePhase.FINISHED
            self._add_log("💀 Все игроки выбыли! Игра завершена.")
            return {"success": True, "game_finished": True, "winner": "none"}
        
        if len(human_alive) == 0 and len(bot_alive) > 0:
            # Остались только боты
            self.phase = GamePhase.FINISHED
            self._add_log("🤖 ПОБЕДА БОТОВ!")
            return {"success": True, "game_finished": True, "winner": "bots"}
        
        if len(human_alive) == 1 and len(bot_alive) == 0:
            # Остался 1 человек
            self.phase = GamePhase.FINISHED
            winner = self.players[human_alive[0]]
            self.winner_id = human_alive[0]
            self._add_log(f"🏆 ПОБЕДА! {winner['name']} выжил!")
            return {"success": True, "game_finished": True, "winner": "human", "winner_name": winner["name"]}
        
        # Если это был финальный раунд — переходим в финал
        if self.round >= self.max_rounds:
            return self.start_final_phase()
        
        # Иначе — следующий раунд
        self.round += 1
        self.phase = GamePhase.PLAYING
        self.votes = {}
        self.players_ready = set()
        self.current_player_index = 0
        
        # Сбрасываем открытые карты для всех живых игроков
        for pid in alive:
            self.players[pid]["revealed_cards"] = []
            if self.round in self.players[pid]["cards_by_round_revealed"]:
                self.players[pid]["cards_by_round_revealed"][self.round] = []
        
        self._add_log(f"📝 НАЧАЛО РАУНДА {self.round}")
        
        return {
            "success": True,
            "new_round": self.round,
            "eliminated": player_id,
            "health_left": player["health"],
        }
    
    # ============================================
    # ФИНАЛЬНАЯ ФАЗА
    # ============================================
    
    def start_final_phase(self) -> Dict[str, Any]:
        """Начинает финальную фазу (титульный лист + голосование)"""
        self.phase = GamePhase.FINAL_READY
        
        # Собираем биографии всех живых игроков
        self.final_biographies = {}
        for pid in self.get_alive_players():
            player = self.players[pid]
            self.final_biographies[pid] = get_full_biography(player)
        
        self._add_log("📜 ФИНАЛЬНАЯ ФАЗА! Игроки могут посмотреть биографии")
        self._add_log("🗳️ Голосование 'Кто тебе нравится?' начнётся после готовности")
        
        return {
            "success": True,
            "phase": "final_ready",
            "biographies": self.final_biographies,
            "message": "Финальная фаза! Изучите биографии игроков.",
        }
    
    def start_final_voting(self) -> Dict[str, Any]:
        """Начинает финальное голосование"""
        if self.phase != GamePhase.FINAL_READY:
            return {"success": False, "message": "Финальная фаза не активна"}
        
        self.phase = GamePhase.FINAL_VOTING
        self.final_votes = {}
        self._add_log("🗳️ ФИНАЛЬНОЕ ГОЛОСОВАНИЕ! Кто тебе нравится?")
        
        return {
            "success": True,
            "phase": "final_voting",
            "message": "Голосуйте за игрока, который вам нравится!",
        }
    
    def submit_final_vote(self, voter_id: str, target_id: str) -> Dict[str, Any]:
        """Принимает финальный голос"""
        if self.phase != GamePhase.FINAL_VOTING:
            return {"success": False, "message": "Финальное голосование не активно"}
        
        if voter_id in self.observer_players or voter_id in self.eliminated_players:
            return {"success": False, "message": "Вы выбыли из игры"}
        
        if voter_id in self.final_votes:
            return {"success": False, "message": "Вы уже проголосовали"}
        
        if target_id not in self.get_alive_players():
            return {"success": False, "message": "Цель не найдена"}
        
        self.final_votes[voter_id] = target_id
        self._add_log(f"⭐ {self.players[voter_id]['name']} проголосовал в финале")
        
        # Проверяем, все ли проголосовали
        alive = self.get_alive_players()
        if len(self.final_votes) >= len(alive):
            return self.process_final_results()
        
        return {
            "success": True,
            "vote_count": len(self.final_votes),
            "total_players": len(alive),
            "message": f"Голос принят ({len(self.final_votes)}/{len(alive)})",
        }
    
    def process_final_results(self) -> Dict[str, Any]:
        """Обрабатывает финальные результаты"""
        # Подсчёт голосов
        vote_results = {}
        for target in self.final_votes.values():
            vote_results[target] = vote_results.get(target, 0) + 1
        
        # Находим победителя
        max_votes = max(vote_results.values())
        winners = [pid for pid, count in vote_results.items() if count == max_votes]
        
        # Если несколько победителей — выбираем случайного
        winner_id = random.choice(winners)
        winner = self.players[winner_id]
        self.winner_id = winner_id
        
        self.phase = GamePhase.FINISHED
        self._add_log(f"🏆 {winner['name']} ПОБЕДИЛ в финальном голосовании!")
        self._add_log(f"📊 Голосов: {vote_results}")
        
        return {
            "success": True,
            "game_finished": True,
            "winner": "human",
            "winner_name": winner["name"],
            "final_results": vote_results,
        }
    
    # ============================================
    # СПОСОБНОСТИ ПЕРСОНАЖЕЙ
    # ============================================
    
    def use_skill(self, player_id: str, target_id: str = None) -> Dict[str, Any]:
        """Использование способности персонажа"""
        if self.phase != GamePhase.VOTING and self.phase != GamePhase.PLAYING:
            return {"success": False, "message": "Сейчас нельзя использовать способность"}
        
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "Игрок не найден"}
        
        if player.get("skill_used", False):
            return {"success": False, "message": "Вы уже использовали способность в этом раунде"}
        
        role = player.get("role")
        skill = player.get("role_skill")
        
        if not role or not skill:
            return {"success": False, "message": "У вас нет способности"}
        
        result = {"success": True, "skill": skill, "role": role}
        
        # ============================================
        # РЕАЛИЗАЦИЯ СПОСОБНОСТЕЙ
        # ============================================
        
        if skill == "Проверка факта" and target_id:
            # Шериф: узнаёт случайный факт о игроке
            target = self.players.get(target_id)
            if target:
                facts = [c for c in target.get("all_cards", []) if c["type"] == "fact"]
                if facts:
                    fact = random.choice(facts)
                    result["message"] = f"📖 Вы узнали факт о {target['name']}: {fact['name']}"
                    self._add_log(f"🔍 Шериф {player['name']} проверил факт о {target['name']}")
                else:
                    result["message"] = f"У {target['name']} нет фактов для проверки"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Соблазнение" and target_id:
            # Проститутка: узнаёт секрет игрока
            target = self.players.get(target_id)
            if target:
                secrets = [c for c in target.get("all_cards", []) if c["type"] == "secret"]
                if secrets:
                    secret = random.choice(secrets)
                    result["message"] = f"🤫 Вы узнали секрет {target['name']}: {secret['name']} — {secret['desc']}"
                    self._add_log(f"💋 Проститутка {player['name']} соблазнила {target['name']}")
                else:
                    result["message"] = f"У {target['name']} нет секретов"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Страйк":
            # Блогер/Инфлюенсер: если кто-то голосует против → ответ в лог
            # Эта способность срабатывает автоматически при голосовании
            result["message"] = "📱 Вы готовы кинуть страйк на того, кто проголосует против вас!"
            self._add_log(f"📱 {player['name']} готовит страйк!")
        
        elif skill == "Мороженое" and target_id:
            # Продавец мороженого: угощает игрока → тот теряет голос
            target = self.players.get(target_id)
            if target:
                result["message"] = f"🍦 Вы угостили {target['name']} мороженым! Он теряет голос в этом раунде."
                self._add_log(f"🍦 {player['name']} угостил {target['name']} мороженым")
                # Помечаем цель, чтобы она не могла голосовать (реализуется в голосовании)
                self.skill_targets[target_id] = "no_vote"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Быстрый выезд":
            # Таксист: избегает вылета 1 раз (реализовано в eliminate_player)
            result["message"] = "🚕 Вы готовы быстро выехать, если вас попытаются выгнать!"
            self._add_log(f"🚕 {player['name']} активировал быстрый выезд")
        
        elif skill == "Вкусный ужин" and target_id:
            # Повар: выбранный игрок получает +1 голос
            target = self.players.get(target_id)
            if target:
                result["message"] = f"🍲 Вы приготовили вкусный ужин для {target['name']}! Он получает +1 голос."
                self._add_log(f"🍲 {player['name']} угостил {target['name']}")
                # Добавляем бонусный голос (реализуется в голосовании)
                self.skill_targets[target_id] = "bonus_vote"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Иллюзия":
            # Фокусник: скрывает одну свою карту от голосования
            result["message"] = "🎩 Вы скрыли одну свою карту от голосования!"
            self._add_log(f"🎩 {player['name']} скрыл карту")
            # Помечаем, что карта скрыта (реализуется в отображении)
            self.skill_targets[player_id] = "hidden_card"
        
        elif skill == "Голос духов":
            # Медиум: узнаёт, кто голосовал против него в прошлом
            # Проверяем историю голосований
            for vote_record in reversed(self.vote_history):
                if player_id in vote_record["votes"].values():
                    voters = [vid for vid, target in vote_record["votes"].items() if target == player_id]
                    if voters:
                        names = [self.players[vid]["name"] for vid in voters if vid in self.players]
                        result["message"] = f"👻 Духи говорят, что против вас голосовали: {', '.join(names)}"
                        self._add_log(f"👻 {player['name']} узнал, кто голосовал против него")
                        break
            if "message" not in result:
                result["message"] = "👻 Духи молчат... Против вас никто не голосовал в прошлом раунде."
        
        elif skill == "Смех" and target_id:
            # Клоун-убийца: заставляет смеяться → не может голосовать
            target = self.players.get(target_id)
            if target:
                result["message"] = f"😂 Вы рассмешили {target['name']}! Он не может голосовать в этом раунде."
                self._add_log(f"😂 {player['name']} рассмешил {target['name']}")
                self.skill_targets[target_id] = "no_vote"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Починка" and target_id:
            # Сантехник: чинит жизнь себе или другому
            target = self.players.get(target_id)
            if target:
                if target["health"] < target["max_health"]:
                    target["health"] += 1
                    result["message"] = f"🔧 Вы починили {target['name']}! Жизни: {target['health']}/3"
                    self._add_log(f"🔧 {player['name']} починил {target['name']}")
                else:
                    result["message"] = f"🔧 У {target['name']} уже полное здоровье!"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Монетизация":
            # Ютубер: если за него голосуют → получает +1 голос в свой счёт
            # Реализуется автоматически при голосовании
            result["message"] = "📹 Вы готовы монетизировать голоса против вас!"
            self._add_log(f"📹 {player['name']} активировал монетизацию")
        
        elif skill == "Лечение" and target_id:
            # Доктор: восстанавливает 1 жизнь
            target = self.players.get(target_id)
            if target:
                if target["health"] < target["max_health"]:
                    target["health"] += 1
                    result["message"] = f"💊 Вы вылечили {target['name']}! Жизни: {target['health']}/3"
                    self._add_log(f"💊 {player['name']} вылечил {target['name']}")
                else:
                    result["message"] = f"💊 У {target['name']} уже полное здоровье!"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Баррикада" and target_id:
            # Инженер: защищает от вылета
            target = self.players.get(target_id)
            if target:
                result["message"] = f"🛡️ Вы защитили {target['name']} от вылета в этом раунде!"
                self._add_log(f"🛡️ {player['name']} защитил {target['name']}")
                self.skill_targets[target_id] = "protected"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Анализ" and target_id:
            # Учёный: узнаёт профессию
            target = self.players.get(target_id)
            if target:
                result["message"] = f"🔬 Вы узнали профессию {target['name']}: {target.get('role', 'Неизвестно')}"
                self._add_log(f"🔬 {player['name']} проанализировал {target['name']}")
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Огневая поддержка" and target_id:
            # Солдат: даёт +2 голоса
            target = self.players.get(target_id)
            if target:
                result["message"] = f"💥 {target['name']} получает +2 голоса в этом раунде!"
                self._add_log(f"💥 {player['name']} дал огневую поддержку {target['name']}")
                self.skill_targets[target_id] = "bonus_vote_2"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Разведка":
            # Разведчик: узнаёт, кто за кого голосовал
            if self.vote_history:
                last = self.vote_history[-1]
                votes_str = "\n".join([f"{self.players.get(vid, {}).get('name', 'Неизвестно')} → {self.players.get(tid, {}).get('name', 'Неизвестно')}" for vid, tid in last["votes"].items() if vid in self.players and tid in self.players])
                result["message"] = f"🔭 В прошлом раунде голосовали так:\n{votes_str}"
                self._add_log(f"🔭 {player['name']} провёл разведку")
            else:
                result["message"] = "🔭 Нет данных о прошлых голосованиях"
        
        elif skill == "Точный выстрел" and target_id:
            # Снайпер: убирает 1 голос
            target = self.players.get(target_id)
            if target:
                result["message"] = f"🎯 Вы убрали 1 голос у {target['name']}!"
                self._add_log(f"🎯 {player['name']} сделал точный выстрел по {target['name']}")
                self.skill_targets[target_id] = "minus_vote"
            else:
                result["success"] = False
                result["message"] = "Игрок не найден"
        
        elif skill == "Мина":
            # Сапёр: если против него голосуют → голосующий теряет голос
            result["message"] = "💣 Вы заложили мину! Если кто-то проголосует против вас, он потеряет голос."
            self._add_log(f"💣 {player['name']} заложил мину")
            self.skill_targets[player_id] = "mine"
        
        elif skill == "Полевая аптечка":
            # Медик: восстанавливает 2 жизни себе
            if player["health"] < player["max_health"]:
                heal = min(2, player["max_health"] - player["health"])
                player["health"] += heal
                result["message"] = f"💉 Вы восстановили {heal} жизни! Жизни: {player['health']}/3"
                self._add_log(f"💉 {player['name']} использовал полевую аптечку")
            else:
                result["message"] = "💉 У вас уже полное здоровье!"
        
        else:
            result["success"] = False
            result["message"] = f"Способность '{skill}' ещё не реализована"
        
        # Отмечаем, что способность использована
        if result["success"]:
            player["skill_used"] = True
            self._add_log(f"⚡ {player['name']} использовал способность: {skill}")
        
        return result
    
    # ============================================
    # ЗАВЕРШЕНИЕ ИГРЫ
    # ============================================
    
    def finish_game(self) -> Dict[str, Any]:
        """Принудительно завершает игру"""
        self.phase = GamePhase.FINISHED
        self._add_log("⛔ Игра завершена")
        return {
            "success": True,
            "game_finished": True,
            "winner": "none",
            "message": "Игра завершена",
        }
    
    def get_final_results(self) -> Dict[str, Any]:
        """Возвращает финальные результаты игры"""
        return {
            "game_id": self.game_id,
            "chat_id": self.chat_id,
            "rounds": self.round,
            "winner_id": self.winner_id,
            "winner_name": self.players.get(self.winner_id, {}).get("name") if self.winner_id else None,
            "players": self.get_players_list(),
            "vote_history": self.vote_history,
            "game_log": self.game_log,
        }


# ============================================
# ФАБРИКА ДЛЯ СОЗДАНИЯ ИГРЫ
# ============================================

def create_game(chat_id: str, host_id: str, host_name: str) -> GameEngine:
    """Создаёт новый экземпляр игры"""
    return GameEngine(chat_id, host_id, host_name)


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ИГРОВОГО ДВИЖКА")
    print("=" * 60)
    
    # Создаём игру
    game = create_game("test_chat", "host_123", "Ведущий")
    print(f"✅ Игра создана: {game.game_id}")
    
    # Добавляем игроков
    game.add_player("user_1", "Матвей")
    game.add_player("user_2", "Анна")
    game.add_player("user_3", "Дмитрий")
    game.add_player("user_4", "Елена")
    game.add_player("user_5", "Алексей")
    
    print(f"👥 Игроков: {len(game.players)}")
    
    # Добавляем бота
    game.add_bot("🤖 Бот-Шериф")
    print(f"🤖 Добавлен бот")
    
    # Запускаем игру
    if game.start_game():
        print("✅ Игра запущена!")
        print(f"📝 Раунд: {game.round}")
        print(f"💀 Катастрофа: {game.disaster}")
        
        # Проверяем состояние
        state = game.get_game_state("user_1")
        print(f"📊 Состояние: {state['phase']}")
        
        print("\n📋 Полная биография первого игрока:")
        print(get_full_biography(game.players["user_1"]))
        
        print("\n✅ Тестирование завершено!")
    else:
        print("❌ Не удалось запустить игру")