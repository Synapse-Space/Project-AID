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

3.  Install Python dependencies (for data scripts):

    ```bash
    pip install kagglehub
    ```

4.  **Important**: Download the WLASL dataset.
    Run the download script from the project root:

    ```bash
    python download_wlasl.py
    ```

    _Note: This may take some time as the dataset is large._

5.  Generate the word map:
    ```bash
    python generate_wordmap.py
    ```

## Configuration

1.  Copy `.env.example` to `.env`:

    ```bash
    cp .env.example .env
    ```

2.  Edit `.env` and set the required variables:
    - `PORT`: The port the server will run on (default: 8080).
    - `ASSEMBLYAI_API_KEY`: Your AssemblyAI API key (if using transcription features).

## Usage

Start the development server:

```bash
npm start
```

The server will start on `http://localhost:8080` (or the port specified in `.env`).

## API Endpoints

### `POST /process-video`

Generates a sign language video from the provided text.

**Request Body:**

```json
{
  "text": "Hello world"
}
```

**Response:**

Returns a stream of the generated video file.

### `GET /health`

Checks if the server is running.

**Response:**

```json
{
  "status": "ok"
}
```
