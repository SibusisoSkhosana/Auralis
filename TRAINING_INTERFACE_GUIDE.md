# Auralis Training Interface - Complete Setup & Launch Guide

## Overview

This guide walks you through setting up and running the minimal A/B training interface for Auralis. The interface lets users (producers/engineers) provide feedback on mixed audio to improve the mixing system over time.

## Prerequisites

- Python 3.8+
- Audio files: one beat file and one or more vocal files in `resources/` folder
- A modern web browser (Chrome, Firefox, Safari, Edge)

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `librosa` - Audio analysis and loading
- `numpy` - Numerical computing
- `scipy` - Signal processing
- `soundfile` - Audio I/O
- `scikit-learn` - Machine learning
- `joblib` - Model serialization
- `streamlit` - Web interface

### 2. Prepare Audio Files

Place your audio files in the `resources/` folder:

```
resources/
├── beat.wav          (drums/instrumental)
├── verse.wav         (vocals or other stem)
├── chorus.wav        (vocals or other stem)
└── final_mix.wav     (optional, for comparison)
```

Supported formats: `.wav` (recommended), `.mp3`, `.flac`

### 3. Configure Audio Stems

Run the configuration tool to specify which files are beat and which are vocals:

```bash
python utils/audio_config.py
```

You'll be guided through selecting:
- **Beat file**: The instrumental/drum track
- **Vocal files**: Any number of vocal or stem files

This creates `audio_config.json`:
```json
{
  "beat": "beat.wav",
  "vocals": ["verse.wav", "chorus.wav"]
}
```

### 4. Launch the Training Interface

```bash
streamlit run ui/training_interface.py
```

The browser will open automatically to `http://localhost:8501`

If it doesn't open, manually visit the URL shown in the terminal.

## Using the Interface

### Home Screen
- Shows current status: "Ready to generate"
- Click **"Generate New Mixes"** button

### Generation Phase (10-30 seconds)
- System loads audio stems
- Creates Mix A and Mix B with slight parameter variations
- Validates mixes for quality
- Exports to `resources/mix_a.wav` and `resources/mix_b.wav`

### Validation Screen
Shows quality metrics for both mixes:
- ✅ **Valid** - Safe, no distortion
- ⚠️ **Warnings** - Minor issues, still usable
- ❌ **Invalid** - Poor quality, skip recommended

### Comparison Screen
Built-in audio players for Mix A and Mix B:
- Play independently
- Open in separate tabs for easier comparison
- Use headphones for accurate listening

### Decision Screen
Four clearly labeled buttons:
- **👍 A is Better** - Record preference for Mix A
- **👍 B is Better** - Record preference for Mix B
- **🤝 They're Equal** - Mark as tie
- **⏭️ Skip This Pair** - Don't record (for poor mixes)

**Critical Rule:** Skip is never recorded as training data. Don't force choices.

### After Rating
- Confirmation message with balloons 🎉
- Button to generate another comparison
- Progress shown at bottom (total recorded, valid, skipped)

## Training Loop

After collecting 5-10 valid comparisons:

```bash
python train.py
```

This retrains the model on your feedback. Next run of the interface will generate improved mixes.

**Repeat** for continuous improvement:
1. Generate mixes
2. Rate comparisons (5-10 times)
3. Train model
4. Go to step 1

## What Gets Saved

Every time you rate a comparison:

**File**: `data/mix_comparisons.jsonl` (one JSON object per line)

```json
{
  "features": [0.15, 0.23, ...],
  "stem_identities": {"beat.wav": {...}, "verse.wav": {...}},
  "params_a": {"beat_target_db": -14, ...},
  "params_b": {"beat_target_db": -14.5, ...},
  "preference": "a"
}
```

**Skipped comparisons**: Not saved (preventing bad data from training the model)

## File Reference

| Path | Purpose |
|------|---------|
| `ui/training_interface.py` | Main Streamlit app |
| `models/mix_generator.py` | Core mixing logic |
| `audio_config.json` | Your stem configuration |
| `data/mix_comparisons.jsonl` | Training data (comparisons) |
| `resources/mix_a.wav` | Current Mix A |
| `resources/mix_b.wav` | Current Mix B |

## Stopping and Restarting

**Stop the interface:**
- Press `Ctrl+C` in the terminal
- Or close the browser tab

**Restart:**
```bash
streamlit run ui/training_interface.py
```

Session state is stored, so if you were comparing mixes:
- Close and reopen = fresh comparison
- The data is saved regardless

## Monitoring Progress

Check training progress:

```bash
# Count total comparisons
wc -l data/mix_comparisons.jsonl

# See latest 5 entries
tail -5 data/mix_comparisons.jsonl

# See how many skipped
grep -c '"skip"' data/mix_comparisons.jsonl
```

View in the interface footer:
- **Total Logged** - All comparisons (including skips)
- **Valid (Training)** - Used for model training
- **Skipped** - Not used (avoiding bad data)

## Troubleshooting

### "Module not found" or import errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Audio files not found
```bash
# Verify resources folder and files
ls resources/
python utils/audio_config.py  # Reconfigure
```

### Interface is slow
- Mix generation takes 10-30 seconds per pair (normal)
- Audio processing is computationally intensive
- Subsequent runs may be faster (models cache)

### No audio playing
- Check browser audio is not muted
- Try different browser
- Ensure speakers/headphones are working
- Check browser permissions for audio

### "Generated mixes are identical"
- Model may have converged
- This is a sign of improvement (differences become subtle)
- Try collecting more diverse comparisons

### Want to reset everything
```bash
# Delete training data (start fresh)
rm data/mix_comparisons.jsonl

# Reset model
rm models/param_predictor.pkl models/scaler.pkl models/param_keys.pkl

# Start over
streamlit run ui/training_interface.py
```

## Tips for Best Results

1. **Consistent Environment**: Use the same listening setup each time
2. **Quality Time**: Don't do too many comparisons in one session (ears get tired)
3. **Diverse Feedback**: Don't always pick A or B - vary your choices
4. **Skip Wisely**: Use Skip button when both mixes are poor
5. **Trust Your Ears**: Your preference is the correct answer
6. **Collect Enough**: 5-10 comparisons minimum before retraining

## Next Steps After Training

```bash
# See what stems were detected
python inspect_stems.py

# Manually check validation
python app.py  # (generates mixes without UI)

# Review training data
tail data/mix_comparisons.jsonl | python -m json.tool
```

## Architecture Overview

```
Streamlit Interface (ui/training_interface.py)
         ↓
    MixGenerator (models/mix_generator.py)
         ↓
    [process_mix() → MixValidator → Audio export]
         ↓
    log_mix_comparison() (models/data_collector.py)
         ↓
    data/mix_comparisons.jsonl
         ↓
    Train model (models/trainer.py)
         ↓
    Next cycle: Better mixes!
```

## Support

If something breaks:
1. Check the terminal output - errors are logged there
2. Try restarting: `Ctrl+C` then `streamlit run ui/training_interface.py`
3. Review `MIXING_GUIDELINES.md` for mixing rules
4. Check `COMPARATIVE_RATING.md` for training system details

---

**Remember:** This is a feedback collection system, not a polished product. Focus on gathering quality training data through consistent, thoughtful comparisons. The mixing quality will improve over time.
