#!/usr/bin/env python3
"""
Test audio playback with ResembleAI generated audio
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

def test_audio_playback():
    print("🎵 Testing ResembleAI audio playback...")
    
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
            title="Audio Playback Test"
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
        
        # Convert to AudioSegment
        audio_segment = AudioSegment.from_wav(BytesIO(audio_response.content))
        print(f"✅ Audio segment created: {len(audio_segment)}ms, {audio_segment.channels} channels, {audio_segment.frame_rate}Hz")
        
        # Play audio
        print("🔊 Playing audio...")
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
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_audio_playback()
    if success:
        print("\n🎉 Audio playback test successful!")
    else:
        print("\n💥 Audio playback test failed!")
