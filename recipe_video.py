"""
recipe_video.py — генератор рецепт-видео с несколькими шагами.

Написан с расчётом на устойчивость:
- скачанные с Pexels видео обязательно проверяются на валидность;
- видео обязано содержать нужное ключевое слово в названии;
- сетевые запросы повторяются при сбое;
- если конкретный шаг совсем не собрался — используется гарантированно
  рабочий запасной клип, а не падение всего скрипта.

Плюс профессиональный монтаж: плавные переходы, цветокоррекция, зум,
выравнивание громкости, фоновая музыка.
"""

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests

import create_short as cs

OUT_DIR = "output"
TMP_DIR = "_recipe_tmp"
API_KEY = os.environ.get("PEXELS_API_KEY", "")
FALLBACK_VIDEO_ID = 10432087

RECIPE_TITLE = "Стейк с чесночным маслом и грибным соусом"

STEPS = [
    {
        "text": "Достаём стейк из холодильника заранее, он должен согреться до комнатной температуры",
        "query": "raw steak wooden board",
        "must_include": ["steak", "meat", "beef"],
    },
    {
        "text": "Обильно солим и перчим с обеих сторон, немного оливкового масла",
        "query": "seasoning steak salt pepper",
        "must_include": ["steak", "meat", "beef", "season"],
    },
    {
        "text": "Раскаляем сковороду на сильном огне, обжариваем стейк по три минуты с каждой стороны",
        "query": "steak pan tongs cooking",
        "video_id": FALLBACK_VIDEO_ID,
        "must_include": ["steak", "meat", "beef", "pan", "tongs"],
    },
    {
        "text": "Добавляем сливочное масло, чеснок и розмарин, поливаем стейк соком постоянно",
        "query": "steak butter basting pan",
        "must_include": ["steak", "meat", "beef", "butter", "baste"],
    },
    {
        "text": "На той же сковороде обжариваем шампиньоны до золотистой корочки",
        "query": "mushrooms frying pan closeup",
        "must_include": ["mushroom"],
    },
    {
        "text": "Вливаем сливки, немного тимьяна, увариваем соус до густоты",
        "query": "cream sauce pan cooking",
        "must_include": ["cream", "sauce"],
    },
    {
        "text": "Даём стейку отдохнуть пять минут, нарезаем, поливаем соусом и подаём",
        "query": "steak plating chef restaurant",
        "must_include": ["steak", "meat", "beef", "plat"],
    },
]


def _download_file(url: str, out_path: str, retries: int = 2) -> bool:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            if cs.is_valid_video(out_path):
                return True
            print(f"  Скачанный файл невалиден (попытка {attempt}/{retries})")
        except Exception as e:
            print(f"  Ошибка скачивания (попытка {attempt}/{retries}): {e}")
        time.sleep(1)
    return False


def _pexels_request(url: str, params: dict = None, retries: int = 2):
    headers = {"Authorization": API_KEY}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 429:
                print("  Pexels: превышен лимит запросов, жду перед повтором")
                time.sleep(3)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  Ошибка запроса к Pexels (попытка {attempt}/{retries}): {e}")
            time.sleep(1)
    return None


def fetch_video_by_id(video_id: int, out_path: str) -> bool:
    if not API_KEY:
        return False
    data = _pexels_request(f"https://api.pexels.com/videos/videos/{video_id}")
    if not data:
        return False
    return _pick_and_download(data, out_path)


