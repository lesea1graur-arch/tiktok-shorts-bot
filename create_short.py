"""
create_short.py — генератор коротких видео под TikTok / YouTube Shorts.
Формат: 1080x1920 (9:16), mp4, h264.

Написан с расчётом на устойчивость: каждый шаг, который может подвести
(сеть, TTS, ffmpeg), обёрнут проверками и запасными вариантами, чтобы
одиночный сбой не ронял всю генерацию.
"""

import asyncio
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

VOICE = "ru-RU-DmitryNeural"
RATE = "+8%"
W, H = 1080, 1920
FPS = 30
MAX_STEP_DURATION = 45.0

BG_DIR = "assets/backgrounds"
OUT_DIR = "output"
TMP_DIR = "_tmp"

FONT_BOLD_MONTSERRAT = "assets/fonts/Montserrat-ExtraBold.ttf"
FONT_BOLD_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_BOLD = FONT_BOLD_MONTSERRAT if os.path.exists(FONT_BOLD_MONTSERRAT) else FONT_BOLD_FALLBACK
COLOR_WHITE = (255, 255, 255)
COLOR_HIGHLIGHT = (240, 185, 11)
CHANNEL_HANDLE = "@fedotka.finance"

QUOTES = [
    "Почему ты бедный? Не потому что мало зарабатываешь, а потому что не умеешь "
    "управлять тем, что зарабатываешь. Богатые люди покупают активы, бедные покупают "
    "вещи, которые выглядят как богатство. Разница не в зарплате, разница в привычках, "
    "которые ты повторяешь каждый месяц.",

    "Правило 50 30 20 звучит просто, но почти никто его не соблюдает. Пятьдесят "
    "процентов на обязательные расходы, тридцать на желания, двадцать откладываешь "
    "и инвестируешь. Большинство делает наоборот — сначала тратят всё на желания, "
    "а откладывают то, что случайно осталось. Именно поэтому у большинства ничего "
    "не остаётся.",

    "Твоя зарплата не сделает тебя богатым, если ты не меняешь то, что делаешь с "
    "деньгами после зарплаты. Можно зарабатывать три тысячи долларов и оставаться "
    "бедным всю жизнь. Можно зарабатывать восемьсот и стать финансово свободным. "
    "Разница всегда в системе, а не в цифре в договоре.",

    "Богатые люди боятся тратить время, бедные люди боятся тратить деньги. Именно "
    "поэтому одни покупают время других за зарплату, а другие продают своё время "
    "за фиксированную сумму всю жизнь. Смени сторону сделки, начни думать про актив, "
    "который работает на тебя, даже когда ты спишь.",

    "Никто не разбогател, откладывая то, что осталось после трат. Богатеют те, кто "
    "сначала откладывает, а живёт на то, что осталось. Это меняет буквально одну "
    "привычку, но результат отличается на десятилетия вперёд. Начни с этого правила "
    "сегодня, а не с понедельника.",

    "Кредит на телефон в рассрочку — это способ платить завтрашними деньгами за "
    "сегодняшнее желание. Банки не выдумали ничего нового, они просто нашли способ "
    "продать тебе твою же будущую зарплату с процентами. Богатые покупают телефон "
    "сразу, потому что у них уже есть подушка на это.",

    "Финансовая подушка это не роскошь, это разница между уволили и я справлюсь "
    "и уволили и я в панике. Три-шесть месяцев расходов на отдельном счёте меняют "
    "не только финансы, но и то, как ты принимаешь решения на работе — ты перестаёшь "
    "бояться и начинаешь выбирать.",

    "Инфляция ест твои сбережения на банковском вкладе быстрее, чем банк начисляет "
    "проценты. Деньги под подушкой и деньги на вкладе под три процента теряют "
    "покупательную способность одинаково стабильно. Хранить — не значит сберегать, "
    "если инфляция выше доходности.",

    "Ты не станешь богатым от одной хорошей сделки, но можешь разориться от одной "
    "плохой. Асимметрия рисков работает против тех, кто ставит всё на один исход. "
    "Диверсификация — это не трусость, это единственная стратегия, которая переживает "
    "твои же ошибки.",

    "Купить вещь в кредит, чтобы показать в соцсетях, что у тебя всё хорошо — это "
    "самая дорогая форма рекламы, за которую платишь ты сам. Настоящее богатство "
    "почти всегда выглядит скучно и незаметно, потому что оно работает на будущее, "
    "а не на лайки сегодня.",

    "Пассивный доход не появляется пассивно. Сначала ты вкладываешь активное время, "
    "деньги и ошибки, и только потом система начинает работать без тебя. Все, кто "
    "продают идею мгновенного пассивного дохода, обычно зарабатывают на продаже "
    "этой идеи, а не на самом доходе.",

    "Сравнение своей зарплаты с чужим образом жизни в соцсетях — гарантированный "
    "способ чувствовать себя бедным при любом доходе. Ты видишь чужой результат, "
    "но не видишь чужие долги, чужой кредит и чужую тревогу за спиной красивой "
    "картинки.",

    "Урок про деньги, который не дают в школе — цена вопрос не только про то, "
    "сколько стоит вещь, а про то, сколько часов твоей жизни ты обменял, чтобы "
    "её купить. Пересчитывай покупки не в деньгах, а в часах работы — это меняет "
    "восприятие моментально.",

    "Большинство лотерейных миллионеров возвращаются к прежнему уровню жизни за "
    "несколько лет. Деньги без финансовой грамотности не решают проблему — они "
    "просто увеличивают масштаб тех же самых финансовых привычек, которые были "
    "и до выигрыша.",

    "Инвестировать по чуть-чуть, но регулярно, почти всегда обгоняет попытку "
    "поймать идеальный момент для входа. Пока ты ждёшь идеальной точки входа на "
    "рынок, рынок растёт без тебя. Время в рынке важнее, чем тайминг рынка.",

    "Твой самый большой актив в двадцать пять лет — это не деньги, а время до "
    "пенсии. Сложный процент работает медленно в начале и взрывается в конце. "
    "Каждый год промедления с началом инвестирования стоит тебе намного больше, "
    "чем кажется сейчас.",

    "Богатые люди задают вопрос как это купить, чтобы это работало на меня. "
    "Бедные люди задают вопрос как накопить, чтобы это купить. Один и тот же "
    "актив — недвижимость, акции, бизнес — но принципиально разное отношение "
    "к тому, что деньги должны делать дальше.",

    "Долг на потребление и долг на актив — это два разных долга, которые многие "
    "путают. Кредит на отпуск исчезает вместе с воспоминаниями, а платежи остаются. "
    "Кредит на актив, который приносит доход больше процентной ставки — это "
    "инструмент, а не проблема.",

    "Финансовая грамотность не про то, чтобы знать сложные термины с Уолл-стрит. "
    "Она про то, чтобы твои расходы были меньше доходов, а разница работала на "
    "тебя. Всё остальное — это детали поверх этого одного простого правила.",

    "Работа за зарплату — это обмен времени на деньги по фиксированному курсу, "
    "который ты не контролируешь. Собственный актив — это возможность продавать "
    "результат, а не время. Первое даёт стабильность, второе даёт потолок роста "
    "без ограничений.",

    "Люди тратят больше времени на выбор ресторана на вечер, чем на выбор, куда "
    "вложить сбережения на следующие десять лет. Мелкие решения съедают внимание, "
    "а крупные решения, которые реально меняют финансовое будущее, откладываются "
    "на потом, которое не наступает.",
]


