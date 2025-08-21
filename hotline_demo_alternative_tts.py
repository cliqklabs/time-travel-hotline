# hotline_demo_alternative_tts.py
import os, queue, time, threading
import sounddevice as sd
import webrtcvad
import argparse
from io import BytesIO
import wave
from deepgram import Deepgram
from openai import OpenAI
from pydub import AudioSegment
from simpleaudio import play_buffer
import numpy as np

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# TTS Provider imports - uncomment the ones you want to use
try:
    from elevenlabs import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    print("⚠️  ElevenLabs not available")

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("⚠️  Azure Speech not available")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    print("⚠️  gTTS not available")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("⚠️  pyttsx3 not available")

try:
    from resemble import Resemble
    RESEMBLE_AVAILABLE = True
except ImportError:
    RESEMBLE_AVAILABLE = False
    print("⚠️  ResembleAI not available")

try:
    from TTS.api import TTS
    XTTS_AVAILABLE = True
except ImportError:
    XTTS_AVAILABLE = False
    print("⚠️  XTTS (Coqui TTS) not available")

# Raspberry Pi specific imports
try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY_PI = True
except ImportError:
    IS_RASPBERRY_PI = False
    print("⚠️  RPi.GPIO not available - running in PC mode")

# Audio system detection
try:
    import alsaaudio
    AUDIO_SYSTEM = "alsa"
except ImportError:
    AUDIO_SYSTEM = "default"

MIN_RMS = 500  # adjust threshold up/down to tune sensitivity
BARGEIN_MIN_RMS = 2000  # Very high threshold for barge-in to reduce false triggers

def is_loud_enough(chunk):
    samples = np.frombuffer(chunk, dtype=np.int16)
    rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
    return rms > MIN_RMS

def is_loud_enough_for_bargein(chunk):
    """More stringent audio check for barge-in detection"""
    samples = np.frombuffer(chunk, dtype=np.int16)
    rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
    return rms > BARGEIN_MIN_RMS

def is_likely_echo(chunk):
    """Simple check to see if audio chunk might be echo from speakers"""
    global current_tts_audio
    if current_tts_audio is None:
        return False
    
    # Convert chunk to numpy array for analysis
    samples = np.frombuffer(chunk, dtype=np.int16)
    
    # Simple heuristic: if the audio has very consistent amplitude (like TTS),
    # it might be echo. Real speech has more variation.
    if len(samples) > 0:
        # Calculate coefficient of variation (std/mean)
        mean_amp = np.mean(np.abs(samples))
        std_amp = np.std(samples)
        if mean_amp > 0:
            cv = std_amp / mean_amp
            # TTS tends to have lower variation than human speech
            return cv < 0.3  # Threshold for "too consistent" audio
            
        # Additional check: if volume is too low, it's probably not real speech
        if mean_amp < 1000:  # Very low volume threshold
            return True
    return False

# ---------- RASPBERRY PI CONFIG ----------
# GPIO pins for rotary dial and hook switch
ROTARY_PIN_A = 17  # Rotary dial pulse A
ROTARY_PIN_B = 18  # Rotary dial pulse B  
HOOK_PIN = 27      # Hook switch (off-hook detection)
PROXIMITY_PIN = 22 # Proximity sensor for ringing
BELL_PIN = 23      # Bell control (relay)

# Audio settings optimized for Raspberry Pi
if IS_RASPBERRY_PI:
    SAMPLE_RATE = 16000  # Keep at 16kHz for Pi performance
    FRAME_MS = 30        # Slightly larger frames for Pi
    CHANNELS = 1
    VAD_SENSITIVITY = 2  # Less sensitive for Pi's audio quality
    MAX_UTTERANCE_SEC = 10  # Shorter for Pi's processing
    SILENCE_TAIL_MS = 800
else:
    # Original PC settings
    SAMPLE_RATE = 16000
    FRAME_MS = 20
    CHANNELS = 1
    VAD_SENSITIVITY = 3
    MAX_UTTERANCE_SEC = 12
    SILENCE_TAIL_MS = 700

# Barge-in controls
ENABLE_BARGEIN = True  # will be overridden by --mode at startup
BARGEIN_DEBOUNCE_FRAMES = 8   # require N consecutive "speech" frames before cutting TTS (increased from 3)
BARGEIN_VAD_SENSITIVITY = 0   # Least sensitive VAD for barge-in (0-3, lower = less sensitive)
TTS_PREROLL_MS = 120          # prevents first-phoneme cutoff
BARGEIN_DELAY_MS = 1000       # longer delay before enabling barge-in to avoid echo from TTS

