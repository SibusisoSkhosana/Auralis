import numpy as np

def detect_muddiness(y, sr):
    #Detect low-mid frequency muddiness in audio.
    y = np.asarray(y)
    if y.ndim == 2:
        if y.shape[0] == 2:
            y = y.mean(axis=0)
        elif y.shape[1] == 2:
            y = y.mean(axis=1)
        else:
            y = y.flatten()
    elif y.ndim != 1:
        y = y.flatten()

    spectrum = np.abs(np.fft.rfft(y))
    freqs = np.fft.rfftfreq(len(y), 1 / sr)

    low_mid = spectrum[(freqs > 200) & (freqs < 400)].mean()
    total = spectrum.mean()

    return low_mid / (total + 1e-6)
