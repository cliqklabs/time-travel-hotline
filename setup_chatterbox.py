#!/usr/bin/env python3
"""
Setup script for Chatterbox TTS integration
This script helps you set up reference audio files for Chatterbox TTS
"""

import os
import sys
import shutil
from pathlib import Path

def create_voices_directory():
    """Create the voices directory structure"""
    voices_dir = Path("voices")
    voices_dir.mkdir(exist_ok=True)
    print(f"✅ Created voices directory: {voices_dir}")
    return voices_dir

def create_sample_reference_files(voices_dir):
    """Create sample reference audio file placeholders"""
    reference_files = {
        "einstein_reference.wav": "Albert Einstein - Warm, wise, German accent",
        "elvis_reference.wav": "Elvis Presley - Southern charm, musical",
        "cleopatra_reference.wav": "Cleopatra - Regal, commanding, exotic",
        "beth_reference.wav": "Beth Dutton - Fierce, cutting, powerful",
        "elon_reference.wav": "Elon Musk - Technical, reflective, visionary"
    }
    
    print("\n📁 Creating reference audio file placeholders:")
    for filename, description in reference_files.items():
        filepath = voices_dir / filename
        if not filepath.exists():
            # Create a placeholder file with instructions
            with open(filepath, 'w') as f:
                f.write(f"# Placeholder for {description}\n")
                f.write(f"# Replace this file with 5-20 seconds of clean audio\n")
                f.write(f"# Format: WAV, 16kHz, mono recommended\n")
                f.write(f"# This file should contain speech in the character's voice\n")
            print(f"   📄 {filename} - {description}")
        else:
            print(f"   ✅ {filename} (already exists)")

def print_setup_instructions():
    """Print detailed setup instructions"""
    print("\n" + "="*60)
    print("🎤 CHATTERBOX TTS SETUP INSTRUCTIONS")
    print("="*60)
    
    print("\n1️⃣ INSTALL CHATTERBOX:")
    print("   pip install chatterbox-tts")
    
    print("\n2️⃣ PREPARE REFERENCE AUDIO FILES:")
    print("   For each character, you need 5-20 seconds of clean audio.")
    print("   Place these files in the 'voices/' directory:")
    print("   - voices/einstein_reference.wav")
    print("   - voices/elvis_reference.wav")
    print("   - voices/cleopatra_reference.wav")
    print("   - voices/beth_reference.wav")
    print("   - voices/elon_reference.wav")
    
    print("\n3️⃣ AUDIO REQUIREMENTS:")
    print("   ✅ Format: WAV (recommended) or MP3")
    print("   ✅ Duration: 5-20 seconds")
    print("   ✅ Quality: Clear, no background noise")
    print("   ✅ Content: Natural speech in character's voice")
    print("   ✅ Sample rate: 16kHz or higher")
    
    print("\n4️⃣ WHERE TO FIND REFERENCE AUDIO:")
    print("   🎬 Movie/TV clips (ensure you have rights)")
    print("   🎵 Public domain recordings")
    print("   🎤 Your own voice acting")
    print("   📺 YouTube clips (with permission)")
    print("   🎭 AI-generated samples (from other TTS)")
    
    print("\n5️⃣ TEST CHATTERBOX:")
    print("   python hotline_demo_alternative_tts.py --tts chatterbox")
    
    print("\n6️⃣ EMOTION INTENSITY SETTINGS:")
    print("   Current settings in the code:")
    print("   - Einstein: 0.3 (thoughtful, measured)")
    print("   - Elvis: 0.7 (charming, expressive)")
    print("   - Cleopatra: 0.8 (regal, dramatic)")
    print("   - Beth: 0.9 (sharp, intense)")
    print("   - Elon: 0.4 (thoughtful, technical)")
    
    print("\n" + "="*60)

def check_chatterbox_installation():
    """Check if Chatterbox is properly installed"""
    try:
        import chatterbox_tts
        print("✅ Chatterbox TTS is installed")
        return True
    except ImportError:
        print("❌ Chatterbox TTS is not installed")
        print("   Run: pip install chatterbox-tts")
        return False

def main():
    print("🎭 Chatterbox TTS Setup for AI Character Hotline")
    print("="*50)
    
    # Check installation
    if not check_chatterbox_installation():
        print("\nPlease install Chatterbox TTS first:")
        print("pip install chatterbox-tts")
        return
    
    # Create directory structure
    voices_dir = create_voices_directory()
    
    # Create sample files
    create_sample_reference_files(voices_dir)
    
    # Print instructions
    print_setup_instructions()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Add your reference audio files to the 'voices/' directory")
    print("2. Test with: python hotline_demo_alternative_tts.py --tts chatterbox")
    print("3. Adjust emotion_intensity values in the code if needed")
    
    print("\n💡 TIP: Start with one character to test, then add more!")

if __name__ == "__main__":
    main()
