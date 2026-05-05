# Auralis A/B Training Interface - Complete Integration Guide

## 🎯 What You Have

A complete, production-ready minimal training interface for Auralis that enables human-in-the-loop improvement of the mixing system. The system is:

✅ **Minimal** - Single page, no over-engineering  
✅ **Safe** - Validates mixes, prevents bad data recording  
✅ **Reliable** - Error handling, clear user feedback  
✅ **Complete** - Ready to collect training data immediately  

## 📦 Deliverables

### Core Implementation

| File | Purpose |
|------|---------|
| `models/mix_generator.py` | Refactored mixing logic for reuse |
| `ui/training_interface.py` | Main Streamlit A/B interface |
| `requirements.txt` | Python dependencies |

### Documentation

| File | Purpose |
|------|---------|
| `ui/README.md` | User guide for the interface |
| `TRAINING_INTERFACE_GUIDE.md` | Setup and launch instructions |
| `IMPLEMENTATION_SUMMARY.md` | Technical architecture overview |
| `verify_setup.py` | Verification script to test setup |

### Data Files (Auto-created)

| File | Created When |
|------|--------------|
| `data/mix_comparisons.jsonl` | First comparison rated |
| `resources/mix_a.wav` | Mix generated |
| `resources/mix_b.wav` | Mix generated |

## 🚀 Getting Started (3 Steps)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**What this installs:**
- Streamlit - web interface
- librosa - audio processing
- numpy, scipy - numerical computing
- scikit-learn, joblib - ML models
- soundfile - audio I/O

### Step 2: Configure Your Audio

```bash
python utils/audio_config.py
```

**What this does:**
- Lists WAV files in `resources/` folder
- Guides you to select beat file
- Guides you to select vocal files
- Saves configuration to `audio_config.json`

### Step 3: Launch the Interface

```bash
streamlit run ui/training_interface.py
```

**What happens:**
- Browser opens automatically to `http://localhost:8501`
- Streamlit loads the interface
- You're ready to start collecting feedback!

## 💡 How It Works

### User Perspective

1. **Generate** - Click button to create Mix A & B
2. **Validate** - See quality metrics (peak, RMS)
3. **Listen** - Play both mixes independently
4. **Compare** - Decide which is better
5. **Record** - Click decision button (A, B, Tie, or Skip)
6. **Repeat** - Generate another pair

### Technical Perspective

```
User clicks "Generate"
        ↓
MixGenerator loads stems + model
        ↓
Creates two parameter sets (seed 42 & 43)
        ↓
process_mix() → limiter → validation → export WAVs
        ↓
User listens via Streamlit audio players
        ↓
User clicks decision button
        ↓
log_mix_comparison() writes to mix_comparisons.jsonl
        ↓
(Skip is NOT recorded)
        ↓
Show statistics: total, valid, skipped
        ↓
Ready for next comparison
```

## 📊 Data Collection

Every valid comparison saves:

```json
{
  "features": [0.15, 0.23, ...],        // Audio analysis
  "stem_identities": {...},              // What stems detected
  "params_a": {                          // Mix A parameters
    "beat_target_db": -14.2,
    "gain_balance": 1.15,
    ...
  },
  "params_b": {...},                     // Mix B parameters
  "preference": "a"                      // User choice
}
```

**Skip comparisons are NOT recorded** (preventing model contamination)

## ✅ Safety Features Implemented

### Parameter Constraints
- Beat level: -24dB to -6dB
- Vocal level: -28dB to -12dB  
- Highpass EQ: 80Hz to 350Hz
- Stereo width: 0 to 0.15

### Validation Checks
- Peak level must be < 0dB
- RMS level in reasonable range
- No NaN or inf values
- Limiter applied to all output

### Data Quality
- Both mixes must be valid
- At least one must be "good"
- Invalid pairs don't train the model
- Skip is always available

## 🧪 Testing Your Setup

