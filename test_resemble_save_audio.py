#!/usr/bin/env python3
"""
Test ResembleAI audio by saving to file first, then playing
"""
import os
import requests
from dotenv import load_dotenv
from resemble import Resemble
from pydub import AudioSegment
from simpleaudio import play_buffer
import time
from io import BytesIO

# Load environment variables
load_dotenv()

def test_resemble_save_audio():
    print("🎵 Testing ResembleAI audio with file save...")
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
            title="Audio Save Test"
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
        
        # Load from file as AudioSegment
        audio_segment = AudioSegment.from_wav(temp_file)
        print(f"✅ Audio segment created: {len(audio_segment)}ms, {audio_segment.channels} channels, {audio_segment.frame_rate}Hz")
        print(f"📊 Audio volume: {audio_segment.dBFS}dB")
        
        # Boost volume
        audio_segment = audio_segment + 15  # Boost by 15dB
        print(f"📊 Boosted volume: {audio_segment.dBFS}dB")
        
        # Play audio
        print("🔊 Playing audio from file...")
        play_obj = play_buffer(
            audio_segment.raw_data,
            audio_segment.channels,
            audio_segment.sample_width,
            audio_segment.frame_rate
        )
        
        # Wait for playback to finish
        while play_obj.is_playing():
            time.sleep(0.1)
        
        print("✅ Audio playback completed!")
        
        # Clean up
        os.remove(temp_file)
        print(f"🗑️ Cleaned up: {temp_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_resemble_save_audio()
    if success:
        print("\n🎉 ResembleAI file save test successful!")
    else:
        print("\n💥 ResembleAI file save test failed!")