def _pick_and_download(video: dict, out_path: str) -> bool:
    files = video.get("video_files", [])
    candidates = [f for f in files if f.get("file_type") == "video/mp4" and f.get("height", 0) >= 1280]
    if not candidates:
        candidates = [f for f in files if f.get("file_type") == "video/mp4"]
    if not candidates:
        return False
    candidates.sort(key=lambda f: f.get("height", 0))
    file_url = candidates[len(candidates) // 2]["link"]
    return _download_file(file_url, out_path)


def fetch_one_video(query: str, out_path: str, must_include: list = None) -> bool:
    if not API_KEY:
        return False

    data = _pexels_request(
        "https://api.pexels.com/videos/search",
        {"query": query, "per_page": 15, "orientation": "portrait"},
    )
    if not data:
        return False

    videos = data.get("videos", [])
    if not videos:
        return False

    if must_include:
        must_include_lower = [w.lower() for w in must_include]
        videos = [v for v in videos if any(w in v.get("url", "").lower() for w in must_include_lower)]
        if not videos:
            print(f"  Нет видео с обязательными словами {must_include} для '{query}'")
            return False

    query_words = set(query.lower().split())

    def relevance(v: dict) -> int:
        slug = v.get("url", "").lower()
        return sum(1 for w in query_words if w in slug)

    videos.sort(key=relevance, reverse=True)

    for v in videos:
        if _pick_and_download(v, out_path):
            return True

    return False


def get_background_for_step(step: dict, out_path: str) -> bool:
    query = step["query"]
    must_include = step.get("must_include")

    if "video_id" in step and fetch_video_by_id(step["video_id"], out_path):
        return True

    if fetch_one_video(query, out_path, must_include):
        return True

    print(f"  Использую запасной проверенный клип вместо '{query}'")
    return fetch_video_by_id(FALLBACK_VIDEO_ID, out_path)


def build_step_segment(step: dict, index: int, tmp_dir: str) -> str:
    step_dir = os.path.join(tmp_dir, f"step_{index}")
    os.makedirs(step_dir, exist_ok=True)

    text = step["text"]

    audio_path = os.path.join(step_dir, "voice.mp3")
    word_timings = asyncio.run(cs.generate_voice_with_timings(
        text, audio_path,
        voice="ru-RU-SvetlanaNeural",
        rate="+18%",
        pitch="+4Hz",
    ))

    if not word_timings:
        print(f"  Шаг {index+1}: использую оценку таймингов (TTS не дал точных данных)")
        word_timings = cs.build_fallback_timings(text)
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 500:
            fallback_dur = word_timings[-1]["end"] + 0.6
            cs.run_ffmpeg([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(fallback_dur), audio_path,
            ], f"silence_fallback_step{index}")

    duration = cs.resolve_duration(word_timings, audio_path, tail=0.6)

    bg_path = os.path.join(step_dir, "bg_raw.mp4")
    got_bg = get_background_for_step(step, bg_path)

    bg_processed = os.path.join(step_dir, "bg.mp4")
    if got_bg:
        zoom_filter = (
            f"scale={cs.W}:{cs.H}:force_original_aspect_ratio=increase,"
            f"crop={cs.W}:{cs.H},"
            f"zoompan=z='min(zoom+0.0012,1.08)':d=1:s={cs.W}x{cs.H}:fps={cs.FPS}"
        )
        ok = cs.run_ffmpeg([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", bg_path,
            "-t", str(duration),
            "-vf", zoom_filter,
            "-an", bg_processed,
        ], f"bg_process_step{index}")
        if not ok or not cs.is_valid_video(bg_processed):
            got_bg = False

    if not got_bg:
        print(f"  Шаг {index+1}: нет валидного видео-фона, использую цветной фон")
        cs.run_ffmpeg([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x14181D:s={cs.W}x{cs.H}:d={duration}",
            "-vf", "noise=alls=6:allf=t",
            bg_processed,
        ], f"bg_color_fallback_step{index}")

    frames_dir = os.path.join(step_dir, "frames")
    cs.render_caption_frames(word_timings, duration, frames_dir)

    segment_path = os.path.join(step_dir, "segment.mp4")
    ok = cs.assemble_final(bg_processed, frames_dir, audio_path, segment_path)
    if not ok:
        raise RuntimeError(f"Не удалось собрать сегмент шага {index+1}: {text[:40]}")

    return segment_path


def concat_segments(segment_paths: list, out_path: str) -> bool:
    TRANSITION = 0.4

    durations = [cs.get_audio_duration(p) for p in segment_paths]
    if any(d <= 0 for d in durations):
        print("  Не удалось определить длительность сегмента, использую простую склейку")
        return _concat_segments_simple(segment_paths, out_path)

    filter_parts = []
    for i in range(len(segment_paths)):
        filter_parts.append(
            f"[{i}:v]fps={cs.FPS},format=yuv420p,setpts=PTS-STARTPTS,"
            f"eq=contrast=1.08:saturation=1.15:brightness=0.01[nv{i}]"
        )
        filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[na{i}]")

    prev_v, prev_a = "nv0", "na0"
    cumulative = durations[0]

    for i in range(1, len(segment_paths)):
        offset = max(0.1, cumulative - TRANSITION)
        out_v, out_a = f"v{i}", f"a{i}"
        filter_parts.append(f"[{prev_v}][nv{i}]xfade=transition=fade:duration={TRANSITION}:offset={offset}[{out_v}]")
        filter_parts.append(f"[{prev_a}][na{i}]acrossfade=d={TRANSITION}[{out_a}]")
        prev_v, prev_a = out_v, out_a
        cumulative += durations[i] - TRANSITION

    filter_parts.append(f"[{prev_a}]loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    filter_complex = ";".join(filter_parts)

    inputs = []
    for p in segment_paths:
        inputs += ["-i", p]

    ok = cs.run_ffmpeg([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_v}]", "-map", "[aout]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(cs.FPS),
        "-c:a", "aac",
        out_path,
    ], "concat_segments_pro")

    if ok and cs.is_valid_video(out_path, min_duration=1.0):
        return True

    print("  Профессиональная склейка не удалась, пробую простую склейку")
    return _concat_segments_simple(segment_paths, out_path)