```bash
# Quick verification
python verify_setup.py

# Full test workflow
streamlit run ui/training_interface.py
# Then:
# 1. Click "Generate New Mixes" (wait 10-30 sec)
# 2. Check validation display
# 3. Play Mix A (should hear audio)
# 4. Play Mix B (should hear audio)
# 5. Click "A is Better"
# 6. Check data/mix_comparisons.jsonl (should have 1 line)
```

## 🔄 Training Loop

After collecting feedback:

```bash
# 1. Generate comparisons (see above)

# 2. After 5-10 valid comparisons, retrain
python train.py

# 3. Launch interface again
streamlit run ui/training_interface.py

# 4. Generate new mixes (should use improved parameters)

# 5. Continue collecting feedback

# Loop back to step 2 every 5-10 comparisons
```

## 📈 Monitoring Progress

### In the Interface
- Footer shows: Total | Valid | Skipped

### In Terminal
```bash
# Count total logged
wc -l data/mix_comparisons.jsonl

# See latest 3
tail -3 data/mix_comparisons.jsonl

# Count skipped
grep -c '"skip"' data/mix_comparisons.jsonl
```

### After Training
```bash
# Check model was saved
ls -la models/param_predictor.pkl
```

## 🎨 Interface Layout (Text)

```
┌─────────────────────────────────────────────────────────┐
│  🎵 Auralis Training Interface                          │
│  Help improve the mixing system through feedback        │
└─────────────────────────────────────────────────────────┘

┌─ Generate Comparison ─┐  ┌─ Status ─────────────────┐
│                       │  │ ✅ Ready to generate     │
│ [🔄 Generate Mixes]   │  │                          │
└───────────────────────┘  └──────────────────────────┘

┌─ Quality Validation ──────────────────────────────────┐
│ ✅ Mix A              │  ✅ Mix B                   │
│ Peak: -0.5 dB        │  Peak: -0.8 dB             │
└───────────────────────────────────────────────────────┘

┌─ Listen and Compare ──────────────────────────────────┐
│ Mix A                  │  Mix B                      │
│ [🎵 Player]           │  [🎵 Player]               │
└───────────────────────────────────────────────────────┘

┌─ Make Your Choice ────────────────────────────────────┐
│ [👍 A Better] [👍 B Better] [🤝 Equal] [⏭️ Skip]    │
└───────────────────────────────────────────────────────┘

┌─ Training Progress ───────────────────────────────────┐
│ Total: 5  Valid: 4  Skipped: 1                       │
└───────────────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt  # Make sure all deps installed
```

### "No audio files found"
```bash
ls resources/              # Check files exist
python utils/audio_config.py  # Reconfigure
```

### "Audio won't play"
- Check browser audio permissions
- Try different browser
- Ensure speakers/headphones work
- Check browser console for errors

### "Mixes sound identical"
- This is okay - model may be converging
- Differences become subtle with good training data
- Continue collecting feedback

### "Mixes sound worse"
- Common early in training with limited data
- Collect 10-20+ diverse comparisons
- Be consistent with your ratings

### "Interface is slow"
- Mix generation takes 10-30 seconds (normal)
- Audio processing is computationally intensive
- First run after restart may be slower

## 🔑 Key Principles

### ✅ Do This
- ✅ Use consistent listening environment
- ✅ Take breaks between sessions
- ✅ Use Skip for poor mixes
- ✅ Rate honestly
- ✅ Collect diverse comparisons
- ✅ Retrain every 5-10 comparisons

### ❌ Don't Do This
- ❌ Force choices on bad mixes (use Skip!)
- ❌ Rate too many comparisons in one session
- ❌ Use low-quality listening setup
- ❌ Ignore validation warnings
- ❌ Rate inconsistently

## 📚 Next Steps

### After First Comparison
1. Check `data/mix_comparisons.jsonl` (should have 1 entry)
2. Verify `resources/mix_a.wav` and `mix_b.wav` exist
3. Listen to both and verify they sound different

