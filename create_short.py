"""
create_short.py — генератор коротких видео под TikTok / YouTube Shorts.
Формат: 1080x1920 (9:16), mp4, h264.
"""

import asyncio
import os
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VOICE = "ru-RU-DmitryNeural"
RATE = "+8%"
W, H = 1080, 1920
FPS = 30

BG_DIR = "assets/backgrounds"
OUT_DIR = "output"
TMP_DIR = "_tmp"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
COLOR_WHITE = (255, 255, 255)
COLOR_HIGHLIGHT = (240, 185, 11)

QUOTES = [
    "Дисциплина побеждает мотивацию каждый раз, когда мотивация решает взять выходной",
    "Ты не устал, тебе просто скучно побеждать медленно",
    "Тело терпит столько, сколько разум ему позволяет",
    "Каждая пропущенная тренировка — подарок для того, с кем ты соревнуешься",
    "Час учёбы сегодня — час свободы завтра",
]


async def generate_voice_with_timings(text: str, audio_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
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


def prepare_background(duration: float, out_path: str):
    files = list(Path(BG_DIR).glob("*.mp4"))
    if files:
        bg = str(random.choice(files))
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg,
            "-t", str(duration),
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
            "-an", out_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x14181D:s={W}x{H}:d={duration}",
            "-vf", "noise=alls=6:allf=t",
            out_path,
        ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_caption_frames(word_timings: list, total_duration: float, frames_dir: str):
    os.makedirs(frames_dir, exist_ok=True)
    font = ImageFont.truetype(FONT_BOLD, 62)
    total_frames = int(total_duration * FPS) + 1
    words = [w["word"] for w in word_timings]

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

        window = 2
        lo = max(0, active_idx - window)
        hi = min(len(words), active_idx + window + 1)
        visible = words[lo:hi]

        spacing = 18
        widths = [draw.textbbox((0, 0), w, font=font)[2] for w in visible]
        total_w = sum(widths) + spacing * (len(visible) - 1)
        x = (W - total_w) // 2
        y = int(H * 0.62)

        for i, w in enumerate(visible):
            real_idx = lo + i
            color = COLOR_HIGHLIGHT if real_idx == active_idx else COLOR_WHITE
            draw.text((x, y), w, font=font, fill=color,
                      stroke_width=4, stroke_fill=(0, 0, 0, 255))
            x += widths[i] + spacing

        img.save(f"{frames_dir}/f_{frame_i:05d}.png")

    return total_frames


def assemble_final(bg_path: str, frames_dir: str, audio_path: str, out_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-i", bg_path,
        "-framerate", str(FPS),
        "-i", f"{frames_dir}/f_%05d.png",
        "-i", audio_path,
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def create_short(quote: str = None, out_name: str = "short.mp4"):
    quote = quote or random.choice(QUOTES)
    print(f"Цитата: {quote}")

    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    audio_path = f"{TMP_DIR}/voice.mp3"
    word_timings = asyncio.run(generate_voice_with_timings(quote, audio_path))
    duration = word_timings[-1]["end"] + 1.0

    bg_path = f"{TMP_DIR}/bg.mp4"
    prepare_background(duration, bg_path)

    frames_dir = f"{TMP_DIR}/frames"
    render_caption_frames(word_timings, duration, frames_dir)

    out_path = os.path.join(OUT_DIR, out_name)
    assemble_final(bg_path, frames_dir, audio_path, out_path)

    shutil.rmtree(TMP_DIR)
    print(f"Готово: {out_path} (~{duration:.1f} сек)")
    return out_path


if __name__ == "__main__":
    create_short()
