import librosa
import numpy as np
import soundfile as sf


def load_audio(path):
    y, sr = librosa.load(path, sr=None, mono=True)
    return np.asarray(y).flatten(), sr


def to_stereo(y):
    y = np.asarray(y)
    if y.ndim == 1:
        return np.vstack([y, y])
    if y.ndim == 2:
        if y.shape[0] == 2:
            return y
        if y.shape[0] == 1:
            return np.vstack([y[0], y[0]])
        if y.shape[1] == 2:
            return y.T
        if y.shape[1] == 1:
            return np.vstack([y[:, 0], y[:, 0]])
    raise ValueError('Unsupported audio shape {}'.format(y.shape))

def save_audio(path, audio, sr):
    """Save audio to file. Expects (2, N) or (1, N), converts to (N, channels) for soundfile."""
    if audio.ndim == 2:
        audio = audio.T  # (2, N) → (N, 2)
    sf.write(path, audio, sr, subtype='PCM_16')  # explicitly set subtype