# ---------- TTS CONFIGURATION ----------
# Choose your TTS provider here
TTS_PROVIDER = "elevenlabs"  # Options: "elevenlabs", "azure", "gtts", "pyttsx3", "resemble", "xtts"

# Voice configurations for different providers
CHARACTERS = {
    "3": {"name": "Albert Einstein", "voice_pref": "JBFqnCBsd6RMkjVDRZzb"},  # George
    "2": {"name": "Elvis Presley",   "voice_pref": "NFG5qt843uXKj4pFvR7C"},   # Adam Stone - late night radio
    "5": {"name": "Cleopatra",       "voice_pref": "XB0fDUnXU5powFXDhCwa"},   # Charlotte
    "7": {"name": "Beth Dutton",     "voice_pref": "cgSgspJ2msm6clMCkdW9"},   # Jessica
    "9": {"name": "Elon Musk",       "voice_pref": "ZUpjkf57YJ1LGUWaKauJ"},   # Roger
}

# Azure Speech voices (different from ElevenLabs)
AZURE_VOICES = {
    "Albert Einstein": "en-US-DavisNeural",  # Male, thoughtful
    "Elvis Presley": "en-US-GuyNeural",      # Male, warm
    "Cleopatra": "en-US-JennyNeural",        # Female, clear
    "Beth Dutton": "en-US-AriaNeural",       # Female, strong
    "Elon Musk": "en-US-DavisNeural",        # Male, thoughtful
}

# gTTS languages (simplified mapping)
GTTS_LANGUAGES = {
    "Albert Einstein": "en",
    "Elvis Presley": "en",
    "Cleopatra": "en", 
    "Beth Dutton": "en",
    "Elon Musk": "en",
}

# ResembleAI voice configurations
RESEMBLE_VOICES = {
	"Albert Einstein": {
		"voice_uuid": None,
		"reference_audio": "voices/einstein_reference.wav",
		"description": "Warm, wise, German accent"
	},
	"Elvis Presley": {
		"voice_uuid": "cb5730f9",
		"reference_audio": "voices/elvis_reference.wav",
		"description": "Southern charm, musical"
	},
	"Cleopatra": {
		"voice_uuid": None,
		"reference_audio": "voices/cleopatra_reference.wav",
		"description": "Regal, commanding, exotic"
	},
	"Beth Dutton": {
		"voice_uuid": None,
		"reference_audio": "voices/beth_reference.wav",
		"description": "Fierce, cutting, powerful"
	},
	"Elon Musk": {
		"voice_uuid": None,
		"reference_audio": "voices/elon_reference.wav",
		"description": "Technical, reflective, visionary"
	},
}

SYSTEM_PROMPTS = {
    "Albert Einstein": "You are Albert Einstein in 1946: warm, witty, plain-spoken. Explain ideas with simple analogies. Keep replies in 2–5 sentences. Stay in character.",
    "Elvis Presley":   "You are Elvis Presley, charming and playful. Light Southern cadence. Keep replies 2–4 sentences. Avoid modern slang.",
    "Cleopatra":       "You are Cleopatra VII Philopator. Regal, strategic, poetic. Reference Alexandria, the Nile, diplomacy. Keep replies 2–5 sentences.",
    "Beth Dutton":     "You are Beth Dutton. Fierce, sharp, sardonic. Keep replies short, cutting, with wit. PG-13.",
    "Elon Musk":       "You are Elon Musk. Speak in a thoughtful, slightly halting cadence with pauses, slight stutters, 'um,' 'you know,' or 'so yeah' as you form ideas aloud. Your tone is reflective and candid, never scripted. You think in first principles, quickly reducing complex problems to their physics roots. You value engineering elegance and efficiency, often mentioning 'economies of scale,' 'iterate fast,' and 'failure is an option here.' You're visionary and pragmatic, thinking about Mars colonization, AI, and long-term survival while staying grounded in engineering feasibility. Use short declarative statements with technical metaphors. Keep replies 2-4 sentences, expanding only for nuanced technical explanations. Inject slight humor with phrases like 'it's not magic, it's just physics' or 'fundamentally...'"
}