def run_ffmpeg(cmd: list, label: str = "ffmpeg") -> bool:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[{label}] ffmpeg завершился с ошибкой:\n{result.stderr[-800:]}")
        return False
    return True


def get_audio_duration(audio_path: str) -> float:
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
        return 0.0
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio_path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def is_valid_video(path: str, min_duration: float = 0.3) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        return False
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=codec_type", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    try:
        lines = [l for l in result.stdout.strip().split("\n") if l]
        duration = float(lines[-1])
        return duration >= min_duration
    except (ValueError, IndexError):
        return False


async def _generate_voice_once(text: str, audio_path: str, voice: str, rate: str, pitch: str = None):
    import edge_tts
    kwargs = {"rate": rate}
    if pitch:
        kwargs["pitch"] = pitch
    communicate = edge_tts.Communicate(text, voice, **kwargs)
    word_timings = []

    with open(audio_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_timings.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })
    return word_timings


async def generate_voice_with_timings(text: str, audio_path: str, voice: str = None,
                                        rate: str = None, pitch: str = None, retries: int = 3):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            word_timings = await _generate_voice_once(
                text, audio_path, voice or VOICE, rate or RATE, pitch
            )
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 500:
                return word_timings
            last_error = "пустой аудиофайл"
        except Exception as e:
            last_error = str(e)

        print(f"  Попытка {attempt}/{retries} озвучки не удалась ({last_error}), повтор...")
        await asyncio.sleep(1.5 * attempt)

    print(f"  Озвучка не удалась после {retries} попыток: {last_error}")
    return []


