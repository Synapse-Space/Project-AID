"""Convert data/islrtc_raw.json -> data/isl_wordmap.json.

Input format (from Task 8, harvest_islrtc_playlists.py):
  [
    {
      "playlist_name": "...",
      "playlist_id": "...",
      "playlist_index": 1,
      "word": "solar system",
      "title_raw": "Solar System",
      "video_id": "LzsozjEet_8",
      "url": "https://www.youtube.com/watch?v=LzsozjEet_8"
    },
    ...
  ]

Output format (flat, consumed by the extension + backend):
  {
    "solar system": {
      "clip_url": "https://www.youtube.com/watch?v=LzsozjEet_8",
      "video_id": "LzsozjEet_8",
      "source": "islrtc-youtube",
      "playlist": "ISL Dictionary - Academic terms"
    },
    ...
  }

Duplicate resolution: first entry wins. Playlists are listed in the
harvest script in priority order (Academic terms first, then 500-signs
sets, then Numbers/Regions, etc.), so first-wins naturally preserves
the highest-quality dictionary entry.
"""

import json
import re
from pathlib import Path

RAW = Path(__file__).parent.parent / "data" / "islrtc_raw.json"
OUT = Path(__file__).parent.parent / "data" / "isl_wordmap.json"


def normalize(word: str) -> str:
    """Lowercase, trim, collapse whitespace, strip trailing digits-in-parens
    that ISLRTC uses to disambiguate duplicates (e.g. 'citizenship1').
    """
    w = word.strip().lower()
    # Strip trailing digit-suffix ISLRTC uses for alternate takes:
    # "citizenship1" -> "citizenship", "physics2" -> "physics"
    w = re.sub(r"(\w)(\d+)$", r"\1", w)
    # Collapse internal whitespace
    w = re.sub(r"\s+", " ", w)
    return w


def main() -> None:
    raw = json.loads(RAW.read_text())
    wm: dict[str, dict] = {}
    skipped_empty = 0
    duplicates = 0

    for entry in raw:
        word_raw = entry.get("word", "")
        if not word_raw:
            skipped_empty += 1
            continue
        key = normalize(word_raw)
        if not key:
            skipped_empty += 1
            continue
        if key in wm:
            duplicates += 1
            continue  # first-wins preserves priority ordering
        wm[key] = {
            "clip_url": entry["url"],
            "video_id": entry["video_id"],
            "source": "islrtc-youtube",
            "playlist": entry.get("playlist_name", ""),
        }

    OUT.write_text(json.dumps(wm, indent=2, sort_keys=True, ensure_ascii=False))
    print(f"wrote {len(wm)} entries to {OUT}")
    print(f"  skipped {skipped_empty} empty-word rows")
    print(f"  collapsed {duplicates} duplicate keys (first-wins)")


if __name__ == "__main__":
    main()
