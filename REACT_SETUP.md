# Auralis Training Interface - Setup & Deployment Guide

## Overview

Auralis now features a professional, React-based training interface for collecting A/B audio mixing preferences. This guide covers setup and deployment.

### Architecture

```
┌─────────────────────────────────────────┐
│   React UI (Vite)                       │
│   localhost:5173                        │
│                                         │
│  - Sidebar: File upload, stats          │
│  - Workspace: Audio comparison          │
│  - Controls: Feedback buttons           │
└────────────┬────────────────────────────┘
             │
         (HTTP/API)
             │
┌────────────▼────────────────────────────┐
│   Flask Backend (api_server.py)         │
│   localhost:5000                        │
│                                         │
│  - Mix generation                       │
│  - Audio serving                        │
│  - Feedback collection                  │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│   Python Core (Auralis)                 │
│                                         │
│  - MixGenerator                         │
│  - Audio processing                     │
│  - Data logging                         │
└─────────────────────────────────────────┘
```

## Prerequisites

- **Python 3.8+** - For backend
- **Node.js 16+** - For React development
- **npm** - Package manager

## Quick Start

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Flask and dependencies
pip install flask flask-cors

# Configure audio (one time only)
python utils/audio_config.py

# Start the API server
python api_server.py
```

**Output should show:**
```
============================================================
AURALIS TRAINING API SERVER
============================================================
✓ Mixer initialized successfully

Starting Flask server on http://localhost:5000
React UI will be available on http://localhost:5173
```

### 2. Frontend Setup

**In a new terminal:**

```bash
cd ui/web

# Install dependencies
npm install

# Start development server
npm run dev
```

On Windows PowerShell, if `npm` is blocked by the execution policy, use:

```powershell
npm.cmd install
npm.cmd run dev
```

**Output should show:**
```
  VITE v5.0.8  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

### 3. Open in Browser

Navigate to **http://localhost:5173** in your browser. You should see:

- Left sidebar with drag-drop file upload
- Main workspace area (empty until you generate mixes)
- Bottom status bar showing training statistics

Do not open `http://localhost:5000` expecting the app UI. Port `5000` is only the Flask API server, so it returns JSON/API responses. Use these URLs:

- React app: `http://127.0.0.1:5173/`
- API health check: `http://127.0.0.1:5000/api/health`
- API stats: `http://127.0.0.1:5000/api/stats`

## Features

### File Upload
- Drag & drop audio files into the sidebar
- Supported formats: WAV, MP3, FLAC, OGG
- Max 100MB per file

### Mix Generation
- Click "Generate Mixes" button
- System creates two slightly different mixes from your stems
- Takes 10-30 seconds depending on file size

### Audio Comparison
- Listen to Mix A and Mix B
- Only one plays at a time (previous stops automatically)
- View mix parameters by expanding "📊 View Mix Parameters"

### Feedback Submission
- Choose: "A Better", "B Better", "Equal", or "Skip"
- Feedback recorded to `data/mix_comparisons.jsonl`
- Training data accumulates for model retraining

### Statistics
- Bottom bar shows: Total logged | Valid (for training) | Skipped
- "Ready to train" indicator when ≥5 valid comparisons

## API Endpoints

### Backend API (Flask)

#### `GET /api/health`
Health check and mixer status.

**Response:**
```json
{
  "status": "ok",
  "mixer_ready": true
}
```

#### `GET /api/stats`
Get training statistics.

**Response:**
```json
{
  "total": 15,
  "valid": 12,
  "skipped": 3
}
```

#### `POST /api/generate-mixes`
Generate comparison mixes.

**Request:** FormData with audio files (optional, uses configured stems)

**Response:**
```json
{
  "mixA_url": "/api/audio/mix_a.wav",
  "mixB_url": "/api/audio/mix_b.wav",
  "paramsA": {
    "reverb": 0.45,
    "compression": 0.8,
    ...
  },
  "paramsB": {
    "reverb": 0.52,
    "compression": 0.75,
    ...
  },
  "bothValid": true
}
```

#### `GET /api/audio/<filename>`
Serve generated audio files (mix_a.wav, mix_b.wav).

#### `POST /api/submit-feedback`
Submit user preference.

**Request:**
```json
{
  "choice": "a|b|tie|skip",
  "paramsA": {...},
  "paramsB": {...}
}
```

**Response:**
```json
{
  "success": true,
  "message": "Feedback recorded: Mix A preferred",
  "recorded": true,
  "choice": "a"
}
```

## Configuration

