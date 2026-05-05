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
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import traceback

# Add parent directory to path for Auralis imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.mix_generator import MixGenerator, to_json_compatible
from models.data_collector import log_mix_comparison
from utils.file_io import save_audio
from utils.audio_config import get_audio_config, load_config, save_config

# ============================================================================
# CONFIGURATION
# ============================================================================

app = Flask(__name__)
CORS(app)

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'ogg'}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB for local stem batches

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('resources', exist_ok=True)

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
        'message': 'This is the backend API. Open the React UI at http://127.0.0.1:5173/',
        'ui': 'http://127.0.0.1:5173/',
        'endpoints': {
            'health': '/api/health',
            'stats': '/api/stats',
            'generate_mixes': 'POST /api/generate-mixes',
            'submit_feedback': 'POST /api/submit-feedback',
            'clear_project': 'POST /api/project/clear'
        }
    })

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
        stats = get_training_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({'total': 0, 'valid': 0, 'skipped': 0})

@app.route('/api/generate-mixes', methods=['POST'])
def generate_mixes():
    """Generate comparison mixes from uploaded or configured audio stems.
    
    Request:
        - optional sourceFiles metadata from the React UI
    
    Response:
        - mixA_url: URL to Mix A WAV
        - mixB_url: URL to Mix B WAV
        - paramsA: Parameters used for Mix A
        - paramsB: Parameters used for Mix B
    """
    global mixer
    try:
        uploaded_files = request.files.getlist('files')
        active_config = None

        if uploaded_files:
            active_config = save_uploaded_project(uploaded_files)
            mixer = MixGenerator(active_config)

        # Check if mixer is initialized
        if mixer is None:
            active_config = load_config() or get_audio_config()
            if active_config:
                mixer = MixGenerator(active_config)
            else:
                return jsonify({
                    'error': 'Mixer not initialized. Upload a project or check audio configuration.'
                }), 400
        
        # Generate mixes
        result = mixer.generate_comparison_mixes()
        
        # Export mixes
        save_audio('resources/mix_a.wav', result['mix_a'], result['sr'])
        save_audio('resources/mix_b.wav', result['mix_b'], result['sr'])
        
        # Prepare response
        response = to_json_compatible({
            'mixA_url': '/api/audio/mix_a.wav',
            'mixB_url': '/api/audio/mix_b.wav',
            'paramsA': result['params_a'],
            'paramsB': result['params_b'],
            'validationA': result['validation_a'],
            'validationB': result['validation_b'],
            'bothValid': result['both_valid'],
            'config': active_config or load_config()
        })
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Error generating mixes: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to generate mixes: {str(e)}'
        }), 500

@app.route('/api/audio/<filename>', methods=['GET'])
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
def clear_project():
    """Clear active project audio files and reset the mixer."""
    global mixer
    try:
        clear_resource_audio()
        config_path = Path('audio_config.json')
        if config_path.exists():
            config_path.unlink()
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
def submit_feedback():
    """Submit user feedback on mix comparison.
    
    Request JSON:
        - choice: 'a' | 'b' | 'tie' | 'skip'
        - paramsA: Parameters for Mix A
        - paramsB: Parameters for Mix B
    
    Response:
        - success: true
        - message: Confirmation message
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        choice = data.get('choice', '').lower()
        params_a = data.get('paramsA')
        params_b = data.get('paramsB')
        
        # Validate choice
        if choice not in ['a', 'b', 'tie', 'skip']:
            return jsonify({'error': f'Invalid choice: {choice}'}), 400
        
        if not params_a or not params_b:
            return jsonify({'error': 'Missing parameters'}), 400
        
        # If skip, don't record (as per safety guidelines)
        if choice == 'skip':
            return jsonify({
                'success': True,
                'message': 'Comparison skipped (not recorded)',
                'recorded': False
            })
        
        # Get current configuration
        config = load_config()
        if not config:
            return jsonify({'error': 'Audio configuration not found'}), 400
        
        # Log the comparison
        vocals_paths = {
            Path(vf).stem: f"resources/{vf}"
            for vf in config['vocals']
        }
        
        log_mix_comparison(
            vocals_paths_dict=vocals_paths,
            beat_path=f"resources/{config['beat']}",
            params_a=params_a,
            params_b=params_b,
            preference=choice
        )
        
        return jsonify({
            'success': True,
            'message': f'Feedback recorded: Mix {choice.upper()} preferred',
            'recorded': True,
            'choice': choice
        })
    
    except Exception as e:
        print(f"Error submitting feedback: {e}")
        traceback.print_exc()
        return jsonify({
            'error': f'Failed to submit feedback: {str(e)}'
        }), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(413)
def file_too_large(e):
    """Handle file too large error."""
    return jsonify({
        'error': 'File too large. Maximum size is 100MB.'
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
    if mixer is None:
        init_mixer()

if __name__ == '__main__':
    print("=" * 60)
    print("AURALIS TRAINING API SERVER")
    print("=" * 60)
    
    # Initialize mixer
    if init_mixer():
        print("[OK] Mixer initialized successfully")
    else:
        print("[WARNING] Mixer not ready - run python utils/audio_config.py first")
    
    print("\nStarting Flask server on http://localhost:5000")
    print("React UI will be available on http://localhost:5173")
    print("\nPress Ctrl+C to stop\n")
    
    # Run server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False
    )
