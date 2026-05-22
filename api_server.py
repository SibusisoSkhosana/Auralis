"""Flask API server for Auralis training interface.

This server bridges the React UI with the Python mixing backend.
It handles:
- Mix generation from audio files
- Feedback submission
- Training statistics
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required, verify_jwt_in_request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import traceback
import librosa
import numpy as np
from urllib.parse import quote
from services import storage_cleanup

# Load environment variables from .env when present
load_dotenv()

# Add parent directory to path for Auralis imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import db, get_database_uri
from models.entities import (
    User,
    AudioUpload,
    ProcessingSession,
    OutputResult,
    Feedback,
)
from models.mix_generator import MixGenerator, to_json_compatible
from models.data_collector import log_mix_comparison
from services.training_data_collector import TrainingDataCollectorService
from audio.alignment import (
    calculate_alignment,
    load_alignment_offsets,
    save_alignment_offsets,
    samples_to_ms,
)
from utils.file_io import save_audio
from utils.audio_config import get_audio_config, load_config, save_config

# ============================================================================
# CONFIGURATION
# ============================================================================

app = Flask(__name__)

# Temporary: allow any origin to avoid CORS interruptions while debugging production
# WARNING: Revert to strict origins after stabilizing (see RENDER_SETUP.md)
CORS(app, resources={r"/*": {"origins": "*"}})

cors_origins = os.getenv('CORS_ORIGINS', '*')
if cors_origins.strip() == '*':
    cors_origins = '*'
else:
    cors_origins = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]

# Database and JWT configuration
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Engine options to keep RDS connections healthy
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "pool_timeout": 30,
}

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'auralis-secret-key')

# Enable SQLAlchemy engine logging to diagnose DB connection issues
logging.basicConfig(level=logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

db.init_app(app)
jwt = JWTManager(app)

# Warn if DATABASE_URL is missing sslmode (helps RDS TLS connections)
try:
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri and 'sslmode' not in db_uri.lower():
        print('[DB] Warning: DATABASE_URL may be missing sslmode=require', flush=True)
except Exception:
    pass

@jwt.unauthorized_loader
def custom_unauthorized_response(err):
    print(f"[JWT] Unauthorized request: {err}", flush=True)
    return jsonify({'error': 'Authorization header missing or invalid.'}), 401

@jwt.invalid_token_loader
def custom_invalid_token_response(err):
    print(f"[JWT] Invalid token: {err}", flush=True)
    return jsonify({'error': 'Invalid authorization token.'}), 401

@jwt.expired_token_loader
def custom_expired_token_response(jwt_header, jwt_payload):
    print('[JWT] Expired token', flush=True)
    return jsonify({'error': 'Authorization token expired.'}), 401

# File upload configuration
UPLOAD_FOLDER = Path(os.getenv('UPLOAD_FOLDER', 'uploads'))
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'ogg'}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB for local stem batches

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
Path('resources').mkdir(parents=True, exist_ok=True)

# Global mixer instance
mixer = None

# ============================================================================
# INITIALIZATION
# ============================================================================

def init_mixer():
    """Initialize the MixGenerator."""
    global mixer
    try:
        config = load_config() or get_audio_config()
        if config:
            mixer = MixGenerator(config)
            return True
    except Exception as e:
        print(f"Warning: Could not initialize mixer with existing config: {e}")
    return False

with app.app_context():
    # Create DB tables at startup (Flask 3 removes before_first_request)
    db.create_all()
    # Attempt a non-fatal cleanup at startup to remove stale ephemeral files.
    try:
        storage_cleanup.cleanup_old_files()
    except Exception:
        print('[CLEANUP] Startup cleanup failed, continuing startup', flush=True)

def get_current_user():
    identity = get_jwt_identity()
    if identity is None:
        return None
    return User.query.filter_by(id=int(identity)).first()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_resource_audio():
    """Remove active project audio files from resources."""
    resources_dir = Path('resources')
    for path in resources_dir.iterdir():
        if path.is_file() and path.suffix.lower().lstrip('.') in ALLOWED_EXTENSIONS:
            path.unlink()

def choose_beat_file(filenames):
    """Choose the beat from uploaded filenames using predictable local rules."""
    beat_terms = ('beat', 'instrumental', 'inst', 'prod')
    for filename in filenames:
        stem = Path(filename).stem.lower()
        if any(term in stem for term in beat_terms):
            return filename
    return filenames[0] if filenames else None

def save_uploaded_project(uploaded_files):
    """Persist uploaded audio files as the active resources project."""
    saved_files = []
    clear_resource_audio()
    alignment_path = Path('data/alignment_offsets.json')
    if alignment_path.exists():
        alignment_path.unlink()

    for uploaded_file in uploaded_files:
        if not uploaded_file.filename or not allowed_file(uploaded_file.filename):
            continue

        filename = secure_filename(uploaded_file.filename)
        if not filename:
            continue

        uploaded_file.save(Path('resources') / filename)
        saved_files.append(filename)

    if len(saved_files) < 2:
        raise ValueError('Upload at least one beat and one vocal/stem file.')

    beat_file = choose_beat_file(saved_files)
    vocal_files = [filename for filename in saved_files if filename != beat_file]

    if not vocal_files:
        raise ValueError('Could not identify vocal/stem files. Include at least two audio files.')

    save_config(beat_file, vocal_files)
    return {'beat': beat_file, 'vocals': vocal_files}

def resource_url(filename):
    return f"/api/source-audio/{quote(filename)}"

def get_project_payload():
    """Return active project metadata for the React UI."""
    config = load_config()
    if not config:
        return {
            'configured': False,
            'beat': None,
            'vocals': [],
            'offsets': {}
        }

    offsets = load_alignment_offsets()
    return {
        'configured': True,
        'beat': {
            'filename': config['beat'],
            'url': resource_url(config['beat'])
        },
        'vocals': [
            {
                'filename': filename,
                'url': resource_url(filename),
                'offsetMs': offsets.get(filename, 0)
            }
            for filename in config['vocals']
        ],
        'offsets': offsets
    }

def get_training_stats():
    """Get training data statistics."""
    stats = {
        'total': 0,
        'valid': 0,
        'skipped': 0
    }
    
    comp_file = Path('data/mix_comparisons.jsonl')
    if comp_file.exists():
        with open(comp_file) as f:
            for line in f:
                try:
                    record = json.loads(line)
                    stats['total'] += 1
                    if record.get('preference') == 'skip':
                        stats['skipped'] += 1
                    else:
                        stats['valid'] += 1
                except json.JSONDecodeError:
                    pass
    
    return stats

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def api_index():
    """Friendly index for users who open the API server in a browser."""
    return jsonify({
        'service': 'Auralis Training API',
        'message': 'This is the backend API. Open the React UI at https://auralis-kappa.vercel.app',
        'ui': 'https://auralis-kappa.vercel.app',
        'endpoints': {
            'health': '/api/health',
            'stats': '/api/stats',
            'project': '/api/project',
            'upload': 'POST /api/upload',
            'history': '/api/history',
            'auth_register': 'POST /api/auth/register',
            'auth_login': 'POST /api/auth/login',
            'source_audio': '/api/source-audio/<filename>',
            'sync_alignment': 'POST /api/alignment/sync',
            'save_alignment': 'POST /api/alignment',
            'generate_mixes': 'POST /api/generate-mixes',
            'feedback': 'POST /api/feedback',
            'clear_project': 'POST /api/project/clear'
        }
    })

@app.route('/api/auth/register', methods=['POST'])
def register():
    payload = request.get_json() or {}
    email = (payload.get('email') or '').strip().lower()
    password = payload.get('password')
    consent = bool(payload.get('consent_to_training', False))

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered.'}), 400

    user = User(email=email, consent_to_training=consent)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'consent_to_training': user.consent_to_training,
        }
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json() or {}
    email = (payload.get('email') or '').strip().lower()
    password = payload.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'consent_to_training': user.consent_to_training,
        }
    })

@app.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    uploads = [
        {
            'id': upload.id,
            'original_name': upload.original_name,
            'filename': upload.filename,
            'content_type': upload.content_type,
            'size': upload.size,
            'path': upload.path,
            'status': upload.status,
            'uploaded_at': upload.uploaded_at.isoformat(),
            'session_id': upload.session_id,
        }
        for upload in AudioUpload.query.filter_by(user_id=user.id).order_by(AudioUpload.uploaded_at.desc()).all()
    ]

    sessions = []
    for session in ProcessingSession.query.filter_by(user_id=user.id).order_by(ProcessingSession.started_at.desc()).all():
        result = session.output_result
        sessions.append({
            'id': session.id,
            'started_at': session.started_at.isoformat(),
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'status': session.status,
            'model_confidence': session.model_confidence,
            'result': {
                'id': result.id,
                'mix_a_path': result.mix_a_path,
                'mix_b_path': result.mix_b_path,
                'both_valid': result.both_valid,
            } if result else None,
        })

    feedback = [
        {
            'id': record.id,
            'result_id': record.result_id,
            'choice': record.choice,
            'metadata': record.meta,
            'recorded_at': record.recorded_at.isoformat(),
            'mix_a_path': record.result.mix_a_path if record.result else None,
            'mix_b_path': record.result.mix_b_path if record.result else None,
        }
        for record in Feedback.query.filter_by(user_id=user.id).order_by(Feedback.recorded_at.desc()).all()
    ]

    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'consent_to_training': user.consent_to_training,
        },
        'uploads': uploads,
        'sessions': sessions,
        'feedback': feedback,
    })

@app.route('/api/upload', methods=['POST'])
@jwt_required()
def upload_project():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        uploaded_files = request.files.getlist('files')
        if not uploaded_files:
            return jsonify({'error': 'No audio files uploaded'}), 400

        session = ProcessingSession(user_id=user.id, status='uploaded', started_at=datetime.utcnow())
        db.session.add(session)
        db.session.commit()

        active_config = save_uploaded_project(uploaded_files)

        for uploaded_file in uploaded_files:
            if not uploaded_file.filename or not allowed_file(uploaded_file.filename):
                continue

            filename = secure_filename(uploaded_file.filename)
            if not filename:
                continue

            file_path = Path('resources') / filename
            upload_record = AudioUpload(
                user_id=user.id,
                session_id=session.id,
                original_name=uploaded_file.filename,
                filename=filename,
                content_type=uploaded_file.mimetype,
                size=file_path.stat().st_size if file_path.exists() else 0,
                path=str(file_path),
                status='saved',
            )
            db.session.add(upload_record)

        db.session.commit()
        return jsonify({**get_project_payload(), 'sessionId': session.id})
    except Exception as e:
        db.session.rollback()
        print(f"Error uploading project: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to upload project: {str(e)}'}), 500

@app.route('/api/project/upload', methods=['POST'])
@jwt_required()
def upload_project_alias():
    return upload_project()

@app.route('/api/feedback', methods=['POST'])
@jwt_required()
def feedback():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json() or {}
        choice = (data.get('choice') or '').lower()
        params_a = data.get('paramsA')
        params_b = data.get('paramsB')
        result_id = data.get('resultId')
        metadata = data.get('metadata') or {}

        if choice not in ['a', 'b', 'tie', 'skip']:
            return jsonify({'error': f'Invalid choice: {choice}'}), 400

        if not result_id:
            return jsonify({'error': 'Result ID is required for feedback.'}), 400

        result = OutputResult.query.join(ProcessingSession).filter(
            OutputResult.id == result_id,
            ProcessingSession.user_id == user.id,
        ).first()
        if not result:
            return jsonify({'error': 'Result not found or unauthorized.'}), 404

        record = Feedback(
            user_id=user.id,
            result_id=result.id,
            choice=choice,
            meta=metadata,
        )
        db.session.add(record)

        if choice != 'skip' and user.consent_to_training:
            result.approved_for_training = True
            db.session.add(result)
            collector = TrainingDataCollectorService(db.session)
            collector.mark_sample_for_training(result)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': choice == 'skip' and 'Comparison skipped.' or f'Feedback recorded: {choice.upper()} preferred',
            'recorded': True,
            'choice': choice,
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error processing feedback: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to submit feedback: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'mixer_ready': mixer is not None
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get training statistics."""
    try:
        total = Feedback.query.count()
        valid = Feedback.query.filter(Feedback.choice.in_(['a', 'b', 'tie'])).count()
        skipped = Feedback.query.filter_by(choice='skip').count()
        return jsonify({'total': total, 'valid': valid, 'skipped': skipped})
    except Exception:
        stats = get_training_stats()
        return jsonify(stats)

