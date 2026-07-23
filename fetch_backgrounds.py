"""
fetch_backgrounds.py — скачивает несколько фоновых видео с Pexels по теме
и кладёт их в assets/backgrounds/, чтобы create_short.py их использовал.
"""

import os
import random
import requests

API_KEY = os.environ.get("PEXELS_API_KEY", "")
BG_DIR = "assets/backgrounds"

QUERIES = [
    "gym workout motivation",
    "sunset city vertical",
    "night city lights",
    "mountain hiking",
    "ocean waves aerial",
]


def fetch_videos(query: str, per_page: int = 3):
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "portrait"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("videos", [])


def pick_best_file_url(video: dict):
    files = video.get("video_files", [])
    candidates = [
        f for f in files
        if f.get("file_type") == "video/mp4"
        and f.get("height", 0) > f.get("width", 0)
        and f.get("height", 0) >= 1280
    ]
    if not candidates:
        candidates = [f for f in files if f.get("file_type") == "video/mp4"]
    if not candidates:
        return None
    candidates.sort(key=lambda f: f.get("height", 0))
    return candidates[len(candidates) // 2]["link"]


def download(url: str, out_path: str):
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def main():
    if not API_KEY:
        print("PEXELS_API_KEY не задан — пропускаю скачивание, будет процедурный фон")
        return

    os.makedirs(BG_DIR, exist_ok=True)
    queries = random.sample(QUERIES, k=min(3, len(QUERIES)))

    downloaded = 0
    for q in queries:
        try:
            videos = fetch_videos(q, per_page=2)
            for v in videos:
                file_url = pick_best_file_url(v)
                if not file_url:
                    continue
                out_path = os.path.join(BG_DIR, f"bg_{v['id']}.mp4")
                if os.path.exists(out_path):
                    continue
                print(f"Скачиваю: {q} -> {out_path}")
                download(file_url, out_path)
                downloaded += 1
        except Exception as e:
            print(f"Ошибка при запросе '{q}': {e}")

    print(f"Готово, скачано файлов: {downloaded}")


if __name__ == "__main__":
    main()
