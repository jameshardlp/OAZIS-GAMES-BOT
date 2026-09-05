"""
Модуль построения биографии для "Кафе ОАЗИС 2.0"
Собирает полную биографию игрока из всех карт и формирует интерактивный титульный лист
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

# Импортируем утилиты из генератора карт
from cards_generator import (
    format_card_for_display,
    get_card_emoji_for_display,
    get_full_biography as get_full_biography_from_generator,
)


# ============================================
# КЛАСС БИОГРАФИИ
# ============================================

class BiographyBuilder:
    """
    Строитель биографии персонажа из всех его карт
    """
    
    def __init__(self, player_data: Dict[str, Any]):
        self.player = player_data
        self.name = player_data.get("name", "Неизвестно")
        self.role = player_data.get("role", "Неизвестно")
        self.role_skill = player_data.get("role_skill", "Нет способности")
        self.health = player_data.get("health", 3)
        self.max_health = player_data.get("max_health", 3)
        self.all_cards = player_data.get("all_cards", [])
        self.rounds = player_data.get("rounds", {})
        self.revealed_cards = player_data.get("revealed_cards", [])
        
        # Кэшируем биографию
        self._biography_cache = None
    
    # ============================================
    # ГРУППИРОВКА КАРТ
    # ============================================
    
    def get_cards_by_type(self, card_type: str) -> List[Dict[str, Any]]:
        """Возвращает все карты определённого типа"""
        return [c for c in self.all_cards if c.get("type") == card_type]
    
    def get_cards_by_round(self, round_num: int) -> List[Dict[str, Any]]:
        """Возвращает все карты определённого раунда"""
        return self.rounds.get(round_num, [])
    
    def get_revealed_cards_by_round(self, round_num: int) -> List[Dict[str, Any]]:
        """Возвращает открытые карты определённого раунда"""
        return self.player.get("cards_by_round_revealed", {}).get(round_num, [])
    
    def get_unrevealed_cards_by_round(self, round_num: int) -> List[Dict[str, Any]]:
        """Возвращает неоткрытые карты определённого раунда"""
        all_round = self.get_cards_by_round(round_num)
        revealed = self.get_revealed_cards_by_round(round_num)
        return [c for c in all_round if c not in revealed]
    
    # ============================================
    # СБОРКА БИОГРАФИИ
    # ============================================
    
    def build_biography(self) -> Dict[str, Any]:
        """
        Собирает полную биографию персонажа
        """
        if self._biography_cache:
            return self._biography_cache
        
        biography = {
            "name": self.name,
            "role": self.role,
            "role_skill": self.role_skill,
            "health": self.health,
            "max_health": self.max_health,
            "sections": {
                "role": self._build_role_section(),
                "skills": self._build_skills_section(),
                "weapons": self._build_weapons_section(),
                "items": self._build_items_section(),
                "facts": self._build_facts_section(),
                "history": self._build_history_section(),
                "relationships": self._build_relationships_section(),
                "plans": self._build_plans_section(),
                "secrets": self._build_secrets_section(),
                "traits": self._build_traits_section(),
                "bonus_traits": self._build_bonus_traits_section(),
            },
            "all_cards": self.all_cards,
            "rounds": self.rounds,
        }
        
        self._biography_cache = biography
        return biography
    
    # ============================================
    # СЕКЦИИ БИОГРАФИИ
    # ============================================
    
    def _build_role_section(self) -> Dict[str, Any]:
        """Секция: Роль и способность"""
        role_cards = self.get_cards_by_type("role")
        if not role_cards:
            return {"title": "🎴 Роль", "items": ["Неизвестно"]}
        
        items = []
        for card in role_cards:
            name = card.get("name", "Неизвестно")
            skill = card.get("skill", self.role_skill)
            desc = card.get("desc", "")
            items.append({
                "name": name,
                "skill": skill,
                "desc": desc,
                "icon": "🎴",
            })
        
        return {
            "title": "🎴 Роль",
            "items": items,
        }
    
    def _build_skills_section(self) -> Dict[str, Any]:
        """Секция: Навыки"""
        skill_cards = self.get_cards_by_type("skill")
        if not skill_cards:
            return {"title": "🔪 Навыки", "items": []}
        
        items = []
        for card in skill_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "🔪",
            })
        
        return {
            "title": "🔪 Навыки",
            "items": items,
        }
    
    def _build_weapons_section(self) -> Dict[str, Any]:
        """Секция: Оружие"""
        weapon_cards = self.get_cards_by_type("weapon")
        if not weapon_cards:
            return {"title": "🔫 Оружие", "items": []}
        
        items = []
        for card in weapon_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "🔫",
            })
        
        return {
            "title": "🔫 Оружие",
            "items": items,
        }
    
    def _build_items_section(self) -> Dict[str, Any]:
        """Секция: Предметы"""
        item_cards = self.get_cards_by_type("item")
        if not item_cards:
            return {"title": "🎒 Предметы", "items": []}
        
        items = []
        for card in item_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "🎒",
            })
        
        return {
            "title": "🎒 Предметы",
            "items": items,
        }
    
    def _build_facts_section(self) -> Dict[str, Any]:
        """Секция: Факты"""
        fact_cards = self.get_cards_by_type("fact")
        if not fact_cards:
            return {"title": "📖 Факты", "items": []}
        
        items = []
        for card in fact_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "📖",
            })
        
        return {
            "title": "📖 Факты",
            "items": items,
        }
    
    def _build_history_section(self) -> Dict[str, Any]:
        """Секция: История из прошлого"""
        history_cards = self.get_cards_by_type("history")
        if not history_cards:
            return {"title": "📜 История", "items": []}
        
        items = []
        for card in history_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "📜",
            })
        
        return {
            "title": "📜 История",
            "items": items,
        }
    
    def _build_relationships_section(self) -> Dict[str, Any]:
        """Секция: Связи (союзники/враги)"""
        rel_cards = self.get_cards_by_type("relationship")
        if not rel_cards:
            return {"title": "🤝 Связи", "items": []}
        
        items = []
        for card in rel_cards:
            name = card.get("name", "Неизвестно")
            desc = card.get("desc", "")
            icon = card.get("icon", "🤝")
            
            # Определяем тип связи
            if "враг" in name.lower() or "enemy" in name.lower():
                icon = "👹"
            else:
                icon = "🤝"
            
            items.append({
                "name": name,
                "desc": desc,
                "icon": icon,
            })
        
        return {
            "title": "🤝 Связи",
            "items": items,
        }
    
    def _build_plans_section(self) -> Dict[str, Any]:
        """Секция: Планы на жизнь"""
        plan_cards = self.get_cards_by_type("plan")
        if not plan_cards:
            return {"title": "🌟 Планы", "items": []}
        
        items = []
        for card in plan_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "🌟",
            })
        
        return {
            "title": "🌟 Планы на жизнь",
            "items": items,
        }
    
    def _build_secrets_section(self) -> Dict[str, Any]:
        """Секция: Секреты (скрытые до финала)"""
        secret_cards = self.get_cards_by_type("secret")
        if not secret_cards:
            return {"title": "🤫 Секреты", "items": []}
        
        items = []
        for card in secret_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "🤫",
                "is_secret": True,
            })
        
        return {
            "title": "🤫 Секреты",
            "items": items,
        }
    
    def _build_traits_section(self) -> Dict[str, Any]:
        """Секция: Черты характера"""
        trait_cards = self.get_cards_by_type("trait")
        if not trait_cards:
            return {"title": "🧠 Черты", "items": []}
        
        items = []
        for card in trait_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "🧠",
            })
        
        return {
            "title": "🧠 Черты характера",
            "items": items,
        }
    
    def _build_bonus_traits_section(self) -> Dict[str, Any]:
        """Секция: Бонусные черты (финал)"""
        bonus_cards = self.get_cards_by_type("bonus_trait")
        if not bonus_cards:
            return {"title": "⭐ Особые черты", "items": []}
        
        items = []
        for card in bonus_cards:
            items.append({
                "name": card.get("name", "Неизвестно"),
                "desc": card.get("desc", ""),
                "icon": "⭐",
            })
        
        return {
            "title": "⭐ Особые черты",
            "items": items,
        }
    
    # ============================================
    # ФОРМАТИРОВАНИЕ ДЛЯ ОТОБРАЖЕНИЯ
    # ============================================
    
    def to_markdown(self, show_secrets: bool = True) -> str:
        """
        Возвращает биографию в формате Markdown
        """
        bio = self.build_biography()
        lines = []
        
        # Заголовок
        lines.append(f"# 📜 ПОЛНАЯ БИОГРАФИЯ: {bio['name']}")
        lines.append("")
        lines.append(f"**Роль:** {bio['role']}")
        lines.append(f"**Способность:** {bio['role_skill']}")
        lines.append(f"**Здоровье:** {'❤️' * bio['health']}{'🖤' * (bio['max_health'] - bio['health'])}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Секции
        sections_order = [
            "role", "skills", "weapons", "items", 
            "facts", "history", "relationships", 
            "plans", "traits", "bonus_traits"
        ]
        
        # Секреты добавляем только если разрешено
        if show_secrets:
            sections_order.append("secrets")
        
        for section_key in sections_order:
            section = bio["sections"].get(section_key, {})
            items = section.get("items", [])
            
            if not items:
                continue
            
            lines.append(f"## {section['title']}")
            for item in items:
                icon = item.get("icon", "•")
                name = item.get("name", "")
                desc = item.get("desc", "")
                
                if desc:
                    lines.append(f"- {icon} **{name}** — {desc}")
                else:
                    lines.append(f"- {icon} **{name}**")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def to_html(self, show_secrets: bool = True) -> str:
        """
        Возвращает биографию в формате HTML для Mini App
        """
        bio = self.build_biography()
        
        # Формируем HTML
        html = f'''
        <div class="biography-container">
            <div class="bio-header" style="text-align:center;padding:20px;background:linear-gradient(145deg,#1a0a00,#2a1a0a);border-radius:12px;border:2px solid #FFB000;margin-bottom:20px;">
                <h1 style="color:#FFB000;font-size:2.5rem;text-shadow:0 0 20px #FFB000;">📜 {bio['name']}</h1>
                <p style="font-size:1.2rem;color:#f5e6d3;">
                    <span style="color:#FFB000;">Роль:</span> {bio['role']}
                </p>
                <p style="font-size:1rem;color:#f5e6d3;opacity:0.8;">
                    ⚡ Способность: {bio['role_skill']}
                </p>
                <p style="font-size:1.5rem;margin-top:10px;">
                    {'❤️' * bio['health']}{'🖤' * (bio['max_health'] - bio['health'])}
                </p>
            </div>
            
            <div class="bio-sections" style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
        '''
        
        # Секции (2 колонки)
        sections_order = [
            ("role", "🎴 Роль"),
            ("skills", "🔪 Навыки"),
            ("weapons", "🔫 Оружие"),
            ("items", "🎒 Предметы"),
            ("facts", "📖 Факты"),
            ("history", "📜 История"),
            ("relationships", "🤝 Связи"),
            ("plans", "🌟 Планы"),
            ("traits", "🧠 Черты"),
            ("bonus_traits", "⭐ Особые черты"),
        ]
        
        if show_secrets:
            sections_order.append(("secrets", "🤫 Секреты"))
        
        for section_key, section_title in sections_order:
            section = bio["sections"].get(section_key, {})
            items = section.get("items", [])
            
            if not items:
                continue
            
            html += f'''
            <div class="bio-section" style="background:#1a0a00;border-radius:12px;border:1px solid #FFB000;padding:15px;">
                <h3 style="color:#FFB000;font-size:1rem;text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid #FFB000;padding-bottom:10px;margin-bottom:10px;">
                    {section_title}
                </h3>
                <ul style="list-style:none;padding:0;margin:0;">
            '''
            
            for item in items:
                icon = item.get("icon", "•")
                name = item.get("name", "")
                desc = item.get("desc", "")
                
                if desc:
                    html += f'''
                    <li style="padding:5px 0;border-bottom:1px solid rgba(255,176,0,0.1);">
                        <span style="color:#FFB000;">{icon}</span>
                        <strong>{name}</strong>
                        <span style="color:#f5e6d3;opacity:0.7;font-size:0.9rem;">— {desc}</span>
                    </li>
                    '''
                else:
                    html += f'''
                    <li style="padding:5px 0;border-bottom:1px solid rgba(255,176,0,0.1);">
                        <span style="color:#FFB000;">{icon}</span>
                        <strong>{name}</strong>
                    </li>
                    '''
            
            html += '''
                </ul>
            </div>
            '''
        
        html += '''
            </div>
        </div>
        '''
        
        return html
    
    def to_json(self) -> str:
        """Возвращает биографию в формате JSON"""
        bio = self.build_biography()
        return json.dumps(bio, ensure_ascii=False, indent=2)
    
    # ============================================
    # ИНТЕРАКТИВНЫЙ ТИТУЛЬНЫЙ ЛИСТ (HTML+CSS+JS)
    # ============================================
    
    @staticmethod
    def get_final_title_sheet(players_data: List[Dict[str, Any]]) -> str:
        """
        Генерирует интерактивный титульный лист для финала
        """
        # Строим биографии для всех игроков
        biographies = {}
        for player in players_data:
            if player.get("is_observer", False) or player.get("is_eliminated", False):
                continue
            builder = BiographyBuilder(player)
            biographies[player["id"]] = builder.to_html(show_secrets=True)
        
        # Формируем HTML
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    background: #0a0a0a;
                    color: #f5e6d3;
                    font-family: 'Courier New', monospace;
                    padding: 20px;
                }
                .final-title {
                    text-align: center;
                    padding: 40px;
                    background: linear-gradient(145deg, #1a0a00, #2a1a0a);
                    border-radius: 16px;
                    border: 2px solid #FFB000;
                    margin-bottom: 30px;
                    box-shadow: 0 0 60px rgba(255, 176, 0, 0.3);
                }
                .final-title h1 {
                    color: #FFB000;
                    font-size: 4rem;
                    text-shadow: 0 0 30px #FFB000;
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
                .final-title p {
                    color: #f5e6d3;
                    opacity: 0.7;
                    font-size: 1.2rem;
                }
                .players-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .player-card {
                    background: #1a0a00;
                    border-radius: 12px;
                    border: 2px solid #FFB000;
                    padding: 20px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .player-card:hover {
                    transform: scale(1.03);
                    box-shadow: 0 0 30px rgba(255, 176, 0, 0.4);
                }
                .player-card h3 {
                    color: #FFB000;
                    font-size: 1.5rem;
                }
                .player-card .role {
                    color: #f5e6d3;
                    opacity: 0.8;
                }
                .player-card .health {
                    font-size: 1.2rem;
                    margin-top: 10px;
                }
                .player-card.selected {
                    border-color: #FFD700;
                    box-shadow: 0 0 40px rgba(255, 215, 0, 0.6);
                }
                .bio-modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.9);
                    z-index: 1000;
                    overflow-y: auto;
                    padding: 20px;
                }
                .bio-modal.active {
                    display: block;
                }
                .bio-modal-content {
                    max-width: 800px;
                    margin: 20px auto;
                    background: #1a0a00;
                    border-radius: 16px;
                    border: 2px solid #FFB000;
                    padding: 30px;
                    position: relative;
                }
                .bio-modal-close {
                    position: absolute;
                    top: 15px;
                    right: 20px;
                    font-size: 2rem;
                    color: #FFB000;
                    cursor: pointer;
                    background: none;
                    border: none;
                }
                .btn-vote {
                    background: #FFB000;
                    color: #0a0a0a;
                    border: none;
                    padding: 15px 40px;
                    font-size: 1.5rem;
                    font-family: 'Courier New', monospace;
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.3s;
                    display: block;
                    margin: 20px auto;
                    font-weight: bold;
                }
                .btn-vote:hover {
                    transform: scale(1.05);
                    box-shadow: 0 0 30px rgba(255, 176, 0, 0.6);
                }
            </style>
        </head>
        <body>
            <div class="final-title">
                <h1>🏆 ФИНАЛ</h1>
                <p>Кто достоин остаться в кафе ОАЗИС?</p>
                <p style="margin-top:10px;font-size:0.9rem;">👆 Нажми на игрока, чтобы увидеть его биографию</p>
            </div>
            
            <div class="players-grid">
        '''
        
        for player in players_data:
            if player.get("is_observer", False) or player.get("is_eliminated", False):
                continue
            
            name = player.get("name", "Неизвестно")
            role = player.get("role", "Неизвестно")
            health = player.get("health", 3)
            max_health = player.get("max_health", 3)
            player_id = player.get("id", "")
            
            health_str = "❤️" * health + "🖤" * (max_health - health)
            
            html += f'''
            <div class="player-card" onclick="showBiography('{player_id}')" id="card-{player_id}">
                <h3>👤 {name}</h3>
                <div class="role">🎴 {role}</div>
                <div class="health">{health_str}</div>
            </div>
            '''
        
        html += '''
            </div>
            
            <button class="btn-vote" onclick="startVoting()">
                🗳️ НАЧАТЬ ГОЛОСОВАНИЕ
            </button>
            
            <div class="bio-modal" id="bioModal">
                <div class="bio-modal-content">
                    <button class="bio-modal-close" onclick="closeBiography()">✕</button>
                    <div id="bioContent"></div>
                </div>
            </div>
            
            <script>
                const biographies = {
        '''
        
        # Добавляем биографии в JS
        for player_id, bio_html in biographies.items():
            # Экранируем кавычки для JS
            bio_escaped = bio_html.replace("'", "\\'").replace('\n', ' ')
            html += f'"{player_id}": `{bio_escaped}`,'
        
        html += '''
                };
                
                function showBiography(playerId) {
                    const modal = document.getElementById('bioModal');
                    const content = document.getElementById('bioContent');
                    
                    if (biographies[playerId]) {
                        content.innerHTML = biographies[playerId];
                        modal.classList.add('active');
                    }
                }
                
                function closeBiography() {
                    document.getElementById('bioModal').classList.remove('active');
                }
                
                function startVoting() {
                    // Отправляем сигнал боту о начале голосования
                    if (window.Telegram && window.Telegram.WebApp) {
                        window.Telegram.WebApp.sendData(JSON.stringify({
                            action: 'start_final_voting'
                        }));
                    }
                }
                
                // Закрытие по Escape
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        closeBiography();
                    }
                });
            </script>
        </body>
        </html>
        '''
        
        return html


# ============================================
# УТИЛИТЫ
# ============================================

def get_player_biography(player: Dict[str, Any], show_secrets: bool = True) -> str:
    """
    Быстрая функция для получения биографии игрока в Markdown
    """
    builder = BiographyBuilder(player)
    return builder.to_markdown(show_secrets)


def get_player_biography_html(player: Dict[str, Any], show_secrets: bool = True) -> str:
    """
    Быстрая функция для получения биографии игрока в HTML
    """
    builder = BiographyBuilder(player)
    return builder.to_html(show_secrets)


def get_final_title_sheet(players: List[Dict[str, Any]]) -> str:
    """
    Быстрая функция для получения финального титульного листа
    """
    return BiographyBuilder.get_final_title_sheet(players)


def generate_biography_preview(player: Dict[str, Any]) -> str:
    """
    Генерирует краткую биографию для отображения в лобби
    """
    builder = BiographyBuilder(player)
    bio = builder.build_biography()
    
    lines = []
    lines.append(f"👤 **{bio['name']}**")
    lines.append(f"  🎴 Роль: {bio['role']}")
    lines.append(f"  ⚡ Способность: {bio['role_skill']}")
    lines.append(f"  ❤️ Здоровье: {bio['health']}/3")
    
    # Добавляем несколько ключевых фактов
    facts = bio["sections"].get("facts", {}).get("items", [])
    if facts:
        lines.append(f"  📖 Факт: {facts[0]['name']}")
    
    return "\n".join(lines)


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ БИОГРАФИИ")
    print("=" * 60)
    
    # Создаём тестового персонажа
    from cards_generator import generate_full_character
    
    character = generate_full_character("Матвей")
    print(f"✅ Персонаж создан: {character['name']}")
    
    # Строим биографию
    builder = BiographyBuilder(character)
    bio = builder.build_biography()
    
    print("\n📋 БИОГРАФИЯ (Markdown):")
    print("-" * 40)
    print(builder.to_markdown(show_secrets=True))
    
    print("\n📋 БИОГРАФИЯ (JSON):")
    print("-" * 40)
    print(builder.to_json())
    
    print("\n✅ Тестирование завершено!")