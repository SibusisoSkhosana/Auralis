# Auralis - Comparative Mix Rating System

This document explains the comparative rating workflow.

## Overview

Instead of rating individual mixes on a scale, the system learns through pairwise comparisons. Each cycle:

1. The system generates two different mixes (Mix A and Mix B) with different processing parameters
2. You listen to both and decide which is better (or if they're equal)
3. The model learns from this preference signal to generate better mixes

This approach is more effective because:
- Comparing two options is more intuitive than absolute scoring
- The model learns what parameter changes lead to improvements
- Preference feedback is clearer

**Note:** The system automatically classifies stems (vocal, drums, bass, etc.) so the model learns mixing patterns based on stem identity, not filenames. This enables generalization to new songs.

## Quick Start

```bash
# 1. Inspect stem classification (optional, to see what the system detects)
python inspect_stems.py

# 2. Generate two comparison mixes
python app.py

# 3. Listen to mix_a.wav and mix_b.wav

# 4. Rate which is better
python rate_mix.py a    # Mix A is better
# or
python rate_mix.py b    # Mix B is better
# or
python rate_mix.py tie  # They're equal

# 5. After collecting a few ratings, retrain the model
python train.py

# 6. Go back to step 2 - the model improves each cycle!
```

## Workflow

### Step 1: Generate Two Comparison Mixes

```bash
python app.py
```

This will:
- Load your audio stems (beat + vocals)
- Automatically classify each stem (vocal, drums, bass, etc.)
- Generate two sets of parameters (Mix A and Mix B) based on model predictions
- Process both into WAV files
- Create mix_a.wav and mix_b.wav in resources/
- Save pending comparison in data/pending_rating.json

### Step 2: Listen and Compare

Play both mixes and decide which is better:

### Step 3: Rate the Comparison

```bash
# If Mix A is better
python rate_mix.py a

# If Mix B is better
python rate_mix.py b

# If they're equally good/bad
python rate_mix.py tie
```

The comparison is now logged in data/mix_comparisons.jsonl with stem classifications.

### Step 4: Train the Model

After collecting a few comparisons (~5-10), retrain:

```bash
python train.py
```

This reads from data/mix_comparisons.jsonl and converts comparisons to synthetic training data:
- If you rated A better: A gets score 4, B gets score 2
- If you rated B better: B gets score 4, A gets score 2
- If they tied: Both get score 3

**The model learns parameter effectiveness for each stem TYPE**, not individual files.

### Step 5: Repeat

Go back to Step 1. Each time you run `python app.py`, the model will generate more refined parameter variations based on what it learned.

---

## Stem Classification (NEW!)

Your stems are automatically classified by audio analysis:

```bash
python inspect_stems.py
```

Shows what the system detected:
```
📁 beat.wav
   └─ Type: DRUMS (confidence: 89%)
   └─ Energy: 0.85

📁 verse.wav
   └─ Type: VOCAL (confidence: 81%)
   └─ Role: LEAD
   └─ Voice Cluster: 0
   └─ Energy: 0.65
```

This allows the model to learn:
- "Lead vocals at this energy level need these settings"
- "Drums with this transient density need this processing"
- Generalizes to **new songs** with different stems!

See [STEM_CLASSIFICATION.md](STEM_CLASSIFICATION.md) for detailed explanation.

---

## Data Format

### Pending Comparison
`data/pending_rating.json` stores two mixes waiting for feedback:
```json
{
  "vocals_paths": {
    "verse": "resources/verse.wav",
    "chorus": "resources/chorus.wav"
  },
  "beat_path": "resources/beat.wav",
  "params_a": { /* parameters for Mix A */ },
  "params_b": { /* parameters for Mix B */ }
}
```

### Comparison Log
`data/mix_comparisons.jsonl` stores all pairwise comparisons **with stem identities**:
```json
{
  "features": [...],
  "stem_identities": {
    "beat.wav": {"type": "drums", "energy": 0.8, ...},
    "verse.wav": {"type": "vocal", "role": "lead", ...}
  },
  "params_a": {...},
  "params_b": {...},
  "preference": "a"
}
```

---

## How the Model Learns

1. **Feature Extraction**: Audio stems are analyzed (RMS, spectral centroid, muddiness, etc.)
2. **Stem Classification**: Each stem is automatically classified (vocal, drums, bass, etc.)
3. **Pairwise Comparison Storage**: Your preference between two mixes is recorded
4. **Synthetic Rating Conversion**: Comparisons are converted to absolute scores for training
5. **Contextual Learning**: Model learns which parameters work for which **stem types**
6. **Loop**: Next run generates new variations around the improved parameters

---

## Tips for Best Results

- **Be consistent**: Use the same listening setup and audio quality each time
- **Take breaks**: Your ears need rest - don't do too many comparisons at once
- **Start simple**: The first few comparisons teach the model the basics
- **Gradual refinement**: As the model improves, differences between A and B become subtler
- **Collect diverse feedback**: Compare different parameter combinations to help the model generalize
- **Check classifications**: Run `python inspect_stems.py` to verify stem detection makes sense

---

## Files Reference

| File | Purpose |
|------|---------|
| `app.py` | Main mixer - generates two mixes for comparison |
| `rate_mix.py` | Records your preference (a/b/tie) |
| `train.py` | Retrains model from comparison data |
| `inspect_stems.py` | See what stems were classified as |
| `data/mix_comparisons.jsonl` | Log of all pairwise comparisons |
| `models/trainer.py` | Converts comparisons to training data |
| `models/data_collector.py` | Records features + preferences + **stem identities** |
| `audio/stem_classifier.py` | **NEW:** Audio-based stem classification |
| `resources/mix_a.wav` | First mix in current comparison |
| `resources/mix_b.wav` | Second mix in current comparison |

---

## Troubleshooting

**Q: "No pending comparison found"**
- Run `python app.py` first to generate mixes

**Q: "No training data found"**
- You need at least one comparison logged
- Run `python app.py` → listen → `python rate_mix.py a` first

**Q: Mixes sound identical**
- The model may have converged, or parameter ranges are too small
- Increase variation in `app.py`'s `vary_params()` function

**Q: Model isn't improving**
- Collect more diverse comparisons (10-20+)
- Ensure your ratings are consistent and honest
- Check that mixes are actually different
- Verify stem classification with `python inspect_stems.py`

**Q: Stem classification seems wrong**
- Classification uses signal heuristics, not perfect
- But it's good enough to give model context
- If needed, customize thresholds in `audio/stem_classifier.py`