# ---------- CLIENTS ----------
# Initialize clients only when needed
dg = None
oai = None
eleven = None
azure_speech_config = None
pyttsx3_engine = None
resemble_project_uuid = None
xtts_engine = None
pygame_initialized = False  # Track pygame initialization

# XTTS voice cloning configurations
XTTS_VOICES = {
    "Albert Einstein": {
        "reference_audio": "voices/einstein_reference.wav",
        "description": "Warm, wise, German accent"
    },
    "Elvis Presley": {
        "reference_audio": "voices/elvis_reference.wav", 
        "description": "Southern charm, musical"
    },
    "Cleopatra": {
        "reference_audio": "voices/cleopatra_reference.wav",
        "description": "Regal, commanding, exotic"
    },
    "Beth Dutton": {
        "reference_audio": "voices/beth_reference.wav",
        "description": "Fierce, cutting, powerful"
    },
    "Elon Musk": {
        "reference_audio": "voices/elon_reference.wav",
        "description": "Technical, reflective, visionary"
    },
}

def init_clients():
    """Initialize API clients when needed"""
    global dg, oai, eleven, azure_speech_config, pyttsx3_engine, resemble_project_uuid, xtts_engine
    
    if dg is None:
        dg = Deepgram(os.getenv("DEEPGRAM_API_KEY"))
    if oai is None:
        oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Initialize TTS provider based on configuration
    if TTS_PROVIDER == "elevenlabs" and ELEVENLABS_AVAILABLE:
        if eleven is None:
            eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
    elif TTS_PROVIDER == "azure" and AZURE_AVAILABLE:
        if azure_speech_config is None:
            azure_speech_config = speechsdk.SpeechConfig(
                subscription=os.getenv("AZURE_SPEECH_KEY"), 
                region=os.getenv("AZURE_SPEECH_REGION")
            )
    elif TTS_PROVIDER == "pyttsx3" and PYTTSX3_AVAILABLE:
        if pyttsx3_engine is None:
            pyttsx3_engine = pyttsx3.init()
    elif TTS_PROVIDER == "resemble" and RESEMBLE_AVAILABLE:
        if resemble_project_uuid is None:
            # Initialize ResembleAI API key
            Resemble.api_key(os.getenv("RESEMBLE_API_KEY"))
            try:
                # Get the first project (you can modify this to use a specific project)
                projects = Resemble.v2.projects.all(1, 10)
                if projects['items']:
                    resemble_project_uuid = projects['items'][0]['uuid']
                    print(f"✅ ResembleAI initialized - using project: {resemble_project_uuid}")
                else:
                    print("❌ No ResembleAI projects found - please create a project in your dashboard")
                    resemble_project_uuid = None
            except Exception as e:
                print(f"❌ Failed to get ResembleAI projects: {e}")
                print("Please check your API key and ensure you have at least one project")
                resemble_project_uuid = None
    elif TTS_PROVIDER == "xtts" and XTTS_AVAILABLE:
        if xtts_engine is None:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                xtts_engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                print(f"✅ XTTS initialized on {device.upper()} - voice cloning ready")
            except Exception as e:
                print(f"❌ XTTS initialization failed: {e}")
                xtts_engine = None

def create_resemble_voice(character_name: str):
    """Get the existing ResembleAI voice UUID for a character"""
    try:
        char_config = RESEMBLE_VOICES.get(character_name)
        if not char_config:
            print(f"❌ No ResembleAI configuration found for character: {character_name}")
            return None
        
        voice_uuid = char_config["voice_uuid"]
        
        if not voice_uuid:
            print(f"❌ No voice UUID configured for character: {character_name}")
            return None
        
        print(f"✅ Using existing ResembleAI voice for {character_name}: {voice_uuid}")
        return voice_uuid
        
    except Exception as e:
        print(f"❌ Failed to get ResembleAI voice for {character_name}: {e}")
        return None

# Playback state (so we can stop it on barge-in)
current_playback = None
playback_lock = threading.Lock()
current_tts_audio = None  # Store current TTS audio for echo detection
bargein_audio_buffer = None  # Store audio that triggered barge-in