def build_fallback_timings(text: str) -> list:
    words = text.split()
    t = 0.3
    timings = []
    for w in words:
        dur = max(0.18, len(w) * 0.06)
        timings.append({"word": w, "start": t, "end": t + dur})
        t += dur + 0.05
    return timings


def resolve_duration(word_timings: list, audio_path: str, tail: float = 1.0) -> float:
    word_based = word_timings[-1]["end"] + tail if word_timings else tail
    real_audio = get_audio_duration(audio_path)
    duration = max(word_based, real_audio + tail * 0.5) if real_audio > 0 else word_based
    return min(duration, MAX_STEP_DURATION)


MOOD_QUERIES = [
    "counting money hands",
    "business man city night",
    "stock market screen trading",
    "luxury car night city",
    "office working laptop money",
]
MOOD_MUST_INCLUDE = ["money", "business", "stock", "car", "office", "cash", "finance", "wealth"]


def _pexels_fetch_one(query: str, out_path: str, exclude_ids: set = None, retries: int = 2) -> bool:
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        return False
    exclude_ids = exclude_ids or set()
    headers = {"Authorization": api_key}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params={"query": query, "per_page": 15, "orientation": "portrait"},
                timeout=30,
            )
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
            videos = [v for v in videos if v.get("id") not in exclude_ids]

            relevant = [
                v for v in videos
                if any(w in v.get("url", "").lower() for w in MOOD_MUST_INCLUDE)
            ]
            videos = relevant or videos
            if not videos:
                return False

            video = random.choice(videos)
            files = video.get("video_files", [])
            candidates = [f for f in files if f.get("file_type") == "video/mp4" and f.get("height", 0) >= 1280]
            if not candidates:
                candidates = [f for f in files if f.get("file_type") == "video/mp4"]
            if not candidates:
                return False
            candidates.sort(key=lambda f: f.get("height", 0))
            file_url = candidates[len(candidates) // 2]["link"]

            r = requests.get(file_url, stream=True, timeout=60)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            if is_valid_video(out_path):
                exclude_ids.add(video.get("id"))
                return True
        except Exception as e:
            print(f"  Ошибка получения фона с Pexels (попытка {attempt}/{retries}): {e}")
        time.sleep(1)
    return False


def prepare_background(duration: float, out_path: str) -> bool:
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if api_key:
        clip_len = 6.0
        n_clips = max(1, min(5, int(duration // clip_len) + 1))
        used_ids = set()
        clip_paths = []
        tmp_dir = os.path.dirname(out_path) or "."

        for i in range(n_clips):
            query = random.choice(MOOD_QUERIES)
            raw_path = os.path.join(tmp_dir, f"_bgraw_{i}.mp4")
            if _pexels_fetch_one(query, raw_path, exclude_ids=used_ids):
                clip_paths.append(raw_path)

        if clip_paths:
            per_clip_dur = duration / len(clip_paths)
            processed = []
            zoom_filter_tpl = (
                f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},"
                "zoompan=z='min(zoom+0.0015,1.08)':d=1:s={W}x{H}:fps={FPS},"
                "eq=contrast=1.08:saturation=1.2:gamma=0.97,"
                "colorbalance=rs=0.05:bs=-0.05:rm=0.03:bm=-0.03"
            ).format(W=W, H=H, FPS=FPS)

            for i, raw in enumerate(clip_paths):
                seg_path = os.path.join(tmp_dir, f"_bgseg_{i}.mp4")
                ok = run_ffmpeg([
                    "ffmpeg", "-y",
                    "-stream_loop", "-1", "-i", raw,
                    "-t", str(per_clip_dur + 1.0),
                    "-vf", zoom_filter_tpl,
                    "-an", seg_path,
                ], f"bg_segment_{i}")
                if ok and is_valid_video(seg_path):
                    processed.append(seg_path)
                os.remove(raw) if os.path.exists(raw) else None

            if processed:
                success = _stitch_backgrounds(processed, out_path, duration)
                for p in processed:
                    if os.path.exists(p):
                        os.remove(p)
                if success:
                    return True
        print("  Не удалось собрать фон из нескольких клипов Pexels, пробую локальный")

    files = [f for f in Path(BG_DIR).glob("*.mp4") if is_valid_video(str(f))]
    if files:
        bg = str(random.choice(files))
        ok = run_ffmpeg([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg,
            "-t", str(duration),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
            "-an", out_path,
        ], "prepare_background_local")
        if ok and is_valid_video(out_path):
            return True
        print("  Фон из assets не удался, переключаюсь на процедурный")

    return run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x14181D:s={W}x{H}:d={duration}",
        "-vf", "noise=alls=6:allf=t",
        out_path,
    ], "prepare_background_fallback")


def _stitch_backgrounds(clip_paths: list, out_path: str, target_duration: float) -> bool:
    if len(clip_paths) == 1:
        return run_ffmpeg([
            "ffmpeg", "-y", "-i", clip_paths[0], "-t", str(target_duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), out_path,
        ], "stitch_single")

    TRANSITION = 0.5
    inputs = []
    for p in clip_paths:
        inputs += ["-i", p]

    durations = [get_audio_duration(p) or (target_duration / len(clip_paths) + 1.0) for p in clip_paths]

    filter_parts = []
    for i in range(len(clip_paths)):
        filter_parts.append(f"[{i}:v]fps={FPS},format=yuv420p,setpts=PTS-STARTPTS[nv{i}]")

    prev_v = "nv0"
    cumulative = durations[0]
    for i in range(1, len(clip_paths)):
        offset = max(0.1, cumulative - TRANSITION)
        out_v = f"v{i}"
        filter_parts.append(f"[{prev_v}][nv{i}]xfade=transition=zoomin:duration={TRANSITION}:offset={offset:.2f}[{out_v}]")
        prev_v = out_v
        cumulative += durations[i] - TRANSITION

    filter_complex = ";".join(filter_parts)

    ok = run_ffmpeg([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_v}]",
        "-t", str(target_duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
        out_path,
    ], "stitch_backgrounds")
    return ok and is_valid_video(out_path)