@app.route('/api/project', methods=['GET'])
@jwt_required()
def get_project():
    """Get active project files and alignment offsets."""
    try:
        user_id = get_jwt_identity()
        payload = get_project_payload()
        return jsonify(payload)
    except Exception as e:
        print(f"Error fetching project: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch project'}), 500

@app.route('/api/source-audio/<path:filename>', methods=['GET'])
@jwt_required()
def serve_source_audio(filename):
    """Serve active project source audio for waveform rendering."""
    try:
        config = load_config()
        if not config:
            return jsonify({'error': 'No active project'}), 404

        allowed = {config['beat'], *config['vocals']}
        safe_filename = os.path.basename(filename)
        if safe_filename not in allowed:
            return jsonify({'error': 'Invalid source audio file'}), 404

        filepath = Path('resources') / safe_filename
        if not filepath.exists():
            return jsonify({'error': 'Audio file not found'}), 404

        return send_file(filepath)
    except Exception as e:
        print(f"Error serving source audio: {e}")
        return jsonify({'error': 'Failed to serve source audio'}), 500

@app.route('/api/alignment/sync', methods=['POST'])
@jwt_required()
def sync_alignment():
    """Calculate suggested alignment offsets for active vocal stems."""
    try:
        config = load_config()
        if not config:
            return jsonify({'error': 'No active project'}), 400

        beat_path = Path('resources') / config['beat']
        beat, sr = librosa.load(beat_path, sr=44100, mono=False)

        vocal_lengths = []
        loaded_vocals = []
        for filename in config['vocals']:
            vocal_path = Path('resources') / filename
            vocal, _ = librosa.load(vocal_path, sr=sr, mono=False)
            loaded_vocals.append((filename, vocal))
            vocal_lengths.append(vocal.shape[-1] if np.asarray(vocal).ndim > 1 else len(vocal))

        beat_len = beat.shape[-1] if np.asarray(beat).ndim > 1 else len(beat)
        use_sequential_layout = (
            len(vocal_lengths) > 1
            and float(np.median(vocal_lengths)) < beat_len * 0.75
        )

        offsets = {}
        cursor = 0
        gap_samples = int(0.25 * sr)
        for filename, vocal in loaded_vocals:
            expected_start = cursor if use_sequential_layout else 0
            best_start = calculate_alignment(beat, vocal, sr, expected_offset=expected_start)
            offset_ms = samples_to_ms(best_start - expected_start, sr)
            offsets[filename] = max(-2000, min(2000, round(offset_ms, 1)))

            vocal_len = vocal.shape[-1] if np.asarray(vocal).ndim > 1 else len(vocal)
            cursor += vocal_len + gap_samples

        return jsonify({
            'offsets': offsets,
            'layout': 'sequential' if use_sequential_layout else 'layered'
        })
    except Exception as e:
        print(f"Error syncing alignment: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to sync alignment: {str(e)}'}), 500

@app.route('/api/alignment', methods=['POST'])
@jwt_required()
def save_alignment():
    """Persist user alignment offsets."""
    try:
        data = request.get_json() or {}
        offsets = data.get('offsets', {})
        config = load_config()
        if not config:
            return jsonify({'error': 'No active project'}), 400

        allowed = set(config['vocals'])
        clean_offsets = {
            filename: max(-2000, min(2000, float(offset_ms)))
            for filename, offset_ms in offsets.items()
            if filename in allowed
        }
        saved = save_alignment_offsets(clean_offsets)

        global mixer
        if config:
            mixer = MixGenerator(config)

        return jsonify({
            'success': True,
            'offsets': saved
        })
    except Exception as e:
        print(f"Error saving alignment: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Failed to save alignment: {str(e)}'}), 500

@app.route('/api/generate-mixes', methods=['POST'])
@jwt_required()
def generate_mixes():
    """Generate comparison mixes from uploaded or configured audio stems.
    
    Request:
        - optional sessionId to bind results to a user session
    
    Response:
        - mixA_url: URL to Mix A WAV
        - mixB_url: URL to Mix B WAV
        - paramsA: Parameters used for Mix A
        - paramsB: Parameters used for Mix B
        - resultId: persisted output result id
        - sessionId: tied processing session id
    """
    global mixer
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401

        payload = request.get_json() or {}
        session_id = payload.get('sessionId')

        processing_session = None
        if session_id:
            processing_session = ProcessingSession.query.filter_by(id=session_id, user_id=user.id).first()

        if processing_session is None:
            processing_session = (
                ProcessingSession.query.filter_by(user_id=user.id)
                .order_by(ProcessingSession.started_at.desc())
                .first()
            )

        if processing_session is None:
            return jsonify({'error': 'No active processing session found for this user.'}), 400

        active_config = None

        if mixer is None:
            active_config = load_config() or get_audio_config()
            if active_config:
                mixer = MixGenerator(active_config)
            else:
                return jsonify({
                    'error': 'Mixer not initialized. Upload a project or check audio configuration.'
                }), 400

        result = mixer.generate_comparison_mixes()

        save_audio('resources/mix_a.wav', result['mix_a'], result['sr'])
        save_audio('resources/mix_b.wav', result['mix_b'], result['sr'])

        output_result = OutputResult(
            session_id=processing_session.id,
            mix_a_path='resources/mix_a.wav',
            mix_b_path='resources/mix_b.wav',
            params_a=result['params_a'],
            params_b=result['params_b'],
            validation_a=result.get('validation_a'),
            validation_b=result.get('validation_b'),
            both_valid=bool(result.get('both_valid', False)),
        )
        db.session.add(output_result)

        processing_session.status = 'generated'
        processing_session.completed_at = datetime.utcnow()
        if 'model_confidence' in result:
            processing_session.model_confidence = float(result['model_confidence'])

        db.session.add(processing_session)
        db.session.commit()

        response = to_json_compatible({
            'mixA_url': '/api/audio/mix_a.wav',
            'mixB_url': '/api/audio/mix_b.wav',
            'paramsA': result['params_a'],
            'paramsB': result['params_b'],
            'validationA': result.get('validation_a'),
            'validationB': result.get('validation_b'),
            'bothValid': result.get('both_valid', False),
            'resultId': output_result.id,
            'sessionId': processing_session.id,
            'config': active_config or load_config(),
        })

        return jsonify(response)
    except Exception as e:
        print(f"Error generating mixes: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to generate mixes: {str(e)}'
        }), 500

@app.route('/api/audio/<filename>', methods=['GET'])
@jwt_required()
def serve_audio(filename):
    """Serve generated audio files."""
    try:
        if filename not in ['mix_a.wav', 'mix_b.wav']:
            return jsonify({'error': 'Invalid audio file'}), 404
        
        filepath = os.path.join('resources', filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Audio file not found'}), 404
        
        return send_file(filepath, mimetype='audio/wav')
    
    except Exception as e:
        print(f"Error serving audio: {e}")
        return jsonify({'error': 'Failed to serve audio'}), 500

@app.route('/api/project/clear', methods=['POST'])
@jwt_required()
def clear_project():
    """Clear active project audio files and reset the mixer."""
    global mixer
    try:
        clear_resource_audio()
        config_path = Path('audio_config.json')
        if config_path.exists():
            config_path.unlink()
        alignment_path = Path('data/alignment_offsets.json')
        if alignment_path.exists():
            alignment_path.unlink()
        mixer = None
        return jsonify({
            'success': True,
            'message': 'Active project resources cleared'
        })
    except Exception as e:
        print(f"Error clearing project: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to clear project: {str(e)}'
        }), 500

@app.route('/api/submit-feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    return feedback()

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(413)
def file_too_large(e):
    """Handle file too large error."""
    return jsonify({
        'error': 'File too large. Maximum upload size is 2GB.'
    }), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal server error'
    }), 500

# ============================================================================
# STARTUP
# ============================================================================

@app.before_request
def before_request():
    """Initialize before first request."""
    global mixer
    # Debug request path for Render logs
    try:
        print(f"[REQUEST] {request.method} {request.path}", flush=True)
    except Exception:
        pass

    auth_header = request.headers.get('Authorization')
    if request.path.startswith('/api/'):
        print(f"[AUTH HEADER] {auth_header}", flush=True)
        if auth_header:
            try:
                verify_jwt_in_request(optional=True)
                print(f"[JWT IDENTITY] {get_jwt_identity()}", flush=True)
            except Exception as exc:
                print(f"[JWT IDENTITY] invalid token: {exc}", flush=True)

    if mixer is None:
        init_mixer()
    # Trigger a throttled cleanup during normal request traffic (no-op if recently run)
    try:
        storage_cleanup.maybe_cleanup_on_request()
    except Exception:
        # Never let cleanup failures impact request handling
        pass

if __name__ == '__main__':
    print("=" * 60)
    print("AURALIS TRAINING API SERVER")
    print("=" * 60)
    
    # Initialize mixer
    if init_mixer():
        print("[OK] Mixer initialized successfully")
    else:
        print("[WARNING] Mixer not ready - run python utils/audio_config.py first")
    
    default_port = int(os.getenv('PORT', 5000))
    flask_debug = os.getenv('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes')
    frontend_url = os.getenv('FRONTEND_URL', 'https://auralis-kappa.vercel.app')

    print(f"\nStarting Flask server on http://0.0.0.0:{default_port}")
    print(f"React UI default URL: {frontend_url}")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=default_port,
        debug=flask_debug,
        use_reloader=False
    )