### Audio Configuration
Edit `audio_config.json` to specify:
- Beat file path
- Vocal stems
- Audio processing parameters

Run `python utils/audio_config.py` to reconfigure.

### Environment Variables
- `FLASK_ENV` - Set to `production` for deployment
- `FLASK_DEBUG` - Set to `0` for production
- `REACT_API_URL` - (Optional) For non-localhost API

## Development

### React Development
```bash
cd ui/web
npm run dev          # Start dev server
npm run build        # Production build
npm run preview      # Preview production build
npm run lint         # Check code style
```

### Python Development
```bash
# Run Flask in debug mode
FLASK_DEBUG=1 python api_server.py

# Run tests
pytest tests/

# Check code style
flake8 .
```

## Production Deployment

### Frontend Build

```bash
cd ui/web
npm run build
```

Outputs optimized files to `ui/web/dist/`. Deploy to:
- Static hosting (Netlify, Vercel, GitHub Pages)
- CDN (Cloudflare, AWS CloudFront)
- Web server (Nginx, Apache)

### Backend Deployment

Option 1: **Heroku**
```bash
heroku create auralis-api
git push heroku main
```

Option 2: **Docker**
```bash
docker build -t auralis-api .
docker run -p 5000:5000 auralis-api
```

Option 3: **Traditional Server**
```bash
# Install production WSGI server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
```

### CORS Configuration
For production domains, update `api_server.py`:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourdomain.com"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
```

## Troubleshooting

### "Mixer not initialized"
**Problem:** Backend returns mixer initialization error.

**Solution:**
```bash
python utils/audio_config.py
# Select your beat and vocal files
# Restart API server
```

### CORS Errors
**Problem:** React UI gets CORS errors from API.

**Solution:** 
- Ensure Flask is running on port 5000
- Check Vite proxy in `ui/web/vite.config.js`
- For local development, ensure both servers running on localhost

### Audio Won't Play
**Problem:** Audio player shows no sound.

**Solution:**
- Check browser console (F12) for errors
- Verify audio files exist in `resources/` folder
- Test with: `curl http://localhost:5000/api/audio/mix_a.wav > test.wav`

### High Memory Usage
**Problem:** Slow performance after many generations.

**Solution:**
- Restart API server every 50+ generations
- Reduce audio file size
- Increase available RAM

## File Structure

```
Auralis/
├── api_server.py                 # Flask API
├── app.py                        # Main Python app
├── audio_config.json             # Audio configuration
├── requirements.txt              # Python dependencies
│
├── audio/                        # Audio processing
│   ├── processor.py
│   ├── analyzer.py
│   └── ...
│
├── models/                       # ML components
│   ├── mix_generator.py          # Core mixing logic
│   ├── data_collector.py         # Data logging
│   └── trainer.py
│
├── data/                         # Training data
│   ├── mix_comparisons.jsonl     # Feedback log
│   └── mix_log.jsonl
│
├── resources/                    # Generated audio
│   ├── mix_a.wav
│   ├── mix_b.wav
│   └── ...
│
├── ui/web/                       # React frontend
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx              # Entry point
│   │   ├── App.jsx               # Main component
│   │   ├── App.css               # Global styles
│   │   ├── api/
│   │   │   └── client.js         # API client
│   │   └── components/
│   │       ├── Sidebar.jsx
│   │       ├── AudioPlayer.jsx
│   │       ├── MixComparison.jsx
│   │       ├── ControlPanel.jsx
│   │       └── StatusBar.jsx
│   └── dist/                     # Production build
│
└── utils/                        # Utilities
    ├── audio_config.py
    ├── file_io.py
    └── ...
```

## Performance Tips

1. **Audio File Size:** Keep stems under 30MB each for fast processing
2. **Caching:** Browser caches audio files - clear cache if hearing stale audio
3. **Network:** Use wired connection for consistent performance
4. **Headphones:** Use quality headphones for accurate listening

## Security Notes

- **Local Only:** Default setup is for local development/testing
- **No Auth:** Runs without authentication - don't expose to internet
- **File Limits:** Max 100MB file uploads
- **Skip Handling:** "Skip" responses aren't recorded in training data
- **Data Privacy:** All data stored locally in `data/` folder

## Support

For issues, check:
1. Flask backend logs on terminal
2. React browser console (F12)
3. Python error traces
4. Audio file integrity: `ffprobe resources/mix_a.wav`

---

**Last Updated:** 2024  
**Version:** 1.0  
**Status:** Production Ready
