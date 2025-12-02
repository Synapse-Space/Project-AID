// sidepanel.js

const videoPlayer = document.getElementById('videoPlayer');
const placeholder = document.getElementById('placeholder');
const captionsBox = document.getElementById('captionsBox');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusEl = document.getElementById('status');

let wordmap = {};
let videoQueue = [];
let isPlaying = false;
let currentCaptionText = "";

// Load wordmap
async function loadWordmap() {
    return new Promise((resolve) => {
        chrome.storage.local.get(['wordmap'], (result) => {
            if (result.wordmap) {
                resolve(result.wordmap);
            } else {
                fetch(chrome.runtime.getURL('data/wordmap.json'))
                    .then(response => response.json())
                    .then(data => resolve(data))
                    .catch(() => resolve({}));
            }
        });
    });
}

// Initialize
(async () => {
    wordmap = await loadWordmap();
    console.log('Sidepanel: Wordmap loaded');
})();

// Controls
startBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'start_captions' }, (resp) => {
        if (resp && resp.ok) {
            statusEl.textContent = "Capturing audio...";
        } else {
            statusEl.textContent = "Error starting capture";
        }
    });
});

stopBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'stop_captions' }, () => {
        statusEl.textContent = "Stopped";
    });
});

// Listen for messages
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'captions_update') {
        handleNewCaption(msg.text);
    } else if (msg.type === 'captions_show') {
        statusEl.textContent = "Capturing audio...";
    } else if (msg.type === 'captions_hide') {
        statusEl.textContent = "Stopped";
    }
});

// Handle new caption text
function handleNewCaption(text) {
    if (!text) return;

    // Simple diffing to find new words
    // This is a naive approach: assumes text only appends. 
    // Web Speech API 'interim' results might change previous words, but 'final' results append.
    // We'll assume we just want to process the *new* part of the string if it's an append,
    // or just process the whole thing if it's short.
    // ACTUALLY, for a smooth "live" feel, we should probably just tokenize the *latest* words.
    // But `captions_update` usually sends the *entire* accumulated text for the session or sentence.

    // Let's try to find the suffix that is new.
    let newText = "";
    if (text.startsWith(currentCaptionText)) {
        newText = text.slice(currentCaptionText.length);
    } else {
        // Text changed completely or restarted
        newText = text;
    }

    currentCaptionText = text;

    if (!newText.trim()) return;

    // Update UI
    const span = document.createElement('span');
    span.textContent = newText;
    captionsBox.appendChild(span);
    captionsBox.scrollTop = captionsBox.scrollHeight;

    // Tokenize and queue videos
    const tokens = newText.toLowerCase().split(/\s+/).filter(t => t.trim());

    tokens.forEach(token => {
        // Strip punctuation
        const cleanToken = token.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "");
        if (!cleanToken) return;

        const videoUrl = wordmap[cleanToken];
        if (videoUrl) {
            // Word found in wordmap
            videoQueue.push(videoUrl);
        } else {
            // Word not found - request text overlay from backend
            videoQueue.push(`text:${encodeURIComponent(cleanToken)}`);
        }

        processQueue();
    });
}

// Video Queue Processor
async function processQueue() {
    if (isPlaying) return;
    if (videoQueue.length === 0) {
        // Show placeholder if idle for a while?
        // placeholder.style.display = 'flex';
        return;
    }

    isPlaying = true;
    const url = videoQueue.shift();

    // Check if this is a text overlay request
    if (url.startsWith('text:')) {
        const text = decodeURIComponent(url.slice(5));
        await generateTextVideo(text);
        isPlaying = false;
        processQueue();
        return;
    }

    // Regular video file
    placeholder.style.display = 'none';
    videoPlayer.src = url;
    videoPlayer.play().catch(e => {
        console.error("Play error:", e);
        isPlaying = false;
        processQueue();
    });
}

// Generate text overlay video from backend
async function generateTextVideo(text) {
    try {
        const backendUrl = 'http://localhost:8080'; // TODO: make configurable
        const response = await fetch(`${backendUrl}/stitch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clips: [`text:${encodeURIComponent(text)}`] })
        });

        if (!response.ok) {
            console.error('Backend error generating text video');
            return;
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);

        placeholder.style.display = 'none';
        videoPlayer.src = objectUrl;
        await videoPlayer.play().catch(e => console.error("Play error:", e));

    } catch (error) {
        console.error('Error generating text video:', error);
    }
}

videoPlayer.addEventListener('ended', () => {
    isPlaying = false;
    processQueue();
});

videoPlayer.addEventListener('error', () => {
    console.warn("Video error, skipping");
    isPlaying = false;
    processQueue();
});
