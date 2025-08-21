#!/usr/bin/env python3
"""
Test simple audio playback with a generated tone
"""
import numpy as np
from pydub import AudioSegment
from simpleaudio import play_buffer
import time

def test_simple_audio():
    print("🎵 Testing simple audio playback...")
    
    # Generate a simple 440Hz sine wave for 2 seconds
    sample_rate = 22050
    duration = 2.0  # seconds
    frequency = 440  # Hz (A4 note)
    
    # Generate the sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM
    audio_data = (tone * 32767).astype(np.int16)
    
    print(f"🔊 Playing 440Hz tone for 2 seconds...")
    print(f"   Sample rate: {sample_rate}Hz")
    print(f"   Duration: {duration}s")
    print(f"   Data length: {len(audio_data)} samples")
    
    # Play the audio
    play_obj = play_buffer(audio_data.tobytes(), 1, 2, sample_rate)
    
    # Wait for playback to finish
    while play_obj.is_playing():
        time.sleep(0.1)
    
    print("✅ Simple audio test completed!")
    return True

if __name__ == "__main__":
    success = test_simple_audio()
    if success:
        print("\n🎉 Simple audio test successful!")
    else:
        print("\n💥 Simple audio test failed!")
