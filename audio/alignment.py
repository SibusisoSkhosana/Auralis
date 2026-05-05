"""Lightweight audio alignment helpers for Auralis."""

from pathlib import Path
import json

import numpy as np


ALIGNMENT_FILE = Path("data/alignment_offsets.json")


def to_mono(audio):
    """Convert channel-first/channel-last audio to mono."""
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim == 1:
        return audio
    if audio.ndim == 2:
        if audio.shape[0] <= 2:
            return np.mean(audio, axis=0)
        if audio.shape[1] <= 2:
            return np.mean(audio, axis=1)
    return audio.reshape(-1)


def detect_start(audio, sr, threshold_ratio=0.08, frame_ms=20, hop_ms=10):
    """Detect the first energetic frame in an audio signal."""
    mono = to_mono(audio)
    frame = max(1, int(sr * frame_ms / 1000))
    hop = max(1, int(sr * hop_ms / 1000))

    if mono.size < frame:
        return 0

    frames = np.lib.stride_tricks.sliding_window_view(mono, frame)[::hop]
    energy = np.sqrt(np.mean(frames * frames, axis=1))
    if energy.size == 0:
        return 0

    threshold = max(float(np.max(energy)) * threshold_ratio, 1e-5)
    active = np.flatnonzero(energy >= threshold)
    if active.size == 0:
        return 0

    return int(active[0] * hop)


def _amplitude_envelope(audio, sr, hop_ms=20):
    mono = np.abs(to_mono(audio))
    hop = max(1, int(sr * hop_ms / 1000))
    trim = (mono.size // hop) * hop
    if trim == 0:
        return np.zeros(1, dtype=np.float32)

    envelope = mono[:trim].reshape(-1, hop).mean(axis=1)
    envelope = envelope - float(np.mean(envelope))
    std = float(np.std(envelope))
    if std > 1e-8:
        envelope = envelope / std
    return envelope.astype(np.float32)


def calculate_alignment(beat, vocal, sr, expected_offset=0, search_ms=2000):
    """Estimate a vocal timing adjustment against the beat.

    Returns an offset in samples. Positive values delay the vocal; negative
    values move it earlier. The search is intentionally bounded for stable,
    producer-friendly fine tuning rather than full arrangement detection.
    """
    vocal_start = detect_start(vocal, sr)
    search_samples = int(sr * search_ms / 1000)
    expected_offset = int(expected_offset)

    beat_mono = to_mono(beat)
    vocal_mono = to_mono(vocal)
    vocal_active = vocal_mono[vocal_start:]
    if vocal_active.size == 0 or beat_mono.size == 0:
        return 0

    max_window = min(vocal_active.size, int(sr * 12), beat_mono.size)
    if max_window < int(sr * 0.25):
        return 0

    vocal_window = vocal_active[:max_window]
    best_offset = 0
    best_score = -np.inf
    step = max(1, int(sr * 0.02))

    expected_active_offset = expected_offset + vocal_start

    for offset in range(expected_active_offset - search_samples, expected_active_offset + search_samples + 1, step):
        beat_start = max(0, offset)
        vocal_start_in_window = max(0, -offset)
        available = min(
            vocal_window.size - vocal_start_in_window,
            beat_mono.size - beat_start,
            max_window,
        )
        if available < int(sr * 0.25):
            continue

        beat_segment = beat_mono[beat_start:beat_start + available]
        vocal_segment = vocal_window[vocal_start_in_window:vocal_start_in_window + available]
        beat_env = _amplitude_envelope(beat_segment, sr)
        vocal_env = _amplitude_envelope(vocal_segment, sr)
        size = min(beat_env.size, vocal_env.size)
        if size < 4:
            continue

        score = float(np.dot(beat_env[:size], vocal_env[:size]) / size)
        if score > best_score:
            best_score = score
            best_offset = offset

    return int(best_offset - vocal_start)


def apply_offset(audio, offset, target_len=None):
    """Apply an offset by padding or trimming without modifying source audio."""
    audio = np.asarray(audio)
    offset = int(offset)

    if audio.ndim == 1:
        working = audio.reshape(1, -1)
        squeeze = True
    else:
        working = audio
        squeeze = False

    channels = working.shape[0]
    if target_len is None:
        target_len = working.shape[1] + max(0, offset)

    output = np.zeros((channels, target_len), dtype=working.dtype)

    source_start = max(0, -offset)
    target_start = max(0, offset)
    length = min(working.shape[1] - source_start, target_len - target_start)
    if length > 0:
        output[:, target_start:target_start + length] = working[:, source_start:source_start + length]

    return output[0] if squeeze else output


def load_alignment_offsets(path=ALIGNMENT_FILE):
    """Load saved alignment offsets in milliseconds."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        return {str(key): float(value) for key, value in data.items()}
    except Exception:
        return {}


def save_alignment_offsets(offsets, path=ALIGNMENT_FILE):
    """Persist alignment offsets in milliseconds."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {str(key): float(value) for key, value in offsets.items()}
    with open(path, "w") as f:
        json.dump(clean, f, indent=2)
    return clean


def samples_to_ms(samples, sr):
    return float(samples) * 1000.0 / float(sr)


def ms_to_samples(ms, sr):
    return int(round(float(ms) * float(sr) / 1000.0))
