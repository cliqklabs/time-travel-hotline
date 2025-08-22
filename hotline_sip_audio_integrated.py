# hotline_sip_audio_integrated.py
import os, queue, time, threading
import webrtcvad
import argparse
from io import BytesIO
import wave
from deepgram import Deepgram
from elevenlabs import ElevenLabs
from openai import OpenAI
from pydub import AudioSegment
import numpy as np
import socket
import random
import hashlib
import struct
import audioop

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# SIP Configuration
SIP_TARGET_IP = "192.168.1.179"
SIP_TARGET_PORT = 5060

# Audio settings for phone compatibility
SAMPLE_RATE = 8000  # Standard phone audio rate
FRAME_MS = 20
CHANNELS = 1
VAD_SENSITIVITY = 3
MAX_UTTERANCE_SEC = 12
SILENCE_TAIL_MS = 700

# RTP settings
RTP_PORT = 5004  # Local RTP port for audio
PHONE_RTP_PORT = 5004  # Phone's RTP port (will be negotiated)

# Global variables
current_playback = None
call_active = False
sip_socket = None
rtp_socket = None
audio_queue = queue.Queue()
tts_queue = queue.Queue()

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

class RTPAudioHandler:
    def __init__(self, phone_ip, phone_rtp_port=5004, local_rtp_port=5004):
        self.phone_ip = phone_ip
        self.phone_rtp_port = phone_rtp_port
        self.local_rtp_port = local_rtp_port
        self.rtp_socket = None
        self.sequence_number = random.randint(0, 65535)
        self.timestamp = random.randint(0, 4294967295)
        self.ssrc = random.randint(0, 4294967295)
        self.running = False
        
    def start_rtp(self):
        """Start RTP audio streaming"""
        try:
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_socket.bind(('', self.local_rtp_port))
            self.running = True
            
            # Start RTP receiver thread
            self.receiver_thread = threading.Thread(target=self._rtp_receiver, daemon=True)
            self.receiver_thread.start()
            
            print(f"🔊 RTP audio started on port {self.local_rtp_port}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start RTP: {e}")
            return False
    
    def stop_rtp(self):
        """Stop RTP audio streaming"""
        self.running = False
        if self.rtp_socket:
            self.rtp_socket.close()
            self.rtp_socket = None
        print("🔇 RTP audio stopped")
    
    def _rtp_receiver(self):
        """Receive RTP audio packets from phone"""
        while self.running:
            try:
                data, addr = self.rtp_socket.recvfrom(1024)
                if len(data) > 12:  # RTP header is 12 bytes
                    # Extract RTP header
                    header = struct.unpack('!BBHII', data[:12])
                    payload = data[12:]
                    
                    # Convert G.711 μ-law to PCM (assuming phone uses G.711)
                    pcm_data = audioop.ulaw2lin(payload, 2)
                    
                    # Add to audio queue for processing
                    audio_queue.put(pcm_data)
                    
            except Exception as e:
                if self.running:
                    print(f"❌ RTP receive error: {e}")
                break
    
    def send_audio(self, pcm_data):
        """Send PCM audio data via RTP to phone"""
        if not self.running or not self.rtp_socket:
            return
            
        try:
            # Convert PCM to G.711 μ-law for phone compatibility
            ulaw_data = audioop.lin2ulaw(pcm_data, 2)
            
            # Create RTP header
            version = 2
            padding = 0
            extension = 0
            cc = 0
            marker = 0
            payload_type = 0  # G.711 μ-law
            
            # Pack RTP header
            header = struct.pack('!BBHII',
                (version << 6) | (padding << 5) | (extension << 4) | cc,
                (marker << 7) | payload_type,
                self.sequence_number,
                self.timestamp,
                self.ssrc
            )
            
            # Send RTP packet
            packet = header + ulaw_data
            self.rtp_socket.sendto(packet, (self.phone_ip, self.phone_rtp_port))
            
            # Update sequence and timestamp
            self.sequence_number = (self.sequence_number + 1) % 65536
            self.timestamp = (self.timestamp + len(ulaw_data)) % 4294967296
            
        except Exception as e:
            print(f"❌ RTP send error: {e}")

