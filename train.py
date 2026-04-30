#!/usr/bin/env python
"""Training script for the mix comparison model."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.trainer import train

if __name__ == "__main__":
    print("Training mix comparison model...")
    
    try:
        train()
        print("Training complete.")
    
    except Exception as e:
        print(f"Training error: {e}")
