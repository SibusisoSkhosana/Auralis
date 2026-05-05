"""Mix generation utility for A/B comparison interface."""

import os
import librosa
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio.analyzer import detect_muddiness
from audio.processor import (
    highpass_filter,
    normalize_audio,
    limiter,
    stereo_widen,
    to_channels_first
)
from audio.validator import MixValidator
from audio.alignment import load_alignment_offsets, ms_to_samples
from utils.file_io import save_audio
from utils.audio_config import get_audio_config

TARGET_SR = 44100

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


class MixGenerator:
    """Generates A/B comparison mixes from audio stems."""
    
    def __init__(self, config=None):
        """Initialize mixer with audio configuration."""
        if config is None:
            config = get_audio_config()
        
        if config is None:
            raise RuntimeError("Audio configuration not found. Run: python utils/audio_config.py")
        
        self.beat_file = config["beat"]
        self.vocal_files = config["vocals"]
        self.sr = TARGET_SR
        self.alignment_offsets = load_alignment_offsets()
        
        # Load beat
        beat_path = f"resources/{self.beat_file}"
        if not os.path.exists(beat_path):
            raise FileNotFoundError(f"Beat file not found: {beat_path}")
        
        self.beat, self.sr = librosa.load(beat_path, sr=self.sr, mono=False)
        self.beat = to_channels_first(self.beat)
        
        # Load vocals
        self.vocals_dict = {}
        self.section_files = {}
        for vocal_file in self.vocal_files:
            vocal_path = f"resources/{vocal_file}"
            section_name = Path(vocal_file).stem
            
            if os.path.exists(vocal_path):
                vocals, _ = librosa.load(vocal_path, sr=self.sr, mono=False)
                self.vocals_dict[section_name] = to_channels_first(vocals)
                self.section_files[section_name] = vocal_file
        
        # Load model if available
        self.model = None
        self.scaler = None
        self.param_keys = None
        self._load_model()
        
        # Default parameters (conservative, safe ranges)
        self.default_params = {
            "beat_target_db": -14,
            "gain_balance": 1.2,
            "mud_threshold": 0.3,
        }
        
        # Add per-vocal-file parameters
        for vocal_file in self.vocal_files:
            section_name = Path(vocal_file).stem
            self.default_params[f"{section_name}_vocal_target_db"] = -20
            self.default_params[f"{section_name}_highpass_cutoff"] = 200
            self.default_params[f"{section_name}_stereo_width"] = 0.03

    def _combine_vocals(self, processed_vocals, beat_len):
        """Combine vocal material without truncating the beat.

        Full-length stems are layered from the start. Short clips are placed
        sequentially, which matches exported takes/phrases from the UI workflow.
        """
        if not processed_vocals:
            return None

        vocal_items = list(processed_vocals.items())
        lengths = [vocals.shape[1] for _, vocals in vocal_items]
        use_sequential_layout = (
            len(vocal_items) > 1
            and float(np.median(lengths)) < beat_len * 0.75
        )

        combined = np.zeros((2, beat_len), dtype=np.float32)

        if use_sequential_layout:
            cursor = 0
            gap_samples = int(0.25 * self.sr)

            for section_name, vocals in vocal_items:
                if cursor >= beat_len:
                    break

                filename = self.section_files.get(section_name, f"{section_name}.wav")
                offset_samples = ms_to_samples(self.alignment_offsets.get(filename, 0), self.sr)
                start = max(0, cursor + offset_samples)
                source_start = max(0, -(cursor + offset_samples))
                if start >= beat_len or source_start >= vocals.shape[1]:
                    cursor += vocals.shape[1] + gap_samples
                    continue

                clip_len = min(vocals.shape[1] - source_start, beat_len - start)
                combined[:, start:start + clip_len] += vocals[:, source_start:source_start + clip_len]
                cursor += vocals.shape[1] + gap_samples
        else:
            for section_name, vocals in vocal_items:
                filename = self.section_files.get(section_name, f"{section_name}.wav")
                offset_samples = ms_to_samples(self.alignment_offsets.get(filename, 0), self.sr)
                start = max(0, offset_samples)
                source_start = max(0, -offset_samples)
                if start >= beat_len or source_start >= vocals.shape[1]:
                    continue

                clip_len = min(vocals.shape[1] - source_start, beat_len - start)
                combined[:, start:start + clip_len] += vocals[:, source_start:source_start + clip_len]

        return combined
    
    def _load_model(self):
        """Load pre-trained model if available."""
        try:
            import joblib
            self.model = joblib.load("models/param_predictor.pkl")
            self.scaler = joblib.load("models/scaler.pkl")
            self.param_keys = joblib.load("models/param_keys.pkl")
        except Exception:
            self.model = None
    
    def vary_params(self, params, seed=None):
        """
        Create conservative variations of parameters for comparison mixing.
        
        From MIXING_GUIDELINES.md:
        - Parameter variation must be small and controlled
        - Limit randomness to prevent instability
        - Only vary within safe ranges
        """
        if seed is not None:
            np.random.seed(seed)
        
        varied = params.copy()
        
        # Vary common params - CONSERVATIVE ranges
        varied["beat_target_db"] = float(np.clip(
            varied["beat_target_db"] + np.random.uniform(-0.8, 0.8),
            -24, -6))
        
        varied["gain_balance"] = float(np.clip(
            varied["gain_balance"] + np.random.uniform(-0.1, 0.1),
            0.9, 1.5))
        
        varied["mud_threshold"] = float(np.clip(
            varied["mud_threshold"] + np.random.uniform(-0.05, 0.05),
            0.15, 0.5))
        
        # Vary per-vocal params
        for section_name in self.vocals_dict.keys():
            section_key = section_name
            
            key_db = f"{section_key}_vocal_target_db"
            if key_db in varied:
                varied[key_db] = float(np.clip(
                    varied[key_db] + np.random.uniform(-0.8, 0.8),
                    -28, -12))
            
            key_hp = f"{section_key}_highpass_cutoff"
            if key_hp in varied:
                varied[key_hp] = float(np.clip(
                    varied[key_hp] + np.random.uniform(-20, 20),
                    80, 350))
            
            key_width = f"{section_key}_stereo_width"
            if key_width in varied:
                varied[key_width] = float(np.clip(
                    varied[key_width] + np.random.uniform(-0.01, 0.01),
                    0.0, 0.15))
        
        return varied
    
    def _get_base_params(self):
        """Get base parameters, using model prediction if available."""
        if self.model is None:
            return self.default_params.copy()
        
        # Use model prediction if available
        from models.data_collector import extract_features_sections
        
        try:
            features = extract_features_sections(self.vocals_dict, self.beat, self.sr)
            X = self.scaler.transform([features])
            predicted = dict(zip(self.param_keys, self.model.predict(X)[0]))
            
            params_base = {}
            params_base["beat_target_db"] = float(np.clip(
                predicted.get("beat_target_db", -14), -24, -6))
            params_base["gain_balance"] = float(np.clip(
                predicted.get("gain_balance", 1.2), 0.8, 1.8))
            params_base["mud_threshold"] = float(np.clip(
                predicted.get("mud_threshold", 0.3), 0.1, 0.6))
            
            for section_name in self.vocals_dict.keys():
                params_base[f"{section_name}_vocal_target_db"] = float(np.clip(
                    predicted.get(f"{section_name}_vocal_target_db", -20), -30, -10))
                params_base[f"{section_name}_highpass_cutoff"] = float(np.clip(
                    predicted.get(f"{section_name}_highpass_cutoff", 200), 60, 400))
                params_base[f"{section_name}_stereo_width"] = float(np.clip(
                    predicted.get(f"{section_name}_stereo_width", 0.03), 0, 0.3))
            
            return params_base
        except Exception:
            return self.default_params.copy()
    
    def process_mix(self, beat, vocals_dict, params):
        """
        Process audio stems with given parameters and return mixed audio.
        
        ENFORCES MIXING_GUIDELINES.md processing order:
        1. Normalize input
        2. Apply subtractive EQ (remove mud)
        3. Apply gain staging (carefully with headroom)
        4. Combine and balance
        5. Apply limiter LAST
        """
        
        beat_target_db = params["beat_target_db"]
        gain_balance = params["gain_balance"]
        mud_threshold = params["mud_threshold"]
        
        # STEP 1: Process beat with headroom
        beat_proc = beat.copy()
        beat_proc = normalize_audio(beat_proc, target_db=beat_target_db, headroom_db=2.0)
        beat_proc = to_channels_first(beat_proc)
        
        # STEP 2: Process each vocal section
        processed_vocals = {}
        for section_name in vocals_dict.keys():
            vocals = vocals_dict[section_name].copy()
            
            vocal_target_db = params.get(f"{section_name}_vocal_target_db", -20)
            highpass_cutoff = params.get(f"{section_name}_highpass_cutoff", 200)
            stereo_width = params.get(f"{section_name}_stereo_width", 0.03)
            
            # Check muddiness
            v_mud = detect_muddiness(vocals[0] if vocals.ndim > 1 else vocals, self.sr)
            
            # Apply subtractive EQ (remove mud carefully)
            if v_mud > mud_threshold:
                vocals = highpass_filter(vocals, self.sr, cutoff=highpass_cutoff)
            
            vocals = to_channels_first(vocals)
            
            # Normalize with headroom preservation
            vocals = normalize_audio(vocals, target_db=vocal_target_db, headroom_db=2.0)
            
            # Apply stereo width (subtle only)
            vocals = stereo_widen(vocals, width=stereo_width)
            vocals = to_channels_first(vocals)
            
            processed_vocals[section_name] = vocals
        
        # STEP 3: Combine all vocals across the full beat timeline
        combined_vocals = self._combine_vocals(processed_vocals, beat_proc.shape[1])
        
        # STEP 4: Gain balance with headroom protection
        if combined_vocals is not None:
            vocals_peak = float(np.max(np.abs(combined_vocals)))
            beat_peak = float(np.max(np.abs(beat_proc)))
            
            if vocals_peak > 1e-6 and beat_peak > 1e-6:
                vocals_rms = float(np.sqrt(np.mean(combined_vocals ** 2)))
                beat_rms = float(np.sqrt(np.mean(beat_proc ** 2)))
                
                if vocals_rms > beat_rms and gain_balance > 1.0:
                    beat_proc *= gain_balance
                elif beat_rms > vocals_rms and gain_balance < 1.0:
                    combined_vocals *= gain_balance
            
            mix = combined_vocals + beat_proc
            
            # STEP 5: Apply limiter LAST
            mix = limiter(mix, threshold=0.85)
        else:
            mix = beat_proc
            mix = limiter(mix, threshold=0.85)
        
        return mix
    
    def generate_comparison_mixes(self):
        """Generate Mix A and Mix B for comparison.
        
        Returns:
            dict with keys: mix_a, mix_b, params_a, params_b, validation_a, validation_b, both_valid
        """
        
        # Get base parameters
        params_base = self._get_base_params()
        
        # Generate variations
        params_a = self.vary_params(params_base, seed=42)
        params_b = self.vary_params(params_base, seed=43)
        
        # Process mixes
        beat_a = self.beat.copy()
        beat_b = self.beat.copy()
        
        vocals_dict_a = {k: v.copy() for k, v in self.vocals_dict.items()}
        vocals_dict_b = {k: v.copy() for k, v in self.vocals_dict.items()}
        
        mix_a = self.process_mix(beat_a, vocals_dict_a, params_a)
        mix_b = self.process_mix(beat_b, vocals_dict_b, params_b)
        
        # Validate mixes
        validator = MixValidator()
        validation_a = validator.validate_mix(mix_a, "MIX A")
        validation_b = validator.validate_mix(mix_b, "MIX B")
        
        both_valid = validation_a['is_valid'] and validation_b['is_valid']
        at_least_one_good = validation_a['is_good'] or validation_b['is_good']
        
        return {
            'mix_a': mix_a,
            'mix_b': mix_b,
            'params_a': to_json_compatible(params_a),
            'params_b': to_json_compatible(params_b),
            'validation_a': validation_a,
            'validation_b': validation_b,
            'both_valid': both_valid,
            'at_least_one_good': at_least_one_good,
            'sr': self.sr
        }
