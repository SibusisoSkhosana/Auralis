"""Audio file configuration and discovery system."""
import os
import sys
from pathlib import Path


def get_resources_dir():
    """Get the resources directory path."""
    root = Path(__file__).parent.parent
    return root / "resources"


def list_audio_files():
    """List all .wav files in resources folder."""
    resources_dir = get_resources_dir()
    audio_files = sorted([f.name for f in resources_dir.glob("*.wav") 
                         if f.name != "final_mix.wav"])
    return audio_files


def load_config(config_path=None):
    """Load audio configuration from JSON file.
    
    Config format:
    {
        "beat": "filename.wav",
        "vocals": ["file1.wav", "file2.wav", ...]
    }
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "audio_config.json"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None


def save_config(beat_file, vocal_files, config_path=None):
    """Save audio configuration to JSON file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "audio_config.json"
    
    config = {
        "beat": beat_file,
        "vocals": vocal_files
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"Audio config saved to {config_path}")


def get_audio_config():
    """Get audio configuration.
    
    Loads saved config if available, otherwise uses beat.wav pattern:
    - beat.wav = beat track
    - all others = vocal tracks
    """
    if "beat.wav" not in audio_files:
        print("ERROR: 'beat.wav' not found in resources folder.")
        print("Please rename your beat file to 'beat.wav'.")
        return None

    beat_file = "beat.wav"
    vocal_files = [f for f in audio_files if f != beat_file]

    if not vocal_files:
        print("ERROR: No vocal files found (only beat.wav present).")
        print("Need at least one vocal file in resources/")
        return None

    print("✓ Auto Configuration")
    print(f"  Beat: {beat_file}")
    print(f"  Vocals: {', '.join(vocal_files)}")

    # Save config for next time
    save_config(beat_file, vocal_files)

    return {
        "beat": beat_file,
        "vocals": vocal_files
    }


if __name__ == "__main__":
    # Can call directly for testing
    config = get_audio_config()
    if config:
        print(f"\nConfiguration loaded!")
        print(f"Beat: {config['beat']}")
        print(f"Vocals: {', '.join(config['vocals'])}")
