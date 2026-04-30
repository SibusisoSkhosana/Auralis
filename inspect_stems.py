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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import librosa
from audio.stem_classifier import classify_stems

def main():
    resources_dir = Path(__file__).parent / "resources"
    
    if not resources_dir.exists():
        print("Error: resources/ folder not found.")
        return
    
    wav_files = list(resources_dir.glob("*.wav"))
    
    if not wav_files:
        print("No .wav files found in resources/")
        return
    
    print(f"Found {len(wav_files)} audio file(s)")
    
    audio_dict = {}
    for wav_file in wav_files:
        try:
            y, sr = librosa.load(wav_file, sr=44100, mono=False)
            if y.ndim == 2:
                y = y.mean(axis=0)
            audio_dict[wav_file.name] = y
        except Exception as e:
            print(f"Error loading {wav_file.name}: {e}")
            return
    
    identities = classify_stems(audio_dict, sr=44100)
    
    print("\nStem Classifications:")
    print("-" * 50)
    
    for filename in sorted(identities.keys()):
        identity = identities[filename]
        ident_dict = identity.to_dict()
        
        print(f"\n{filename}")
        print(f"  Type: {ident_dict['type']}")
        print(f"  Energy: {ident_dict['energy']:.2f}")
        print(f"  Confidence: {ident_dict['confidence']:.2f}")
        
        if ident_dict['role']:
            print(f"  Role: {ident_dict['role']}")
        
        if ident_dict['voice_cluster'] is not None:
            print(f"  Voice Cluster: {ident_dict['voice_cluster']}")
    
    print("\n" + "-" * 50)
    print("Stem Type Summary:")
    
    type_summary = {}
    for identity in identities.values():
        stem_type = identity.stem_type
        type_summary[stem_type] = type_summary.get(stem_type, 0) + 1
    
    for stem_type, count in sorted(type_summary.items()):
        print(f"  {stem_type}: {count}")

if __name__ == "__main__":
    main()