# ---------- TTS PROVIDER FUNCTIONS ----------
def generate_tts_audio(character_name: str, text: str) -> AudioSegment:
    """Generate TTS audio using the configured provider"""
    
    if TTS_PROVIDER == "elevenlabs" and ELEVENLABS_AVAILABLE:
        return generate_elevenlabs_audio(character_name, text)
    elif TTS_PROVIDER == "azure" and AZURE_AVAILABLE:
        return generate_azure_audio(character_name, text)
    elif TTS_PROVIDER == "gtts" and GTTS_AVAILABLE:
        return generate_gtts_audio(character_name, text)
    elif TTS_PROVIDER == "pyttsx3" and PYTTSX3_AVAILABLE:
        return generate_pyttsx3_audio(character_name, text)
    elif TTS_PROVIDER == "resemble" and RESEMBLE_AVAILABLE:
        return generate_resemble_audio(character_name, text)
    elif TTS_PROVIDER == "xtts" and XTTS_AVAILABLE:
        return generate_xtts_audio(character_name, text)
    else:
        print(f"❌ TTS provider '{TTS_PROVIDER}' not available")
        return None

def generate_elevenlabs_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using ElevenLabs"""
    try:
        # Find the voice ID for this character
        voice_id = None
        for char_id, char_data in CHARACTERS.items():
            if char_data["name"] == character_name:
                voice_id = char_data["voice_pref"]
                break
        
        if not voice_id:
            print(f"❌ No voice found for character: {character_name}")
            return None
            
        stream = eleven.text_to_speech.convert(
            voice_id,
            model_id="eleven_multilingual_v2",
            text=text,
        )
        audio_bytes = b"".join(stream)
        return AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
    except Exception as e:
        print(f"❌ ElevenLabs TTS failed: {e}")
        return None

def generate_azure_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using Azure Speech"""
    try:
        voice_name = AZURE_VOICES.get(character_name, "en-US-DavisNeural")
        azure_speech_config.speech_synthesis_voice_name = voice_name
        
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=azure_speech_config)
        result = speech_synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Azure returns audio data directly
            audio_data = result.audio_data
            # Convert to AudioSegment (assuming WAV format)
            audio_segment = AudioSegment(
                data=audio_data,
                sample_width=2,  # 16-bit
                frame_rate=16000,  # 16kHz
                channels=1  # Mono
            )
            return audio_segment
        else:
            print(f"❌ Azure TTS failed: {result.reason}")
            return None
    except Exception as e:
        print(f"❌ Azure TTS failed: {e}")
        return None

def generate_gtts_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using gTTS (Google Text-to-Speech)"""
    try:
        language = GTTS_LANGUAGES.get(character_name, "en")
        tts = gTTS(text=text, lang=language, slow=False)
        
        # Save to temporary file
        temp_file = "temp_tts.mp3"
        tts.save(temp_file)
        
        # Load as AudioSegment
        audio_segment = AudioSegment.from_mp3(temp_file)
        
        # Clean up temp file
        os.remove(temp_file)
        
        return audio_segment
    except Exception as e:
        print(f"❌ gTTS failed: {e}")
        return None

def generate_pyttsx3_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using pyttsx3 (offline TTS)"""
    try:
        # Configure voice properties
        voices = pyttsx3_engine.getProperty('voices')
        if voices:
            # Try to find a suitable voice
            for voice in voices:
                if "en" in voice.languages[0].lower():
                    pyttsx3_engine.setProperty('voice', voice.id)
                    break
        
        # Set speech rate and volume
        pyttsx3_engine.setProperty('rate', 150)  # Speed of speech
        pyttsx3_engine.setProperty('volume', 0.9)  # Volume level
        
        # Save to temporary file
        temp_file = "temp_tts.wav"
        pyttsx3_engine.save_to_file(text, temp_file)
        pyttsx3_engine.runAndWait()
        
        # Load as AudioSegment
        audio_segment = AudioSegment.from_wav(temp_file)
        
        # Clean up temp file
        os.remove(temp_file)
        
        return audio_segment
    except Exception as e:
        print(f"❌ pyttsx3 failed: {e}")
        return None