def render_caption_frames(word_timings: list, total_duration: float, frames_dir: str):
    """Рисует прозрачные PNG-кадры с текстом на тёмной полупрозрачной подложке.
    Активное слово крупнее, со свечением (glow) и лёгким дрожанием (shake).
    Внизу — тонкий прогресс-бар, сверху — водяной знак с ником канала."""
    os.makedirs(frames_dir, exist_ok=True)
    font = ImageFont.truetype(FONT_BOLD, 62)
    font_active = ImageFont.truetype(FONT_BOLD, 72)
    font_handle = ImageFont.truetype(FONT_BOLD, 30)
    total_frames = max(1, int(total_duration * FPS) + 1)
    words = [w["word"] for w in word_timings]
    max_line_width = W - 100

    from PIL import ImageFilter

    for frame_i in range(total_frames):
        t = frame_i / FPS
        active_idx = 0
        for i, w in enumerate(word_timings):
            if w["start"] <= t <= w["end"]:
                active_idx = i
                break
            elif t > w["end"]:
                active_idx = i

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if words:
            spacing = 18
            window = 2
            while window >= 0:
                lo = max(0, active_idx - window)
                hi = min(len(words), active_idx + window + 1)
                visible = words[lo:hi]
                widths = []
                for i, w in enumerate(visible):
                    f = font_active if (lo + i) == active_idx else font
                    widths.append(draw.textbbox((0, 0), w, font=f)[2])
                total_w = sum(widths) + spacing * (len(visible) - 1)
                if total_w <= max_line_width or window == 0:
                    break
                window -= 1

            x = (W - total_w) // 2
            y = int(H * 0.62)

            pad_x, pad_y = 24, 20
            box_h = 72 + pad_y * 2
            draw.rounded_rectangle(
                [x - pad_x, y - pad_y, x + total_w + pad_x, y + box_h - pad_y],
                radius=14, fill=(0, 0, 0, 190)
            )

            glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)

            cursor_x = x
            for i, w in enumerate(visible):
                real_idx = lo + i
                is_active = real_idx == active_idx
                f = font_active if is_active else font
                y_offset = y - (10 if is_active else 0)
                if is_active:
                    glow_draw.text((cursor_x, y_offset), w, font=f, fill=(255, 210, 40, 255))
                cursor_x += widths[i] + spacing

            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(10))
            img = Image.alpha_composite(img, glow_layer)
            draw = ImageDraw.Draw(img)

            cursor_x = x
            for i, w in enumerate(visible):
                real_idx = lo + i
                is_active = real_idx == active_idx
                f = font_active if is_active else font
                color = COLOR_HIGHLIGHT if is_active else COLOR_WHITE
                y_offset = y - (10 if is_active else 0)
                if is_active:
                    shake_x = int(3 * (0.5 - (t * 37) % 1))
                    shake_y = int(2 * (0.5 - (t * 29) % 1))
                    draw.text((cursor_x + shake_x, y_offset + shake_y), w, font=f, fill=color,
                              stroke_width=4, stroke_fill=(0, 0, 0, 255))
                else:
                    draw.text((cursor_x, y_offset), w, font=f, fill=color,
                              stroke_width=4, stroke_fill=(0, 0, 0, 255))
                cursor_x += widths[i] + spacing

        draw.text((30, 50), CHANNEL_HANDLE, font=font_handle, fill=(255, 255, 255, 160),
                  stroke_width=2, stroke_fill=(0, 0, 0, 160))

        progress = min(1.0, t / total_duration) if total_duration > 0 else 0
        bar_y = H - 14
        draw.rectangle([0, bar_y, W, bar_y + 6], fill=(255, 255, 255, 60))
        draw.rectangle([0, bar_y, int(W * progress), bar_y + 6], fill=(240, 185, 11, 230))

        img.save(f"{frames_dir}/f_{frame_i:05d}.png")

    return total_frames


