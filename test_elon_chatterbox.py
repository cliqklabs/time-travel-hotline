#!/usr/bin/env python3
"""
Simple test script for Chatterbox TTS with Elon Musk
"""

import os
import time
from chatterbox import ChatterboxTTS
from pydub import AudioSegment
import soundfile as sf

def test_chatterbox_basic():
    """Test basic Chatterbox TTS without voice cloning"""
    print("🎭 Testing Chatterbox TTS with Elon Musk...")
    
    try:
        # Initialize Chatterbox
        print("📥 Initializing Chatterbox TTS...")
        tts = ChatterboxTTS.from_pretrained(device='cpu')
        print("✅ Chatterbox initialized successfully")
        
        # Test basic generation
        test_text = "Hello, this is Elon Musk. How may I assist you today?"
        print(f"🎤 Generating: '{test_text}'")
        
        start_time = time.time()
        wav = tts.generate(text=test_text)
        end_time = time.time()
        
        print(f"✅ Audio generated in {end_time - start_time:.2f} seconds")
        print(f"📊 Audio shape: {wav.shape}")
        print(f"📊 Sample rate: {tts.sr}")
        
        # Convert to AudioSegment and save
        import torch
        audio_numpy = wav.cpu().numpy().squeeze()
        temp_file = "elon_test.wav"
        sf.write(temp_file, audio_numpy, tts.sr, format='WAV')
        
        # Load as AudioSegment
        audio_segment = AudioSegment.from_wav(temp_file)
        print(f"✅ Audio saved as {temp_file} ({len(audio_segment)}ms)")
        
        # Clean up
        os.remove(temp_file)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_chatterbox_basic()
    if success:
        print("\n🎉 Chatterbox test successful!")
    else:
        print("\n💥 Chatterbox test failed!")


