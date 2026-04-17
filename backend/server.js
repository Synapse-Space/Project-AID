import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import axios from 'axios';
import ffmpeg from 'fluent-ffmpeg';

import { SidecarClient } from './lib/sidecar_client.js';
import { ClipCache } from './lib/clip_cache.js';
import { makeTranscribeRoute } from './routes/transcribe.js';
import { makeSignRoute } from './routes/sign.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 8080;
const SIDECAR_URL = process.env.SIDECAR_URL || 'http://127.0.0.1:8090';

const app = express();

// Enable CORS for all routes
app.use(cors());

// Parse JSON bodies (increase limit for audio base64 uploads)
app.use(express.json({ limit: '25mb' }));

// Serve static files from the extension directory
app.use(express.static(path.join(__dirname, '..')));

// Ensure temp directory exists
const tempDir = path.join(__dirname, '..', 'temp');
if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir, { recursive: true });
}

// Sidecar client + transcription route
const sidecar = new SidecarClient(SIDECAR_URL);
app.use('/transcribe', makeTranscribeRoute(sidecar));

// /sign end-to-end route: text -> gloss -> clips -> concat MP4
const CLIP_CACHE_DIR = process.env.CLIP_CACHE_DIR || path.join(__dirname, '..', 'data', 'clip_cache');
const WORDMAP_PATH = path.join(__dirname, '..', 'data', 'isl_wordmap.json');

app.use('/sign', makeSignRoute({
  sidecar,
  clipCache: new ClipCache(CLIP_CACHE_DIR),
  wordmapPath: WORDMAP_PATH,
}));

// Example API endpoint
app.get('/api/translate', (req, res) => {
    const text = req.query.text || '';
    // This is a placeholder - you'll need to implement the actual translation logic
    res.json({
        status: 'success',
        message: 'Translation endpoint hit',
        originalText: text,
        // Add your translation response here
    });
});

