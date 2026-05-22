# Auralis

AI-powered audio mixing engine.

## Features
- Multi-track processing
- Automatic stem classification
- Learning-based mixing (in progress)

## Local Setup
1. Add audio files to `/resources` (not tracked).
2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure audio files:
   ```bash
   python utils/audio_config.py
   ```
4. Start the backend API server:
   ```bash
   python api_server.py
   ```

## React Frontend Setup
```bash
cd ui/web
npm install
npm run dev
```

## Deployment Ready
This repository is ready for production deployment with the backend hosted on Render and the frontend hosted on Vercel.

### Backend (Render) entrypoint
- `Procfile` contains: `web: gunicorn api_server:app --bind 0.0.0.0:$PORT`
- `runtime.txt` pins Python: `python-3.12.6`
- `requirements.txt` includes backend dependencies and `gunicorn`.
- `api_server.py` now uses environment variables for `PORT`, `HOST`, `FLASK_DEBUG`, `DATABASE_URL`, `UPLOAD_FOLDER`, and `CORS_ORIGINS`.

### Frontend (Vercel)
- `ui/web/.env.example` documents `VITE_API_BASE_URL`.
- `ui/web/vite.config.js` uses `/api` proxy in development only.
- Build with:
  ```bash
  cd ui/web
  npm run build
  ```

### Environment files
- Root `.env.example` provides backend env variable examples.
- `ui/web/.env.example` provides frontend env variable examples.

### GitHub / .gitignore
- `.gitignore` now excludes:
  - `venv/`
  - `node_modules/`
  - `__pycache__/`
  - `*.db`
  - `.env`
  - `uploads/`
  - `ui/web/.env`

## Ephemeral Storage Behavior

Render provides ephemeral filesystem storage that may be cleared or is not durable across deploys.

- **Automatic expiration:** Uploaded files and generated mixes placed in `uploads/` and `resources/` are automatically cleaned up after a configurable retention window (default 24 hours).
- **Configuration:** Control behavior with environment variables in your Render service or `.env`:
   - `FILE_RETENTION_HOURS` — number of hours to retain files (default `24`).
   - `ENABLE_STORAGE_CLEANUP` — set to `true` or `false` to enable/disable cleanup (default `true`).
- **Operational notes:** Users should download any mixes they want to keep; the app does not provide durable long-term storage for audio artifacts in the MVP.
- **Future persistence:** Approved training samples or long-term assets can be migrated to S3 or another object store in a future release.

See `services/storage_cleanup.py` for implementation details and the app's startup behavior.
