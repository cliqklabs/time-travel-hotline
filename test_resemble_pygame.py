#!/usr/bin/env python3
"""
Test ResembleAI audio with pygame
"""
import os
import requests
from dotenv import load_dotenv
from resemble import Resemble
from pydub import AudioSegment
import time
import pygame

# Load environment variables
load_dotenv()

def test_resemble_pygame():
    print("🎵 Testing ResembleAI audio with pygame...")
    try:
        # Initialize ResembleAI
        api_key = os.getenv("RESEMBLE_API_KEY")
        if not api_key:
            print("❌ RESEMBLE_API_KEY not found in .env file")
            return False
        Resemble.api_key(api_key)
        
        # Get projects
        projects = Resemble.v2.projects.all(1, 10)
        if not projects['items']:
            print("❌ No projects found")
            return False
        project_uuid = projects['items'][0]['uuid']
        voice_uuid = "cb5730f9"  # Your Elvis voice UUID
        
        # Create a test clip
        print("🎭 Generating test audio...")
        response = Resemble.v2.clips.create_sync(
            project_uuid=project_uuid,
            voice_uuid=voice_uuid,
            body="Hello, this is a test of the audio playback system.",
            title="Audio Pygame Test"
        )
        if not response.get('success'):
            print("❌ Failed to generate audio")
            return False
        
        audio_url = response['item']['audio_src']
        print(f"🎵 Audio URL: {audio_url}")
        
        # Download audio
        print("📥 Downloading audio...")
        audio_response = requests.get(audio_url)
        if audio_response.status_code != 200:
            print(f"❌ Failed to download audio: {audio_response.status_code}")
            return False
        
        print(f"✅ Audio downloaded: {len(audio_response.content)} bytes")
        
        # Save to file first
        temp_file = "test_resemble_audio.wav"
        with open(temp_file, 'wb') as f:
            f.write(audio_response.content)
        print(f"💾 Audio saved to: {temp_file}")
        
        # Load with pydub and boost volume
        audio_segment = AudioSegment.from_wav(temp_file)
        print(f"📊 Original volume: {audio_segment.dBFS}dB")
        
        # Boost volume significantly
        audio_segment = audio_segment + 25  # Boost by 25dB
        print(f"📊 Boosted volume: {audio_segment.dBFS}dB")
        
        # Save boosted audio
        boosted_file = "test_resemble_boosted.wav"
        audio_segment.export(boosted_file, format="wav")
        print(f"💾 Boosted audio saved to: {boosted_file}")
        
        # Initialize pygame mixer
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        print("🔊 Pygame mixer initialized")
        
        # Load and play audio
        print("🎵 Loading audio into pygame...")
        pygame.mixer.music.load(boosted_file)
        
        print("🔊 Playing audio with pygame...")
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        
        print("✅ Pygame playback completed!")
        
        # Clean up
        pygame.mixer.quit()
        os.remove(temp_file)
        os.remove(boosted_file)
        print(f"🗑️ Cleaned up temporary files")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_resemble_pygame()
    if success:
        print("\n🎉 Pygame test completed!")
    else:
        print("\n💥 Pygame test failed!")
