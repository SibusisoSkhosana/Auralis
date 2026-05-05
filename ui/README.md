# Auralis Training Interface

Minimal A/B comparison interface for collecting human feedback to improve the audio mixing system.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Your Audio Files

```bash
python utils/audio_config.py
```

You'll be prompted to select your beat and vocal stem files from the `resources/` folder.

### 3. Launch the Training Interface

```bash
streamlit run ui/training_interface.py
```

The interface will open in your browser at `http://localhost:8501`

## Workflow

### Step 1: Generate Mixes
Click the **"Generate New Mixes"** button to create Mix A and Mix B with controlled parameter variations.

### Step 2: Quality Check
The system automatically validates both mixes:
- ✅ **Green** = Valid mix, safe for listening
- ⚠️ **Yellow** = Quality issues but acceptable
- ❌ **Red** = Poor quality, not used for training

### Step 3: Listen and Compare
Use the built-in audio players to listen to both mixes. You can open them in separate browser tabs for easier side-by-side comparison.

**Tips:**
- Use headphones or a good speaker setup
- Take your time with each comparison
- Your ears are the judge

### Step 4: Provide Feedback
Choose one of four options:

- **👍 A is Better** - Mix A was clearly better
- **👍 B is Better** - Mix B was clearly better  
- **🤝 They're Equal** - Both mixes were equally good or bad
- **⏭️ Skip This Pair** - Both mixes are poor, don't record for training

**Important:** The Skip button is critical. Never force a choice on bad mixes. Only valid comparisons train the model.

### Step 5: Repeat and Train

After collecting 5-10 valid comparisons, retrain the model:

```bash
python train.py
```

Then return to Step 1. Each cycle improves the mixing parameters based on your feedback.

## Design Principles

### Minimal & Focused
- Single-page interface
- No accounts, authentication, or user management
- No advanced features (yet)
- Focus on speed and reliability

### No Bad Data
- "Skip" button is always available
- Poor mixes are never recorded as training data
- Validation prevents learning from distorted audio

### Reliable Mixing
- All mixes follow safety constraints
- No clipping, proper limiters applied
- Conservative parameter variations
- Deterministic generation (seeds for reproducibility)

## Data Collection

Every comparison logs:
- **Audio Features**: RMS, spectral properties, muddiness, etc.
- **Mix Parameters**: beat level, vocal level, EQ settings, etc.
- **Your Choice**: a, b, tie, or skip
- **Stem Classification**: vocals, drums, bass (auto-detected)

Skipped comparisons are NOT stored as training data.

## File Structure

```
ui/training_interface.py    # Main Streamlit app (you are here)
models/mix_generator.py     # Core mixing logic
data/
  mix_comparisons.jsonl     # All comparisons (training data)
  pending_rating.json       # Current comparison being rated
resources/
  mix_a.wav                 # Current Mix A
  mix_b.wav                 # Current Mix B
```

## Troubleshooting

### "No audio playing"
- Ensure your audio device is working
- Check browser audio permissions
- Try a different browser if issues persist

### "Mixes sound identical"
- The model may be converging
- After enough good training data, differences become subtle
- This is actually a sign of improvement!

### "Mixes sound worse than before"
- This usually happens early in training with limited data
- Collect 10-20+ diverse comparisons for better results
- Be consistent with your ratings

### "Interface is slow"
- Mix generation takes 10-30 seconds depending on audio length
- This is normal - the system is computing audio processing
- First run after startup may be slightly slower

## Next Steps

Once you have trained comparisons:

1. **Inspect Stems**: `python inspect_stems.py` - See what the system detected
2. **Train Model**: `python train.py` - Retrain with your feedback
3. **Check Results**: Run the interface again - parameters should improve

## Architecture Notes

The interface reuses the core Auralis mixing pipeline:
- `process_mix()` - Applies parameters to audio
- `MixValidator` - Ensures mixes meet safety standards
- `log_mix_comparison()` - Records feedback for training
- `vary_params()` - Creates controlled parameter variations

Everything is designed for **stability over features** and **data quality over speed**.
