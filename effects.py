"""
effects.py — стили и эффекты для трейдинг-видео
"""

# Слова, которые будут подсвечиваться золотым когда активны
HIGHLIGHT_WORDS = {
    'fomo', 'убивает', 'пике', 'верху', 'разворачивается', 'забирает', 
    'плечо', 'ликвидация', 'стоп', 'убыток', 'прибыль', 'дисциплина',
    'эмоции', 'деньги', 'депозит', 'рынок', 'трейдер', 'крипта', 'биткоин',
    'памп', 'дамп', 'лонг', 'шорт', 'маржа', 'фьючерс', 'тейк', 'профит',
    'план', 'стратегия', 'риск', 'упустить', 'опоздавших', 'раньше',
    'заработали', 'зашёл', 'вошёл', 'вход', 'вошел', 'слив', 'колл', 'пут'
}

def get_word_color(word, is_active):
    """Цвет слова: золотой для ключевых, белый для обычных, серый для неактивных"""
    w = word.lower().strip('.,!?;:"')
    if is_active and w in HIGHLIGHT_WORDS:
        return (255, 215, 0)      # Золотой #FFD700
    elif is_active:
        return (255, 255, 255)    # Белый
    else:
        return (140, 140, 140)    # Серый неактивный

def calculate_fade_alpha(word_start, current_time, fade_duration=0.10):
    """Прозрачность для плавного появления слова (0-255)"""
    elapsed = current_time - word_start
    if elapsed < 0:
        return 0
    if elapsed < fade_duration:
        return int(255 * (elapsed / fade_duration))
    return 255

def get_hook_color(text):
    """Определяет цвет хука по смыслу"""
    t = text.lower()
    if any(w in t for w in ['fomo', 'убивает', 'слив', 'потеря', 'убыток', 'ликвидация', 'красный']):
        return (255, 60, 60)   # Красный
    if any(w in t for w in ['прибыль', 'заработок', 'план', 'стратегия', 'выигрыш', 'зеленый']):
        return (0, 230, 120)   # Зелёный
    return (255, 200, 0)       # Золотой

def split_words_into_lines(words, font, draw, max_width, spacing=20):
    """Перенос слов на новую строку по ширине экрана"""
    lines = []
    current_line = []
    current_width = 0
    
    for word in words:
        bbox = draw.textbbox((0, 0), word, font=font)
        word_w = bbox[2] - bbox[0]
        
        if current_width + word_w + (spacing if current_line else 0) > max_width and current_line:
            lines.append(current_line)
            current_line = [word]
            current_width = word_w
        else:
            current_line.append(word)
            current_width += word_w + (spacing if len(current_line) > 1 else 0)
    
    if current_line:
        lines.append(current_line)
    
    return lines
