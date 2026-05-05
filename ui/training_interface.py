"""Streamlit Training Interface for Auralis A/B Comparison.

This is a minimal feedback collection system that allows producers to:
1. Generate two slightly different mixes
2. Listen and compare them
3. Choose which is better (A, B, Tie, or Skip)
4. Provide training data for the mixing model

Design principles:
- Simple, single-page layout
- No forced choices (Skip option critical)
- Clear validation feedback
- Reliable data capture
"""

import streamlit as st
import numpy as np
import os
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.mix_generator import MixGenerator, to_json_compatible
from models.data_collector import log_mix_comparison
from utils.file_io import save_audio
from audio.validator import MixValidator

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Auralis - Training Interface",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🎵 Auralis Training Interface")
st.write(
    "Help improve the mixing system by comparing mixes. Your feedback trains the model."
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'mix_generator' not in st.session_state:
    try:
        st.session_state.mix_generator = MixGenerator()
    except Exception as e:
        st.error(f"❌ Failed to initialize mixer: {e}")
        st.stop()

if 'current_comparison' not in st.session_state:
    st.session_state.current_comparison = None

if 'choice_made' not in st.session_state:
    st.session_state.choice_made = False

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_validation_report(validation, name):
    """Format validation results for display."""
    status_icon = "✅" if validation['is_valid'] else "⚠️"
    
    report = f"{status_icon} **{name}**\n\n"
    
    if validation['is_valid']:
        report += f"Peak: {validation['peak_db']:.1f} dB  |  RMS: {validation['rms_db']:.1f} dB"
    else:
        report += "**Issues detected:**\n"
        for error in validation.get('errors', []):
            report += f"- {error}\n"
    
    if validation.get('warnings'):
        report += "\n**Warnings:**\n"
        for warning in validation['warnings']:
            report += f"- {warning}\n"
    
    return report

def save_comparison(params_a, params_b, choice):
    """Save comparison data to training log."""
    try:
        config = __import__('utils.audio_config', fromlist=['get_audio_config']).get_audio_config()
        log_mix_comparison(
            vocals_paths_dict={
                Path(vf).stem: f"resources/{vf}" 
                for vf in config["vocals"]
            },
            beat_path=f"resources/{config['beat']}",
            params_a=params_a,
            params_b=params_b,
            preference=choice
        )
        return True
    except Exception as e:
        st.error(f"Error saving comparison: {e}")
        return False

# ============================================================================
# MAIN UI
# ============================================================================

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Generate Comparison")
    if st.button("🔄 Generate New Mixes", use_container_width=True, key="generate_btn"):
        with st.spinner("Generating mixes... This may take a moment."):
            try:
                result = st.session_state.mix_generator.generate_comparison_mixes()
                
                # Export mixes to resources
                save_audio("resources/mix_a.wav", result['mix_a'], result['sr'])
                save_audio("resources/mix_b.wav", result['mix_b'], result['sr'])
                
                st.session_state.current_comparison = result
                st.session_state.choice_made = False
                st.success("✅ Mixes generated and ready!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to generate mixes: {e}")

with col2:
    st.subheader("Status")
    if st.session_state.current_comparison is None:
        st.info("👉 Click 'Generate New Mixes' to start")
    else:
        comp = st.session_state.current_comparison
        if comp['both_valid']:
            st.success("✅ Both mixes are valid")
        elif comp['at_least_one_good']:
            st.warning("⚠️ One mix has quality issues")
        else:
            st.error("❌ Both mixes are poor quality")

# ============================================================================
# SHOW VALIDATION RESULTS
# ============================================================================

if st.session_state.current_comparison is not None:
    st.divider()
    st.subheader("📊 Quality Validation")
    
    comp = st.session_state.current_comparison
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(format_validation_report(comp['validation_a'], "Mix A"))
    with col2:
        st.markdown(format_validation_report(comp['validation_b'], "Mix B"))
    
    if not comp['both_valid']:
        st.warning(
            "⚠️ **Quality Notice**: One or both mixes have issues. "
            "You can still rate them, but consider 'Skip' for poor pairs."
        )
    
    if not comp['at_least_one_good']:
        st.error(
            "❌ **Both Mixes Are Poor**: This pair won't be used for training. "
            "Click 'Generate New Mixes' to try again."
        )

# ============================================================================
# AUDIO COMPARISON
# ============================================================================

if st.session_state.current_comparison is not None and st.session_state.current_comparison['at_least_one_good']:
    st.divider()
    st.subheader("🎧 Listen and Compare")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Mix A")
        st.audio("resources/mix_a.wav", format="audio/wav")
    
    with col2:
        st.write("### Mix B")
        st.audio("resources/mix_b.wav", format="audio/wav")
    
    st.info(
        "ℹ️ **Tip**: Open both players in separate browser tabs for easy comparison. "
        "Use headphones for accurate listening."
    )

# ============================================================================
# USER DECISION
# ============================================================================

if st.session_state.current_comparison is not None and st.session_state.current_comparison['at_least_one_good']:
    st.divider()
    st.subheader("🗳️ Make Your Choice")
    
    if not st.session_state.choice_made:
        choice_col1, choice_col2, choice_col3, choice_col4 = st.columns(4)
        
        with choice_col1:
            if st.button("👍 A is Better", use_container_width=True, key="choice_a"):
                save_comparison(
                    st.session_state.current_comparison['params_a'],
                    st.session_state.current_comparison['params_b'],
                    'a'
                )
                st.session_state.choice_made = True
                st.success("✅ Feedback recorded! Mix A is better.")
                st.balloons()
                st.rerun()
        
        with choice_col2:
            if st.button("👍 B is Better", use_container_width=True, key="choice_b"):
                save_comparison(
                    st.session_state.current_comparison['params_a'],
                    st.session_state.current_comparison['params_b'],
                    'b'
                )
                st.session_state.choice_made = True
                st.success("✅ Feedback recorded! Mix B is better.")
                st.balloons()
                st.rerun()
        
        with choice_col3:
            if st.button("🤝 They're Equal", use_container_width=True, key="choice_tie"):
                save_comparison(
                    st.session_state.current_comparison['params_a'],
                    st.session_state.current_comparison['params_b'],
                    'tie'
                )
                st.session_state.choice_made = True
                st.success("✅ Feedback recorded! Mixes are equally good.")
                st.balloons()
                st.rerun()
        
        with choice_col4:
            if st.button("⏭️ Skip This Pair", use_container_width=True, key="choice_skip"):
                st.session_state.choice_made = True
                st.warning("⏭️ Comparison skipped. This pair won't be used for training.")
                st.rerun()
    else:
        st.success("✅ Your feedback has been recorded.")
        if st.button("🔄 Compare Another Pair", use_container_width=True):
            st.session_state.current_comparison = None
            st.session_state.choice_made = False
            st.rerun()

# ============================================================================
# FOOTER & INFO
# ============================================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📚 How It Works")
    st.markdown(
        """
        1. **Generate**: System creates two mixes with slight parameter variations
        2. **Listen**: You compare Mix A and Mix B
        3. **Rate**: Choose which is better (or skip if both are poor)
        4. **Learn**: Model learns from your preferences to improve future mixes
        """
    )

with col2:
    st.markdown("### ⚡ Tips")
    st.markdown(
        """
        - Use **good listening environment** (speakers or headphones)
        - **Trust your ears** - your preference is valid
        - **Skip liberally** - don't force choices on poor mixes
        - Collect **5-10 comparisons**, then retrain the model
        - Be **consistent** in your listening setup
        """
    )

with col3:
    st.markdown("### 🛡️ Data Collection")
    st.markdown(
        """
        We capture:
        - Audio features from your stems
        - Parameters used for each mix
        - Your choice (A, B, tie, or skip)
        - Stem classifications (vocals, drums, etc.)
        
        **Skip is never recorded as training data.**
        """
    )

# Display statistics
st.divider()
st.subheader("📈 Training Progress")

try:
    if os.path.exists("data/mix_comparisons.jsonl"):
        with open("data/mix_comparisons.jsonl") as f:
            lines = f.readlines()
        
        total_logged = len(lines)
        skipped = sum(1 for line in lines if '"skip"' in line.lower() or '"preference": "skip"' in line)
        valid_comparisons = total_logged - skipped
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Logged", total_logged)
        with col2:
            st.metric("Valid (Training)", valid_comparisons)
        with col3:
            st.metric("Skipped", skipped)
        
        if valid_comparisons >= 5:
            st.info(
                f"✅ You have **{valid_comparisons}** valid comparisons. "
                "Ready to train! Run: `python train.py`"
            )
    else:
        st.info("👉 Start collecting comparisons to train the model!")
except Exception as e:
    st.debug(f"Could not load statistics: {e}")
