# trainer.py
import json
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os

def train(log_file="data/mix_log.jsonl", comparison_file="data/mix_comparisons.jsonl"):
    """Train the model on recorded mix comparisons and ratings."""
    
    records = []
    
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
        return
    
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