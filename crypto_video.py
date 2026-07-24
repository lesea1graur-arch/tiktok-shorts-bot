"""
crypto_video.py — генератор видео про крипту/трейдинг для TikTok/Shorts.
Использует ту же инфраструктуру, что create_short.py (голос, фон с Pexels,
субтитры, музыка), но с текстами и визуалом под крипто-тематику.
"""

import os
import random

import create_short as cs

OUT_DIR = "output"
TMP_DIR = "_crypto_tmp"

CRYPTO_SCRIPTS = [
    "Девяносто процентов трейдеров теряют деньги не потому, что не знают стратегию. "
    "Они теряют деньги, потому что не могут следовать своей же стратегии, когда рынок "
    "давит на эмоции. Дисциплина в трейдинге важнее любого индикатора.",

    "Вход на хаях без подтверждения тренда — это не трейдинг, это гэмблинг с лишним шагом. "
    "Дождись отката к уровню, подтверди объёмом, и только потом заходи. Скучная стратегия "
    "всегда переживает захватывающую.",

    "Стоп-лосс это не признание поражения, это стоимость входного билета в игру. "
    "Трейдеры без стопа не управляют риском, они просто откладывают неизбежное на потом, "
    "и потом это всегда дороже.",

    "Рынок не помнит, сколько ты потерял вчера, и не обязан тебе это вернуть сегодня. "
    "Месть рынку через отыгрыш убытков — самый быстрый способ слить депозит до нуля.",

    "Индикаторы не предсказывают будущее, они описывают прошлое. EMA, RSI, объёмы — это "
    "статистика уже случившегося. Реальное преимущество трейдера не в индикаторах, "
    "а в управлении риском на сделку.",
]

MOOD_QUERIES = [
    "cryptocurrency bitcoin trading",
    "stock market chart screen",
    "trading candlestick chart",
    "blockchain technology digital",
    "finance trader screen night",
]
MOOD_MUST_INCLUDE = ["crypto", "bitcoin", "trading", "stock", "chart", "blockchain", "finance", "market"]


def build_crypto_video(script: str = None, out_name: str = "crypto.mp4"):
    original_quotes = cs.QUOTES
    original_mood = cs.MOOD_QUERIES
    original_must = cs.MOOD_MUST_INCLUDE

    cs.QUOTES = CRYPTO_SCRIPTS
    cs.MOOD_QUERIES = MOOD_QUERIES
    cs.MOOD_MUST_INCLUDE = MOOD_MUST_INCLUDE

    try:
        return cs.create_short(quote=script, out_name=out_name)
    finally:
        cs.QUOTES = original_quotes
        cs.MOOD_QUERIES = original_mood
        cs.MOOD_MUST_INCLUDE = original_must


if __name__ == "__main__":
    build_crypto_video()
