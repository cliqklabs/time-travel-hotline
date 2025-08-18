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
    from chatterbox_tts import Chatterbox
    CHATTERBOX_AVAILABLE = True
except ImportError:
    CHATTERBOX_AVAILABLE = False
    print("⚠️  Chatterbox TTS not available")

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
TTS_PROVIDER = "elevenlabs"  # Options: "elevenlabs", "azure", "gtts", "pyttsx3", "chatterbox"

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

# Chatterbox TTS reference audio files and emotion settings
CHATTERBOX_VOICES = {
    "Albert Einstein": {
        "reference_audio": "voices/einstein_reference.wav",
        "emotion_intensity": 0.3,  # Thoughtful, measured
        "description": "Warm, wise, German accent"
    },
    "Elvis Presley": {
        "reference_audio": "voices/elvis_reference.wav", 
        "emotion_intensity": 0.7,  # Charming, expressive
        "description": "Southern charm, musical"
    },
    "Cleopatra": {
        "reference_audio": "voices/cleopatra_reference.wav",
        "emotion_intensity": 0.8,  # Regal, dramatic
        "description": "Regal, commanding, exotic"
    },
    "Beth Dutton": {
        "reference_audio": "voices/beth_reference.wav",
        "emotion_intensity": 0.9,  # Sharp, intense
        "description": "Fierce, cutting, powerful"
    },
    "Elon Musk": {
        "reference_audio": "voices/elon_reference.wav",
        "emotion_intensity": 0.4,  # Thoughtful, technical
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
chatterbox_tts = None

def init_clients():
    """Initialize API clients when needed"""
    global dg, oai, eleven, azure_speech_config, pyttsx3_engine, chatterbox_tts
    
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
    elif TTS_PROVIDER == "chatterbox" and CHATTERBOX_AVAILABLE:
        if chatterbox_tts is None:
            chatterbox_tts = Chatterbox()

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
    elif TTS_PROVIDER == "chatterbox" and CHATTERBOX_AVAILABLE:
        return generate_chatterbox_audio(character_name, text)
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

def generate_chatterbox_audio(character_name: str, text: str) -> AudioSegment:
    """Generate audio using Chatterbox TTS"""
    try:
        # Get character configuration
        char_config = CHATTERBOX_VOICES.get(character_name)
        if not char_config:
            print(f"❌ No Chatterbox configuration found for character: {character_name}")
            return None
        
        reference_audio_path = char_config["reference_audio"]
        emotion_intensity = char_config["emotion_intensity"]
        
        # Check if reference audio file exists
        if not os.path.exists(reference_audio_path):
            print(f"❌ Reference audio file not found: {reference_audio_path}")
            print(f"💡 Please create the voices directory and add reference audio files:")
            print(f"   - {reference_audio_path}")
            print(f"   - Use 5-20 seconds of clean audio for best results")
            return None
        
        # Generate audio using Chatterbox
        audio_bytes = chatterbox_tts.generate(
            text=text,
            reference_audio=reference_audio_path,
            emotion_intensity=emotion_intensity
        )
        
        # Convert to AudioSegment
        audio_segment = AudioSegment.from_file(BytesIO(audio_bytes), format="wav")
        return audio_segment
        
    except Exception as e:
        print(f"❌ Chatterbox TTS failed: {e}")
        return None

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
            with playback_lock:
                current_playback = play_buffer(segment.raw_data, segment.channels, segment.sample_width, segment.frame_rate)
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
    parser = argparse.ArgumentParser(description="AI Character Hotline")
    parser.add_argument("--mode", choices=["normal", "bargein"], default="normal",
                       help="Conversation mode: normal or bargein")
    parser.add_argument("--tts", choices=["elevenlabs", "azure", "gtts", "pyttsx3", "chatterbox"], 
                       default=TTS_PROVIDER, help="TTS provider to use")
    args = parser.parse_args()
    
    # Set global configuration based on args
    global ENABLE_BARGEIN, TTS_PROVIDER
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
                
                # Get user input (simulated speech-to-text)
                print("\n🎤 Listening... (type your message or 'hangup' to end call)")
                user_input = input("You: ").strip()
                
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
