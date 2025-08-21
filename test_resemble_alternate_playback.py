#!/usr/bin/env python3
"""
Test ResembleAI audio with different playback methods
"""
import os
import requests
from dotenv import load_dotenv
from resemble import Resemble
from pydub import AudioSegment
import time
from io import BytesIO

# Load environment variables
load_dotenv()

def test_resemble_alternate_playback():
    print("🎵 Testing ResembleAI audio with alternate playback methods...")
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
            title="Audio Alternate Test"
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
        
        # Method 1: Try simpleaudio
        print("\n🔊 Method 1: simpleaudio")
        try:
            from simpleaudio import play_buffer
            audio_segment = AudioSegment.from_wav(temp_file)
            print(f"   Audio: {len(audio_segment)}ms, {audio_segment.channels} channels, {audio_segment.frame_rate}Hz")
            print(f"   Volume: {audio_segment.dBFS}dB")
            
            # Boost volume significantly
            audio_segment = audio_segment + 20  # Boost by 20dB
            print(f"   Boosted volume: {audio_segment.dBFS}dB")
            
            play_obj = play_buffer(
                audio_segment.raw_data,
                audio_segment.channels,
                audio_segment.sample_width,
                audio_segment.frame_rate
            )
            
            while play_obj.is_playing():
                time.sleep(0.1)
            print("   ✅ simpleaudio playback completed")
            
        except Exception as e:
            print(f"   ❌ simpleaudio failed: {e}")
        
        # Method 2: Try pygame
        print("\n🔊 Method 2: pygame")
        try:
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
            
            audio_segment = AudioSegment.from_wav(temp_file)
            audio_segment = audio_segment + 20  # Boost volume
            
            # Save as temporary file for pygame
            pygame_temp = "temp_pygame.wav"
            audio_segment.export(pygame_temp, format="wav")
            
            pygame.mixer.music.load(pygame_temp)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            pygame.mixer.quit()
            os.remove(pygame_temp)
            print("   ✅ pygame playback completed")
            
        except Exception as e:
            print(f"   ❌ pygame failed: {e}")
        
        # Method 3: Try playsound
        print("\n🔊 Method 3: playsound")
        try:
            from playsound import playsound
            
            audio_segment = AudioSegment.from_wav(temp_file)
            audio_segment = audio_segment + 20  # Boost volume
            
            # Save as temporary file for playsound
            playsound_temp = "temp_playsound.wav"
            audio_segment.export(playsound_temp, format="wav")
            
            playsound(playsound_temp)
            
            os.remove(playsound_temp)
            print("   ✅ playsound playback completed")
            
        except Exception as e:
            print(f"   ❌ playsound failed: {e}")
        
        # Clean up
        os.remove(temp_file)
        print(f"\n🗑️ Cleaned up: {temp_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_resemble_alternate_playback()
    if success:
        print("\n🎉 Alternate playback test completed!")
    else:
        print("\n💥 Alternate playback test failed!")
