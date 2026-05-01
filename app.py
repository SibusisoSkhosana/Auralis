import os
import librosa
import json
import numpy as np
import sys
from pathlib import Path
from audio.analyzer import detect_muddiness
from audio.processor import (
    highpass_filter,
    normalize_audio,
    limiter,
    stereo_widen,
    to_channels_first
)
from audio.validator import MixValidator
from utils.file_io import save_audio
from models.data_collector import extract_features_sections, log_mix_session
from utils.audio_config import get_audio_config

TARGET_SR = 44100

config = get_audio_config()

if config is None:
    print("Error: Audio configuration not found. Run: python utils/audio_config.py")
    sys.exit(1)

beat_file = config["beat"]
vocal_files = config["vocals"]

def to_json_compatible(value):
    """Convert NumPy values into strict JSON-compatible Python values."""
    if isinstance(value, dict):
        return {key: to_json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_compatible(item) for item in value]
    if isinstance(value, np.ndarray):
        return to_json_compatible(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
        return value if np.isfinite(value) else None
    if isinstance(value, float):
        return value if np.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value

# Default parameters (conservative, safe ranges from MIXING_GUIDELINES.md)
DEFAULT_PARAMS = {
    "beat_target_db": -14,
    "gain_balance": 1.2,
    "mud_threshold": 0.3,
}

# Add per-vocal-file parameters (using filename stem as section name)
for vocal_file in vocal_files:
    section_name = Path(vocal_file).stem
    DEFAULT_PARAMS[f"{section_name}_vocal_target_db"] = -20
    DEFAULT_PARAMS[f"{section_name}_highpass_cutoff"] = 200
    DEFAULT_PARAMS[f"{section_name}_stereo_width"] = 0.03

def vary_params(params, seed=None):
    """
    Create conservative variations of parameters for comparison mixing.
    
    IMPORTANT: From MIXING_GUIDELINES.md
    - Parameter variation must be small and controlled
    - Limit randomness to prevent instability
    - Only vary within safe ranges
    """
    if seed is not None:
        np.random.seed(seed)
    
    varied = params.copy()
    
    # Vary common params - CONSERVATIVE ranges (from MIXING_GUIDELINES.md)
    # Rule: Small variations only, avoid extreme changes
    
    varied["beat_target_db"] = float(np.clip(
        varied["beat_target_db"] + np.random.uniform(-0.8, 0.8),  # REDUCED from ±1.5 to ±0.8
        -24, -6))
    
    varied["gain_balance"] = float(np.clip(
        varied["gain_balance"] + np.random.uniform(-0.1, 0.1),  # REDUCED from ±0.2 to ±0.1
        0.9, 1.5))  # TIGHTENED from [0.8, 1.8]
    
    varied["mud_threshold"] = float(np.clip(
        varied["mud_threshold"] + np.random.uniform(-0.05, 0.05),  # REDUCED from ±0.1 to ±0.05
        0.15, 0.5))  # TIGHTENED from [0.1, 0.6]
    
    # Vary per-vocal params - CONSERVATIVE ranges
    for section_name in vocal_files:
        section_key = Path(section_name).stem
        
        key_db = f"{section_key}_vocal_target_db"
        if key_db in varied:
            varied[key_db] = float(np.clip(
                varied[key_db] + np.random.uniform(-0.8, 0.8),  # REDUCED from ±2 to ±0.8
                -28, -12))  # TIGHTENED from [-30, -10]
        
        key_hp = f"{section_key}_highpass_cutoff"
        if key_hp in varied:
            varied[key_hp] = float(np.clip(
                varied[key_hp] + np.random.uniform(-20, 20),  # REDUCED from ±40 to ±20
                80, 350))  # TIGHTENED from [60, 400]
        
        key_width = f"{section_key}_stereo_width"
        if key_width in varied:
            varied[key_width] = float(np.clip(
                varied[key_width] + np.random.uniform(-0.01, 0.01),  # REDUCED from ±0.02 to ±0.01
                0.0, 0.15))  # TIGHTENED from [0, 0.3]
    
    return varied

try:
    import joblib
    model = joblib.load("models/param_predictor.pkl")
    scaler = joblib.load("models/scaler.pkl")
    param_keys = joblib.load("models/param_keys.pkl")
    USE_MODEL = True
except Exception:
    USE_MODEL = False
vocals_dict = {}
sr = None

beat_path = f"resources/{beat_file}"
if not os.path.exists(beat_path):
    print(f"Error: Beat file not found: {beat_path}")
    sys.exit(1)

beat, sr = librosa.load(beat_path, sr=TARGET_SR, mono=False)
beat = to_channels_first(beat)

for vocal_file in vocal_files:
    vocal_path = f"resources/{vocal_file}"
    section_name = Path(vocal_file).stem
    
    if os.path.exists(vocal_path):
        vocals_dict[section_name], sr = librosa.load(vocal_path, sr=TARGET_SR, mono=False)
        vocals_dict[section_name] = to_channels_first(vocals_dict[section_name])

if USE_MODEL:
    features = extract_features_sections(vocals_dict, beat, sr)
    X = scaler.transform([features])
    predicted = dict(zip(param_keys, model.predict(X)[0]))
    
    params_base = {}
    params_base["beat_target_db"] = float(np.clip(predicted.get("beat_target_db", -14), -24, -6))
    params_base["gain_balance"] = float(np.clip(predicted.get("gain_balance", 1.2), 0.8, 1.8))
    params_base["mud_threshold"] = float(np.clip(predicted.get("mud_threshold", 0.3), 0.1, 0.6))
    
    for section_name in vocals_dict.keys():
        params_base[f"{section_name}_vocal_target_db"] = float(np.clip(
            predicted.get(f"{section_name}_vocal_target_db", -20), -30, -10))
        params_base[f"{section_name}_highpass_cutoff"] = float(np.clip(
            predicted.get(f"{section_name}_highpass_cutoff", 200), 60, 400))
        params_base[f"{section_name}_stereo_width"] = float(np.clip(
            predicted.get(f"{section_name}_stereo_width", 0.03), 0, 0.3))
    
    params_a = vary_params(params_base, seed=42)
    params_b = vary_params(params_base, seed=43)
else:
    params_a = vary_params(DEFAULT_PARAMS.copy(), seed=42)
    params_b = vary_params(DEFAULT_PARAMS.copy(), seed=43)

def process_mix(beat, vocals_dict, params, sr, mix_name):
    """
    Process audio stems with given parameters and return mixed audio.
    
    ENFORCES MIXING_GUIDELINES.md processing order:
    1. Normalize input
    2. Apply subtractive EQ (remove mud)
    3. Apply gain staging (carefully with headroom)
    4. Combine and balance
    5. Apply limiter LAST
    """
    
    # Extract params
    beat_target_db = params["beat_target_db"]
    gain_balance = params["gain_balance"]
    mud_threshold = params["mud_threshold"]
    
    # ========== STEP 1: Process beat with headroom ==========
    beat_proc = beat.copy()
    beat_proc = normalize_audio(beat_proc, target_db=beat_target_db, headroom_db=2.0)
    beat_proc = to_channels_first(beat_proc)
    
    # ========== STEP 2: Process each vocal section ==========
    processed_vocals = {}
    for section_name in vocals_dict.keys():
        vocals = vocals_dict[section_name].copy()
        
        vocal_target_db = params.get(f"{section_name}_vocal_target_db", -20)
        highpass_cutoff = params.get(f"{section_name}_highpass_cutoff", 200)
        stereo_width = params.get(f"{section_name}_stereo_width", 0.03)
        
        # Check muddiness
        v_mud = detect_muddiness(vocals[0] if vocals.ndim > 1 else vocals, sr)
        
        # STEP 2A: Apply subtractive EQ (remove mud carefully)
        if v_mud > mud_threshold:
            vocals = highpass_filter(vocals, sr, cutoff=highpass_cutoff)
        
        vocals = to_channels_first(vocals)
        
        # STEP 2B: Normalize with headroom preservation
        vocals = normalize_audio(vocals, target_db=vocal_target_db, headroom_db=2.0)
        
        # STEP 2C: Apply stereo width (subtle only)
        vocals = stereo_widen(vocals, width=stereo_width)
        vocals = to_channels_first(vocals)
        
        processed_vocals[section_name] = vocals
    
    # ========== STEP 3: Combine all vocals ==========
    combined_vocals = None
    for section, vocals in processed_vocals.items():
        if combined_vocals is None:
            combined_vocals = vocals.copy()
        else:
            min_len = min(combined_vocals.shape[1], vocals.shape[1])
            combined_vocals[:, :min_len] += vocals[:, :min_len]
    
    # ========== STEP 4: Gain balance with headroom protection ==========
    if combined_vocals is not None:
        # Check levels before balancing
        vocals_peak = float(np.max(np.abs(combined_vocals)))
        beat_peak = float(np.max(np.abs(beat_proc)))
        
        # Only apply gain if peaks are significantly different
        # Avoid aggressive gain staging
        if vocals_peak > 1e-6 and beat_peak > 1e-6:
            vocals_rms = float(np.sqrt(np.mean(combined_vocals ** 2)))
            beat_rms = float(np.sqrt(np.mean(beat_proc ** 2)))
            
            if vocals_rms > beat_rms and gain_balance > 1.0:
                # Vocals are too loud - scale beat up instead of scaling vocals down
                beat_proc *= gain_balance
            elif beat_rms > vocals_rms and gain_balance < 1.0:
                # Beat is too loud - scale vocals up
                combined_vocals *= gain_balance
        
        # Combine at equal lengths
        min_len = min(combined_vocals.shape[1], beat_proc.shape[1])
        mix = combined_vocals[:, :min_len] + beat_proc[:, :min_len]
        
        # ========== STEP 5: Apply limiter LAST ==========
        mix = limiter(mix, threshold=0.85)
    else:
        mix = beat_proc
        mix = limiter(mix, threshold=0.85)
    
    return mix

# Generate both mixes
print("\n" + "="*50)
print("GENERATING COMPARISON MIXES")
print("="*50)

# Load fresh copies of stems for processing
print("\nLoading stems for processing...")
beat_proc = beat.copy()
vocals_dict_a = {}
vocals_dict_b = {}

for section_name in vocals_dict.keys():
    vocals_dict_a[section_name] = vocals_dict[section_name].copy()
    vocals_dict_b[section_name] = vocals_dict[section_name].copy()

mix_a = process_mix(beat_proc, vocals_dict_a, params_a, sr, "MIX A")
mix_b = process_mix(beat_proc, vocals_dict_b, params_b, sr, "MIX B")

# ========== VALIDATE MIXES (from MIXING_GUIDELINES.md) ==========
print("\n" + "="*60)
print("VALIDATING MIXES")
print("="*60)

validator = MixValidator()
validation_a = validator.validate_mix(mix_a, "MIX A")
validation_b = validator.validate_mix(mix_b, "MIX B")

# Print detailed validation reports
print(validator.format_validation_report(validation_a))
print(validator.format_validation_report(validation_b))

# Check if both mixes are valid
both_valid = validation_a['is_valid'] and validation_b['is_valid']
at_least_one_good = validation_a['is_good'] or validation_b['is_good']

if not both_valid:
    print("  WARNING: One or more mixes are INVALID")
    if not at_least_one_good:
        print("\n" + "!"*60)
        print(" SKIP TRAINING: Both mixes are poor quality")
        print("   Neither mix will be logged to training data.")
        print("   Reason: Prevent destructive learning from bad outputs")
        print("   (from MIXING_GUIDELINES.md rule #6)")
        print("!"*60)
        
        # Still export mixes for manual inspection, but don't save pending rating
        save_audio("resources/mix_a.wav", mix_a, sr)
        save_audio("resources/mix_b.wav", mix_b, sr)
        print("\n[INFO] Mixes exported for inspection: mix_a.wav and mix_b.wav")
        print("  (These will NOT be used for training)")
        
        # Create a SKIP marker file
        SKIP_FILE = "data/last_comparison_skipped.json"
        os.makedirs("data", exist_ok=True)
        with open(SKIP_FILE, "w") as f:
            json.dump(to_json_compatible({
                "reason": "Both mixes invalid - avoiding negative reinforcement",
                "validation_a": validation_a,
                "validation_b": validation_b,
                "timestamp": str(np.datetime64('now'))
            }), f, indent=2, allow_nan=False)
        
        sys.exit(0)
    else:
        print("\n  [WARNING] One mix is acceptable for training, the other is poor.")
else:
    print("\n[OK] Both mixes are VALID - safe to proceed with training")

# Export both mixes
save_audio("resources/mix_a.wav", mix_a, sr)
save_audio("resources/mix_b.wav", mix_b, sr)
print("\n[OK] Exported: mix_a.wav and mix_b.wav")

# Save pending comparison for rating
try:
    PENDING_FILE = "data/pending_rating.json"
    os.makedirs("data", exist_ok=True)
    
    vocals_paths = {Path(vf).stem: f"resources/{vf}" for vf in vocal_files}
    pending_payload = to_json_compatible({
        "vocals_paths": vocals_paths,
        "beat_path": f"resources/{beat_file}",
        "params_a": params_a,
        "params_b": params_b,
        "validation_a": validation_a,
        "validation_b": validation_b,
        "both_valid": both_valid
    })

    pending_tmp_file = f"{PENDING_FILE}.tmp"
    with open(pending_tmp_file, "w") as f:
        json.dump(pending_payload, f, indent=2, allow_nan=False)
    os.replace(pending_tmp_file, PENDING_FILE)
    
    print("\n" + "="*60)
    print("READY FOR COMPARISON RATING")
    print("="*60)
    print("\nListen to the two mixes:")
    print("  - resources/mix_a.wav (Mix A)")
    print("  - resources/mix_b.wav (Mix B)")
    print("\nThen rate which is better:")
    print("  python rate_mix.py a   # Mix A is better")
    print("  python rate_mix.py b   # Mix B is better")
    print("  python rate_mix.py tie # They're equal")
    print("\n  python rate_mix.py skip # Skip this comparison (both mixes are bad)")
    print("="*60)
   
except Exception as e:
    print(f"ERROR saving pending comparison: {e}")
