# hotline_demo_windows.py
import os, queue, time, threading
import sounddevice as sd
import webrtcvad
import argparse
from io import BytesIO
import wave
from deepgram import Deepgram
from elevenlabs import ElevenLabs
from openai import OpenAI
from pydub import AudioSegment
from simpleaudio import play_buffer
import numpy as np

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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

# ---------- CONFIG ----------
# voice_pref accepts a voice NAME or a voice ID; using IDs for precision here.
CHARACTERS = {
    "3": {"name": "Albert Einstein", "voice_pref": "JBFqnCBsd6RMkjVDRZzb"},  # George
    "2": {"name": "Elvis Presley",   "voice_pref": "NFG5qt843uXKj4pFvR7C"},   # Adam Stone - late night radio
    "5": {"name": "Cleopatra",       "voice_pref": "XB0fDUnXU5powFXDhCwa"},   # Charlotte
    "7": {"name": "Beth Dutton",     "voice_pref": "cgSgspJ2msm6clMCkdW9"},   # Jessica
    "9": {"name": "Elon Musk",       "voice_pref": "CwhRBWXzGAHq8TQ4Fs17"},   # Roger
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

def init_clients():
    """Initialize API clients when needed"""
    global dg, oai, eleven
    if dg is None:
        dg = Deepgram(os.getenv("DEEPGRAM_API_KEY"))
    if oai is None:
        oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if eleven is None:
        eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# Playback state (so we can stop it on barge-in)
current_playback = None
playback_lock = threading.Lock()
current_tts_audio = None  # Store current TTS audio for echo detection
bargein_audio_buffer = None  # Store audio that triggered barge-in

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
        return False  # No proximity detection in PC mode
    
    try:
        return GPIO.input(PROXIMITY_PIN) == GPIO.LOW  # LOW = someone detected
    except Exception as e:
        # Hardware not available, assume no one nearby
        return False

# Rotary dial state machine
rotary_state = 0
rotary_count = 0
last_rotary_time = 0

def rotary_callback(channel):
    """Handle rotary dial pulses to decode dialed numbers"""
    global rotary_state, rotary_count, last_rotary_time
    
    current_time = time.time()
    if current_time - last_rotary_time < 0.01:  # Debounce
        return
    
    last_rotary_time = current_time
    
    a_state = GPIO.input(ROTARY_PIN_A)
    b_state = GPIO.input(ROTARY_PIN_B)
    
    # Gray code decoding for rotary dial
    new_state = (a_state << 1) | b_state
    
    if rotary_state == 0 and new_state == 2:  # Start of pulse
        rotary_count += 1
    elif rotary_state == 2 and new_state == 0:  # End of pulse
        # Complete pulse detected
        pass
    
    rotary_state = new_state

def get_dialed_number():
    """Get the number dialed on the rotary dial"""
    global rotary_count
    
    if not IS_RASPBERRY_PI:
        return None
    
    # Wait for dialing to complete (timeout after 3 seconds)
    start_time = time.time()
    while time.time() - start_time < 3:
        if rotary_count > 0:
            time.sleep(0.1)  # Wait for more pulses
            if time.time() - start_time > 0.5:  # Gap indicates end of digit
                break
    
    if rotary_count > 0:
        number = rotary_count
        rotary_count = 0
        return str(number)
    
    return None

# ---------- AUDIO VALIDATION ----------
def validate_audio_devices():
    """Check if required audio devices are available and accessible."""
    try:
        # List all audio devices
        devices = sd.query_devices()
        input_devices = []
        output_devices = []
        
        # Check each device for input/output capabilities
        for device in devices:
            # Check if device has input channels
            if 'max_input_channels' in device and device['max_input_channels'] > 0:
                input_devices.append(device)
                
            # Check if device has output channels  
            if 'max_output_channels' in device and device['max_output_channels'] > 0:
                output_devices.append(device)
        
        if not input_devices:
            print("❌ No audio input devices found!")
            if IS_RASPBERRY_PI:
                print("💡 On Raspberry Pi, try: sudo apt-get install python3-pyaudio")
            return False
            
        if not output_devices:
            print("❌ No audio output devices found!")
            if IS_RASPBERRY_PI:
                print("💡 On Raspberry Pi, check: sudo raspi-config -> System Options -> Audio")
            return False
            
        # Test default input device
        try:
            test_stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')
            test_stream.close()
        except Exception as e:
            print(f"❌ Cannot access default input device: {e}")
            if IS_RASPBERRY_PI:
                print("💡 Try: sudo apt-get install libasound2-dev")
            return False
            
        # Test default output device
        try:
            test_stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')
            test_stream.close()
        except Exception as e:
            print(f"❌ Cannot access default output device: {e}")
            if IS_RASPBERRY_PI:
                print("💡 Try: sudo apt-get install libasound2-dev")
            return False
            
        print(f"✅ Audio devices validated - {len(input_devices)} input(s), {len(output_devices)} output(s)")
        
        # Raspberry Pi specific audio optimization
        if IS_RASPBERRY_PI:
            print("🔧 Optimizing audio for Raspberry Pi...")
            # Set ALSA buffer size for lower latency
            os.environ['ALSA_PCM_CARD'] = '0'
            os.environ['ALSA_PCM_DEVICE'] = '0'
        
        return True
        
    except Exception as e:
        print(f"❌ Audio device validation failed: {e}")
        return False

def list_audio_devices():
    """List all available audio devices for debugging."""
    try:
        devices = sd.query_devices()
        print("\n📱 Available Audio Devices:")
        for i, device in enumerate(devices):
            device_type = []
            
            # Check for input/output capability using correct attribute names
            if 'max_input_channels' in device and device['max_input_channels'] > 0:
                device_type.append("INPUT")
            if 'max_output_channels' in device and device['max_output_channels'] > 0:
                device_type.append("OUTPUT")
                
            print(f"  {i}: {device['name']} ({', '.join(device_type)})")
        
        if IS_RASPBERRY_PI:
            print("\n🔧 Raspberry Pi Audio Tips:")
            print("  - Default device should be 'bcm2835 ALSA'")
            print("  - If no devices found, run: sudo raspi-config")
            print("  - Install audio support: sudo apt-get install python3-pyaudio")
        
        print()
    except Exception as e:
        print(f"❌ Could not list audio devices: {e}")

# ---------- AUDIO CAPTURE ----------
def record_until_silence():
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

# Helper: wrap raw PCM16 as WAV bytes (Deepgram works best with standard containers)
def pcm16_to_wav_bytes(pcm_bytes, sample_rate=16000, channels=1):
    bio = BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return bio.getvalue()

# ---------- ASR (Deepgram v2 REST) ----------
import asyncio

def asr_deepgram_pcm16(audio_bytes):
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

# ---------- LLM ----------
def llm_character_reply(character_name, user_text):
    try:
        init_clients()  # Initialize clients if needed
        system = SYSTEM_PROMPTS[character_name]
        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[{"role":"system","content":system},
                      {"role":"user","content":user_text}],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ AI response generation failed: {e}")
        return "I'm having trouble thinking right now. Could you try again?"

# ---------- TTS with barge-in ----------
def speak_tts_with_barge_in(voice_id_or_name: str, text: str):
    """Play TTS with pre-roll; if barge-in enabled, stop as soon as user starts speaking."""
    global current_playback

    try:
        init_clients()  # Initialize clients if needed
        # Generate audio
        stream = eleven.text_to_speech.convert(
            voice_id_or_name,
            model_id="eleven_multilingual_v2",
            text=text,
        )
        audio_bytes = b"".join(stream)
        seg = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
        
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
                        print("⛔ Barge-in detected: stopping playback")
                        
                        # Store the audio buffer for processing
                        global bargein_audio_buffer
                        bargein_audio_buffer = b"".join(audio_buffer)
                        
                        with playback_lock:
                            if current_playback and current_playback.is_playing():
                                current_playback.stop()
                                current_playback = None
                        break
                else:
                    debounce = 0
    except Exception as e:
        print(f"❌ Barge-in monitoring failed: {e}")

    # Ensure playback thread exits
    t.join(timeout=0.1)

# ---------- UI ----------
def pick_character():
    print("\nCharacters:")
    for k,v in CHARACTERS.items():
        print(f"  {k}: {v['name']}")
    while True:
        sel = input("Dial a character (e.g., 3 for Einstein): ").strip()
        if sel in CHARACTERS: return CHARACTERS[sel]
        print("Not in service. Try again.")

def main_loop(text_mode=False):
    print("\nTime Travel Hotline (PC Prototype)")
    
    if IS_RASPBERRY_PI:
        print("🍓 Running on Raspberry Pi with hardware integration")
        try:
            # Initialize GPIO
            init_gpio()
            
            # Set up rotary dial interrupt
            GPIO.add_event_detect(ROTARY_PIN_A, GPIO.BOTH, callback=rotary_callback, bouncetime=10)
            GPIO.add_event_detect(ROTARY_PIN_B, GPIO.BOTH, callback=rotary_callback, bouncetime=10)
        except Exception as e:
            print(f"⚠️  Hardware not connected: {e}")
            print("📞 Running in software mode (no rotary dial)")
            # Skip hardware-dependent features when hardware not available
            pass
        else:
            # Proximity detection loop (only if hardware is connected)
            print("👁️  Monitoring for approaching users...")
            while not is_someone_nearby():
                time.sleep(0.1)
            
            print("🔔 Someone approaching - ringing bell!")
            ring_bell(3)  # Ring for 3 seconds
            
            # Wait for phone to be picked up
            print("📞 Waiting for phone to be picked up...")
            while not is_phone_off_hook():
                time.sleep(0.1)
            
            print("📞 Phone picked up!")
    else:
        input("Press Enter to start a session; Ctrl+C to quit...")

    try:
        if IS_RASPBERRY_PI and not text_mode:
            # Always use software character selection for now
            # (Hardware detection can be added later when rotary dial is connected)
            print("📞 Using software character selection")
            persona = pick_character()
        else:
            persona = pick_character()
            
        name = persona["name"]
        voice_pref = persona["voice_pref"]

        if text_mode:
            print(f"Hello. You are speaking with {name}. Type your questions below.")
        else:
            speak_tts_with_barge_in(voice_pref, f"Hello. You are speaking with {name}. Ask your question.")

        while True:
            try:
                # Check if phone is still off-hook (Raspberry Pi only)
                if IS_RASPBERRY_PI and not text_mode:
                    try:
                        hook_status = is_phone_off_hook()
                        if not hook_status:
                            print("📞 Phone hung up - ending call")
                            break
                    except Exception as e:
                        # Hardware not available, skip hook detection
                        print(f"🔧 Hook check failed: {e}, continuing...")
                        pass
                
                if text_mode:
                    user_text = input("YOU: ").strip()
                    if not user_text:
                        continue
                    
                    if user_text.lower() in {"goodbye","hang up","bye","end call","quit","exit"}:
                        print(f"{name}: Goodbye.")
                        print("Call ended.")
                        break
                    
                    print("🤖 Thinking...")
                    reply = llm_character_reply(name, user_text)
                    print(f"{name.upper()}: {reply}")
                    print()  # Add spacing for readability
                    
                else:
                    # Check if we have barge-in audio to process first
                    global bargein_audio_buffer
                    if bargein_audio_buffer is not None:
                        print("📝 Processing barge-in audio...")
                        user_text = asr_deepgram_pcm16(bargein_audio_buffer)
                        bargein_audio_buffer = None  # Clear the buffer
                        print(f"YOU: {user_text}")
                        if not user_text:
                            continue
                    else:
                        print("🎤 Listening...")
                        pcm = record_until_silence()
                        if len(pcm) < 16000:
                            continue

                        print("📝 Transcribing...")
                        user_text = asr_deepgram_pcm16(pcm)
                        print(f"YOU: {user_text}")
                        if not user_text:
                            continue

                    if user_text.lower() in {"goodbye","hang up","bye","end call"}:
                        speak_tts_with_barge_in(voice_pref, "Goodbye.")
                        print("Call ended.")
                        break

                    print("🤖 Thinking...")
                    reply = llm_character_reply(name, user_text)
                    print(f"{name.upper()}: {reply}")

                    print("🔊 Speaking...")
                    speak_tts_with_barge_in(voice_pref, reply)
                
            except KeyboardInterrupt:
                print("\n\n📞 Call interrupted by user.")
                break
            except Exception as e:
                print(f"❌ Unexpected error in conversation loop: {e}")
                print("Continuing...")
                continue
                
    except KeyboardInterrupt:
        print("\n\n📞 Call ended by user.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print("Application will exit.")
    finally:
        if IS_RASPBERRY_PI:
            cleanup_gpio()

if __name__ == "__main__":
    # CLI: choose interaction mode
    parser = argparse.ArgumentParser(description="Time Travel Hotline")
    parser.add_argument(
        "--mode",
        choices=["barge", "turn"],
        default=os.getenv("HOTLINE_MODE", "barge"),
        help="barge = stop TTS when user speaks; turn = wait until TTS finishes",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="list available audio devices and exit",
    )
    parser.add_argument(
        "--text-mode",
        action="store_true",
        help="use text input instead of voice (type questions in console)",
    )
    args = parser.parse_args()

    # Set global barge-in flag
    ENABLE_BARGEIN = (args.mode == "barge")

    # Check for required environment variables
    missing = [k for k in ("ELEVEN_API_KEY","DEEPGRAM_API_KEY","OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please create a .env file with your API keys:")
        print("1. Copy env_template.txt to .env")
        print("2. Replace placeholder values with your actual API keys")
        print("3. Restart the application")
        exit(1)

    # List audio devices if requested
    if args.list_devices:
        list_audio_devices()
        exit(0)

    # Validate audio devices only if not in text mode
    if not args.text_mode:
        if not validate_audio_devices():
            print("❌ Audio device validation failed. Cannot continue.")
            print("Try running with --list-devices to see available devices.")
            print("Or use --text-mode for console input instead.")
            exit(1)
    else:
        print("📝 Running in TEXT MODE - type your questions in the console")

    # If you need a specific mic, uncomment to list/set:
    # import pprint; pprint.pp(sd.query_devices()); sd.default.device = (INPUT_INDEX, None)
    main_loop(text_mode=args.text_mode)

