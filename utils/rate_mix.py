import sys
import json
import os

# Add parent directory to Python path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_collector import log_mix_comparison

PENDING_FILE = "data/pending_rating.json"

if len(sys.argv) < 2:
    print("Usage: python rate_mix.py <a|b|tie>")
    print("  a    = Mix A is better")
    print("  b    = Mix B is better")
    print("  tie  = Mixes are equally good/bad")
    sys.exit(1)

preference = sys.argv[1].lower()
if preference not in ['a', 'b', 'tie']:
    print("ERROR: preference must be 'a', 'b', or 'tie'")
    sys.exit(1)

if not os.path.exists(PENDING_FILE):
    print("No pending comparison found. Run app.py first.")
    sys.exit(1)

with open(PENDING_FILE) as f:
    comparison = json.load(f)

log_mix_comparison(
    vocals_paths_dict=comparison["vocals_paths"],
    beat_path=comparison["beat_path"],
    params_a=comparison["params_a"],
    params_b=comparison["params_b"],
    preference=preference
)

os.remove(PENDING_FILE)
print(f"\nComparison logged: Mix {preference.upper()} preferred")
print(f"Total comparisons: {sum(1 for _ in open('data/mix_comparisons.jsonl'))}")