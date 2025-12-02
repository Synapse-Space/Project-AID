#!/usr/bin/env python3
"""
Generate wordmap.json from WLASL dataset (Kaggle version)
Maps words (glosses) to local video file paths
"""

import json
import os
from pathlib import Path

# Paths
# Update this to the path found by kagglehub
DATASET_PATH = "/home/8231k/.cache/kagglehub/datasets/risangbaskoro/wlasl-processed/versions/5"
CLASS_LIST = os.path.join(DATASET_PATH, "wlasl_class_list.txt")
NSLT_JSON = os.path.join(DATASET_PATH, "nslt_2000.json")
VIDEOS_DIR = os.path.join(DATASET_PATH, "videos")
OUTPUT_FILE = "/home/8231k/Downloads/extension-main/data/wordmap.json"

def generate_wordmap():
    """Generate wordmap from WLASL dataset"""
    
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset path not found: {DATASET_PATH}")
        return

    # 1. Load Class List (id -> gloss)
    print(f"Loading {CLASS_LIST}...")
    id_to_gloss = {}
    with open(CLASS_LIST, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                class_id = int(parts[0])
                gloss = parts[1]
                id_to_gloss[class_id] = gloss
    
    print(f"Loaded {len(id_to_gloss)} classes")

    # 2. Load NSLT JSON (video_id -> [class_id, ...])
    print(f"Loading {NSLT_JSON}...")
    with open(NSLT_JSON, 'r') as f:
        nslt_data = json.load(f)
    
    # 3. Scan available videos
    print(f"Scanning videos directory...")
    available_videos = set()
    if os.path.exists(VIDEOS_DIR):
        for video_file in os.listdir(VIDEOS_DIR):
            if video_file.endswith('.mp4'):
                video_id = video_file.replace('.mp4', '')
                available_videos.add(video_id)
    else:
        print(f"Error: Videos directory not found: {VIDEOS_DIR}")
        return

    print(f"Found {len(available_videos)} video files")

    # 4. Build wordmap
    # We want to map gloss -> video_path
    # If multiple videos exist for a gloss, pick the first one found in available_videos
    
    wordmap = {
        "_fallback": "", # Will set if we find a fallback
        "_comment": "The _fallback video is shown when a word is not found in the dictionary"
    }
    
    # Group videos by gloss
    gloss_to_videos = {}
    
    for video_id, data in nslt_data.items():
        if video_id in available_videos:
            action = data.get('action', [])
            if action and len(action) > 0:
                class_id = action[0]
                if class_id in id_to_gloss:
                    gloss = id_to_gloss[class_id]
                    if gloss not in gloss_to_videos:
                        gloss_to_videos[gloss] = []
                    gloss_to_videos[gloss].append(video_id)

    # Select one video per gloss (e.g., the first one, or maybe sort/prioritize?)
    # For now, just pick the first one.
    
    matched_count = 0
    for gloss, videos in gloss_to_videos.items():
        # Pick the first video
        video_id = videos[0]
        video_path = f"file://{VIDEOS_DIR}/{video_id}.mp4"
        wordmap[gloss] = video_path
        matched_count += 1

    # Set fallback to 'book' or something common if available, or just the first one
    if 'book' in wordmap:
        wordmap['_fallback'] = wordmap['book']
    elif matched_count > 0:
        # Pick random existing key
        first_key = list(wordmap.keys())[2] # skip _fallback, _comment
        wordmap['_fallback'] = wordmap[first_key]

    print(f"Matched {matched_count} words to videos")
    
    # Write output
    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(wordmap, f, indent=2)
    
    print("Done!")
    print(f"Total entries in wordmap: {len(wordmap) - 2}")

if __name__ == '__main__':
    generate_wordmap()
