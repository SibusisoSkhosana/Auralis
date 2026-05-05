# Auralis Training Interface - Quick Reference Card

## 🚀 Launch (3 Commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure audio files
python utils/audio_config.py

# 3. Start the interface
streamlit run ui/training_interface.py
```

Then open browser to: `http://localhost:8501`

## 🎯 In the Interface

1. **Click** "Generate New Mixes" (10-30 seconds)
2. **Check** validation (green = good)
3. **Listen** to Mix A and Mix B
4. **Click** one of four buttons:
   - 👍 A is Better
   - 👍 B is Better
   - 🤝 They're Equal
   - ⏭️ Skip (for poor mixes)
5. **Repeat** steps 1-4

## 📊 Training Loop

```
Collect 5-10 comparisons
         ↓
python train.py
         ↓
streamlit run ui/training_interface.py
         ↓
Generate mixes (now improved!)
         ↓
Repeat
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `models/mix_generator.py` | Mixing logic |
| `ui/training_interface.py` | Streamlit app |
| `requirements.txt` | Dependencies |
| `data/mix_comparisons.jsonl` | Training data |
| `resources/mix_a.wav` | Current Mix A |
| `resources/mix_b.wav` | Current Mix B |

## ⚠️ Important Rules

✅ **Do This**
- Use the Skip button for bad mixes
- Take breaks between sessions
- Rate honestly
- Collect diverse comparisons
- Retrain every 5-10 comparisons

❌ **Don't Do This**
- Force choices on poor mixes
- Ignore validation warnings
- Rate inconsistently
- Do too many comparisons at once

## 🧪 Verify Setup

```bash
python verify_setup.py
```

If green checkmarks ✅ - you're ready!
If red X's ❌ - fix issues then try again

## 📞 Need Help?

1. **Setup issues?** → `TRAINING_INTERFACE_GUIDE.md`
2. **How to use?** → `ui/README.md`
3. **Technical details?** → `IMPLEMENTATION_SUMMARY.md`
4. **General integration?** → `INTEGRATION_GUIDE.md`

## 🎵 What Gets Saved

When you rate a comparison:

```json
{
  "features": [...],           // Audio analysis
  "stem_identities": {...},    // What stems detected
  "params_a": {...},           // Mix A parameters
  "params_b": {...},           // Mix B parameters
  "preference": "a"            // Your choice
}
```

Written to: `data/mix_comparisons.jsonl`

**Important:** Skip = NOT saved (prevents bad data)

## 📈 Monitor Progress

In the interface footer:
- **Total Logged** - All entries
- **Valid (Training)** - Actually used
- **Skipped** - Not used

In terminal:
```bash
wc -l data/mix_comparisons.jsonl          # Total count
tail -3 data/mix_comparisons.jsonl        # See latest
grep -c '"skip"' data/mix_comparisons.jsonl  # Count skips
```

## ⚡ Tips

- **Headphones** - Use headphones for accurate listening
- **Consistent** - Use same listening setup each time
- **Breaks** - Take 15 min breaks every 5-10 comparisons
- **Diverse** - Don't always pick A or B
- **Honest** - Your preference is the correct answer

## 🔄 Common Issues

| Issue | Fix |
|-------|-----|
| "Module not found" | `pip install -r requirements.txt` |
| No audio files | Put .wav files in `resources/` |
| Audio won't play | Check browser audio permissions |
| Interface is slow | Generation takes 10-30s (normal) |
| Mixes sound same | Model converging (good sign!) |

## 🎯 Success Criteria - All ✅

- ✅ A/B comparison interface
- ✅ Audio playback
- ✅ Decision buttons (A, B, Tie, Skip)
- ✅ Data capture
- ✅ No bad data recording
- ✅ Validation checks
- ✅ Streamlit UI
- ✅ Single page
- ✅ No crashes
- ✅ Usable training data

## 📱 Browser Support

Works on:
- Chrome ✅
- Firefox ✅
- Safari ✅
- Edge ✅

**Recommended:** Chrome or Firefox on desktop

## 🔐 Safety Guarantees

- No clipping in output
- Limiter applied to all mixes
- Parameters constrained to safe ranges
- Validation before recording
- Skip never recorded as training data

## 🚀 Ready?

```bash
streamlit run ui/training_interface.py
```

Click "Generate New Mixes" and start improving Auralis! 🎵

---

**Questions?** See the full documentation:
- `INTEGRATION_GUIDE.md` - Complete guide
- `TRAINING_INTERFACE_GUIDE.md` - Setup details
- `IMPLEMENTATION_SUMMARY.md` - Technical overview
