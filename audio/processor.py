import numpy as np
from scipy.signal import butter, sosfilt

def highpass_filter(y, sr, cutoff=200):
    nyquist = 0.5 * sr
    sos = butter(2, cutoff / nyquist, btype='high', output='sos')
    return sosfilt(sos, y)

def normalize_audio(y, target_db=-20):
    y = np.asarray(y)
    rms = np.sqrt(np.mean(y**2, axis=-1, keepdims=True))
    current_db = 20 * np.log10(rms + 1e-6)
    gain = target_db - current_db
    factor = 10 ** (gain / 20)
    return y * factor

def limiter(y, threshold=0.9):
    y = np.asarray(y)
    return np.tanh(y / threshold) * threshold

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