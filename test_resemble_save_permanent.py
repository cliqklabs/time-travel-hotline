#!/usr/bin/env python3
"""
Test ResembleAI audio and save permanently for examination
"""
import os
import requests
from dotenv import load_dotenv
from resemble import Resemble
from pydub import AudioSegment
import time

# Load environment variables
load_dotenv()

def test_resemble_save_permanent():
    print("🎵 Testing ResembleAI audio and saving permanently...")
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
            title="Audio Permanent Test"
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
        
        # Save to permanent file
        permanent_file = "resemble_test_audio.wav"
        with open(permanent_file, 'wb') as f:
            f.write(audio_response.content)
        print(f"💾 Audio saved permanently to: {permanent_file}")
        
        # Load with pydub and analyze
        audio_segment = AudioSegment.from_wav(permanent_file)
        print(f"📊 Audio analysis:")
        print(f"   Duration: {len(audio_segment)}ms")
        print(f"   Channels: {audio_segment.channels}")
        print(f"   Sample rate: {audio_segment.frame_rate}Hz")
        print(f"   Sample width: {audio_segment.sample_width} bytes")
        print(f"   Volume: {audio_segment.dBFS}dB")
        print(f"   Max amplitude: {audio_segment.max_possible_amplitude}")
        
        # Check if audio has any content
        if audio_segment.dBFS < -60:
            print("⚠️  Audio appears to be very quiet or silent")
        elif audio_segment.dBFS > -10:
            print("✅ Audio appears to have good volume")
        else:
            print("📊 Audio volume is moderate")
        
        # Create a boosted version
        boosted_file = "resemble_test_boosted.wav"
        boosted_audio = audio_segment + 30  # Boost by 30dB
        boosted_audio.export(boosted_file, format="wav")
        print(f"💾 Boosted audio saved to: {boosted_file}")
        print(f"📊 Boosted volume: {boosted_audio.dBFS}dB")
        
        print(f"\n📁 Files saved:")
        print(f"   Original: {permanent_file}")
        print(f"   Boosted: {boosted_file}")
        print(f"\n🎵 Try playing these files with your system media player to test if they work!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_resemble_save_permanent()
    if success:
        print("\n🎉 Audio files saved successfully!")
    else:
        print("\n💥 Failed to save audio files!")
