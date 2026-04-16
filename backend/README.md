# Project-AID Backend

The backend server for Project-AID, built with Node.js and Express. It handles video processing, data management, and external API integrations.

## Prerequisites

- Node.js (v14 or higher)
- FFmpeg (must be installed and available in your system PATH)
- Python 3 (for data scripts)

## Installation

1.  Navigate to the backend directory:

    ```bash
    cd backend
    ```

2.  Install Node.js dependencies:

    ```bash
    npm install
    ```

3.  Set up the Python sidecar (separate service — see `python-sidecar/README.md` once Task 2 lands).

4.  Build the ISL word map from ISLRTC (replaces the old WLASL pipeline — see plan Tasks 7–9).

## Configuration

1.  Copy `.env.example` to `.env`:

    ```bash
    cp .env.example .env
    ```

2.  Edit `.env` and set the required variables:
    - `PORT`: The port the server will run on (default: 8080).
    - `SIDECAR_URL`: URL of the Python NLP/ASR sidecar (default: `http://127.0.0.1:8090`).
    - `CLIP_CACHE_DIR`: Where cached ISL clips are stored on disk.
    - `ISL_CLIP_BASE_URL`: Base URL for the ISLRTC clip source (set after reconnaissance).

## Usage

Start the development server:

```bash
npm start
```

The server will start on `http://localhost:8080` (or the port specified in `.env`).

## API Endpoints

### `POST /stitch`

Stitches a list of video clips into a single MP4. Used internally by the extension.

### `POST /sign` *(added in Task 14)*

Generates an ISL video from the provided text.

**Request Body:**

```json
{
  "text": "I drink water."
}
```

**Response:** `video/mp4` binary.

### `POST /transcribe` *(added in Task 6)*

Proxies audio to the Python sidecar for Whisper transcription.
