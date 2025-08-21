#!/usr/bin/env python3
"""
Test script to demonstrate XTTS voice cloning with reference audio
"""

import os
import time
from pydub import AudioSegment
from TTS.api import TTS

def analyze_reference_audio():
    """Analyze the reference audio files"""
    print("🎤 REFERENCE AUDIO ANALYSIS")
    print("=" * 50)
    
    for file in ['elon_reference.wav', 'elvis_reference.wav']:
        path = f'voices/{file}'
        if os.path.exists(path):
            audio = AudioSegment.from_wav(path)
            print(f"\n📁 {file}:")
            print(f"   Duration: {len(audio)/1000:.1f} seconds")
            print(f"   File size: {os.path.getsize(path)/1024/1024:.1f} MB")
            print(f"   Quality: {audio.frame_rate}Hz, {audio.channels} channels, {audio.sample_width*8}bit")
            
            # Check if it's a real audio file or placeholder
            if len(audio) > 1000:  # More than 1 second
                print(f"   ✅ Real audio file - Good for voice cloning")
            else:
                print(f"   ⚠️  Placeholder file - Needs real audio")

def test_voice_cloning():
    """Test voice cloning with XTTS"""
    print("\n🎭 VOICE CLONING TEST")
    print("=" * 50)
    
    try:
        # Initialize XTTS
        print("📥 Loading XTTS model...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        print("✅ XTTS loaded successfully")
        
        # Test text
        test_text = "Hello, this is a test of voice cloning technology."
        
        # Test with Elon
        if os.path.exists('voices/elon_reference.wav'):
            print(f"\n🎤 Testing Elon voice cloning...")
            start_time = time.time()
            
            wav = tts.tts(
                text=test_text,
                speaker_wav="voices/elon_reference.wav",
                language="en"
            )
            
            end_time = time.time()
            print(f"✅ Generated in {end_time - start_time:.2f} seconds")
            
            # Save the result
            import soundfile as sf
            sf.write("elon_cloned_test.wav", wav, tts.synthesizer.output_sample_rate)
            print(f"💾 Saved as: elon_cloned_test.wav")
        
        # Test with Elvis
        if os.path.exists('voices/elvis_reference.wav'):
            print(f"\n🎤 Testing Elvis voice cloning...")
            start_time = time.time()
            
            wav = tts.tts(
                text=test_text,
                speaker_wav="voices/elvis_reference.wav",
                language="en"
            )
            
            end_time = time.time()
            print(f"✅ Generated in {end_time - start_time:.2f} seconds")
            
            # Save the result
            import soundfile as sf
            sf.write("elvis_cloned_test.wav", wav, tts.synthesizer.output_sample_rate)
            print(f"💾 Saved as: elvis_cloned_test.wav")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def explain_voice_cloning():
    """Explain how voice cloning works"""
    print("\n🔬 HOW VOICE CLONING WORKS")
    print("=" * 50)
    print("""
1. REFERENCE AUDIO ANALYSIS:
   • XTTS analyzes your reference audio file
   • Extracts voice characteristics (pitch, timbre, accent)
   • Learns phonetic patterns and speaking style
   • Creates a 'voice embedding' (digital fingerprint)

2. NEURAL VOICE SYNTHESIS:
   • Uses the voice embedding to guide text-to-speech
   • Generates new speech that matches the reference voice
   • Maintains the original voice's unique qualities
   • Adapts to different text while keeping the voice consistent

3. QUALITY FACTORS:
   • Reference audio quality (higher = better)
   • Duration (5-30 seconds is optimal)
   • Clarity (no background noise)
   • Speaking style consistency

4. YOUR SAMPLES:
   • Elon: 19.9s, 48kHz, stereo - Excellent quality
   • Elvis: 25.2s, 48kHz, stereo - Excellent quality
   • Both are real audio files, perfect for cloning
    """)

if __name__ == "__main__":
    analyze_reference_audio()
    explain_voice_cloning()
    test_voice_cloning()
    print("\n🎉 Voice cloning test complete!")
