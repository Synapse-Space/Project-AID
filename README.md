# Project AID (Audio/Video Integration & Development)

A browser extension with backend services for audio/video processing and translation.

## Features

- **Browser Extension**: Chrome extension for capturing and processing media
- **Backend Server**: Node.js/Express server for handling media processing
- **Video Processing**: Stitching and normalizing video clips
- **Translation API**: Integration with translation services

## Project Structure

```
Project-AID/
├── backend/               # Backend server code
│   ├── server.js         # Main server file
│   └── .env.example      # Environment variables template
├── content/              # Content scripts
├── data/                 # Data files
├── offscreen/            # Offscreen documents
├── options/              # Extension options page
├── popup/                # Browser action popup
├── background.js         # Extension background script
├── manifest.json         # Extension manifest
├── package.json          # Project dependencies
└── README.md            # This file
```

## Prerequisites

- Node.js (v14+)
- npm or yarn
- Chrome or Chromium-based browser
- FFmpeg (for video processing)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/Project-AID.git
   cd Project-AID
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env` in the backend directory
   - Update the values as needed

## Development

1. Start the backend server:
   ```bash
   cd backend
   npm start
   ```

2. Load the extension in Chrome:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the project root directory

## Building for Production

1. Build the extension:
   ```bash
   npm run build
   ```

2. The built extension will be available in the `dist/` directory

## Configuration

The following environment variables can be set in `.env`:

```
PORT=8080
NODE_ENV=development
# Add other environment variables as needed
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository. Project-AID