class SipAudioCallManager:
    def __init__(self, target_ip=SIP_TARGET_IP, target_port=SIP_TARGET_PORT):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = self.get_local_ip()
        self.call_id = None
        self.cseq = 1
        self.call_active = False
        self.rtp_handler = None
        
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
    
    def create_sdp(self):
        """Create SDP (Session Description Protocol) for audio"""
        return f"""v=0
o=hotline {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}
s=Time Travel Hotline Audio Session
c=IN IP4 {self.local_ip}
t=0 0
m=audio {RTP_PORT} RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=sendrecv
"""
    
    def create_sip_invite(self):
        """Create a SIP INVITE message with SDP"""
        self.call_id = self.generate_call_id()
        sdp_body = self.create_sdp()
        
        sip_message = f"""INVITE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{self.generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline SIP Audio Client
Content-Type: application/sdp
Content-Length: {len(sdp_body)}

{sdp_body}"""
        return sip_message
    
    def make_call(self):
        """Make a call to the phone with audio capabilities"""
        try:
            print(f"📞 Making audio call to {self.target_ip}...")
            
            # Start RTP handler
            self.rtp_handler = RTPAudioHandler(self.target_ip)
            if not self.rtp_handler.start_rtp():
                print("❌ Failed to start RTP audio")
                return False
            
            # Create UDP socket for SIP
            global sip_socket
            sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sip_socket.settimeout(5)
            
            # Send INVITE with SDP
            invite_message = self.create_sip_invite()
            print("📤 Sending SIP INVITE with audio capabilities...")
            sip_socket.sendto(invite_message.encode(), (self.target_ip, self.target_port))
            
            print("🔔 Phone should be ringing now...")
            print("⏳ Waiting for call to be answered...")
            
            # Wait for response
            time.sleep(3)
            
            try:
                data, addr = sip_socket.recvfrom(2048)  # Larger buffer for SDP
                response = data.decode()
                print(f"📥 Received: {response.split()[1] if len(response.split()) > 1 else 'Unknown response'}")
                
                if "200 OK" in response:
                    print("✅ Call answered with audio!")
                    self.call_active = True
                    return True
                elif "180 Ringing" in response or "183 Session Progress" in response:
                    print("🔔 Phone is ringing...")
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
        if self.call_active:
            try:
                if sip_socket:
                    # Send BYE message
                    bye_message = f"""BYE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{self.generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq + 1} BYE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline SIP Audio Client
Content-Length: 0

"""
                    sip_socket.sendto(bye_message.encode(), (self.target_ip, self.target_port))
                    sip_socket.close()
                    sip_socket = None
                
                # Stop RTP
                if self.rtp_handler:
                    self.rtp_handler.stop_rtp()
                
                print("📞 Call ended")
                
            except Exception as e:
                print(f"❌ Error hanging up: {e}")
            finally:
                self.call_active = False

def pcm16_to_wav_bytes(pcm_bytes, sample_rate=8000, channels=1):
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

def generate_tts_audio(voice_id, text):
    """Generate TTS audio and return PCM data for phone transmission"""
    try:
        init_clients()
        stream = eleven.text_to_speech.convert(
            voice_id,
            model_id="eleven_multilingual_v2",
            text=text,
        )
        audio_bytes = b"".join(stream)
        seg = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
        
        # Convert to phone-compatible format (8kHz, mono, 16-bit)
        seg = seg.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS)
        
        return seg.raw_data
        
    except Exception as e:
        print(f"❌ Text-to-speech failed: {e}")
        return None

