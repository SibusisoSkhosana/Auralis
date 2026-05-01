import numpy as np
from scipy.signal import butter, sosfilt

# === SAFETY PARAMETERS (from MIXING_GUIDELINES.md) ===
MAX_PEAK_LINEAR = 0.95  # Absolute max before limiter (safety margin)
LIMITER_THRESHOLD = 0.85  # Limiter engages at this level
MIN_HEADROOM_DB = 1.0  # Minimum headroom after normalization

def highpass_filter(y, sr, cutoff=200):
    """Apply high-pass filter to remove mud frequencies."""
    nyquist = 0.5 * sr
    sos = butter(2, cutoff / nyquist, btype='high', output='sos')
    return sosfilt(sos, y)

def normalize_audio(y, target_db=-20, headroom_db=1.0):
    """
    Normalize audio to target level with safety headroom.
    
    IMPORTANT: This enforces safe levels to prevent over-normalization.
    After normalization, audio should have at least headroom_db of space
    before clipping.
    """
    y = np.asarray(y)
    
    # Enforce safe target range (from MIXING_GUIDELINES.md)
    target_db = np.clip(target_db, -30, -6)
    
    rms = np.sqrt(np.mean(y**2, axis=-1, keepdims=True))
    current_db = 20 * np.log10(rms + 1e-6)
    gain = target_db - current_db
    factor = 10 ** (gain / 20)
    normalized = y * factor
    
    # Check peak after normalization
    peak_linear = np.max(np.abs(normalized))
    peak_db = 20 * np.log10(peak_linear + 1e-6) if peak_linear > 0 else -np.inf
    
    # If peak is too close to clipping, scale down further
    if peak_db > (0 - headroom_db):
        reduction_db = peak_db - (0 - headroom_db) + 0.5
        reduction_factor = 10 ** (-reduction_db / 20)
        normalized *= reduction_factor
    
    return normalized

def limiter(y, threshold=0.85, makeup_gain_db=0):
    """
    Hard limiter using clipping to prevent peaks exceeding threshold.
    
    This is a SAFETY limiter - it prevents clipping, not a creative effect.
    Operates in two stages:
    1. Soft knee (tanh) for smooth onset
    2. Hard clip for absolute safety
    
    Args:
        y: Input audio
        threshold: Peak threshold (default 0.85, safe headroom to 1.0)
        makeup_gain_db: Optional makeup gain (use cautiously)
    
    Returns:
        Limited audio
    """
    y = np.asarray(y)
    
    # Hard safety clip at max_peak_linear
    y_clipped = np.clip(y, -MAX_PEAK_LINEAR, MAX_PEAK_LINEAR)
    
    # Apply soft knee limiter for smooth limiting
    # Using tanh for smooth saturation before hard clip
    y_limited = np.where(
        np.abs(y) > threshold,
        np.sign(y) * threshold * np.tanh(np.abs(y) / threshold),
        y
    )
    
    # Final hard clip as absolute safety
    y_limited = np.clip(y_limited, -MAX_PEAK_LINEAR, MAX_PEAK_LINEAR)
    
    # Optional makeup gain (use sparingly)
    if makeup_gain_db != 0:
        makeup_factor = 10 ** (makeup_gain_db / 20)
        y_limited *= makeup_factor
        y_limited = np.clip(y_limited, -MAX_PEAK_LINEAR, MAX_PEAK_LINEAR)
    
    return y_limited

def stereo_widen(y, width=0.15):
    """Apply stereo widening using Mid/Side technique."""
    y = np.asarray(y)
    y = ensure_stereo(y)
    if y.ndim != 2 or y.shape[0] != 2:
        raise ValueError(f"stereo_widen expects shape (2, N), got {y.shape}")

    mid  = (y[0] + y[1]) / 2
    side = (y[0] - y[1]) / 2
    side *= (1 + width)
    return np.vstack([mid + side, mid - side])

def ensure_stereo(audio):
    """Convert mono (N,) or already-stereo (2, N) audio to stereo (2, N)."""
    audio = np.asarray(audio)
    if audio.ndim == 1:
        return np.vstack([audio, audio])
    if audio.ndim == 2:
        if audio.shape[0] == 2:
            return audio
        if audio.shape[0] == 1:
            return np.vstack([audio[0], audio[0]])
        if audio.shape[1] == 2:
            return audio.T
        if audio.shape[1] == 1:
            return np.vstack([audio[:, 0], audio[:, 0]])
    raise ValueError(f"Unsupported audio shape {audio.shape}")

def to_channels_first(audio):
    """Always returns (2, N)."""
    if audio.ndim == 1:
        return np.stack([audio, audio], axis=0)       # (N,) → (2, N)
    if audio.shape[0] == 1:
        return np.vstack([audio, audio])              # (1, N) → (2, N)
    if audio.shape[0] == 2:
        return audio                                   # already (2, N)
    if audio.shape[1] == 2:
        return audio.T                                 # (N, 2) → (2, N)
    return audio