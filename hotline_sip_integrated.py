# hotline_sip_integrated.py
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
import socket
import random
import hashlib

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# SIP Configuration
SIP_TARGET_IP = "192.168.1.179"
SIP_TARGET_PORT = 5060

# Audio settings
SAMPLE_RATE = 16000
FRAME_MS = 20
CHANNELS = 1
VAD_SENSITIVITY = 3
MAX_UTTERANCE_SEC = 12
SILENCE_TAIL_MS = 700

# TTS settings
TTS_PREROLL_MS = 100
BARGEIN_DELAY_MS = 300
BARGEIN_VAD_SENSITIVITY = 2
ENABLE_BARGEIN = True

# Global variables
current_playback = None
current_tts_audio = None
playback_lock = threading.Lock()
call_active = False
sip_socket = None

# Initialize clients
oai = None
dg = None
eleven = None

def init_clients():
    global oai, dg, eleven
    if oai is None:
        oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if dg is None:
        dg = Deepgram(os.getenv("DEEPGRAM_API_KEY"))
    if eleven is None:
        eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# Character system prompts
SYSTEM_PROMPTS = {
    "einstein": """You are Albert Einstein, the brilliant physicist. You're speaking from 1955, just before your death. 
    You're wise, philosophical, and love to discuss physics, the universe, and human nature. 
    You have a gentle German accent and speak with wonder about the mysteries of the cosmos.
    Keep responses under 3 sentences and speak naturally as if in a real conversation.""",
    
    "tesla": """You are Nikola Tesla, the visionary inventor and electrical engineer. You're speaking from 1943, near the end of your life.
    You're passionate about electricity, wireless power, and your inventions. You have a Serbian accent and speak with enthusiasm about the future of technology.
    You're slightly eccentric but brilliant. Keep responses under 3 sentences and speak naturally.""",
    
    "curie": """You are Marie Curie, the pioneering physicist and chemist. You're speaking from 1934, near the end of your life.
    You're the first woman to win a Nobel Prize and you discovered radium and polonium. You have a Polish accent and speak with quiet determination.
    You're passionate about science and women's rights. Keep responses under 3 sentences and speak naturally.""",
    
    "darwin": """You are Charles Darwin, the naturalist and biologist. You're speaking from 1882, near the end of your life.
    You're the author of 'On the Origin of Species' and you're passionate about evolution, nature, and scientific observation.
    You have a British accent and speak thoughtfully about the natural world. Keep responses under 3 sentences and speak naturally."""
}

class SipCallManager:
    def __init__(self, target_ip=SIP_TARGET_IP, target_port=SIP_TARGET_PORT):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = self.get_local_ip()
        self.call_id = None
        self.cseq = 1
        self.call_active = False
        
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def generate_call_id(self):
        """Generate a unique Call-ID"""
        timestamp = str(time.time())
        random_num = str(random.randint(1000, 9999))
        return hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()
    
    def create_sip_invite(self):
        """Create a SIP INVITE message"""
        self.call_id = self.generate_call_id()
        sip_message = f"""INVITE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{self.generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline SIP Client
Content-Length: 0

"""
        return sip_message
    
    def make_call(self):
        """Make a call to the phone"""
        try:
            print(f"📞 Making call to {self.target_ip}...")
            
            # Create UDP socket
            global sip_socket
            sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sip_socket.settimeout(5)
            
            # Send INVITE
            invite_message = self.create_sip_invite()
            sip_socket.sendto(invite_message.encode(), (self.target_ip, self.target_port))
            
            print("🔔 Phone should be ringing now...")
            print("⏳ Waiting for call to be answered...")
            
            # Wait a moment for the phone to ring
            time.sleep(3)
            
            # Check if we get any response
            try:
                data, addr = sip_socket.recvfrom(1024)
                response = data.decode()
                print(f"📥 Received: {response.split()[1] if len(response.split()) > 1 else 'Unknown response'}")
                
                if "200 OK" in response:
                    print("✅ Call answered!")
                    self.call_active = True
                    return True
                elif "180 Ringing" in response:
                    print("🔔 Phone is ringing...")
                    # Wait for answer
                    time.sleep(5)
                    self.call_active = True
                    return True
                else:
                    print(f"📋 Response: {response}")
                    return False
                    
            except socket.timeout:
                print("⏰ No response, but call may be active")
                self.call_active = True
                return True
                
        except Exception as e:
            print(f"❌ Error making call: {e}")
            return False
    
    def hang_up(self):
        """Hang up the call"""
        global sip_socket
        if self.call_active and sip_socket:
            try:
                # Send BYE message
                bye_message = f"""BYE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{self.generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq + 1} BYE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline SIP Client
Content-Length: 0

"""
                sip_socket.sendto(bye_message.encode(), (self.target_ip, self.target_port))
                print("📞 Call ended")
                
            except Exception as e:
                print(f"❌ Error hanging up: {e}")
            finally:
                self.call_active = False
                sip_socket.close()
                sip_socket = None

