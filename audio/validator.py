"""
Audio Validation Module - Ensures mixes meet quality standards before logging to training data.

Implements MANDATORY checks from MIXING_GUIDELINES.md
"""

import numpy as np
from typing import Dict, Tuple

class MixValidator:
    """Validates generated mixes against safety and quality standards."""
    
    # Safety thresholds (from MIXING_GUIDELINES.md)
    MAX_PEAK_DB = -0.5  # Safe headroom: peaks should be at least -0.5 dB from clipping
    LIMITER_THRESHOLD = 0.9  # Limiter should engage before peaks exceed this
    MAX_RMS_DB = -6.0  # Mixes shouldn't be dangerously loud
    MIN_RMS_DB = -30.0  # Mixes shouldn't be too quiet to be useful
    CLIPPING_THRESHOLD = 0.98  # Anything above this is considered clipping
    
    @staticmethod
    def get_peak_db(audio: np.ndarray) -> float:
        """Get peak level in dB."""
        audio = np.asarray(audio)
        peak = np.max(np.abs(audio))
        if peak < 1e-10:
            return -np.inf
        return 20 * np.log10(peak)
    
    @staticmethod
    def get_rms_db(audio: np.ndarray) -> float:
        """Get RMS level in dB."""
        audio = np.asarray(audio)
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-10:
            return -np.inf
        return 20 * np.log10(rms)
    
    @staticmethod
    def check_clipping(audio: np.ndarray, threshold: float = 0.98) -> Tuple[bool, int]:
        """
        Check if audio contains clipping (samples near or exceeding ±1.0).
        
        Returns:
            (is_clipped, num_clipped_samples)
        """
        audio = np.asarray(audio)
        clipped_samples = np.sum(np.abs(audio) > threshold)
        return clipped_samples > 0, clipped_samples
    
    @staticmethod
    def check_distortion(audio: np.ndarray) -> Tuple[bool, Dict]:
        """
        Detect signs of distortion through harmonic analysis.
        
        Returns:
            (has_distortion, details_dict)
        """
        audio = np.asarray(audio)
        peak = np.max(np.abs(audio))
        
        if peak < 1e-10:
            return False, {"reason": "Silent audio"}
        
        # If peak is above limiter threshold without being hard-clipped,
        # it might indicate soft-clipping artifacts
        if peak > MixValidator.LIMITER_THRESHOLD and peak < 0.99:
            return True, {"reason": "Soft-clipping detected (peak above limiter without hard clipping)"}
        
        # Check for excessive high-frequency content (often indicates distortion)
        # This is a simple heuristic
        if len(audio) > 1000:
            diff = np.abs(np.diff(audio))
            high_frequency_energy = np.mean(diff)
            if high_frequency_energy > 0.3:
                return True, {"reason": "High transient energy (possible distortion)", "energy": float(high_frequency_energy)}
        
        return False, {"reason": "No distortion detected"}
    
    @classmethod
    def validate_mix(cls, audio: np.ndarray, mix_name: str = "mix") -> Dict:
        """
        Comprehensive validation of a mix.
        
        Returns dict with:
            - is_valid: bool
            - is_good: bool (more permissive, still trainable)
            - checks: dict of all check results
            - warnings: list of warnings
            - errors: list of errors
        """
        audio = np.asarray(audio)
        
        checks = {}
        errors = []
        warnings = []
        
        # 1. Peak level check
        peak_db = cls.get_peak_db(audio)
        checks['peak_db'] = peak_db
        if peak_db > 0:
            errors.append(f"CRITICAL: Peak level is {peak_db:.2f} dB (above 0 dB = clipping)")
        elif peak_db > cls.MAX_PEAK_DB:
            warnings.append(f"Peak level is {peak_db:.2f} dB (recommended <= {cls.MAX_PEAK_DB} dB for headroom)")
        else:
            checks['peak_level_ok'] = True
        
        # 2. Clipping detection
        is_clipped, num_clipped = cls.check_clipping(audio)
        checks['clipped_samples'] = num_clipped
        if is_clipped:
            errors.append(f"CRITICAL: {num_clipped} samples are clipping")
        else:
            checks['clipping_ok'] = True
        
        # 3. Distortion detection
        has_distortion, distortion_details = cls.check_distortion(audio)
        checks['distortion'] = distortion_details
        if has_distortion:
            errors.append(f"DISTORTION DETECTED: {distortion_details.get('reason', 'Unknown')}")
        else:
            checks['distortion_ok'] = True
        
        # 4. RMS level check
        rms_db = cls.get_rms_db(audio)
        checks['rms_db'] = rms_db
        if rms_db < cls.MIN_RMS_DB:
            errors.append(f"Mix is too quiet (RMS {rms_db:.2f} dB < {cls.MIN_RMS_DB} dB)")
        elif rms_db > cls.MAX_RMS_DB:
            warnings.append(f"Mix is loud (RMS {rms_db:.2f} dB, consider reducing)")
        else:
            checks['rms_level_ok'] = True
        
        # 5. Check audio is not silent or too quiet for practical use
        peak_linear = 10 ** (peak_db / 20)
        if peak_linear < 0.01:  # Peak below -40 dB
            errors.append("Mix is essentially silent")
        
        # Determine validity
        is_valid = len(errors) == 0
        is_good = is_valid and len(warnings) == 0
        
        return {
            'mix_name': mix_name,
            'is_valid': is_valid,
            'is_good': is_good,
            'checks': checks,
            'warnings': warnings,
            'errors': errors,
            'peak_db': peak_db,
            'rms_db': rms_db,
        }
    
    @classmethod
    def format_validation_report(cls, validation_result: Dict) -> str:
        """Format validation result as human-readable report."""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"VALIDATION REPORT: {validation_result['mix_name'].upper()}")
        lines.append(f"{'='*60}")
        
        if validation_result['is_valid']:
            lines.append("[OK] STATUS: VALID (passes all safety checks)")
        else:
            lines.append("[FAIL] STATUS: INVALID (fails safety checks)")
        
        if validation_result['is_good']:
            lines.append("[OK] QUALITY: GOOD (ready for training)")
        elif validation_result['is_valid']:
            lines.append("[WARNING] QUALITY: ACCEPTABLE (trainable, but has warnings)")
        else:
            lines.append("[FAIL] QUALITY: POOR (should not train on this mix)")
        
        lines.append(f"\nMetrics:")
        lines.append(f"  Peak Level:  {validation_result['peak_db']:7.2f} dB  (target <= -0.5 dB)")
        lines.append(f"  RMS Level:   {validation_result['rms_db']:7.2f} dB  (target -15 to -6 dB)")
        
        if validation_result['checks'].get('clipped_samples', 0) > 0:
            lines.append(f"  Clipping:    [FAIL] {validation_result['checks']['clipped_samples']} samples")
        else:
            lines.append(f"  Clipping:    [OK] None detected")
        
        if validation_result['errors']:
            lines.append(f"\n[ERROR] ERRORS ({len(validation_result['errors'])}):")
            for error in validation_result['errors']:
                lines.append(f"   - {error}")
        
        if validation_result['warnings']:
            lines.append(f"\n[WARNING] WARNINGS ({len(validation_result['warnings'])}):")
            for warning in validation_result['warnings']:
                lines.append(f"   - {warning}")
        
        if not validation_result['errors'] and not validation_result['warnings']:
            lines.append("\n[OK] All checks passed!")
        
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)