def generate_resemble_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using ResembleAI voice cloning"""
    try:
        # Get voice UUID
        voice_uuid = create_resemble_voice(character_name)
        if not voice_uuid:
            print(f"❌ No ResembleAI voice available for character: {character_name}")
            return None
        
        print(f"🎭 Generating ResembleAI audio for {character_name}...")
        
        # Use ResembleAI clips API for voice cloning
        init_clients()  # Make sure ResembleAI is initialized
        
        # Create clip using ResembleAI
        response = Resemble.v2.clips.create_sync(
            project_uuid=resemble_project_uuid,
            voice_uuid=voice_uuid,
            body=text,
            title=f"{character_name} Response"
        )
        
        # Check for API errors first
        if not response.get('success'):
            error_msg = response.get('message', 'Unknown error')
            print(f"❌ ResembleAI API error: {error_msg}")
            if 'usage limit' in error_msg.lower():
                print("💡 You've reached your ResembleAI usage limit. Please upgrade your account or wait for reset.")
            return None
        
        # Try different possible audio URL fields
        audio_url = None
        if response.get('success') and 'item' in response:
            item = response['item']
            if 'audio_src' in item:
                audio_url = item['audio_src']
            elif 'audio_url' in item:
                audio_url = item['audio_url']
            elif 'url' in item:
                audio_url = item['url']
        elif 'audio_src' in response:
            audio_url = response['audio_src']
        elif 'audio_url' in response:
            audio_url = response['audio_url']
        elif 'url' in response:
            audio_url = response['url']
        elif 'data' in response and isinstance(response['data'], dict):
            if 'audio_src' in response['data']:
                audio_url = response['data']['audio_src']
            elif 'audio_url' in response['data']:
                audio_url = response['data']['audio_url']
        
        if not audio_url:
            print(f"❌ No audio URL found in response")
            return None
        
        # Download the audio from the URL
        import requests
        
        audio_response = requests.get(audio_url)
        
        if audio_response.status_code == 200:
            # Convert to AudioSegment
            audio_segment = AudioSegment.from_wav(BytesIO(audio_response.content))
            
            # Boost volume by 15dB to make it louder
            audio_segment = audio_segment + 15
            
            print(f"📊 Audio volume: {audio_segment.dBFS}dB")
            return audio_segment
        else:
            print(f"❌ Failed to download ResembleAI audio: {audio_response.status_code}")
            return None
        
    except Exception as e:
        print(f"❌ ResembleAI TTS failed: {e}")
        return None

def generate_xtts_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using XTTS voice cloning"""
    try:
        # Get character configuration
        char_config = XTTS_VOICES.get(character_name)
        if not char_config:
            print(f"❌ No XTTS configuration found for character: {character_name}")
            return None
        
        reference_audio_path = char_config["reference_audio"]
        
        if not os.path.exists(reference_audio_path):
            print(f"❌ Reference audio file not found: {reference_audio_path}")
            return None
        
        # Generate audio using XTTS voice cloning
        wav = xtts_engine.tts(
            text=text,
            speaker_wav=reference_audio_path,
            language="en"
        )
        
        # Convert to AudioSegment
        import soundfile as sf
        
        # Save to temporary WAV file
        temp_file = "temp_xtts.wav"
        sf.write(temp_file, wav, xtts_engine.synthesizer.output_sample_rate, format='WAV')
        
        # Load as AudioSegment
        audio_segment = AudioSegment.from_wav(temp_file)
        
        # Clean up temp file
        os.remove(temp_file)
        return audio_segment
        
    except Exception as e:
        print(f"❌ XTTS failed: {e}")
        return None

# ---------- AUDIO CAPTURE ----------
def record_until_silence():
    """Record audio until silence is detected"""
    vad = webrtcvad.Vad(VAD_SENSITIVITY)
    buf, q = [], queue.Queue()
    def cb(indata, frames, time_info, status): q.put(bytes(indata))
    with sd.RawInputStream(samplerate=SAMPLE_RATE,
                           blocksize=int(SAMPLE_RATE * FRAME_MS / 1000),
                           channels=CHANNELS, dtype='int16', callback=cb):
        start = time.time()
        last_voice_ms = 0
        while True:
            chunk = q.get()
            buf.append(chunk)
            if len(chunk) == int(SAMPLE_RATE * FRAME_MS / 1000) * 2:
                if vad.is_speech(chunk, SAMPLE_RATE) and is_loud_enough(chunk):
                    last_voice_ms = (time.time() - start) * 1000
            elapsed_ms = (time.time() - start) * 1000
            if elapsed_ms > MAX_UTTERANCE_SEC * 1000: break
            if last_voice_ms > 0 and (elapsed_ms - last_voice_ms) > SILENCE_TAIL_MS: break
    return b"".join(buf)

