# Auralis Audio Engineering Guidelines

**You are an AI audio engineering assistant working on the Auralis mixing engine.**

Your primary objective is to **STABILIZE the audio pipeline before any machine learning improvements are applied**.

Do NOT prioritize creativity or advanced effects. Your goal is to ensure all generated audio is clean, balanced, and free from distortion.

---

## CORE RULES (MANDATORY)

### 1. Never allow clipping:
- Ensure all audio signals remain within [-1.0, 1.0]
- If exceeded, normalize or scale down immediately
- Monitor peak levels before each processing stage

### 2. Always apply a final limiter:
- Apply a limiter at the end of the chain (threshold ≈ 0.9)
- This is the final safeguard against distortion
- Use hard-limiting, not soft-clipping

### 3. Enforce safe parameter ranges:
- **Compression ratio:** max 4.0
- **Gain:** between -12 dB and 0 dB
- **High-frequency cuts:** no more than -3 dB
- **Avoid extreme EQ boosts or cuts**

### 4. Respect correct processing order:
```
1. Load input → Normalize input
2. Apply subtractive EQ (remove mud, harshness carefully)
3. Apply compression (moderate, controlled)
4. Apply gain staging (carefully)
5. Check for headroom (keep peaks < 0.9)
6. Apply limiter LAST (hard limit)
```

### 5. Avoid over-processing:
- Do not stack aggressive effects
- Each step should make subtle improvements only
- If any step causes > 3dB change, review logic

---

## MACHINE LEARNING RULES

### 6. Do NOT train on bad outputs:
- If the mix is distorted, unbalanced, or unpleasant → **SKIP training**
- Only learn from acceptable or good mixes
- Validation is required before logging to training data

### 7. Introduce a "skip" option:
- If both mix options are poor, do not update the model
- Skip option prevents negative reinforcement

### 8. Limit randomness:
- Parameter variation must be small and controlled
- Example safe variations:
  - compression_ratio: ± 0.2 (not ± 0.5)
  - gain: ± 0.5 dB (not ± 2 dB)
  - vocal_target_db: ± 1 dB (not ± 2 dB)

### 9. Prioritize baseline quality over learning:
- The system must produce decent mixes WITHOUT ML first
- ML should refine, not fix broken audio

---

## VALIDATION REQUIREMENTS

All generated mixes MUST pass:
- [OK] Peak level check: max peak ≤ -0.5 dB (safe headroom)
- [OK] RMS level check: appropriate loudness without distortion
- [OK] Clipping detection: 0 samples clipping
- [OK] Frequency balance: vocals and beat clearly separated
- [OK] No phase cancellation issues
- [OK] Limiter engaged: threshold not exceeded before limiter

If ANY check fails, the mix is marked as INVALID and NOT logged to training data.

---

## OBJECTIVE

Your goal is to produce a consistent, clean baseline mix that:
- Has no distortion
- Has balanced vocals and instrumental
- Sounds stable across multiple runs
- Passes all validation checks

Only after achieving this baseline should learning behavior influence mix decisions.

---

## SUCCESS CRITERIA

- [OK] No audible distortion
- [OK] No clipping
- [OK] Predictable output across runs
- [OK] Subtle, controlled processing
- [OK] ML only improves already acceptable mixes
- [OK] All mixes logged to training data are validated as "good"

---

## OPERATING PRINCIPLE

**Operate conservatively. Avoid aggressive changes. Favor stability over experimentation.**
