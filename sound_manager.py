"""
Модуль управления звуками для "Кафе ОАЗИС 2.0"
Генерирует звуки через Web Audio API (без внешних файлов)
"""

import json
import base64
from typing import Dict, Any, Optional, List, Callable
from enum import Enum


# ============================================
# ТИПЫ ЗВУКОВ
# ============================================

class SoundType(Enum):
    """Типы звуков в игре"""
    CARD_FLIP = "card_flip"          # Открытие карты
    VOTING_START = "voting_start"    # Начало голосования
    ELIMINATION = "elimination"      # Кто-то выбыл
    WIN = "win"                      # Победа
    CLICK = "click"                  # Нажатие кнопки
    SKILL = "skill"                  # Использование способности
    REVEAL = "reveal"                # Открытие карты (другой вариант)
    FINAL = "final"                  # Финальная фаза
    ERROR = "error"                  # Ошибка
    NOTIFICATION = "notification"    # Уведомление


# ============================================
# ГЕНЕРАТОР ЗВУКОВ (Web Audio API)
# ============================================

class SoundGenerator:
    """
    Генерирует звуки программно через Web Audio API
    """
    
    @staticmethod
    def generate_card_flip() -> str:
        """
        Звук открытия карты (щелчок с высокочастотным хвостом)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.15,
            frequency=800,
            type="square",
            decay=0.05,
            volume=0.3,
            vibrato=False
        )
    
    @staticmethod
    def generate_voting_start() -> str:
        """
        Звук начала голосования (двойной сигнал)
        """
        # Первый сигнал
        audio1 = SoundGenerator._generate_audio_data(
            duration=0.2,
            frequency=600,
            type="sine",
            decay=0.1,
            volume=0.3,
            vibrato=True
        )
        # Второй сигнал (выше)
        audio2 = SoundGenerator._generate_audio_data(
            duration=0.2,
            frequency=900,
            type="sine",
            decay=0.1,
            volume=0.3,
            vibrato=True
        )
        # Комбинируем
        return SoundGenerator._combine_audio([audio1, audio2], gap=0.1)
    
    @staticmethod
    def generate_elimination() -> str:
        """
        Звук выбывания (низкий удар с затуханием)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.5,
            frequency=150,
            type="sawtooth",
            decay=0.4,
            volume=0.4,
            vibrato=False
        )
    
    @staticmethod
    def generate_win() -> str:
        """
        Звук победы (фанфары - восходящая гамма)
        """
        notes = [523, 587, 659, 784, 880, 988, 1047]  # C5, D5, E5, G5, A5, B5, C6
        audios = []
        for freq in notes:
            audio = SoundGenerator._generate_audio_data(
                duration=0.15,
                frequency=freq,
                type="sine",
                decay=0.05,
                volume=0.25,
                vibrato=False
            )
            audios.append(audio)
        return SoundGenerator._combine_audio(audios, gap=0.02)
    
    @staticmethod
    def generate_click() -> str:
        """
        Звук нажатия кнопки (короткий щелчок)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.05,
            frequency=1200,
            type="square",
            decay=0.01,
            volume=0.2,
            vibrato=False
        )
    
    @staticmethod
    def generate_skill() -> str:
        """
        Звук использования способности (магический сигнал)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.3,
            frequency=500,
            type="sine",
            decay=0.2,
            volume=0.3,
            vibrato=True
        )
    
    @staticmethod
    def generate_reveal() -> str:
        """
        Звук открытия карты (альтернативный - мягкий)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.2,
            frequency=600,
            type="triangle",
            decay=0.1,
            volume=0.25,
            vibrato=False
        )
    
    @staticmethod
    def generate_final() -> str:
        """
        Звук финальной фазы (эпический сигнал)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.8,
            frequency=440,
            type="sine",
            decay=0.6,
            volume=0.35,
            vibrato=True
        )
    
    @staticmethod
    def generate_error() -> str:
        """
        Звук ошибки (короткий низкий сигнал)
        """
        return SoundGenerator._generate_audio_data(
            duration=0.2,
            frequency=300,
            type="square",
            decay=0.15,
            volume=0.25,
            vibrato=False
        )
    
    @staticmethod
    def generate_notification() -> str:
        """
        Звук уведомления (короткий двойной сигнал)
        """
        audio1 = SoundGenerator._generate_audio_data(
            duration=0.1,
            frequency=800,
            type="sine",
            decay=0.05,
            volume=0.2,
            vibrato=False
        )
        audio2 = SoundGenerator._generate_audio_data(
            duration=0.1,
            frequency=1000,
            type="sine",
            decay=0.05,
            volume=0.2,
            vibrato=False
        )
        return SoundGenerator._combine_audio([audio1, audio2], gap=0.05)
    
    # ============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ============================================
    
    @staticmethod
    def _generate_audio_data(
        duration: float = 0.2,
        frequency: float = 440,
        type: str = "sine",
        decay: float = 0.1,
        volume: float = 0.3,
        vibrato: bool = False,
        sample_rate: int = 44100
    ) -> str:
        """
        Генерирует аудио-данные в формате base64 (WAV)
        """
        import math
        import struct
        import io
        
        num_samples = int(duration * sample_rate)
        audio_data = []
        
        # Параметры для вибрато
        vibrato_depth = 0.02 if vibrato else 0
        vibrato_freq = 5 if vibrato else 0
        
        for i in range(num_samples):
            t = i / sample_rate
            
            # Частота с вибрато
            current_freq = frequency * (1 + vibrato_depth * math.sin(2 * math.pi * vibrato_freq * t))
            
            # Генерация волны
            if type == "sine":
                sample = math.sin(2 * math.pi * current_freq * t)
            elif type == "square":
                sample = 1 if math.sin(2 * math.pi * current_freq * t) > 0 else -1
            elif type == "sawtooth":
                sample = 2 * (t * current_freq - math.floor(0.5 + t * current_freq))
            elif type == "triangle":
                sample = 2 * abs(2 * (t * current_freq - math.floor(0.5 + t * current_freq))) - 1
            else:
                sample = math.sin(2 * math.pi * current_freq * t)
            
            # Затухание (ADSR - простой вариант)
            if t < 0.01:
                # Attack
                env = t / 0.01
            elif t < duration - decay:
                # Sustain
                env = 1.0
            else:
                # Release
                env = 1.0 - (t - (duration - decay)) / decay
            
            # Применяем огибающую
            sample = sample * env * volume
            
            # Ограничиваем
            sample = max(-1, min(1, sample))
            
            # Конвертируем в 16-bit
            audio_data.append(int(sample * 32767))
        
        # Создаём WAV файл в памяти
        with io.BytesIO() as wav:
            # Заголовок RIFF
            wav.write(b'RIFF')
            wav.write(struct.pack('<I', 36 + len(audio_data) * 2))
            wav.write(b'WAVE')
            
            # fmt-субчанк
            wav.write(b'fmt ')
            wav.write(struct.pack('<I', 16))
            wav.write(struct.pack('<H', 1))  # Audio format (PCM)
            wav.write(struct.pack('<H', 1))  # Num channels (моно)
            wav.write(struct.pack('<I', sample_rate))
            wav.write(struct.pack('<I', sample_rate * 2))  # Byte rate
            wav.write(struct.pack('<H', 2))  # Block align
            wav.write(struct.pack('<H', 16))  # Bits per sample
            
            # data-субчанк
            wav.write(b'data')
            wav.write(struct.pack('<I', len(audio_data) * 2))
            for sample in audio_data:
                wav.write(struct.pack('<h', sample))
            
            # Конвертируем в base64
            wav_data = wav.getvalue()
            return base64.b64encode(wav_data).decode('utf-8')
    
    @staticmethod
    def _combine_audio(audios: List[str], gap: float = 0.05) -> str:
        """
        Комбинирует несколько аудио-фрагментов в один
        """
        import math
        import struct
        import io
        import base64
        
        # Декодируем все аудио
        decoded_audios = []
        for audio_b64 in audios:
            wav_data = base64.b64decode(audio_b64)
            decoded_audios.append(wav_data)
        
        # Извлекаем аудио-данные из WAV
        audio_parts = []
        sample_rate = 44100
        gap_samples = int(gap * sample_rate)
        
        for wav_data in decoded_audios:
            # Пропускаем заголовок WAV
            # Ищем начало data-субчанка
            data_start = wav_data.find(b'data')
            if data_start == -1:
                continue
            
            # Читаем размер данных
            data_size = struct.unpack('<I', wav_data[data_start + 4:data_start + 8])[0]
            audio_data = wav_data[data_start + 8:data_start + 8 + data_size]
            
            # Конвертируем в список сэмплов
            samples = []
            for i in range(0, len(audio_data), 2):
                sample = struct.unpack('<h', audio_data[i:i+2])[0]
                samples.append(sample)
            
            audio_parts.append(samples)
        
        # Объединяем с паузой
        combined = []
        for i, part in enumerate(audio_parts):
            if i > 0:
                # Добавляем паузу
                for _ in range(gap_samples):
                    combined.append(0)
            combined.extend(part)
        
        # Создаём WAV
        with io.BytesIO() as wav:
            wav.write(b'RIFF')
            wav.write(struct.pack('<I', 36 + len(combined) * 2))
            wav.write(b'WAVE')
            
            wav.write(b'fmt ')
            wav.write(struct.pack('<I', 16))
            wav.write(struct.pack('<H', 1))
            wav.write(struct.pack('<H', 1))
            wav.write(struct.pack('<I', sample_rate))
            wav.write(struct.pack('<I', sample_rate * 2))
            wav.write(struct.pack('<H', 2))
            wav.write(struct.pack('<H', 16))
            
            wav.write(b'data')
            wav.write(struct.pack('<I', len(combined) * 2))
            for sample in combined:
                wav.write(struct.pack('<h', sample))
            
            wav_data = wav.getvalue()
            return base64.b64encode(wav_data).decode('utf-8')


