#!/usr/bin/env python
"""
Inspect stem identities for your audio files.

Usage:
  python inspect_stems.py

Shows detailed classification for each audio file in resources/
- Type: vocal, drums, bass, melody, pad, other
- Role: lead, background (for vocals)
- Section: verse, chorus, etc.
- Signal characteristics: energy, spectral content, transients
"""

import sys
import os
from pathlib import Path
from utils.audio_config import get_resources_dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import librosa
from audio.stem_classifier import classify_stems

def main():
    
    

    resources_dir = get_resources_dir()
  
    if not resources_dir.exists():
        print("ERROR: resources/ folder not found!")
        return
    
    # Find all .wav files
    wav_files = list(resources_dir.glob("*.wav"))
    
    if not wav_files:
        print("No .wav files found in resources/")
        return
    
    print("="*70)
    print("AURALIS STEM CLASSIFIER - INSPECTION")
    print("="*70)
    print(f"\nFound {len(wav_files)} audio files\n")
    
    # Load all stems
    audio_dict = {}
    for wav_file in wav_files:
        try:
            y, sr = librosa.load(wav_file, sr=44100, mono=False)
            if y.ndim == 2:
                y = y.mean(axis=0)
            audio_dict[wav_file.name] = y
        except Exception as e:
            print(f"ERROR loading {wav_file.name}: {e}")
            return
    
    # Classify
    identities = classify_stems(audio_dict, sr=44100)
    
    # Display results
    print("\n" + "="*70)
    print("STEM CLASSIFICATIONS")
    print("="*70)
    
    for filename in sorted(identities.keys()):
        identity = identities[filename]
        ident_dict = identity.to_dict()
        
        print(f"\n📁 {filename}")
        print(f"   └─ Type: {ident_dict['type'].upper():<12} (confidence: {ident_dict['confidence']:.1%})")
        
        if ident_dict['role']:
            print(f"   └─ Role: {ident_dict['role'].upper()}")
        
        print(f"   └─ Section: {ident_dict['section'].upper()}")
        
        if ident_dict['voice_cluster'] is not None:
            print(f"   └─ Voice Cluster: {ident_dict['voice_cluster']} (voice identity group)")
        
        print(f"   └─ Energy: {ident_dict['energy']:.2f} (0-1 scale)")
        print(f"   └─ Spectral Centroid: {ident_dict['spectral_centroid']:.0f} Hz")
        print(f"   └─ Zero Crossing Rate: {ident_dict['zcr']:.4f}")
        print(f"   └─ Transient Density: {ident_dict['transient_density']:.2f} (punchiness)")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    type_summary = {}
    for identity in identities.values():
        stem_type = identity.stem_type
        type_summary[stem_type] = type_summary.get(stem_type, 0) + 1
    
    print("\nStem Types Detected:")
    for stem_type, count in sorted(type_summary.items()):
        emoji = {
            'vocal': '🎤',
            'drums': '🥁',
            'bass': '🔊',
            'melody': '🎹',
            'pad': '🎸',
            'other': '❓'
        }.get(stem_type, '•')
        print(f"  {emoji} {stem_type}: {count}")
    
    print("\n Classification complete!")
    print("\nThis information is automatically recorded when you:")
    print("  1. Run: python app.py")
    print("  2. Rate: python rate_mix.py a/b/tie")
    print("  3. Train: python train.py")
    print("\nYour model learns mixing patterns based on STEM TYPE, not filenames!")

if __name__ == "__main__":
    main()
