#!/usr/bin/env python
"""Verification script for Auralis Training Interface setup."""

import sys
import os
from pathlib import Path

def check_file(path, description):
    """Check if a file exists."""
    if os.path.exists(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description} NOT FOUND: {path}")
        return False

def check_import(module_name, package_name=None):
    """Check if a Python module can be imported."""
    package = package_name or module_name
    try:
        __import__(module_name)
        print(f"✅ {package} installed")
        return True
    except ImportError:
        print(f"❌ {package} NOT installed")
        return False

def main():
    print("=" * 60)
    print("AURALIS TRAINING INTERFACE - VERIFICATION")
    print("=" * 60)
    
    all_good = True
    
    # Check Python version
    print("\n📌 Python Version")
    if sys.version_info >= (3, 8):
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        print(f"❌ Python {sys.version_info.major}.{sys.version_info.minor} (need 3.8+)")
        all_good = False
    
    # Check key files
    print("\n📁 Required Files")
    files_to_check = [
        ("models/mix_generator.py", "Mix Generator module"),
        ("ui/training_interface.py", "Streamlit Interface"),
        ("audio_config.json", "Audio Configuration"),
        ("requirements.txt", "Dependencies"),
    ]
    
    for file_path, desc in files_to_check:
        if not check_file(file_path, desc):
            all_good = False
    
    # Check resources
    print("\n🎵 Audio Resources")
    resources_dir = Path("resources")
    if resources_dir.exists():
        wav_files = list(resources_dir.glob("*.wav"))
        if wav_files:
            print(f"✅ Found {len(wav_files)} WAV files in resources/")
            for f in wav_files:
                print(f"   - {f.name}")
        else:
            print("⚠️  No WAV files in resources/ folder (add audio files)")
            all_good = False
    else:
        print("❌ resources/ folder not found")
        all_good = False
    
    # Check data directory
    print("\n💾 Data Directory")
    data_dir = Path("data")
    if data_dir.exists():
        print(f"✅ data/ directory exists")
        comp_file = data_dir / "mix_comparisons.jsonl"
        if comp_file.exists():
            count = sum(1 for _ in open(comp_file))
            print(f"   - {count} comparisons logged")
    else:
        print("⚠️  data/ directory will be created on first run")
    
    # Check dependencies
    print("\n📦 Python Dependencies")
    dependencies = [
        ("librosa", "librosa"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("soundfile", "soundfile"),
        ("sklearn", "scikit-learn"),
        ("joblib", "joblib"),
        ("streamlit", "streamlit"),
    ]
    
    for import_name, package_name in dependencies:
        if not check_import(import_name, package_name):
            all_good = False
    
    # Check Auralis modules
    print("\n🎛️ Auralis Modules")
    try:
        from models.mix_generator import MixGenerator
        print("✅ MixGenerator module")
    except Exception as e:
        print(f"❌ MixGenerator: {e}")
        all_good = False
    
    try:
        from audio.processor import process_mix
        print("✅ Audio processor module")
    except Exception as e:
        print(f"⚠️  Audio processor: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL CHECKS PASSED - Ready to launch!")
        print("\nQuick start:")
        print("  1. streamlit run ui/training_interface.py")
        print("  2. Click 'Generate New Mixes'")
        print("  3. Listen and rate!")
    else:
        print("⚠️ SOME ISSUES FOUND - See above")
        print("\nFix issues then:")
        print("  pip install -r requirements.txt")
        print("  python utils/audio_config.py")
    
    print("=" * 60)
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