def _concat_segments_simple(segment_paths: list, out_path: str) -> bool:
    inputs = []
    for p in segment_paths:
        inputs += ["-i", p]

    n = len(segment_paths)
    filter_parts = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n))
    filter_complex = f"{filter_parts}concat=n={n}:v=1:a=1[outv][outa]"

    ok = cs.run_ffmpeg([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", str(cs.FPS), "-vsync", "cfr",
        "-c:a", "aac",
        out_path,
    ], "concat_segments_simple")
    return ok and cs.is_valid_video(out_path, min_duration=1.0)


def add_background_music(video_path: str, out_path: str) -> bool:
    music_dir = "assets/music"
    music_files = list(Path(music_dir).glob("*.mp3")) if os.path.isdir(music_dir) else []

    duration = cs.get_audio_duration(video_path)
    if duration <= 0:
        return False

    music_path = None
    if music_files:
        music_path = str(music_files[0])
    else:
        synth_path = "_music_synth.mp3"
        ok = cs.run_ffmpeg([
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

    ok = cs.run_ffmpeg([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{duration},volume=1[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.35[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        out_path,
    ], "add_background_music")

    if music_path.startswith("_music_synth"):
        try:
            os.remove(music_path)
        except OSError:
            pass

    return ok and cs.is_valid_video(out_path, min_duration=1.0)


def build_recipe_video(out_name: str = "recipe.mp4"):
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    os.makedirs(TMP_DIR)

    print(f"Рецепт: {RECIPE_TITLE}")
    segment_paths = []
    failed_steps = []

    for i, step in enumerate(STEPS):
        print(f"Шаг {i+1}/{len(STEPS)}: {step['text'][:40]}...")
        try:
            seg = build_step_segment(step, i, TMP_DIR)
            segment_paths.append(seg)
        except Exception as e:
            print(f"  Шаг {i+1} полностью провалился, пропускаю: {e}")
            failed_steps.append(i + 1)

    if not segment_paths:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        raise RuntimeError("Ни один шаг не собрался — видео не может быть создано")

    if failed_steps:
        print(f"Внимание: пропущены шаги {failed_steps} (не удалось собрать)")

    out_path = os.path.join(OUT_DIR, out_name)
    transitioned_path = os.path.join(TMP_DIR, "_transitioned.mp4")
    success = concat_segments(segment_paths, transitioned_path)

    if not success:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        raise RuntimeError("Не удалось склеить финальное видео из сегментов")

    if not add_background_music(transitioned_path, out_path):
        print("  Музыка не подмешалась, сохраняю видео без неё")
        shutil.copy(transitioned_path, out_path)

    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print(f"Готово: {out_path}")
    return out_path


if __name__ == "__main__":
    build_recipe_video()