### After 5-10 Comparisons
```bash
python train.py
streamlit run ui/training_interface.py
# Generate new mixes - should sound improved!
```

### Ongoing
- Continue the loop: Generate → Rate → Train → Repeat
- Monitor statistics in interface footer
- Inspect stems: `python inspect_stems.py`
- Check training logs: `tail -5 data/mix_comparisons.jsonl`

## 🏗️ Architecture Overview

### Component Graph
```
Streamlit UI (training_interface.py)
    ├─ Session State (current comparison)
    ├─ MixGenerator (mix_generator.py)
    │   ├─ Load stems (audio_config.json)
    │   ├─ Generate parameters
    │   └─ Process mixes
    ├─ MixValidator (audio/validator.py)
    │   └─ Check quality
    ├─ Audio players (built-in)
    └─ log_mix_comparison() (data_collector.py)
        └─ Save to mix_comparisons.jsonl

Training Loop
    └─ trainer.py
        ├─ Read mix_comparisons.jsonl
        ├─ Train model on valid comparisons
        └─ Save param_predictor.pkl
```

### Data Files
```
resources/
├─ beat.wav
├─ verse.wav
├─ chorus.wav
├─ mix_a.wav (current)
└─ mix_b.wav (current)

data/
├─ mix_comparisons.jsonl (training data)
└─ mix_log.jsonl (legacy)

models/
├─ param_predictor.pkl (trained model)
├─ scaler.pkl (normalization)
└─ param_keys.pkl (parameter names)
```

## 🎓 Learning Path

For understanding the complete system:

1. **Start Here**: This file (you're reading it)
2. **Run It**: Follow "Getting Started" above
3. **Use It**: Follow interface prompts
4. **Understand It**: Read `IMPLEMENTATION_SUMMARY.md`
5. **Deep Dive**: Read `MIXING_GUIDELINES.md` and `COMPARATIVE_RATING.md`

## 🤝 Integration with Existing System

The training interface **does NOT modify** existing Auralis code:

✅ `app.py` - Unchanged (CLI still works)  
✅ `train.py` - Unchanged (training still works)  
✅ `models/trainer.py` - Unchanged  
✅ `audio/*` - All unchanged  
✅ `utils/*` - All unchanged  

**New components only:**
- `models/mix_generator.py` - Extracted logic for reuse
- `ui/training_interface.py` - New Streamlit app

Both old CLI and new UI can run side-by-side without conflict.

## 📝 Files Summary

### Created (5 New)
1. `models/mix_generator.py` - 400 lines, refactored mixing logic
2. `ui/training_interface.py` - 350 lines, Streamlit interface
3. `requirements.txt` - 7 dependencies
4. `verify_setup.py` - 150 lines, verification script
5. Documentation files (guides, README, etc.)

### Modified (1)
1. `requirements.txt` - Added Streamlit + dependencies

### Unchanged (No Breaking Changes)
- All existing Python modules
- All existing scripts
- Training pipeline
- Data formats

## 🎯 Success Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Audio configured (`python utils/audio_config.py`)
- [ ] Setup verified (`python verify_setup.py`)
- [ ] Interface launches (`streamlit run ui/training_interface.py`)
- [ ] Mixes generate on button click
- [ ] Audio players work
- [ ] Feedback is recorded
- [ ] Data file created (`data/mix_comparisons.jsonl`)
- [ ] Can retrain model (`python train.py`)
- [ ] Improved mixes generated on next run

---

## 🎉 You're All Set!

The Auralis Training Interface is ready to transform your mixing system through human feedback.

**Start collecting training data:**

```bash
streamlit run ui/training_interface.py
```

**Questions?** Check these in order:
1. `TRAINING_INTERFACE_GUIDE.md` - How to use
2. `IMPLEMENTATION_SUMMARY.md` - What was built
3. `verify_setup.py` - Debug setup issues
4. Terminal output - Real-time error messages

Happy mixing! 🎵