def pcm16_to_wav_bytes(pcm_bytes, sample_rate=16000, channels=1):
    """Convert PCM16 bytes to WAV format"""
    bio = BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return bio.getvalue()

# ---------- ASR (Deepgram) ----------
import asyncio

def asr_deepgram_pcm16(audio_bytes):
    """Convert speech to text using Deepgram"""
    try:
        init_clients()  # Initialize clients if needed
        wav_bytes = pcm16_to_wav_bytes(audio_bytes, SAMPLE_RATE, CHANNELS)
        source = {"buffer": wav_bytes, "mimetype": "audio/wav"}
        
        # Create a new event loop for this async call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            resp = loop.run_until_complete(dg.transcription.prerecorded(source, {
                "model": "nova-2",
                "smart_format": True,
                "punctuate": True,
                "language": "en-US"
            }))
            alt = resp["results"]["channels"][0]["alternatives"][0]
            return alt["transcript"].strip() if alt["transcript"] else ""
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ Speech recognition failed: {e}")
        return ""

# ---------- TTS with barge-in ----------
def speak_tts_with_barge_in(character_name: str, text: str):
    """Play TTS with pre-roll; if barge-in enabled, stop as soon as user starts speaking."""
    global current_playback

    try:
        init_clients()  # Initialize clients if needed
        
        # Generate audio using the configured TTS provider
        seg = generate_tts_audio(character_name, text)
        if seg is None:
            print("❌ Failed to generate TTS audio")
            return
        
        print(f"✅ TTS audio generated: {len(seg)}ms, {seg.channels} channels, {seg.frame_rate}Hz")
        
        # Store TTS audio for echo detection
        global current_tts_audio
        current_tts_audio = seg
    except Exception as e:
        print(f"❌ Text-to-speech failed: {e}")
        return

    # Prepend a short silence to avoid cutting off first phoneme
    if TTS_PREROLL_MS > 0:
        seg = AudioSegment.silent(duration=TTS_PREROLL_MS) + seg

    # Start playback in a background thread
    def _play(segment: AudioSegment):
        global current_playback
        try:
            print(f"🔊 Starting audio playback...")
            print(f"   Audio details: {len(segment)}ms, {segment.channels} channels, {segment.frame_rate}Hz, {segment.sample_width} bytes")
            print(f"   Raw data length: {len(segment.raw_data)} bytes")
            
            # Use pygame for ResembleAI audio, simpleaudio for others
            if TTS_PROVIDER == "resemble":
                import pygame
                global pygame_initialized
                if not pygame_initialized:
                    pygame.mixer.init(frequency=segment.frame_rate, size=-16, channels=segment.channels)
                    pygame_initialized = True
                
                # Save to temporary file for pygame
                temp_file = "temp_playback.wav"
                segment.export(temp_file, format="wav")
                
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                
                # Create a simple wrapper to track playback state
                class PygamePlayback:
                    def __init__(self, temp_file):
                        self.temp_file = temp_file
                        self._playing = True
                    
                    def is_playing(self):
                        if not pygame.mixer.music.get_busy():
                            self._playing = False
                            try:
                                os.remove(self.temp_file)
                            except:
                                pass
                        return self._playing
                    
                    def stop(self):
                        pygame.mixer.music.stop()
                        self._playing = False
                        try:
                            os.remove(self.temp_file)
                        except:
                            pass
                
                current_playback = PygamePlayback(temp_file)
                print(f"✅ Pygame audio playback started")
                
            else:
                # Use simpleaudio for other TTS providers
                with playback_lock:
                    current_playback = play_buffer(segment.raw_data, segment.channels, segment.sample_width, segment.frame_rate)
                print(f"✅ Simpleaudio playback started")
            
            # Wait a moment and check if it's still playing
            time.sleep(0.1)
            if current_playback and current_playback.is_playing():
                print(f"✅ Audio is actively playing")
            else:
                print(f"❌ Audio stopped playing immediately")
                
        except Exception as e:
            print(f"❌ Audio playback failed: {e}")
            with playback_lock:
                current_playback = None
    
    t = threading.Thread(target=_play, args=(seg,), daemon=True)
    t.start()

    if not ENABLE_BARGEIN:
        t.join()
        # Wait for playback to finish
        while True:
            with playback_lock:
                po = current_playback
            if po is None or not po.is_playing():
                break
            time.sleep(0.05)
        return

    # Wait for initial TTS playback to avoid echo detection
    time.sleep(BARGEIN_DELAY_MS / 1000.0)

    # While playback is active, watch mic for speech; stop playback when detected
    vad = webrtcvad.Vad(BARGEIN_VAD_SENSITIVITY)  # Use less sensitive VAD for barge-in
    q = queue.Queue()
    
    # Audio buffer to capture speech that triggers barge-in
    audio_buffer = []
    buffer_size = int(2.0 * SAMPLE_RATE / (SAMPLE_RATE * FRAME_MS / 1000))  # 2 seconds of audio

    def mic_cb(indata, frames, time_info, status):
        # Push raw 16-bit bytes
        q.put(bytes(indata))

    debounce = 0
    start_time = time.time()
    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE,
                               blocksize=int(SAMPLE_RATE * FRAME_MS / 1000),
                               channels=CHANNELS, dtype='int16', callback=mic_cb):
            while True:
                # Check if playback already ended
                with playback_lock:
                    po = current_playback
                if po is None or not po.is_playing():
                    break

                try:
                    chunk = q.get(timeout=0.05)
                except queue.Empty:
                    continue

                # Add chunk to audio buffer (maintain rolling 2-second buffer)
                audio_buffer.append(chunk)
                if len(audio_buffer) > buffer_size:
                    audio_buffer.pop(0)

                # Only enable barge-in after a delay to avoid echo from TTS startup
                elapsed = time.time() - start_time
                if elapsed < 3.0:  # Disable barge-in for first 3 seconds
                    continue

                # More stringent barge-in detection: require VAD, volume, and not echo
                if (len(chunk) == int(SAMPLE_RATE * FRAME_MS / 1000) * 2 and 
                    vad.is_speech(chunk, SAMPLE_RATE) and 
                    is_loud_enough_for_bargein(chunk) and
                    not is_likely_echo(chunk)):
                    
                    debounce += 1
                    if debounce >= BARGEIN_DEBOUNCE_FRAMES:
                        print("🎤 Barge-in detected! Stopping TTS...")
                        # Stop playback
                        with playback_lock:
                            if current_playback:
                                current_playback.stop()
                                current_playback = None
                        
                        # Store the audio that triggered barge-in
                        global bargein_audio_buffer
                        bargein_audio_buffer = b"".join(audio_buffer)
                        return
                else:
                    debounce = 0

    except Exception as e:
        print(f"❌ Barge-in monitoring failed: {e}")
        with playback_lock:
            if current_playback:
                current_playback.stop()
                current_playback = None

