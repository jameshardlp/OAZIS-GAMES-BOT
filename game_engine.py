"""
Модуль игрового движка для "Кафе ОАЗИС 2.0"
Управляет логикой игры, ходами, голосованиями, способностями и жизнями
"""

import random
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from enum import Enum

from cards_generator import (
    generate_full_character,
    generate_character_with_specific_role,
    format_card_for_display,
    get_full_biography,
    get_card_emoji_for_display,
    ROLES,
)


class GamePhase(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    READY = "ready"
    VOTING = "voting"
    SKILL = "skill"
    FINAL_READY = "final_ready"
    FINAL_VOTING = "final_voting"
    FINISHED = "finished"


class PlayerStatus(Enum):
    ALIVE = "alive"
    ELIMINATED = "eliminated"
    OBSERVER = "observer"
    BOT = "bot"


class GameEngine:
    
    def __init__(self, chat_id: str, host_id: str, host_name: str):
        self.chat_id = chat_id
        self.host_id = host_id
        self.host_name = host_name
        self.game_id = self._generate_game_id()
        
        self.players: Dict[str, Dict] = {}
        self.player_order: List[str] = []
        
        self.phase: GamePhase = GamePhase.WAITING
        self.round: int = 0
        self.max_rounds: int = 5
        self.current_player_index: int = 0
        
        self.votes: Dict[str, str] = {}
        self.final_votes: Dict[str, str] = {}
        self.vote_history: List[Dict] = []
        
        self.skill_usage: Dict[str, bool] = {}
        self.skill_targets: Dict[str, str] = {}
        self.skill_log: List[str] = []
        
        self.eliminated_players: List[str] = []
        self.observer_players: Set[str] = set()
        
        self.reveal_order: List[str] = []
        self.players_ready: Set[str] = set()
        
        self.final_biographies: Dict[str, str] = {}
        self.final_results: Dict[str, int] = {}
        self.winner_id: Optional[str] = None
        
        self.disaster: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.game_log: List[str] = []
        self._add_log("🎮 Игра создана!")
    
    def _generate_game_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _add_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.game_log.append(f"[{timestamp}] {message}")
    
    def get_game_state(self, player_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "game_id": self.game_id,
            "chat_id": self.chat_id,
            "phase": self.phase.value,
            "round": self.round,
            "max_rounds": self.max_rounds,
            "players": self.get_players_list(player_id),
            "is_host": str(self.host_id) == str(player_id) if player_id else False,
            "is_observer": player_id in self.observer_players if player_id else False,
            "is_eliminated": player_id in self.eliminated_players if player_id else False,
            "current_turn": self.get_current_player_id(),
            "vote_count": len(self.votes),
            "total_players": len(self.get_alive_players()),
            "game_log": self.game_log[-20:],
            "disaster": self.disaster,
        }
    
    def get_players_list(self, viewer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = []
        for player_id, player in self.players.items():
            data = {
                "id": player_id,
                "name": player.get("name", "Игрок"),
                "role": player.get("role", "Неизвестно"),
                "health": player.get("health", 3),
                "max_health": player.get("max_health", 3),
                "is_host": str(player_id) == str(self.host_id),
                "is_bot": player.get("is_bot", False),
                "is_observer": player_id in self.observer_players,
                "is_eliminated": player_id in self.eliminated_players,
                "status": self._get_player_status(player_id),
                "revealed_count": len(player.get("revealed_cards", [])),
                "total_cards": len(player.get("all_cards", [])),
            }
            
            if viewer_id and viewer_id == player_id:
                data["cards"] = player.get("all_cards", [])
                data["revealed_cards"] = player.get("revealed_cards", [])
            elif viewer_id and viewer_id in self.observer_players:
                data["cards"] = player.get("revealed_cards", [])
            
            result.append(data)
        return result
    
    def _get_player_status(self, player_id: str) -> str:
        if player_id in self.eliminated_players:
            return PlayerStatus.ELIMINATED.value
        if player_id in self.observer_players:
            return PlayerStatus.OBSERVER.value
        if self.players.get(player_id, {}).get("is_bot", False):
            return PlayerStatus.BOT.value
        return PlayerStatus.ALIVE.value
    
    def get_current_player_id(self) -> Optional[str]:
        if not self.player_order or self.phase != GamePhase.PLAYING:
            return None
        if self.current_player_index >= len(self.player_order):
            return None
        return self.player_order[self.current_player_index]
    
    def get_alive_players(self) -> List[str]:
        return [
            pid for pid in self.players
            if pid not in self.eliminated_players
            and pid not in self.observer_players
        ]
    
    def get_human_players(self) -> List[str]:
        return [
            pid for pid in self.get_alive_players()
            if not self.players[pid].get("is_bot", False)
        ]
    
    def get_bot_players(self) -> List[str]:
        return [
            pid for pid in self.get_alive_players()
            if self.players[pid].get("is_bot", False)
        ]
    
    def add_player(self, player_id: str, name: str, is_bot: bool = False) -> bool:
        if player_id in self.players:
            return False
        
        if len(self.players) >= 6:
            return False
        
        self.players[player_id] = {
            "id": player_id,
            "name": name,
            "is_bot": is_bot,
            "is_host": str(player_id) == str(self.host_id),
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
        bot_id = f"bot_{self._generate_game_id()}"
        return self.add_player(bot_id, bot_name, is_bot=True)
    
    def remove_player(self, player_id: str) -> bool:
        if player_id not in self.players:
            return False
        
        name = self.players[player_id]["name"]
        del self.players[player_id]
        if player_id in self.player_order:
            self.player_order.remove(player_id)
        self._add_log(f"🚪 {name} покинул игру")
        return True
    
    def start_game(self) -> bool:
        if self.phase != GamePhase.WAITING:
            return False
        
        alive_players = self.get_alive_players()
        if len(alive_players) < 4:
            return False
        
        from cards_generator import get_random_disaster
        self.disaster = get_random_disaster()
        self._add_log(f"💀 КАТАСТРОФА: {self.disaster}")
        
        for player_id in self.players:
            player = self.players[player_id]
            if player.get("is_bot", False):
                character = generate_full_character(player["name"])
            else:
                character = generate_full_character(player["name"])
            
            player["role"] = character["role"]
            player["role_skill"] = character["role_skill"]
            player["role_desc"] = character["role_desc"]
            player["rounds"] = character["rounds"]
            player["all_cards"] = character["all_cards"]
            player["health"] = character["health"]
            player["max_health"] = character["max_health"]
            player["revealed_cards"] = []
            player["cards_by_round_revealed"] = {1: [], 2: [], 3: [], 4: [], 5: []}
            player["skill_used"] = False
        
        self.round = 1
        self.phase = GamePhase.PLAYING
        self.current_player_index = 0
        self.reveal_order = self.player_order.copy()
        
        self._add_log(f"🔥 ИГРА НАЧАЛАСЬ! Раунд {self.round}")
        self._add_log(f"👥 Игроков: {len(self.get_alive_players())}")
        self._add_log(f"💀 Катастрофа: {self.disaster}")
        
        return True
    
    def reveal_card(self, player_id: str, card_index: int) -> Dict[str, Any]:
        if self.phase != GamePhase.PLAYING:
            return {"success": False, "message": "Не время открывать карты"}
        
        if player_id in self.observer_players or player_id in self.eliminated_players:
            return {"success": False, "message": "Вы выбыли из игры"}
        
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "Игрок не найден"}
        
        current = self.get_current_player_id()
        if current and current != player_id:
            return {"success": False, "message": "Сейчас не ваш ход"}
        
        round_cards = player["rounds"].get(self.round, [])
        if not round_cards:
            return {"success": False, "message": "Нет карт для открытия"}
        
        if card_index < 0 or card_index >= len(round_cards):
            return {"success": False, "message": "Неверный индекс карты"}
        
        card = round_cards[card_index]
        
        if card in player["revealed_cards"] or card in player["cards_by_round_revealed"].get(self.round, []):
            return {"success": False, "message": "Эта карта уже открыта"}
        
        player["revealed_cards"].append(card)
        player["cards_by_round_revealed"][self.round].append(card)
        
        self._add_log(f"🃏 {player['name']} открыл карту: {format_card_for_display(card)}")
        
        all_revealed = len(player["cards_by_round_revealed"][self.round]) >= len(round_cards)
        
        if all_revealed:
            self._move_to_next_player()
        
        return {
            "success": True,
            "card": card,
            "all_revealed": all_revealed,
            "player_name": player["name"],
        }
    
    def _move_to_next_player(self) -> None:
        alive = self.get_alive_players()
        
        all_done = True
        for pid in alive:
            player = self.players[pid]
            round_cards = player["rounds"].get(self.round, [])
            revealed = len(player["cards_by_round_revealed"].get(self.round, []))
            if revealed < len(round_cards):
                all_done = False
                break
        
        if all_done:
            self.phase = GamePhase.READY
            self.players_ready = set()
            self._add_log(f"📢 Все игроки открыли карты в раунде {self.round}")
            self._add_log("⏳ Нажмите 'Продолжить' чтобы перейти к голосованию")
            return
        
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
        
        self.phase = GamePhase.READY
        self.players_ready = set()
        self._add_log(f"📢 Все игроки открыли карты в раунде {self.round}")
    
    def player_ready(self, player_id: str) -> Dict[str, Any]:
        if self.phase != GamePhase.READY:
            return {"success": False, "message": "Игра не в режиме готовности"}
        
        if player_id in self.observer_players or player_id in self.eliminated_players:
            return {"success": False, "message": "Вы выбыли из игры"}
        
        self.players_ready.add(player_id)
        
        for pid in self.get_bot_players():
            self.players_ready.add(pid)
        
        alive = len(self.get_alive_players())
        ready = len(self.players_ready)
        
        self._add_log(f"✅ {self.players[player_id]['name']} готов ({ready}/{alive})")
        
        if ready >= alive:
            return self.start_voting()
        
        return {
            "success": True,
            "ready_count": ready,
            "total_players": alive,
            "message": f"Ожидаем остальных игроков ({ready}/{alive})",
        }
    
    def start_voting(self) -> Dict[str, Any]:
        if self.phase == GamePhase.FINAL_VOTING:
            return self.start_final_voting()
        
        if self.phase != GamePhase.READY:
            return {"success": False, "message": "Игра не в режиме готовности"}
        
        self.phase = GamePhase.VOTING
        self.votes = {}
        self._add_log(f"🗳️ НАЧАЛО ГОЛОСОВАНИЯ! Раунд {self.round}")
        
        return {
            "success": True,
            "phase": "voting",
            "message": "Голосование началось!",
        }
    
    def submit_vote(self, voter_id: str, target_id: str) -> Dict[str, Any]:
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
        vote_results = {}
        for target in self.votes.values():
            vote_results[target] = vote_results.get(target, 0) + 1
        
        max_votes = max(vote_results.values())
        eliminated = [pid for pid, count in vote_results.items() if count == max_votes]
        
        target_id = random.choice(eliminated)
        
        self.vote_history.append({
            "round": self.round,
            "votes": self.votes.copy(),
            "results": vote_results.copy(),
            "eliminated": target_id,
        })
        
        target_player = self.players.get(target_id)
        if target_player and target_player.get("role") == "Таксист" and target_player.get("skill_used", False) == False:
            target_player["skill_used"] = True
            self._add_log(f"🚕 {target_player['name']} использовал 'Быстрый выезд' и избежал вылета!")
            
            candidates = [pid for pid in self.get_alive_players() if pid != target_id]
            if candidates:
                target_id = random.choice(candidates)
        
        return self.eliminate_player(target_id)
    
    def eliminate_player(self, player_id: str) -> Dict[str, Any]:
        player = self.players.get(player_id)
        if not player:
            return {"success": False, "message": "Игрок не найден"}
        
        name = player["name"]
        
        player["health"] -= 1
        self._add_log(f"💔 {name} теряет жизнь! Осталось: {player['health']}/3")
        
        if player["health"] <= 0:
            self.eliminated_players.append(player_id)
            self.observer_players.add(player_id)
            self._add_log(f"💀 {name} ПОЛНОСТЬЮ ВЫБЫЛ из игры!")
            self._add_log(f"👀 {name} теперь наблюдатель")
        else:
            self._add_log(f"🔄 {name} остаётся в игре с {player['health']} жизнями")
        
        alive = self.get_alive_players()
        human_alive = self.get_human_players()
        bot_alive = self.get_bot_players()
        
        if len(alive) == 0:
            self.phase = GamePhase.FINISHED
            self._add_log("💀 Все игроки выбыли! Игра завершена.")
            return {"success": True, "game_finished": True, "winner": "none"}
        
        if len(human_alive) == 0 and len(bot_alive) > 0:
            self.phase = GamePhase.FINISHED
            self._add_log("🤖 ПОБЕДА БОТОВ!")
            return {"success": True, "game_finished": True, "winner": "bots"}
        
        if len(human_alive) == 1 and len(bot_alive) == 0:
            self.phase = GamePhase.FINISHED
            winner = self.players[human_alive[0]]
            self.winner_id = human_alive[0]
            self._add_log(f"🏆 ПОБЕДА! {winner['name']} выжил!")
            return {"success": True, "game_finished": True, "winner": "human", "winner_name": winner["name"]}
        
        if self.round >= self.max_rounds:
            return self.start_final_phase()
        
        self.round += 1
        self.phase = GamePhase.PLAYING
        self.votes = {}
        self.players_ready = set()
        self.current_player_index = 0
        
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
    
    def start_final_phase(self) -> Dict[str, Any]:
        self.phase = GamePhase.FINAL_READY
        
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
        vote_results = {}
        for target in self.final_votes.values():
            vote_results[target] = vote_results.get(target, 0) + 1
        
        max_votes = max(vote_results.values())
        winners = [pid for pid, count in vote_results.items() if count == max_votes]
        
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
    
    def use_skill(self, player_id: str, target_id: str = None) -> Dict[str, Any]:
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
        
        result["message"] = f"⚡ Вы использовали способность '{skill}'"
        player["skill_used"] = True
        self._add_log(f"⚡ {player['name']} использовал способность: {skill}")
        
        return result
    
    def finish_game(self) -> Dict[str, Any]:
        self.phase = GamePhase.FINISHED
        self._add_log("⛔ Игра завершена")
        return {
            "success": True,
            "game_finished": True,
            "winner": "none",
            "message": "Игра завершена",
        }
    
    def get_final_results(self) -> Dict[str, Any]:
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


def create_game(chat_id: str, host_id: str, host_name: str) -> GameEngine:
    return GameEngine(chat_id, host_id, host_name)