def is_loud_enough(chunk):
    samples = np.frombuffer(chunk, dtype=np.int16)
    rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
    return rms > 500

def is_likely_echo(chunk):
    """Simple check to see if audio chunk might be echo from speakers"""
    global current_tts_audio
    if current_tts_audio is None:
        return False
    
    samples = np.frombuffer(chunk, dtype=np.int16)
    if len(samples) > 0:
        mean_amp = np.mean(np.abs(samples))
        std_amp = np.std(samples)
        if mean_amp > 0:
            cv = std_amp / mean_amp
            return cv < 0.3
        if mean_amp < 1000:
            return True
    return False

def pcm16_to_wav_bytes(pcm_bytes, sample_rate=16000, channels=1):
    bio = BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return bio.getvalue()

def asr_deepgram_pcm16(audio_bytes):
    try:
        init_clients()
        wav_bytes = pcm16_to_wav_bytes(audio_bytes, SAMPLE_RATE, CHANNELS)
        source = {"buffer": wav_bytes, "mimetype": "audio/wav"}
        
        import asyncio
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

def llm_character_reply(character_name, user_text):
    try:
        init_clients()
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

def speak_tts_with_barge_in(voice_id_or_name: str, text: str):
    """Play TTS with pre-roll; if barge-in enabled, stop as soon as user starts speaking."""
    global current_playback, current_tts_audio

    try:
        init_clients()
        stream = eleven.text_to_speech.convert(
            voice_id_or_name,
            model_id="eleven_multilingual_v2",
            text=text,
        )
        audio_bytes = b"".join(stream)
        seg = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
        current_tts_audio = seg
    except Exception as e:
        print(f"❌ Text-to-speech failed: {e}")
        return

    if TTS_PREROLL_MS > 0:
        seg = AudioSegment.silent(duration=TTS_PREROLL_MS) + seg

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
        while True:
            with playback_lock:
                po = current_playback
            if po is None or not po.is_playing():
                break
            time.sleep(0.05)
        return

    time.sleep(BARGEIN_DELAY_MS / 1000.0)

    vad = webrtcvad.Vad(BARGEIN_VAD_SENSITIVITY)
    q = queue.Queue()
    
    audio_buffer = []
    buffer_size = int(2.0 * SAMPLE_RATE / (SAMPLE_RATE * FRAME_MS / 1000))

    def mic_cb(indata, frames, time_info, status):
        q.put(bytes(indata))

    debounce = 0
    start_time = time.time()
    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE,
                               blocksize=int(SAMPLE_RATE * FRAME_MS / 1000),
                               channels=CHANNELS, dtype='int16', callback=mic_cb):
            
            while True:
                try:
                    chunk = q.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Check if TTS is still playing
                with playback_lock:
                    po = current_playback
                if po is None or not po.is_playing():
                    break
                
                # VAD check
                try:
                    is_speech = vad.is_speech(chunk, SAMPLE_RATE)
                except:
                    is_speech = False
                
                if is_speech and not is_likely_echo(chunk):
                    debounce += 1
                    if debounce >= 3:  # Require 3 consecutive speech frames
                        print("🎤 Barge-in detected!")
                        with playback_lock:
                            if current_playback:
                                current_playback.stop()
                                current_playback = None
                        break
                else:
                    debounce = 0
                
                # Store audio for potential processing
                audio_buffer.append(chunk)
                if len(audio_buffer) > buffer_size:
                    audio_buffer.pop(0)
                    
    except Exception as e:
        print(f"❌ Barge-in monitoring failed: {e}")

