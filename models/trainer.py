# trainer.py
import json
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os

def train(log_file="data/mix_log.jsonl", comparison_file="data/mix_comparisons.jsonl"):
    """
    Train the model on recorded mix comparisons and ratings.
    
    IMPORTANT: From MIXING_GUIDELINES.md
    - Only trains on VALID mixes (preference != "skip")
    - Skips entries marked as "skip" to prevent negative reinforcement
    """
    
    records = []
    skipped_count = 0
    
    if os.path.exists(log_file):
        try:
            records.extend([json.loads(l) for l in open(log_file)])
        except Exception:
            pass
    
    if os.path.exists(comparison_file):
        try:
            comparisons = [json.loads(l) for l in open(comparison_file)]
            
            for comp in comparisons:
                preference = comp.get("preference", "tie")
                
                # SKIP entries marked as "skip" (from MIXING_GUIDELINES.md rule #6)
                if preference == "skip":
                    skipped_count += 1
                    print(f"  Skipping: Bad mix comparison (prevents negative learning)")
                    continue
                
                features = comp["features"]
                stem_identities = comp.get("stem_identities", {})
                
                if preference == "a":
                    # Mix A was better: A gets higher score (4), B gets lower (2)
                    records.append({
                        "features": features,
                        "params": comp["params_a"],
                        "rating": 4,
                        "stem_identities": stem_identities  # NEW: context for learning
                    })
                    records.append({
                        "features": features,
                        "params": comp["params_b"],
                        "rating": 2,
                        "stem_identities": stem_identities
                    })
                elif preference == "b":
                    records.append({
                        "features": features,
                        "params": comp["params_a"],
                        "rating": 2,
                        "stem_identities": stem_identities
                    })
                    records.append({
                        "features": features,
                        "params": comp["params_b"],
                        "rating": 4,
                        "stem_identities": stem_identities
                    })
                elif preference == "tie":
                    records.append({
                        "features": features,
                        "params": comp["params_a"],
                        "rating": 3,
                        "stem_identities": stem_identities
                    })
                    records.append({
                        "features": features,
                        "params": comp["params_b"],
                        "rating": 3,
                        "stem_identities": stem_identities
                    })
            
        except Exception:
            pass
    
    if len(records) == 0:
        print("Error: No training data found.")
        print(f"  Checked for: {log_file}")
        print(f"  Checked for: {comparison_file}")
        print(f"  (Skipped {skipped_count} bad comparisons)")
        print("\nTo generate training data:")
        print("  1. Run: python app.py")
        print("  2. Listen to mix_a.wav and mix_b.wav")
        print("  3. Run: python rate_mix.py a  (or b, or tie, or skip)")
        print("  4. Repeat 2-3 times, then run this again")
        return
    
    if skipped_count > 0:
        print(f"\n[INFO] Skipped {skipped_count} bad comparisons (preventing negative reinforcement)")
    
    X = np.array([r["features"] for r in records])
    ratings = np.array([r["rating"] for r in records])
    weights = ratings / ratings.sum()

    param_keys = list(records[0]["params"].keys())
    Y = np.array([[r["params"][k] for k in param_keys] for r in records])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=1000, random_state=42)
    model.fit(X_scaled, Y, sample_weight=weights)

    joblib.dump(model, "models/param_predictor.pkl")
    joblib.dump(scaler, "models/scaler.pkl")
    joblib.dump(param_keys, "models/param_keys.pkl")