# ---------- RASPBERRY PI HARDWARE CONTROL ----------
def init_gpio():
    """Initialize GPIO pins for rotary dial, hook switch, and bell"""
    if not IS_RASPBERRY_PI:
        return
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Rotary dial pins (input with pull-up)
    GPIO.setup(ROTARY_PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(ROTARY_PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Hook switch (input with pull-up)
    GPIO.setup(HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Proximity sensor (input with pull-up)
    GPIO.setup(PROXIMITY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Bell control (output)
    GPIO.setup(BELL_PIN, GPIO.OUT)
    GPIO.output(BELL_PIN, GPIO.LOW)  # Bell off initially
    
    print("✅ GPIO initialized for Raspberry Pi hardware")

def cleanup_gpio():
    """Clean up GPIO pins on exit"""
    if IS_RASPBERRY_PI:
        GPIO.cleanup()
        print("✅ GPIO cleaned up")
    
    # Clean up pygame if it was initialized
    global pygame_initialized
    if pygame_initialized:
        try:
            import pygame
            pygame.mixer.quit()
            print("✅ Pygame mixer cleaned up")
        except:
            pass

def ring_bell(duration=2):
    """Ring the phone bell for specified duration"""
    if not IS_RASPBERRY_PI:
        print("🔔 Bell ring simulation (PC mode)")
        return
    
    GPIO.output(BELL_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(BELL_PIN, GPIO.LOW)

def is_phone_off_hook():
    """Check if phone handset is lifted (off-hook)"""
    if not IS_RASPBERRY_PI:
        return True  # Always assume off-hook in PC mode
    
    try:
        return GPIO.input(HOOK_PIN) == GPIO.LOW  # LOW = off-hook
    except Exception as e:
        # Hardware not available, assume off-hook
        print(f"🔧 Hook detection: Hardware not available, assuming off-hook")
        return True

def is_someone_nearby():
    """Check proximity sensor for someone approaching"""
    if not IS_RASPBERRY_PI:
        return True  # Always assume someone nearby in PC mode
    
    try:
        return GPIO.input(PROXIMITY_PIN) == GPIO.LOW  # LOW = someone detected
    except Exception as e:
        print(f"🔧 Proximity detection: Hardware not available, assuming someone nearby")
        return True

# ---------- MAIN CONVERSATION LOOP ----------
def main():
    global ENABLE_BARGEIN
    global TTS_PROVIDER
    
    parser = argparse.ArgumentParser(description="AI Character Hotline")
    parser.add_argument("--mode", choices=["normal", "bargein"], default="normal",
                       help="Conversation mode: normal or bargein")
    parser.add_argument("--tts", choices=["elevenlabs", "azure", "gtts", "pyttsx3", "resemble", "xtts"], 
                       default=TTS_PROVIDER, help="TTS provider to use")
    args = parser.parse_args()
    
    # Set global configuration based on args
    ENABLE_BARGEIN = (args.mode == "bargein")
    TTS_PROVIDER = args.tts
    
    print(f"🎭 AI Character Hotline - TTS Provider: {TTS_PROVIDER}")
    print(f"🔊 Barge-in mode: {'ON' if ENABLE_BARGEIN else 'OFF'}")
    
    # Initialize hardware if on Raspberry Pi
    if IS_RASPBERRY_PI:
        init_gpio()
    
    try:
        # Main conversation loop
        while True:
            # Check if phone is off-hook (or always true in PC mode)
            if not is_phone_off_hook():
                time.sleep(0.1)
                continue
            
            # Check for someone nearby (or always true in PC mode)
            if not is_someone_nearby():
                time.sleep(0.1)
                continue
            
            # Ring bell to attract attention
            ring_bell(2)
            
            # Wait for user to pick up (simulated in PC mode)
            print("📞 Phone ringing... (press Enter to answer)")
            input()
            
            # Start conversation
            print("🎭 Welcome to the AI Character Hotline!")
            print("Dial a number to talk to a character:")
            for char_id, char_data in CHARACTERS.items():
                print(f"  {char_id} - {char_data['name']}")
            print("  0 - Hang up")
            
            # Get character selection
            selection = input("Dial: ").strip()
            if selection == "0":
                print("👋 Goodbye!")
                break
            
            if selection not in CHARACTERS:
                print("❌ Invalid selection")
                continue
            
            character = CHARACTERS[selection]
            character_name = character["name"]
            system_prompt = SYSTEM_PROMPTS[character_name]
            
            print(f"🎭 Connecting to {character_name}...")
            
            # Initial greeting
            greeting = f"Hello, this is {character_name}. How may I assist you today?"
            speak_tts_with_barge_in(character_name, greeting)
            
            # Conversation loop
            while True:
                # Check if still off-hook
                if not is_phone_off_hook():
                    print("📞 Phone hung up")
                    break
                
                # Get user input via speech recognition
                print("\n🎤 Listening... (speak now, or say 'hangup' to end call)")
                pcm = record_until_silence()
                if len(pcm) < 16000:  # Less than 1 second
                    continue
                
                print("📝 Transcribing...")
                user_input = asr_deepgram_pcm16(pcm)
                print(f"You: {user_input}")
                if not user_input:
                    continue
                
                if user_input.lower() in ['hangup', 'hang up', 'goodbye', 'bye']:
                    print("👋 Ending call...")
                    break
                
                if not user_input:
                    continue
                
                # Get AI response
                try:
                    response = oai.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_input}
                        ],
                        max_tokens=150,
                        temperature=0.8
                    )
                    
                    ai_response = response.choices[0].message.content.strip()
                    print(f"{character_name}: {ai_response}")
                    
                    # Speak the response
                    speak_tts_with_barge_in(character_name, ai_response)
                    
                except Exception as e:
                    print(f"❌ AI response failed: {e}")
                    error_msg = "I apologize, but I'm having trouble responding right now."
                    speak_tts_with_barge_in(character_name, error_msg)
    
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    finally:
        cleanup_gpio()

if __name__ == "__main__":
    main()
