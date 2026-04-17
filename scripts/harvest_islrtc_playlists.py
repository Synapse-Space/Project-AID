"""Harvest ISLRTC's YouTube dictionary playlists into data/islrtc_raw.json.

Enumerates a curated list of ISLRTC 'ISL Dictionary' playlists via yt-dlp
(flat-playlist mode = metadata only, no downloads). Writes one entry per
video with the video's title as the word key.

No video content is downloaded here. Only public YouTube metadata.

Resumable: if data/islrtc_raw.json already exists, entries for playlists
previously harvested are preserved; only new playlists are fetched.
"""

from __future__ import annotations

import json
from pathlib import Path

import yt_dlp

# ISLRTC YouTube playlists confirmed to contain per-word sign videos.
# See scripts/recon_islrtc_report.md for how these were identified.
PLAYLISTS = [
    # Name                                             # YouTube playlist ID
    ("ISL Dictionary - Academic terms",               "PLFjydPMg4Dao754g-aMpjuqBcZQlEnqdV"),
    ("500 signs - Anuprayas (Sep 2024)",              "PLFjydPMg4Dap2aqWP7MlB1hEtczCP23nk"),
    ("500 signs - Yunikee (Sep 2024)",                "PLFjydPMg4Daq1Er_e4mNiF6BKUm3L5q8l"),
    ("ISL Dictionary - Numbers",                      "PLFjydPMg4DarnMdkwFwOQz__g-Sj25ISO"),
    ("ISL Dictionary - Indian States and Cities",     "PLFjydPMg4Dar_Ip1RyVLj-a5-xl_ERieZ"),
    ("ISL Dictionary - Continents and Countries",     "PLFjydPMg4Dapy6Z-H2L0sauuhdcSzl8RT"),
    ("ISL Dictionary - English Idioms in ISL",        "PLFjydPMg4DarxA0Pe3EbAlKP2uknntTRe"),
    ("ISL Dictionary - Regional Signs",               "PLFjydPMg4DaoFednqpyLSCwmFbE4mFliI"),
    ("ISL Signs for Well-being and Mental Health",    "PLFjydPMg4Dar-oytwy9SSJhirsLc0Zd6X"),
]

OUT = Path(__file__).parent.parent / "data" / "islrtc_raw.json"
OUT.parent.mkdir(parents=True, exist_ok=True)


def fetch_playlist(playlist_id: str) -> list[dict]:
    """Return a list of {index, title, video_id} from a YouTube playlist."""
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries", []) or []
    out = []
    for i, e in enumerate(entries, start=1):
        if not e:
            continue
        out.append({
            "playlist_index": i,
            "title": (e.get("title") or "").strip(),
            "video_id": e.get("id"),
        })
    return out


def main() -> None:
    existing: dict[str, list[dict]] = {}
    if OUT.exists():
        previous = json.loads(OUT.read_text())
        # Old format (flat list) or new grouped format — accept both.
        if isinstance(previous, list):
            # Keep existing entries keyed by playlist_name to allow merging.
            for entry in previous:
                existing.setdefault(entry.get("playlist_name", ""), []).append(entry)
        elif isinstance(previous, dict):
            existing = previous

    raw: list[dict] = []
    for name, playlist_id in PLAYLISTS:
        if name in existing and existing[name]:
            print(f"[skip] {name}: {len(existing[name])} entries already harvested")
            raw.extend(existing[name])
            continue
        print(f"[fetch] {name} ({playlist_id})")
        try:
            videos = fetch_playlist(playlist_id)
        except Exception as e:
            print(f"  failed: {e}")
            continue
        print(f"  got {len(videos)} videos")
        for v in videos:
            raw.append({
                "playlist_name": name,
                "playlist_id": playlist_id,
                "playlist_index": v["playlist_index"],
                "word": v["title"].lower().strip(),
                "title_raw": v["title"],
                "video_id": v["video_id"],
                "url": f"https://www.youtube.com/watch?v={v['video_id']}",
            })

    OUT.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
    print(f"\nwrote {len(raw)} entries to {OUT}")


if __name__ == "__main__":
    main()
