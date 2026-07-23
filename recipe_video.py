"""
recipe_video.py — генератор рецепт-видео с несколькими шагами.
"""

import asyncio
import os
import shutil
import subprocess

import requests

import create_short as cs

OUT_DIR = "output"
TMP_DIR = "_recipe_tmp"
API_KEY = os.environ.get("PEXELS_API_KEY", "")

RECIPE_TITLE = "Стейк с чесночным маслом и грибным соусом"

STEPS = [
    {
        "text": "Достаём стейк из холодильника заранее, он должен согреться до комнатной температуры",
        "query": "raw steak meat",
    },
    {
        "text": "Обильно солим и перчим с обеих сторон, немного оливкового масла",
        "query": "seasoning meat cooking",
    },
    {
        "text": "Раскаляем сковороду на сильном огне, обжариваем стейк по три минуты с каждой стороны",
        "query": "steak searing pan fire",
    },
    {
        "text": "Добавляем сливочное масло, чеснок и розмарин, поливаем стейк соком постоянно",
        "query": "butter garlic pan cooking",
    },
    {
        "text": "На той же сковороде обжариваем шампиньоны до золотистой корочки",
        "query": "mushrooms cooking pan",
    },
    {
        "text": "Вливаем сливки, немного тимьяна, увариваем соус до густоты",
        "query": "cream sauce cooking pan",
    },
    {
        "text": "Даём стейку отдохнуть пять минут, нарезаем, поливаем соусом и подаём",
        "query": "steak plating restaurant",
    },
]


def fetch_one_video(query: str, out_path: str) -> bool:
    if not API_KEY:
        return False
    try:
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": API_KEY}
        params = {"query": query, "per_page": 3, "orientation": "portrait"}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            return False

        for v in videos:
            files = v.get("video_files", [])
            candidates = [
                f for f in files
                if f.get("file_type") == "video/mp4"
                and f.get("height", 0) >= 1280
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda f: f.get("height", 0))
            file_url = candidates[len(candidates) // 2]["link"]

            r = requests.get(file_url, stream=True, timeout=60)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"  Ошибка скачивания фона '{query}': {e}")
    return False


def build_step_segment(step: dict, index: int, tmp_dir: str) -> str:
    step_dir = os.path.join(tmp_dir, f"step_{index}")
    os.makedirs(step_dir, exist_ok=True)

    text = step["text"]
    query = step["query"]

    audio_path = os.path.join(step_dir, "voice.mp3")
    word_timings = asyncio.run(cs.generate_voice_with_timings(
        text, audio_path,
        voice="ru-RU-SvetlanaNeural",
        rate="+18%",
        pitch="+4Hz",
    ))

    if not word_timings:
        words = text.split()
        t = 0.3
        for w in words:
            dur = max(0.18, len(w) * 0.06)
            word_timings.append({"word": w, "start": t, "end": t + dur})
            t += dur + 0.05

    duration = word_timings[-1]["end"] + 0.6

    bg_path = os.path.join(step_dir, "bg_raw.mp4")
    got_bg = fetch_one_video(query, bg_path)

    bg_processed = os.path.join(step_dir, "bg.mp4")
    if got_bg:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg_path,
            "-t", str(duration),
            "-vf", f"scale={cs.W}:{cs.H}:force_original_aspect_ratio=increase,crop={cs.W}:{cs.H}",
            "-an", bg_processed,
        ]
    else:
        print(f"  Нет фона для '{query}', использую нейтральный")
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x14181D:s={cs.W}x{cs.H}:d={duration}",
            bg_processed,
        ]
    subprocess.run(cmd, check=True, capture_output=True)

    frames_dir = os.path.join(step_dir, "frames")
    cs.render_caption_frames(word_timings, duration, frames_dir)

    segment_path = os.path.join(step_dir, "segment.mp4")
    cs.assemble_final(bg_processed, frames_dir, audio_path, segment_path)

    return segment_path


def concat_segments(segment_paths: list, out_path: str):
    """Перекодируем при склейке (не copy), чтобы убрать дёрганье на стыках."""
    list_file = os.path.join(TMP_DIR, "concat_list.txt")
    with open(list_file, "w") as f:
        for p in segment_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-r", str(cs.FPS),
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def build_recipe_video(out_name: str = "recipe.mp4"):
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    print(f"Рецепт: {RECIPE_TITLE}")
    segment_paths = []
    for i, step in enumerate(STEPS):
        print(f"Шаг {i+1}/{len(STEPS)}: {step['text'][:40]}...")
        seg = build_step_segment(step, i, TMP_DIR)
        segment_paths.append(seg)

    out_path = os.path.join(OUT_DIR, out_name)
    concat_segments(segment_paths, out_path)

    shutil.rmtree(TMP_DIR)
    print(f"Готово: {out_path}")
    return out_path


if __name__ == "__main__":
    build_recipe_video()