def assemble_final(bg_path: str, frames_dir: str, audio_path: str, out_path: str) -> bool:
    ok = run_ffmpeg([
        "ffmpeg", "-y",
        "-i", bg_path,
        "-framerate", str(FPS),
        "-i", f"{frames_dir}/f_%05d.png",
        "-i", audio_path,
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-vsync", "cfr",
        "-c:a", "aac", "-shortest",
        out_path,
    ], "assemble_final")
    return ok and is_valid_video(out_path)


def add_intro_sfx(video_path: str, out_path: str) -> bool:
    sfx_path = "_sfx_intro.mp3"
    ok = run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=0.15",
        "-f", "lavfi", "-i", "sine=frequency=1320:duration=0.15",
        "-filter_complex", "[1:a]adelay=120|120[a1];[0:a][a1]amix=inputs=2:duration=longest,volume=2.5",
        sfx_path,
    ], "sfx_synth")
    if not ok:
        return False

    result = run_ffmpeg([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", sfx_path,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        out_path,
    ], "add_intro_sfx")

    if os.path.exists(sfx_path):
        os.remove(sfx_path)

    return result and is_valid_video(out_path, min_duration=1.0)


def add_background_music(video_path: str, out_path: str) -> bool:
    music_dir = "assets/music"
    music_files = list(Path(music_dir).glob("*.mp3")) if os.path.isdir(music_dir) else []

    duration = get_audio_duration(video_path)
    if duration <= 0:
        return False

    music_path = None
    if music_files:
        music_path = str(random.choice(music_files))
    else:
        synth_path = "_music_synth.mp3"
        ok = run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=330:duration={duration}",
            "-filter_complex", "[0:a]volume=0.05[a0];[1:a]volume=0.03[a1];[a0][a1]amix=inputs=2:duration=first",
            synth_path,
        ], "music_synth")
        if ok:
            music_path = synth_path

    if not music_path:
        return False

    ok = run_ffmpeg([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{duration},volume=1[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.3[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        out_path,
    ], "add_background_music")

    if music_path.startswith("_music_synth") and os.path.exists(music_path):
        os.remove(music_path)

    return ok and is_valid_video(out_path, min_duration=1.0)


def create_short(quote: str = None, out_name: str = "short.mp4"):
    if not quote:
        run_number = os.environ.get("GITHUB_RUN_NUMBER")
        if run_number:
            quote = QUOTES[int(run_number) % len(QUOTES)]
        else:
            quote = random.choice(QUOTES)
    print(f"Цитата: {quote}")

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    audio_path = f"{TMP_DIR}/voice.mp3"
    word_timings = asyncio.run(generate_voice_with_timings(quote, audio_path))

    if not word_timings:
        print("  Использую оценку таймингов по длине слов (TTS не дал точных данных)")
        word_timings = build_fallback_timings(quote)
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 500:
            fallback_dur = word_timings[-1]["end"] + 1.0
            run_ffmpeg([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(fallback_dur), audio_path,
            ], "silence_fallback")

    duration = resolve_duration(word_timings, audio_path)

    bg_path = f"{TMP_DIR}/bg.mp4"
    prepare_background(duration, bg_path)

    frames_dir = f"{TMP_DIR}/frames"
    render_caption_frames(word_timings, duration, frames_dir)

    out_path = os.path.join(OUT_DIR, out_name)
    silent_path = f"{TMP_DIR}/_novoice_music.mp4"
    success = assemble_final(bg_path, frames_dir, audio_path, silent_path)

    if not success:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        raise RuntimeError(f"Не удалось собрать видео для цитаты: {quote}")

    if not add_background_music(silent_path, out_path):
        print("  Музыка не подмешалась, сохраняю видео без неё")
        shutil.copy(silent_path, out_path)

    sfx_path = f"{TMP_DIR}/_with_sfx.mp4"
    if add_intro_sfx(out_path, sfx_path):
        shutil.copy(sfx_path, out_path)
    else:
        print("  SFX не подмешался, оставляю видео без него")

    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print(f"Готово: {out_path} (~{duration:.1f} сек)")
    return out_path


if __name__ == "__main__":
    create_short()
