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

# Default parameters
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
    """Create variations of parameters for comparison mixing."""
    if seed is not None:
        np.random.seed(seed)
    
    varied = params.copy()
    
    # Vary common params slightly
    varied["beat_target_db"] = float(np.clip(
        varied["beat_target_db"] + np.random.uniform(-1.5, 1.5), -24, -6))
    varied["gain_balance"] = float(np.clip(
        varied["gain_balance"] + np.random.uniform(-0.2, 0.2), 0.8, 1.8))
    varied["mud_threshold"] = float(np.clip(
        varied["mud_threshold"] + np.random.uniform(-0.1, 0.1), 0.1, 0.6))
    
    # Vary per-vocal params
    for section_name in vocal_files:
        section_key = Path(section_name).stem
        
        key_db = f"{section_key}_vocal_target_db"
        if key_db in varied:
            varied[key_db] = float(np.clip(
                varied[key_db] + np.random.uniform(-2, 2), -30, -10))
        
        key_hp = f"{section_key}_highpass_cutoff"
        if key_hp in varied:
            varied[key_hp] = float(np.clip(
                varied[key_hp] + np.random.uniform(-40, 40), 60, 400))
        
        key_width = f"{section_key}_stereo_width"
        if key_width in varied:
            varied[key_width] = float(np.clip(
                varied[key_width] + np.random.uniform(-0.02, 0.02), 0, 0.3))
    
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
    """Process audio stems with given parameters and return mixed audio."""
    
    # Extract params
    beat_target_db = params["beat_target_db"]
    gain_balance = params["gain_balance"]
    mud_threshold = params["mud_threshold"]
    
    # Process beat
    beat_proc = normalize_audio(beat.copy(), target_db=beat_target_db)
    beat_proc = to_channels_first(beat_proc)
    
    # Process each vocal section
    processed_vocals = {}
    for section_name in vocals_dict.keys():
        vocals = vocals_dict[section_name].copy()
        
        vocal_target_db = params.get(f"{section_name}_vocal_target_db", -20)
        highpass_cutoff = params.get(f"{section_name}_highpass_cutoff", 200)
        stereo_width = params.get(f"{section_name}_stereo_width", 0.03)
        
        # Check muddiness
        v_mud = detect_muddiness(vocals[0], sr)
        
        if v_mud > mud_threshold:
            vocals = highpass_filter(vocals, sr, cutoff=highpass_cutoff)
        
        vocals = to_channels_first(vocals)
        vocals = normalize_audio(vocals, target_db=vocal_target_db)
        vocals = stereo_widen(vocals, width=stereo_width)
        vocals = to_channels_first(vocals)
        
        processed_vocals[section_name] = vocals
    
    # Combine all vocals
    combined_vocals = None
    for section, vocals in processed_vocals.items():
        if combined_vocals is None:
            combined_vocals = vocals.copy()
        else:
            min_len = min(combined_vocals.shape[1], vocals.shape[1])
            combined_vocals[:, :min_len] += vocals[:, :min_len]
    
    # Gain balance
    if combined_vocals is not None:
        vocals_rms = float(np.sqrt(np.mean(combined_vocals ** 2)))
        beat_rms = float(np.sqrt(np.mean(beat_proc ** 2)))
        
        if vocals_rms > beat_rms:
            beat_proc *= gain_balance
        else:
            combined_vocals *= gain_balance
        
        min_len = min(combined_vocals.shape[1], beat_proc.shape[1])
        mix = combined_vocals[:, :min_len] + beat_proc[:, :min_len]
        mix = limiter(mix, threshold=0.9)
    else:
        mix = beat_proc
    
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

# Export both mixes
save_audio("resources/mix_a.wav", mix_a, sr)
save_audio("resources/mix_b.wav", mix_b, sr)
print("\n Exported: mix_a.wav and mix_b.wav")

# Save pending comparison for rating
try:
    PENDING_FILE = "data/pending_rating.json"
    os.makedirs("data", exist_ok=True)
    
    with open(PENDING_FILE, "w") as f:
        vocals_paths = {Path(vf).stem: f"resources/{vf}" for vf in vocal_files}
        json.dump({
            "vocals_paths": vocals_paths,
            "beat_path": f"resources/{beat_file}",
            "params_a": params_a,
            "params_b": params_b
        }, f, indent=2)
    
    print("\n" + "="*50)
    print("READY FOR COMPARISON RATING")
    print("="*50)
    print("\nListen to the two mixes:")
    print("  - resources/mix_a.wav (Mix A)")
    print("  - resources/mix_b.wav (Mix B)")
    print("\nThen rate which is better:")
    print("  python rate_mix.py a   # Mix A is better")
    print("  python rate_mix.py b   # Mix B is better")
    print("  python rate_mix.py tie # They're equal")
   
except Exception as e:
    print(f"ERROR saving pending comparison: {e}")