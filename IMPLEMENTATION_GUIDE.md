# Auralis Safety Implementation Guide

**Date:** 2026-05-01  
**Version:** 2.0 - Stability-First Architecture

---

## Overview

Your audio mixing engine has been upgraded with a **stability-first architecture** that prevents distortion and poor-quality output from corrupting the ML model. This implements the MIXING_GUIDELINES.md rules to create a sustainable feedback loop.

## What Changed

### 1. **New Validation System** (`audio/validator.py`)

A comprehensive `MixValidator` class that checks every generated mix against safety standards:

- **Peak Level Check:** Ensures peaks stay ≤ -0.5 dB (safe headroom)
- **Clipping Detection:** Counts any samples exceeding safe thresholds
- **Distortion Analysis:** Detects signs of over-processing or soft-clipping
- **RMS Level Check:** Ensures mixes are at appropriate loudness (-15 to -6 dB)
- **Validation Report:** Human-readable output showing exactly what passed/failed

### 2. **Enhanced Audio Processor** (`audio/processor.py`)

Upgraded with:
- **Safe parameter ranges enforced** in the limiter (threshold 0.85, max peak 0.95)
- **Headroom-aware normalization** that prevents over-normalization
- **Proper hard-limiting** instead of just soft-clipping via tanh
- **Dual-stage limiter:** Soft knee for smooth limiting + hard clip for absolute safety

### 3. **Conservative Parameter Ranges** (`app.py`)

All parameter variations are now restricted to prevent instability:

| Parameter | Old Range | New Range | Reason |
|-----------|-----------|-----------|--------|
| beat_target_db | ± 1.5 dB | ± 0.8 dB | Prevent extreme loudness shifts |
| gain_balance | ± 0.2 | ± 0.1 | Subtle balancing only |
| mud_threshold | ± 0.1 | ± 0.05 | Conservative mud removal |
| vocal_target_db | ± 2 dB | ± 0.8 dB | Tight level control |
| highpass_cutoff | ± 40 Hz | ± 20 Hz | Avoid over-filtering |
| stereo_width | ± 0.02 | ± 0.01 | Minimal stereo effects |

### 4. **Enforced Processing Order** (`app.py` → `process_mix()`)

The mixer now strictly follows the safety processing order:

```
1. Normalize input (with headroom preservation)
2. Apply subtractive EQ (remove mud carefully)
3. Apply gain staging (conservative, with level monitoring)
4. Combine and balance (only when differences are significant)
5. Apply limiter LAST (hard safety limit)
```

### 5. **Validation Before Training**

New workflow in `app.py`:

1. Generate Mix A and Mix B
2. **Validate both mixes** against all safety checks
3. If BOTH mixes are invalid:
   - [SKIP] Skip training (create `last_comparison_skipped.json`)
   - Print detailed error report
   - Exit without creating rating prompt
4. If at least one is valid:
   - [OK] Proceed with rating and training

### 6. **Skip Option in Rating** (`utils/rate_mix.py`)

New capability: `python rate_mix.py skip`

