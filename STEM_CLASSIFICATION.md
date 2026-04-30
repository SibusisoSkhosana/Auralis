# Audio-Based Stem Classification

## Overview

The system automatically analyzes audio to classify stems by type rather than relying on filenames. This enables the model to generalize to new songs and artists.

Each stem is automatically analyzed and assigned:

```
stem_identity = {
  "type":              "vocal" | "drums" | "bass" | "melody" | "pad" | "other"
  "role":              "lead" | "background" (for vocals only)
  "section":           "verse" | "chorus" | "bridge" | "intro" | "outro" | "mixed"
  "voice_cluster":     0, 1, 2, ... (groups similar voices)
  "energy":            0.0-1.0 (loudness relative to peak)
  "spectral_centroid": Hz (frequency center of mass)
  "zcr":               0.0-1.0 (variation/complexity)
  "transient_density": 0.0-1.0 (punchiness - high for drums)
  "confidence":        0.0-1.0 (how sure classifier is)
}
```

### Example Classification

**beat.wav:**
```
Type:        drums
Energy:      0.85 (loud and punchy)
Transients:  0.72 (lots of attacks)
Confidence:  0.89
```

**verse.wav:**
```
Type:        vocal
Role:        lead (loud)
Cluster:     0 (singer A)
Energy:      0.65
Confidence:  0.81
```

**adlib.wav:**
```
Type:        vocal
Role:        background (quiet)
Cluster:     1 (singer B)
Energy:      0.28
Confidence:  0.74
```

## Classification Rules

### Vocal Detection
- Spectral Centroid > 1500 Hz (voices have higher frequency content)
- Zero Crossing Rate > 0.05 (high variation, not smooth)
- Not highly transient (lacks drum-like attacks)

### Drums
- **High Transient Density** (sudden attacks)
- Consistent rhythm and onset patterns
- Lower frequencies (bass drum content)

### Bass
- **Very low frequencies** (<200 Hz primary energy)
- Moderate transients (kick attacks)
- Smooth envelope

### Pad/Ambient
- **High spectral centroid** (lots of high-end texture)
- Low transients (smooth, sustained)
- Consistent energy

### Melody (Instrument)
- **Vocal-like spectral content** but instrumental
- Medium transients (note attacks)
- Clear pitch content

### Song Section

- **High Energy + Repetition** indicates Chorus
- **Low Energy** indicates Intro/Outro
- **Variable Energy** indicates Verse

### Voice Identity

Uses **MFCC (Mel-Frequency Cepstral Coefficients)** to distinguish singers
- Creates embedding for each vocal
- K-Means clustering groups similar voices
- Result: "Voice Cluster 0" vs "Voice Cluster 1" (not tied to names)

## How Training Works Now

### Old Approach (Filename-Based)

Model learns parameters based on specific filenames, which doesn't generalize to new songs.

### New Approach (Identity-Based)

Model learns mixing patterns based on stem type and characteristics, enabling generalization to different songs and artists.

## Usage

### Inspect Stem Classifications
```bash
python inspect_stems.py
```

Output:
```
📁 beat.wav
   └─ Type: DRUMS (confidence: 89%)
   └─ Energy: 0.85 (0-1 scale)
   └─ Transient Density: 0.72 (punchiness)

📁 verse.wav
   └─ Type: VOCAL (confidence: 81%)
   └─ Role: LEAD
   └─ Voice Cluster: 0 (voice identity group)
   └─ Energy: 0.65
```

### Full Training Loop
```bash
# 1. Generate mixes (auto-classifies stems)
python app.py

# 2. Listen and rate
python rate_mix.py a

# 3. After collecting data, retrain
python train.py
```

Training output now shows:
```
✓ Model trained and saved

📊 Stem types in training data:
  drums: 24 occurrences
  vocal: 18 occurrences
  bass: 12 occurrences
```

---

## 🎛️ Processing Flow

```
Audio File
    ↓
Analyze Signal Characteristics
  • Spectral centroid
  • Zero crossing rate
  • Transient density
  • Energy envelope
  • Onset strength
    ↓
Classify Type
  (vocal / drums / bass / melody / pad)
    ↓
If Vocal: Classify Role
  (lead / background)
    ↓
Detect Section
  (verse / chorus / bridge / intro / outro)
    ↓
Voice Clustering
  (group similar timbres)
    ↓
StemIdentity Object
  {type, role, section, cluster, energy, ...}
    ↓
Stored with Comparison Data
  (logged for model training)
    ↓
Model Learns
  "When I see [type=vocal, role=lead, energy=0.65],
   these parameters work best"
```

---

## 🚀 Why This Enables Better Learning

### Problem 1: Overfitting to Specific Files
- **Before**: "apply_reverb=0.3 works on vocals.wav"
- **After**: "apply_reverb=0.3 works on all lead vocals with energy ~0.65"

### Problem 2: No Transfer to New Stems
- **Before**: New song with different recording = model useless
- **After**: New song with similar stem types = model applies learned patterns

### Problem 3: Artist/Voice Variation
- **Before**: Each voice needed separate training
- **After**: Model understands "lead vs background" and "voice characteristics"

### Result: 🎯
Your model becomes a **general-purpose audio mixer** that understands:
- What role each stem plays
- How its energy/frequency content affects the mix
- What settings work for that stem type

Not: "this specific file"  
But: "this type of audio in this context"

---

## 📈 Next Steps

1. **Test it:**
   ```bash
   python inspect_stems.py
   ```
   See if classifications make sense

2. **Generate initial data:**
   ```bash
   python app.py && python rate_mix.py a && python train.py
   ```

3. **Iterate:**
   Each cycle, model understands more about stems and mixing

---

## 🔬 Advanced: Customizing Classifications

To adjust classification sensitivity, edit the heuristic thresholds in `audio/stem_classifier.py`:

```python
# Example: make vocal detection stricter
def is_vocal(self, features):
    sc_score = min(1.0, (sc - 1500) / 2000)  # Changed from 1000 to 1500
    ...
```

Or add new classifications:
```python
def is_noise(self, features) -> Tuple[bool, float]:
    """Detect if stem is mostly noise."""
    # Your custom logic
    ...
```

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `audio/stem_classifier.py` | Core classification engine |
| `models/data_collector.py` | Integrates classification into logging |
| `models/trainer.py` | Uses stem identity in training |
| `inspect_stems.py` | Debug tool to see classifications |
| `app.py` | Auto-classifies when loading stems |

---

## 💡 Philosophy

> "You're not building an AI that mixes audio.  
> You're building an AI that understands roles in a mix."

The classifier isn't perfect—it's based on simple heuristics. But it's **good enough** to give the model meaningful context, and it improves over time as you collect more training data!