// Video stitching endpoint
app.post('/stitch', async (req, res) => {
    try {
        const { clips } = req.body;

        if (!clips || !Array.isArray(clips) || clips.length === 0) {
            return res.status(400).json({
                status: 'error',
                message: 'Invalid clips data provided'
            });
        }

        console.log('Stitching clips:', clips);

        // Download all video clips
        const clipPaths = [];
        const failedClips = [];

        for (let i = 0; i < clips.length; i++) {
            const clipUrl = clips[i];
            const clipPath = path.join(tempDir, `clip_${i}.mp4`);

            try {
                // Check if it's a local file:// URL
                if (clipUrl.startsWith('file://')) {
                    const localPath = clipUrl.replace('file://', '');
                    console.log(`Copying local file ${i}: ${localPath}`);

                    // Check if file exists
                    if (!fs.existsSync(localPath)) {
                        throw new Error(`Local file not found: ${localPath}`);
                    }

                    // Copy the file
                    fs.copyFileSync(localPath, clipPath);
                    clipPaths.push(clipPath);
                    console.log(`Copied clip ${i} to ${clipPath}`);
                } else if (clipUrl.startsWith('text:')) {
                    // Create a short text clip for missing words
                    const raw = clipUrl.slice(5);
                    // decode in case frontend encoded it
                    const word = decodeURIComponent(raw);
                    // escape single quotes for drawtext
                    const escaped = word.replace(/'/g, "\\'");
                    console.log(`Generating text clip ${i}: ${word}`);

                    await new Promise((resolve, reject) => {
                        ffmpeg('color=black:s=640x480:r=25:d=2')
                            .inputOptions(['-f', 'lavfi'])
                            .videoFilters([
                                `drawtext=fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2:text='${escaped}'`
                            ])
                            .outputOptions([
                                '-c:v', 'libx264',
                                '-pix_fmt', 'yuv420p',
                                '-movflags', '+faststart'
                            ])
                            .on('end', () => {
                                console.log(`Generated text clip ${i} to ${clipPath}`);
                                resolve();
                            })
                            .on('error', (err) => {
                                console.error(`Error generating text clip ${i}:`, err);
                                reject(err);
                            })
                            .save(clipPath);
                    });

                    clipPaths.push(clipPath);
                } else {
                    // Download from HTTP/HTTPS URL
                    console.log(`Downloading clip ${i}: ${clipUrl}`);
                    const response = await axios({
                        method: 'GET',
                        url: clipUrl,
                        responseType: 'stream',
                        headers: {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        },
                        timeout: 10000 // 10 second timeout
                    });

                    const writer = fs.createWriteStream(clipPath);
                    response.data.pipe(writer);

                    // Wait for download to complete
                    await new Promise((resolve, reject) => {
                        writer.on('finish', resolve);
                        writer.on('error', reject);
                    });

                    clipPaths.push(clipPath);
                    console.log(`Downloaded clip ${i} to ${clipPath}`);
                }
            } catch (error) {
                console.error(`Error processing clip ${i}:`, error.message);
                failedClips.push({ index: i, url: clipUrl, error: error.message });
                // Continue with other clips even if one fails
            }
        }

        if (clipPaths.length === 0) {
            return res.status(400).json({
                status: 'error',
                message: 'No valid clips could be downloaded',
                failedClips: failedClips
            });
        }

        if (clipPaths.length < clips.length) {
            console.log(`Warning: Only ${clipPaths.length} out of ${clips.length} clips were successfully downloaded`);
        }

        // Normalize all clips to same resolution and framerate first
        console.log('Normalizing clips...');
        const normalizedPaths = [];

        for (let i = 0; i < clipPaths.length; i++) {
            const normalizedPath = path.join(tempDir, `normalized_${i}.mp4`);

            await new Promise((resolve, reject) => {
                ffmpeg(clipPaths[i])
                    .outputOptions([
                        '-vf', 'scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2',
                        '-r', '25',                // Set framerate to 25fps
                        '-c:v', 'libx264',
                        '-preset', 'fast',
                        '-crf', '23',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                        '-ar', '44100',            // Audio sample rate
                        '-ac', '2',                // Stereo audio
                        '-pix_fmt', 'yuv420p'
                    ])
                    .on('end', () => {
                        console.log(`Normalized clip ${i}`);
                        resolve();
                    })
                    .on('error', (err) => {
                        console.error(`Error normalizing clip ${i}:`, err);
                        reject(err);
                    })
                    .save(normalizedPath);
            });

            normalizedPaths.push(normalizedPath);
        }

        // Create a text file listing all normalized clips for ffmpeg concatenation
        const listFilePath = path.join(tempDir, 'cliplist.txt');
        const listContent = normalizedPaths.map(clipPath => `file '${clipPath}'`).join('\n');
        fs.writeFileSync(listFilePath, listContent);

        // Output video path
        const outputPath = path.join(tempDir, 'output.mp4');

        // Use ffmpeg to concatenate normalized videos
        console.log('Concatenating videos...');
        await new Promise((resolve, reject) => {
            ffmpeg()
                .input(listFilePath)
                .inputOptions(['-f concat', '-safe 0'])
                .outputOptions([
                    '-c', 'copy',              // Copy since all clips are now normalized
                    '-movflags', '+faststart'
                ])
                .on('end', () => {
                    console.log('Video concatenation completed');
                    resolve();
                })
                .on('error', (err) => {
                    console.error('Error during video concatenation:', err);
                    reject(err);
                })
                .save(outputPath);
        });

        // Read the output video file and send it
        const videoBuffer = fs.readFileSync(outputPath);

        // Clean up temporary files
        try {
            fs.unlinkSync(listFilePath);
            clipPaths.forEach(clipPath => fs.unlinkSync(clipPath));
            normalizedPaths.forEach(normalizedPath => fs.unlinkSync(normalizedPath));
            fs.unlinkSync(outputPath);
        } catch (cleanupError) {
            console.warn('Warning: Could not clean up all temporary files:', cleanupError.message);
        }

        // Send response with information about failed clips
        res.setHeader('Content-Type', 'video/mp4');
        res.setHeader('Content-Disposition', 'attachment; filename="sign_video.mp4"');

        if (failedClips.length > 0) {
            // Include failed clip info in response headers
            res.setHeader('X-Failed-Clips', JSON.stringify(failedClips));
        }

        res.status(200).send(videoBuffer);
    } catch (error) {
        console.error('Error stitching videos:', error);
        res.status(500).json({
            status: 'error',
            message: 'Internal server error: ' + error.message
        });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
