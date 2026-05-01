import sys
import json
import os

# Add parent directory to Python path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_collector import log_mix_comparison
from audio.validator import MixValidator

PENDING_FILE = "data/pending_rating.json"

def load_pending_comparison(path):
    """Load pending comparison data, salvaging older partially-written files."""
    with open(path) as f:
        raw = f.read()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        validation_marker = ',\n  "validation_a":'
        if validation_marker not in raw:
            raise

        comparison = json.loads(raw.split(validation_marker, 1)[0] + "\n}")
        print("[WARNING] Recovered rating data from a partially-written pending file.")
        print("          Run app.py again before your next rating to regenerate clean metadata.")
        return comparison

if len(sys.argv) < 2:
    print("Usage: python rate_mix.py <a|b|tie|skip>")
    print("  a    = Mix A is better")
    print("  b    = Mix B is better")
    print("  tie  = Mixes are equally good/bad")
    print("  skip = Skip this comparison (both mixes are poor)")
    sys.exit(1)

preference = sys.argv[1].lower()
if preference not in ['a', 'b', 'tie', 'skip']:
    print("ERROR: preference must be 'a', 'b', 'tie', or 'skip'")
    sys.exit(1)

if not os.path.exists(PENDING_FILE):
    print("No pending comparison found. Run app.py first.")
    sys.exit(1)

comparison = load_pending_comparison(PENDING_FILE)

# Get validation results (if available)
validation_a = comparison.get("validation_a", {})
validation_b = comparison.get("validation_b", {})
both_valid = comparison.get("both_valid", not validation_a and not validation_b)

# ===== VALIDATION CHECK (from MIXING_GUIDELINES.md) =====
if preference == "skip":
    print("\n" + "="*60)
    print("SKIPPING COMPARISON")
    print("="*60)
    print("[INFO] This comparison will NOT be used for training")
    print("  (Preventing negative reinforcement from poor mixes)")
    
    # Log the skip for analytics
    skip_file = "data/mix_comparisons.jsonl"
    os.makedirs("data", exist_ok=True)
    with open(skip_file, "a") as f:
        json.dump({
            "preference": "skip",
            "validation_a": validation_a,
            "validation_b": validation_b,
            "timestamp": str(np.datetime64('now')) if 'np' in dir() else "unknown"
        }, f)
    
    os.remove(PENDING_FILE)
    print("="*60)
    sys.exit(0)

# For normal ratings (a/b/tie), check validation
if not both_valid:
    print("\n" + "="*60)
    print("  [WARNING] Quality check indicates at least one mix is poor")
    print("="*60)
    
    if validation_a.get('is_valid'):
        print("[OK] Mix A is VALID")
    else:
        print("[WARNING] Mix A has issues:")
        for error in validation_a.get('errors', []):
            print(f"  - {error}")
    
    if validation_b.get('is_valid'):
        print("[OK] Mix B is VALID")
    else:
        print("[WARNING] Mix B has issues:")
        for error in validation_b.get('errors', []):
            print(f"  - {error}")
    
    proceed = input("\nProceed with rating anyway? (y/n): ").lower()
    if proceed != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    print("  Recording as valid despite quality warnings...")
    print("="*60)

log_mix_comparison(
    vocals_paths_dict=comparison["vocals_paths"],
    beat_path=comparison["beat_path"],
    params_a=comparison["params_a"],
    params_b=comparison["params_b"],
    preference=preference
)

os.remove(PENDING_FILE)
print(f"\n Comparison logged: Mix {preference.upper()} preferred")
print(f"Total valid comparisons: {sum(1 for l in open('data/mix_comparisons.jsonl') if 'skip' not in l)}")