def phone_audio_handler(sip_manager, character_name, voice_id):
    """Handle bidirectional audio through phone handset"""
    print("🎤 Phone audio handler started")
    
    # Audio processing buffers
    received_audio_buffer = []
    silence_frames = 0
    speech_detected = False
    vad = webrtcvad.Vad(VAD_SENSITIVITY)
    
    # Send initial greeting
    greeting = f"Hello! This is {character_name.replace('_', ' ').title()}. I'm calling from the past. How may I assist you today?"
    print(f"🤖 {character_name}: {greeting}")
    
    greeting_audio = generate_tts_audio(voice_id, greeting)
    if greeting_audio and sip_manager.rtp_handler:
        # Send greeting in chunks
        chunk_size = 160  # 20ms at 8kHz
        for i in range(0, len(greeting_audio), chunk_size):
            chunk = greeting_audio[i:i+chunk_size]
            if len(chunk) == chunk_size:
                sip_manager.rtp_handler.send_audio(chunk)
                time.sleep(0.02)  # 20ms interval
    
    print("🎤 Listening through phone handset...")
    
    while call_active:
        try:
            # Check for received audio from phone
            if not audio_queue.empty():
                audio_chunk = audio_queue.get_nowait()
                received_audio_buffer.append(audio_chunk)
                
                # VAD check on received audio
                try:
                    is_speech = vad.is_speech(audio_chunk, SAMPLE_RATE)
                except:
                    is_speech = False
                
                if is_speech:
                    silence_frames = 0
                    speech_detected = True
                    print("🎤 Speech detected from phone...")
                else:
                    silence_frames += 1
                
                # Process speech when silence detected after speech
                silence_threshold = int(SILENCE_TAIL_MS / FRAME_MS)
                if speech_detected and silence_frames >= silence_threshold:
                    print("🎤 Processing speech from phone...")
                    
                    # Combine audio buffer
                    if received_audio_buffer:
                        audio_data = b"".join(received_audio_buffer)
                        user_text = asr_deepgram_pcm16(audio_data)
                        
                        if user_text.strip():
                            print(f"👤 You (via phone): {user_text}")
                            
                            # Generate AI response
                            ai_response = llm_character_reply(character_name, user_text)
                            print(f"🤖 {character_name}: {ai_response}")
                            
                            # Convert response to audio and send to phone
                            response_audio = generate_tts_audio(voice_id, ai_response)
                            if response_audio and sip_manager.rtp_handler:
                                # Send response in chunks
                                chunk_size = 160  # 20ms at 8kHz
                                for i in range(0, len(response_audio), chunk_size):
                                    chunk = response_audio[i:i+chunk_size]
                                    if len(chunk) == chunk_size:
                                        sip_manager.rtp_handler.send_audio(chunk)
                                        time.sleep(0.02)  # 20ms interval
                        else:
                            print("🔇 No speech detected in audio")
                    
                    # Reset for next utterance
                    received_audio_buffer = []
                    speech_detected = False
                    silence_frames = 0
                    print("🎤 Listening through phone handset...")
            else:
                time.sleep(0.01)  # Small delay to prevent busy loop
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Audio processing error: {e}")
            time.sleep(0.1)

def run_phone_conversation(character_name, voice_id):
    """Run the main phone conversation loop"""
    global call_active
    
    sip_manager = SipAudioCallManager()
    
    print(f"🔧 Time Travel Hotline - Phone Audio Integrated")
    print(f"📞 Character: {character_name}")
    print(f"🎤 Voice: {voice_id}")
    print("=" * 50)
    
    # Make the call
    if not sip_manager.make_call():
        print("❌ Failed to make call")
        return
    
    print("✅ Audio call connected!")
    print("💡 Speak into the phone handset - the AI will respond through the phone speaker")
    print("💡 Press Ctrl+C to end the call")
    
    try:
        # Start phone audio handling
        phone_audio_handler(sip_manager, character_name, voice_id)
        
    except KeyboardInterrupt:
        print("\n📞 Ending call...")
    finally:
        call_active = False
        sip_manager.hang_up()
        print("👋 Goodbye!")

def main():
    global SIP_TARGET_IP, call_active
    
    parser = argparse.ArgumentParser(description="Time Travel Hotline - Phone Audio Integrated")
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
    
    print("🔧 Time Travel Hotline - Phone Audio Integrated")
    print("=" * 50)
    print(f"📞 Target Phone: {SIP_TARGET_IP}")
    print(f"🎭 Character: {args.character}")
    print(f"🎤 Voice: {args.voice}")
    print("🔊 Audio will use phone handset microphone and speaker")
    print()
    print("Press Enter to start the call...")
    input()
    
    call_active = True
    run_phone_conversation(args.character, args.voice)

if __name__ == "__main__":
    main()