# ============================================
# МЕНЕДЖЕР ЗВУКОВ
# ============================================

class SoundManager:
    """
    Менеджер звуков для игры
    """
    
    def __init__(self):
        self._sounds: Dict[str, str] = {}
        self._enabled: bool = True
        self._volume: float = 0.5
        self._init_sounds()
    
    def _init_sounds(self) -> None:
        """Инициализирует все звуки"""
        self._sounds = {
            SoundType.CARD_FLIP.value: SoundGenerator.generate_card_flip(),
            SoundType.VOTING_START.value: SoundGenerator.generate_voting_start(),
            SoundType.ELIMINATION.value: SoundGenerator.generate_elimination(),
            SoundType.WIN.value: SoundGenerator.generate_win(),
            SoundType.CLICK.value: SoundGenerator.generate_click(),
            SoundType.SKILL.value: SoundGenerator.generate_skill(),
            SoundType.REVEAL.value: SoundGenerator.generate_reveal(),
            SoundType.FINAL.value: SoundGenerator.generate_final(),
            SoundType.ERROR.value: SoundGenerator.generate_error(),
            SoundType.NOTIFICATION.value: SoundGenerator.generate_notification(),
        }
    
    def get_sound(self, sound_type: SoundType) -> Optional[str]:
        """Возвращает звук в формате base64"""
        return self._sounds.get(sound_type.value)
    
    def get_sound_by_name(self, name: str) -> Optional[str]:
        """Возвращает звук по имени"""
        try:
            sound_type = SoundType(name)
            return self.get_sound(sound_type)
        except ValueError:
            return None
    
    def play_sound(self, sound_type: SoundType) -> str:
        """
        Возвращает HTML/JS код для воспроизведения звука
        """
        sound_data = self.get_sound(sound_type)
        if not sound_data:
            return ""
        
        return f'''
        <script>
            (function() {{
                try {{
                    const audioData = "{sound_data}";
                    const binaryString = atob(audioData);
                    const bytes = new Uint8Array(binaryString.length);
                    for (let i = 0; i < binaryString.length; i++) {{
                        bytes[i] = binaryString.charCodeAt(i);
                    }}
                    const audioBlob = new Blob([bytes], {{ type: 'audio/wav' }});
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audio = new Audio(audioUrl);
                    audio.volume = {self._volume};
                    audio.play().catch(e => console.log('Audio play failed:', e));
                }} catch (e) {{
                    console.log('Audio error:', e);
                }}
            }})();
        </script>
        '''
    
    def get_sound_js(self, sound_type: SoundType) -> str:
        """
        Возвращает JavaScript функцию для воспроизведения звука
        """
        sound_data = self.get_sound(sound_type)
        if not sound_data:
            return ""
        
        return f'''
        function playSound_{sound_type.value}() {{
            try {{
                const audioData = "{sound_data}";
                const binaryString = atob(audioData);
                const bytes = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {{
                    bytes[i] = binaryString.charCodeAt(i);
                }}
                const audioBlob = new Blob([bytes], {{ type: 'audio/wav' }});
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                audio.volume = {self._volume};
                audio.play().catch(e => console.log('Audio play failed:', e));
            }} catch (e) {{
                console.log('Audio error:', e);
            }}
        }}
        '''
    
    def get_all_sounds_js(self) -> str:
        """
        Возвращает JavaScript код для всех звуков
        """
        js_code = []
        js_code.append("// ============================================")
        js_code.append("// ЗВУКИ ДЛЯ ИГРЫ 'КАФЕ ОАЗИС'")
        js_code.append("// ============================================")
        js_code.append("")
        js_code.append("const Sounds = {")
        
        for sound_type in SoundType:
            sound_data = self.get_sound(sound_type)
            if sound_data:
                js_code.append(f'    {sound_type.value}: "{sound_data}",')
        
        js_code.append("};")
        js_code.append("")
        js_code.append("function playSound(soundName) {")
        js_code.append("    try {")
        js_code.append("        const audioData = Sounds[soundName];")
        js_code.append("        if (!audioData) return;")
        js_code.append("        const binaryString = atob(audioData);")
        js_code.append("        const bytes = new Uint8Array(binaryString.length);")
        js_code.append("        for (let i = 0; i < binaryString.length; i++) {")
        js_code.append("            bytes[i] = binaryString.charCodeAt(i);")
        js_code.append("        }")
        js_code.append("        const audioBlob = new Blob([bytes], { type: 'audio/wav' });")
        js_code.append("        const audioUrl = URL.createObjectURL(audioBlob);")
        js_code.append("        const audio = new Audio(audioUrl);")
        js_code.append(f"        audio.volume = {self._volume};")
        js_code.append("        audio.play().catch(e => console.log('Audio play failed:', e));")
        js_code.append("    } catch (e) {")
        js_code.append("        console.log('Audio error:', e);")
        js_code.append("    }")
        js_code.append("}")
        js_code.append("")
        js_code.append("// Удобные функции для каждого звука")
        for sound_type in SoundType:
            js_code.append(f"function playSound_{sound_type.value}() {{ playSound('{sound_type.value}'); }}")
        
        js_code.append("")
        js_code.append("// Глобальные переменные для управления звуком")
        js_code.append("let soundEnabled = true;")
        js_code.append("let soundVolume = 0.5;")
        js_code.append("")
        js_code.append("function toggleSound() {")
        js_code.append("    soundEnabled = !soundEnabled;")
        js_code.append("    return soundEnabled;")
        js_code.append("}")
        js_code.append("")
        js_code.append("function setSoundVolume(volume) {")
        js_code.append("    soundVolume = Math.max(0, Math.min(1, volume));")
        js_code.append("    return soundVolume;")
        js_code.append("}")
        js_code.append("")
        js_code.append("// Переопределяем playSound для учёта глобальных настроек")
        js_code.append("const originalPlaySound = playSound;")
        js_code.append("playSound = function(soundName) {")
        js_code.append("    if (!soundEnabled) return;")
        js_code.append("    originalPlaySound(soundName);")
        js_code.append("};")
        
        return "\n".join(js_code)
    
    def get_sound_html(self) -> str:
        """
        Возвращает полный HTML-код со звуками
        """
        return f'''
        <script>
        {self.get_all_sounds_js()}
        </script>
        '''
    
    def set_enabled(self, enabled: bool) -> None:
        """Включает/выключает звуки"""
        self._enabled = enabled
    
    def set_volume(self, volume: float) -> None:
        """Устанавливает громкость звуков (0-1)"""
        self._volume = max(0, min(1, volume))
    
    def is_enabled(self) -> bool:
        """Возвращает, включены ли звуки"""
        return self._enabled
    
    def get_volume(self) -> float:
        """Возвращает текущую громкость"""
        return self._volume
    
    def get_all_sounds_info(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает информацию о всех звуках"""
        return {
            sound_type.value: {
                "name": sound_type.value,
                "length": len(self._sounds.get(sound_type.value, "")),
                "enabled": self._enabled,
                "volume": self._volume,
            }
            for sound_type in SoundType
        }


# ============================================
# ФАБРИКА ДЛЯ СОЗДАНИЯ МЕНЕДЖЕРА
# ============================================

def create_sound_manager() -> SoundManager:
    """Создаёт новый экземпляр менеджера звуков"""
    return SoundManager()


# ============================================
# ТЕСТИРОВАНИЕ
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ЗВУКОВ")
    print("=" * 60)
    
    # Создаём менеджер
    manager = create_sound_manager()
    print(f"✅ Звуки инициализированы: {len(manager._sounds)} звуков")
    
    # Проверяем каждый звук
    for sound_type in SoundType:
        sound_data = manager.get_sound(sound_type)
        if sound_data:
            print(f"  ✅ {sound_type.value}: {len(sound_data)} символов")
        else:
            print(f"  ❌ {sound_type.value}: НЕ НАЙДЕН")
    
    # Генерируем HTML
    print("\n📋 Генерация HTML со звуками...")
    html = manager.get_sound_html()
    print(f"  ✅ HTML сгенерирован: {len(html)} символов")
    
    # Проверяем JS функции
    print("\n📋 Проверка JS функций...")
    for sound_type in SoundType:
        js_func = manager.get_sound_js(sound_type)
        if js_func:
            print(f"  ✅ playSound_{sound_type.value}()")
        else:
            print(f"  ❌ playSound_{sound_type.value}()")
    
    print("\n✅ Тестирование завершено!")