# data_collector.py
import json
import numpy as np
import librosa
import os
import sys

# Import stem classifier
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audio.stem_classifier import classify_stems

def extract_features(vocals, beat, sr):
    """Extract features from stems that correlate with mix decisions."""
    
    def stem_features(y):
        # Use mono for analysis
        mono = y.mean(axis=0) if y.ndim == 2 else y
        rms        = float(np.sqrt(np.mean(mono**2)))
        centroid   = float(librosa.feature.spectral_centroid(y=mono, sr=sr).mean())
        rolloff    = float(librosa.feature.spectral_rolloff(y=mono, sr=sr).mean())
        zcr        = float(librosa.feature.zero_crossing_rate(mono).mean())
        bandwidth  = float(librosa.feature.spectral_bandwidth(y=mono, sr=sr).mean())
        # Low-mid muddiness (200-400Hz energy ratio)
        stft       = np.abs(librosa.stft(mono))
        freqs      = librosa.fft_frequencies(sr=sr)
        mud_mask   = (freqs > 200) & (freqs < 400)
        muddiness  = float(stft[mud_mask].mean() / (stft.mean() + 1e-6))
        return [rms, centroid, rolloff, zcr, bandwidth, muddiness]

    v_feats = stem_features(vocals)
    b_feats = stem_features(beat)
    # Ratio features — these are what actually drive mix decisions
    rms_ratio      = v_feats[0] / (b_feats[0] + 1e-6)
    centroid_ratio = v_feats[1] / (b_feats[1] + 1e-6)

    return v_feats + b_feats + [rms_ratio, centroid_ratio]

def extract_features_sections(vocals_dict, beat, sr):
    """Extract features from multiple vocal sections and combine them.
    
    Args:
        vocals_dict: dict with keys like 'verse', 'chorus' mapping to audio arrays
        beat: beat audio array
        sr: sample rate
    
    Returns:
        combined features list with per-section analysis
    """
    b_feats = stem_features(beat)
    all_features = []
    
    # Process each vocal section
    for section_name in ['verse', 'chorus']:
        if section_name in vocals_dict:
            v_feats = stem_features(vocals_dict[section_name])
            rms_ratio = v_feats[0] / (b_feats[0] + 1e-6)
            centroid_ratio = v_feats[1] / (b_feats[1] + 1e-6)
            all_features.extend(v_feats + b_feats + [rms_ratio, centroid_ratio])
    
    return all_features

def stem_features(y):
    """Helper to extract features from a single stem."""
    mono = y.mean(axis=0) if y.ndim == 2 else y
    rms        = float(np.sqrt(np.mean(mono**2)))
    centroid   = float(librosa.feature.spectral_centroid(y=mono, sr=44100).mean())
    rolloff    = float(librosa.feature.spectral_rolloff(y=mono, sr=44100).mean())
    zcr        = float(librosa.feature.zero_crossing_rate(mono).mean())
    bandwidth  = float(librosa.feature.spectral_bandwidth(y=mono, sr=44100).mean())
    stft       = np.abs(librosa.stft(mono))
    freqs      = librosa.fft_frequencies(sr=44100)
    mud_mask   = (freqs > 200) & (freqs < 400)
    muddiness  = float(stft[mud_mask].mean() / (stft.mean() + 1e-6))
    return [rms, centroid, rolloff, zcr, bandwidth, muddiness]

def log_mix_session(vocals_paths_dict, beat_path, params_used, rating, out_file="data/mix_log.jsonl"):
    """Log a mix session to the training set."""
    vocals_dict = {}
    sr = None
    
    for section, path in vocals_paths_dict.items():
        vocals_dict[section], sr = librosa.load(path, sr=44100, mono=False)
    
    beat, _ = librosa.load(beat_path, sr=44100, mono=False)
    
    features = extract_features_sections(vocals_dict, beat, sr)

    record = {
        "features": features,
        "params": params_used,
        "rating": rating,
    }

    with open(out_file, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"Logged mix session → {out_file}")

def get_stem_identities(vocals_paths_dict, beat_path, sr=44100):
    """Classify stems by audio analysis."""
    audio_dict = {}
    
    beat, _ = librosa.load(beat_path, sr=sr, mono=False)
    audio_dict['beat.wav'] = beat.mean(axis=0) if beat.ndim == 2 else beat
    
    for section, path in vocals_paths_dict.items():
        vocals, _ = librosa.load(path, sr=sr, mono=False)
        basename = os.path.basename(path)
        audio_dict[basename] = vocals.mean(axis=0) if vocals.ndim == 2 else vocals
    
    identities = classify_stems(audio_dict, sr=sr)
    
    stem_ids = {fname: ident.to_dict() for fname, ident in identities.items()}
    
    return stem_ids


def log_mix_comparison(vocals_paths_dict, beat_path, params_a, params_b, preference, out_file="data/mix_comparisons.jsonl"):
    """Log a pairwise mix comparison with stem classifications."""
    vocals_dict = {}
    sr = 44100
    
    for section, path in vocals_paths_dict.items():
        vocals_dict[section], sr = librosa.load(path, sr=sr, mono=False)
    
    beat, _ = librosa.load(beat_path, sr=sr, mono=False)
    
    features = extract_features_sections(vocals_dict, beat, sr)
    
    # Classify stems by signal analysis
    stem_identities = get_stem_identities(vocals_paths_dict, beat_path, sr=sr)

    record = {
        "features":           features,
        "stem_identities":    stem_identities,  # NEW: audio-based classification
        "params_a":           params_a,
        "params_b":           params_b,
        "preference":         preference,  # 'a', 'b', or 'tie'
    }

    with open(out_file, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"Logged mix comparison ({preference.upper()}) → {out_file}")
    print(f"  Stem identities recorded: {list(stem_identities.keys())}")