- Use when both mixes sound bad/distorted
- Prevents training on poor outputs (MIXING_GUIDELINES.md rule #6)
- Logs the skip event for tracking
- Keeps the model from learning destructive patterns

### 7. **Smart Training Exclusion** (`models/trainer.py`)

The trainer now:
- [OK] Counts and skips all "skip" entries
- [OK] Only trains on valid (non-skipped) comparisons
- [OK] Reports how many bad comparisons were filtered out
- [OK] Prevents negative reinforcement

---

## How to Use

### Normal Workflow (Unchanged)

```bash
# Generate two comparison mixes
python app.py

# Listen to both mixes
# Then rate the better one:
python rate_mix.py a      # Mix A is better
python rate_mix.py b      # Mix B is better
python rate_mix.py tie    # They're equally good

# Train the model on accumulated ratings
python models/trainer.py
```

### New: Handle Poor Mixes

```bash
# If app.py shows BOTH mixes are INVALID:
# The comparison is automatically skipped
# You'll see: [CRITICAL] SKIP TRAINING: Both mixes are poor quality

# If you want to skip a comparison manually:
python rate_mix.py skip    # This mix pair won't be used for training
```

### Monitoring Quality

After running `app.py`, you'll see validation reports:

```
============================================================
VALIDATION REPORT: MIX A
============================================================
[OK] STATUS: VALID (passes all safety checks)
[OK] QUALITY: GOOD (ready for training)

Metrics:
  Peak Level:    -3.45 dB  (target ≤ -0.5 dB)
  RMS Level:    -12.50 dB  (target -15 to -6 dB)
  Clipping:      [OK] None detected

[OK] All checks passed!
============================================================
```

---

## Safety Guardrails

### [OK] Hard Limits (Cannot be violated)

1. **Peak level** cannot exceed -0.5 dB (absolute safety)
2. **Limiter threshold** set to 0.85 (safe buffer before clipping)
3. **Parameter ranges** are clipped in code (cannot be exceeded)
4. **Processing order** is enforced (cannot be skipped)

### [WARNING] Soft Limits (Warnings)

1. **RMS too quiet** (< -30 dB): Mix is essentially silent
2. **RMS too loud** (> -6 dB): Mix is dangerously loud
3. **Distortion detected:** Possible over-processing

### [CRITICAL] Training Blockers

1. **Both mixes invalid:** Automatic skip (prevents destructive learning)
2. **User marks as skip:** Manual override (when human says both are bad)
3. **Any critical errors:** Mix marked INVALID and not used

---

## Files Changed

### New Files
- `MIXING_GUIDELINES.md` — System prompt for audio engineering rules
- `audio/validator.py` — Comprehensive mix validation system
- `IMPLEMENTATION_GUIDE.md` (this file) — Usage documentation

### Modified Files
- `app.py` — Now validates mixes and enforces safety rules
- `audio/processor.py` — Enhanced with safety mechanisms
- `utils/rate_mix.py` — Added skip option and validation checks
- `models/trainer.py` — Now filters out "skip" entries

---

## Expected Improvements

### Before (Destructive Cycle)
- [FAIL] Generate mixes → Distorted audio
- [FAIL] Rate them anyway (because there's no skip option)
- [FAIL] Train model on distortion → Model learns to distort
- [FAIL] Next iteration makes it worse
- [LOOP] Feedback loop = disaster

### After (Stable Cycle)
- [OK] Generate mixes → Validate quality
- [OK] If poor: Skip training automatically
- [OK] If good: Train model only on clean audio
- [OK] Model learns from high-quality examples
- [OK] Gradual improvement → Better mixes over time

---

## Parameters Explained

### Beat Target dB (-14 dB default, now ±0.8 range)
- Controls the normalized loudness of the beat/instrumental
- Narrow range prevents extreme volume shifts that cause clipping
- Default -14 dB leaves headroom for vocals

### Vocal Target dB (-20 dB default, now ±0.8 range)
- Controls the normalized loudness of vocals
- Tighter than beat because vocals need clarity
- -20 dB provides space for beat/instrumental

### Gain Balance (1.2 default, now ±0.1 range)
- Ratio of beat-to-vocal levels
- 1.2 means beat is 20% louder
- Narrow range prevents sudden mix balance shifts

### Mud Threshold (0.3 default, now ±0.05 range)
- Triggers high-pass filter if muddiness exceeds this
- Lower = more aggressive filtering
- Now conservative to avoid over-filtering

### Highpass Cutoff (200 Hz default, now ±20 Hz range)
- Frequency above which muddy frequencies are removed
- Typical range: 80-350 Hz
- Conservative variation prevents loss of important bass

### Stereo Width (0.03 default, now ±0.01 range)
- How much side channel is enhanced (0 = mono, 0.3 = very wide)
- Very subtle by default
- Tight range prevents over-processing

---

## Troubleshooting

### Problem: "Both mixes are poor — comparison skipped"
**Solution:** This is working as designed! The system is preventing bad mixes from corrupting the model. Run `app.py` again to generate better options.

### Problem: Validation shows "DISTORTION DETECTED"
**Solution:** Check the detailed error message:
- If "Peak level too high": Reduce `beat_target_db` or `vocal_target_db`
- If "Soft-clipping detected": Limiter is being pushed too hard; reduce initial levels
- If "High transient energy": Try increasing `mud_threshold` slightly

### Problem: "Mix is too quiet" warning
**Solution:** One or more levels are set too conservatively. Increase the appropriate `_target_db` parameter by 1-2 dB.

### Problem: Mixes sound lifeless (no dynamics)
**Solution:** This is the safety-first approach. Once you have 5-10 good comparisons, the ML model will learn to add back subtle variation while staying within safe bounds.

---

## Next Steps

1. **Run the system:** `python app.py` to see validation in action
2. **Listen & Rate:** Compare the mixes and use `python rate_mix.py a/b/tie/skip`
3. **Monitor:** Look at validation reports after each run
4. **Train:** After 5-10 good comparisons, run `python models/trainer.py`
5. **Iterate:** As the model learns from clean audio, mixes should gradually improve

---

## Remember

> **Operate conservatively. Avoid aggressive changes. Favor stability over experimentation.**

The goal is to create a baseline that's consistently clean. ML refinement comes later.