def run_hotline_conversation(character_name, voice_id):
    """Run the main hotline conversation loop"""
    global call_active
    
    sip_manager = SipCallManager()
    
    print(f"🔧 Time Travel Hotline - SIP Integrated")
    print(f"📞 Character: {character_name}")
    print(f"🎤 Voice: {voice_id}")
    print("=" * 50)
    
    # Make the call
    if not sip_manager.make_call():
        print("❌ Failed to make call")
        return
    
    print("✅ Call connected! Starting conversation...")
    print("💡 Speak naturally - the AI will respond")
    print("💡 Press Ctrl+C to end the call")
    
    try:
        # Initial greeting
        greeting = f"Hello! This is {character_name.replace('_', ' ').title()}. I'm calling from the past. How may I assist you today?"
        print(f"🤖 {character_name}: {greeting}")
        speak_tts_with_barge_in(voice_id, greeting)
        
        # Main conversation loop
        while call_active:
            # Record user speech
            print("\n🎤 Listening...")
            
            q = queue.Queue()
            audio_buffer = []
            vad = webrtcvad.Vad(VAD_SENSITIVITY)
            
            def mic_callback(indata, frames, time_info, status):
                q.put(bytes(indata))
            
            # Record audio
            with sd.RawInputStream(samplerate=SAMPLE_RATE,
                                   blocksize=int(SAMPLE_RATE * FRAME_MS / 1000),
                                   channels=CHANNELS, dtype='int16', callback=mic_callback):
                
                silence_frames = 0
                speech_detected = False
                start_time = time.time()
                
                while True:
                    try:
                        chunk = q.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    
                    audio_buffer.append(chunk)
                    
                    # VAD check
                    try:
                        is_speech = vad.is_speech(chunk, SAMPLE_RATE)
                    except:
                        is_speech = False
                    
                    if is_speech and not is_likely_echo(chunk):
                        silence_frames = 0
                        speech_detected = True
                    else:
                        silence_frames += 1
                    
                    # Stop conditions
                    silence_threshold = int(SILENCE_TAIL_MS / FRAME_MS)
                    time_elapsed = time.time() - start_time
                    
                    if speech_detected and (silence_frames >= silence_threshold or time_elapsed >= MAX_UTTERANCE_SEC):
                        break
            
            # Process speech
            if len(audio_buffer) > 0:
                audio_data = b"".join(audio_buffer)
                user_text = asr_deepgram_pcm16(audio_data)
                
                if user_text.strip():
                    print(f"👤 You: {user_text}")
                    
                    # Generate AI response
                    ai_response = llm_character_reply(character_name, user_text)
                    print(f"🤖 {character_name}: {ai_response}")
                    
                    # Speak response
                    speak_tts_with_barge_in(voice_id, ai_response)
                else:
                    print("🔇 No speech detected")
            else:
                print("🔇 No audio captured")
                
    except KeyboardInterrupt:
        print("\n📞 Ending call...")
    finally:
        sip_manager.hang_up()
        print("👋 Goodbye!")

def main():
    global SIP_TARGET_IP, call_active
    
    parser = argparse.ArgumentParser(description="Time Travel Hotline - SIP Integrated")
    parser.add_argument("--character", choices=["einstein", "tesla", "curie", "darwin"], 
                       default="einstein", help="Historical character to speak as")
    parser.add_argument("--voice", default="pNInz6obpgDQGcFmaJgB", 
                       help="ElevenLabs voice ID")
    parser.add_argument("--target-ip", default=SIP_TARGET_IP,
                       help="Target phone IP address")
    
    args = parser.parse_args()
    
    # Update SIP target if provided
    if args.target_ip != SIP_TARGET_IP:
        SIP_TARGET_IP = args.target_ip
    
    print("🔧 Time Travel Hotline - SIP Integrated")
    print("=" * 50)
    print(f"📞 Target Phone: {SIP_TARGET_IP}")
    print(f"🎭 Character: {args.character}")
    print(f"🎤 Voice: {args.voice}")
    print()
    print("Press Enter to start the call...")
    input()
    
    run_hotline_conversation(args.character, args.voice)

if __name__ == "__main__":
    main()
