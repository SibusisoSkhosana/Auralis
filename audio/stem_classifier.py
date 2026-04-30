"""
Automatic stem classification based on audio signal analysis.

Instead of relying on filenames, this module classifies stems by analyzing:
- Spectral characteristics (frequency content, texture)
- Temporal dynamics (energy, transients, rhythm)
- Structural position (verse/chorus detection)
- Voice identity (clustering similar timbres)

This creates a "Stem Identity" object that the mixer learns from.
"""

import numpy as np
import librosa
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple


class StemIdentity:
    """Represents the identity and characteristics of a stem."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.stem_type = None          # 'vocal', 'drums', 'bass', 'melody', 'pad', 'other'
        self.role = None               # 'lead', 'background', 'adlib', None
        self.section = None            # 'verse', 'chorus', 'bridge', 'intro', 'outro', 'mixed'
        self.voice_cluster = None      # cluster ID if vocal (for distinguishing artists)
        self.energy = 0.0              # 0-1 normalized
        self.spectral_centroid = 0.0   # Hz
        self.zero_crossing_rate = 0.0  # 0-1
        self.spectral_bandwidth = 0.0  # Hz
        self.transient_density = 0.0   # 0-1 (how "punchy")
        self.confidence = 0.0          # 0-1 classification confidence
    
    def to_dict(self):
        """Convert to dict for logging/storage."""
        return {
            'filename': self.filename,
            'type': self.stem_type,
            'role': self.role,
            'section': self.section,
            'voice_cluster': self.voice_cluster,
            'energy': float(self.energy),
            'spectral_centroid': float(self.spectral_centroid),
            'zcr': float(self.zero_crossing_rate),
            'spectral_bandwidth': float(self.spectral_bandwidth),
            'transient_density': float(self.transient_density),
            'confidence': float(self.confidence),
        }
    
    def __repr__(self):
        return f"StemID({self.stem_type}/{self.role}@{self.section}, energy={self.energy:.2f}, conf={self.confidence:.2f})"


class StemClassifier:
    """Classifies audio stems by signal analysis."""
    
    def __init__(self, sr=44100):
        self.sr = sr
    
    # ========== FEATURE EXTRACTION ==========
    
    def extract_features(self, y: np.ndarray) -> Dict[str, float]:
        """Extract signal characteristics from audio."""
        # Ensure mono for analysis
        if y.ndim == 2:
            y = y.mean(axis=0)
        
        features = {}
        
        # Energy
        features['energy'] = float(np.sqrt(np.mean(y ** 2)))
        features['energy_norm'] = features['energy'] / (np.max(np.abs(y)) + 1e-6)
        
        # Spectral features
        features['spectral_centroid'] = float(
            librosa.feature.spectral_centroid(y=y, sr=self.sr).mean()
        )
        features['spectral_rolloff'] = float(
            librosa.feature.spectral_rolloff(y=y, sr=self.sr).mean()
        )
        features['spectral_bandwidth'] = float(
            librosa.feature.spectral_bandwidth(y=y, sr=self.sr).mean()
        )
        
        # Zero crossing rate (high for vocals/noise, low for bass/pads)
        features['zcr'] = float(
            librosa.feature.zero_crossing_rate(y).mean()
        )
        
        # Spectral contrast (difference between peaks and valleys)
        features['spectral_contrast'] = float(
            librosa.feature.spectral_contrast(y=y, sr=self.sr).mean()
        )
        
        # Temporal features
        features['transient_density'] = self._compute_transient_density(y)
        features['onset_strength'] = self._compute_onset_strength(y)
        
        # MFCC for voice identity (mean across time)
        mfcc = librosa.feature.mfcc(y=y, sr=self.sr, n_mfcc=13)
        features['mfcc_mean'] = mfcc.mean(axis=1)
        
        return features
    
    def _compute_transient_density(self, y: np.ndarray, hop_length=512) -> float:
        """Estimate how "punchy" the audio is (high for drums, low for pads)."""
        S = np.abs(librosa.stft(y, hop_length=hop_length))
        
        # Energy in each frame
        energy_frames = np.sqrt(np.sum(S ** 2, axis=0))
        
        # Compute frame-to-frame changes
        delta = np.abs(np.diff(energy_frames))
        
        # Normalize by average energy
        avg_energy = np.mean(energy_frames) + 1e-6
        transient_score = np.mean(delta) / avg_energy
        
        # Clip to 0-1
        return min(1.0, transient_score)
    
    def _compute_onset_strength(self, y: np.ndarray) -> float:
        """Detect how rhythmically strong the signal is."""
        onset_env = librosa.onset.onset_strength(y=y, sr=self.sr)
        return float(np.mean(onset_env))
    
    # ========== CLASSIFICATION LOGIC ==========
    
    def is_vocal(self, features: Dict) -> Tuple[bool, float]:
        """Detect if stem is vocal.
        
        Vocals have:
        - Higher spectral centroid (frequency content > 1500 Hz)
        - Higher zero crossing rate (more variation)
        - Lower transient density (less punchy than drums)
        
        Returns:
            (is_vocal, confidence)
        """
        sc = features['spectral_centroid']
        zcr = features['zcr']
        transient = features['transient_density']
        
        # Heuristics
        sc_score = min(1.0, (sc - 1000) / 2000)  # Expect 1000-3000 Hz
        zcr_score = min(1.0, zcr / 0.1)           # Expect 0.02-0.1
        transient_score = 1.0 - min(1.0, transient / 0.5)  # Expect < 0.5
        
        # Combined confidence
        confidence = np.mean([sc_score, zcr_score, transient_score])
        
        # Decision threshold
        is_vocal = confidence > 0.5
        
        return is_vocal, confidence
    
    def is_lead_vocal(self, features: Dict) -> Tuple[bool, float]:
        """Detect if vocal is lead (louder) vs background.
        
        Lead vocals: higher energy
        
        Returns:
            (is_lead, confidence)
        """
        energy_norm = features['energy_norm']
        
        # Lead typically > 0.6 normalized energy
        confidence = min(1.0, energy_norm / 0.7)
        
        is_lead = energy_norm > 0.5
        
        return is_lead, confidence
    
    def is_drums(self, features: Dict) -> Tuple[bool, float]:
        """Detect if stem is drums/percussion.
        
        Drums have:
        - High transient density (punchy attacks)
        - Lower spectral centroid (mostly bass + mids)
        - High onset strength
        
        Returns:
            (is_drums, confidence)
        """
        transient = features['transient_density']
        sc = features['spectral_centroid']
        onset = features['onset_strength']
        
        # Heuristics
        transient_score = min(1.0, transient / 0.4)  # High transients
        sc_score = 1.0 - min(1.0, sc / 2000)         # Lower frequencies
        onset_score = min(1.0, onset / 0.5)          # Strong onsets
        
        confidence = np.mean([transient_score, sc_score, onset_score])
        
        is_drums = confidence > 0.5
        
        return is_drums, confidence
    
    def classify_stem_type(self, features: Dict) -> Tuple[str, float]:
        """Classify stem into one of: vocal, drums, bass, melody, pad, other.
        
        Returns:
            (stem_type, confidence)
        """
        sc = features['spectral_centroid']
        zcr = features['zcr']
        transient = features['transient_density']
        onset = features['onset_strength']
        
        scores = {}
        
        # Vocal
        is_vocal, vocal_conf = self.is_vocal(features)
        scores['vocal'] = vocal_conf if is_vocal else vocal_conf * 0.5
        
        # Drums
        is_drums, drums_conf = self.is_drums(features)
        scores['drums'] = drums_conf if is_drums else drums_conf * 0.5
        
        # Bass (low frequencies, some transients)
        bass_score = (1.0 - min(1.0, sc / 500)) * (0.5 + transient / 2)
        scores['bass'] = bass_score
        
        # Pad/ambient (high spectral centroid, smooth, low transients)
        pad_score = (1.0 - transient) * min(1.0, sc / 3000)
        scores['pad'] = pad_score
        
        # Melody (vocal-like but instrumental, medium transients)
        melody_score = max(0, vocal_conf - 0.2) * (0.3 + transient / 2)
        scores['melody'] = melody_score
        
        # Normalize scores
        total = sum(scores.values()) + 1e-6
        scores = {k: v / total for k, v in scores.items()}
        
        stem_type = max(scores, key=scores.get)
        confidence = scores[stem_type]
        
        return stem_type, confidence
    
    # ========== SONG STRUCTURE DETECTION ==========
    
    def detect_song_section(self, y: np.ndarray) -> Tuple[str, float]:
        """Detect if audio is verse, chorus, bridge, intro, outro, or mixed.
        
        This is a heuristic based on energy, spectral content, and repetition.
        Full song analysis would need more context.
        
        For individual stems, we estimate based on energy profile.
        
        Returns:
            (section, confidence)
        """
        # Compute energy over time
        S = np.abs(librosa.stft(y))
        energy_frames = np.sqrt(np.sum(S ** 2, axis=0))
        
        # Normalize
        energy_norm = energy_frames / (np.max(energy_frames) + 1e-6)
        
        # Compute statistics
        mean_energy = np.mean(energy_norm)
        std_energy = np.std(energy_norm)
        max_energy = np.max(energy_norm)
        
        # Simple heuristics (in a full system, would use beat tracking + clustering)
        if max_energy > 0.8 and mean_energy > 0.6:
            # High energy, consistent → likely chorus
            section = 'chorus'
            confidence = 0.7
        elif mean_energy < 0.3:
            # Very low energy → likely intro/outro
            section = 'intro'  # (or outro, hard to distinguish without full song)
            confidence = 0.6
        elif std_energy > 0.2:
            # Variable energy → likely verse (vocal dynamics)
            section = 'verse'
            confidence = 0.6
        else:
            # Moderate, steady energy
            section = 'mixed'
            confidence = 0.4
        
        return section, confidence
    
    # ========== VOICE CLUSTERING ==========
    
    @staticmethod
    def cluster_voices(vocal_stems: List[np.ndarray], sr=44100, n_clusters=None) -> np.ndarray:
        """Cluster vocal stems by similarity (to distinguish between singers/artists).
        
        Args:
            vocal_stems: List of audio arrays (vocal stems)
            sr: Sample rate
            n_clusters: Number of clusters. If None, auto-detect (assumes 2-3 singers)
        
        Returns:
            Cluster assignments for each stem
        """
        if len(vocal_stems) < 2:
            return np.array([0] * len(vocal_stems))
        
        # Extract MFCCs for each stem
        mfcc_features = []
        for y in vocal_stems:
            if y.ndim == 2:
                y = y.mean(axis=0)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_features.append(mfcc.mean(axis=1))
        
        # Stack features
        X = np.array(mfcc_features)
        
        # Auto-detect clusters if not specified
        if n_clusters is None:
            n_clusters = max(2, min(3, len(vocal_stems)))
        
        # Cluster
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        kmeans = KMeans(n_clusters=min(n_clusters, len(vocal_stems)), random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        
        return clusters
    
    # ========== MAIN CLASSIFICATION PIPELINE ==========
    
    def classify(self, y: np.ndarray, filename: str) -> StemIdentity:
        """Classify a stem and return its identity object.
        
        Args:
            y: Audio array
            filename: Original filename (for reference)
        
        Returns:
            StemIdentity object with all classification results
        """
        # Extract features
        features = self.extract_features(y)
        
        # Create identity object
        identity = StemIdentity(filename)
        
        # Classify type
        identity.stem_type, identity.confidence = self.classify_stem_type(features)
        
        # If vocal, classify role
        if identity.stem_type == 'vocal':
            is_lead, lead_conf = self.is_lead_vocal(features)
            identity.role = 'lead' if is_lead else 'background'
        
        # Detect song section
        identity.section, section_conf = self.detect_song_section(y)
        
        # Store computed features
        identity.energy = features['energy_norm']
        identity.spectral_centroid = features['spectral_centroid']
        identity.zero_crossing_rate = features['zcr']
        identity.spectral_bandwidth = features['spectral_bandwidth']
        identity.transient_density = features['transient_density']
        
        return identity


def classify_stems(audio_dict: Dict[str, np.ndarray], sr=44100, cluster_vocals=False) -> Dict[str, StemIdentity]:
    """Classify all stems in a dict.
    
    Args:
        audio_dict: Dict mapping filenames to audio arrays
        sr: Sample rate
        cluster_vocals: Whether to cluster vocal stems (slow with many files)
    
    Returns:
        Dict mapping filenames to StemIdentity objects
    """
    classifier = StemClassifier(sr=sr)
    identities = {}
    
    # First pass: classify each stem
    for filename, y in audio_dict.items():
        identities[filename] = classifier.classify(y, filename)
    
    # Second pass: cluster voices if requested (optional, can be slow)
    if cluster_vocals:
        vocal_stems = {
            f: y for f, y in audio_dict.items()
            if identities[f].stem_type == 'vocal'
        }
        
        if len(vocal_stems) > 1:
            vocal_filenames = list(vocal_stems.keys())
            vocal_arrays = list(vocal_stems.values())
            clusters = StemClassifier.cluster_voices(vocal_arrays, sr=sr)
            
            for filename, cluster_id in zip(vocal_filenames, clusters):
                identities[filename].voice_cluster = int(cluster_id)
    
    return identities
