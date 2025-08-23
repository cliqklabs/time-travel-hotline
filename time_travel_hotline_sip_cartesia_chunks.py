#!/usr/bin/env python3
"""
Time Travel Hotline - Full SIP Integration
Combines working SIP proxy approach with ElevenLabs TTS and Deepgram ASR
"""

import os
import sys
import time
import socket
import random
import struct
import math
import threading
import signal
import argparse
import asyncio
import json
import io
import numpy as np
from dotenv import load_dotenv

# Audio processing imports
try:
    import sounddevice as sd
    import webrtcvad
    from pydub import AudioSegment
    import simpleaudio as sa
    try:
        from scipy import signal
        SCIPY_AVAILABLE = True
    except ImportError:
        SCIPY_AVAILABLE = False
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    SCIPY_AVAILABLE = False
    print("⚠️ Audio libraries not available - install with: pip install sounddevice webrtcvad pydub simpleaudio scipy")

# AI service imports
try:
    from elevenlabs.client import ElevenLabs
    import cartesia
    import openai
    from deepgram import Deepgram
    AI_AVAILABLE = True
    print("✅ AI libraries loaded successfully")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI libraries not available: {e}")
    print("Install with: pip install elevenlabs cartesia openai deepgram-sdk==2.12.0")

# Load environment variables
load_dotenv()

# SIP Configuration
SIP_SERVER_IP = "192.168.1.254"  # Your computer running the proxy
HT801_IP = "192.168.1.179"       # The HT801 device
SIP_PORT = 5060
LOCAL_RTP_PORT = 6000            # Our RTP port (different from HT801's 5004)

# Audio settings
SAMPLE_RATE = 8000  # 8kHz for G.711
CHANNELS = 1
CHUNK_SIZE = 160    # 20ms at 8kHz
FRAME_DURATION = 20  # ms

# ===== BARGE-IN SETTINGS (Easy to tweak!) =====
BARGE_IN_GREETING_GRACE = 0.5      # Seconds before barge-in allowed for greetings
BARGE_IN_RESPONSE_GRACE = 0.2      # Seconds before barge-in allowed for responses  
BARGE_IN_AUDIO_THRESHOLD = 0.015   # Audio level threshold for barge-in (lowered for better detection)
BARGE_IN_CHECK_FREQUENCY = 1       # Check every chunk for maximum responsiveness

# ===== AUDIO TIMING SETTINGS =====
AUDIO_CHUNK_DELAY = 0.015          # Seconds between RTP packets (0.01-0.02)

# ===== TTS PROVIDER SETTINGS =====
TTS_PROVIDER = "cartesia"           # Options: "elevenlabs", "cartesia"
CARTESIA_MODEL = "sonic-english"       # Cartesia's fastest English model

# Character configurations
CHARACTERS = {
    "einstein": {
        "name": "Albert Einstein",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "personality": "You are Albert Einstein, the brilliant physicist. You speak with wisdom about science, relativity, and the universe. You're curious, thoughtful, and occasionally make references to your theories.",
        "greeting": "Guten Tag! This is Albert Einstein speaking from the past. I've been pondering the mysteries of space and time. What scientific questions trouble your mind today?"
    },
    "shakespeare": {
        "name": "William Shakespeare", 
        "voice_id": "flq6f7yk4E4fJM5XTYuZ",
        "personality": "You are William Shakespeare, the great playwright and poet. You speak in eloquent, poetic language with occasional Early Modern English phrases. You're passionate about human nature, love, and the arts.",
        "greeting": "Hark! 'Tis William Shakespeare, calling from ages past. Mine quill rests whilst I speak with thee through this wondrous device. What tales or troubles dost thou bring to mine ear?"
    },
    "tesla": {
        "name": "Nikola Tesla",
        "voice_id": "ErXwobaYiN019PkySvjV", 
        "personality": "You are Nikola Tesla, the visionary inventor. You're passionate about electricity, wireless technology, and the future. You speak with intensity about your inventions and visions.",
        "greeting": "Greetings! This is Nikola Tesla, speaking to you through the ether itself! My mind races with visions of wireless power and electric futures. What electrical mysteries shall we explore together?"
    },
    "elon": {
        "name": "Elon Musk",
        "voice_id": "b2660972-924c-4a2b-ab38-6499ef14020d",  # Cartesia voice ID
        "provider": "cartesia",  # Use Cartesia for low latency
        "personality": "You are Elon Musk, the tech entrepreneur and visionary. You're passionate about Mars colonization, electric vehicles, AI, and making life multiplanetary. You speak with enthusiasm about the future, often mention SpaceX, Tesla, and your ambitious goals. Keep responses conversational and exciting.",
        "greeting": "Hey! This is Elon calling from the future... well, technically the present. I'm working on some insane projects - Mars rockets, neural interfaces, the works. What's on your mind? Let's talk about making the future awesome!"
    },
    "cleopatra": {
        "name": "Cleopatra VII",
        "voice_id": "EXAVITQu4vr4xnSDxMaL",  # Female voice
        "personality": "You are Cleopatra VII, the last pharaoh of Egypt. You are intelligent, charismatic, and politically savvy. You speak with regal authority about ancient Egypt, politics, power, and the complexities of ruling an empire. You're well-educated in mathematics, philosophy, and languages.",
        "greeting": "Greetings, mortal. I am Cleopatra, Queen of Egypt, Pharaoh of the Upper and Lower Nile. From my palace in Alexandria, I speak to you across the sands of time. What wisdom do you seek from the last of the Ptolemaic dynasty?"
    },
    "burt": {
        "name": "Burt Reynolds",
        "voice_id": "4YYIPFl9wE5c4L2eu2Gb",
        "personality": "You are Burt Reynolds, the legendary actor and cultural icon. You're charming, witty, and effortlessly cool with that famous mustache and million-dollar smile. You speak with Southern charm and confidence about Hollywood, acting, cars, and life. You're known for your roles in Smokey and the Bandit, Deliverance, and Boogie Nights. Keep it smooth, funny, and just a little bit cocky in that lovable Burt way.",
        "greeting": "Well hey there, good lookin'! Burt Reynolds here, calling from wherever handsome guys go when they're done making movies. Hope you're ready for some smooth talk and maybe a story or two about the good ol' days in Hollywood. What's on your mind, partner?"
    },
    "myself": {
        "name": "Your AI Twin",
        "voice_id": "zN91Rcq9rz3S6Q1xiw21",
        "personality": "You are an AI version of the user themselves. You have their voice and speak in their style. You're thoughtful, helpful, and curious about their thoughts and experiences. You can discuss their projects, ideas, and life from an outside perspective while maintaining their voice and speaking patterns. Be supportive and engaging, offering insights and asking thoughtful questions.",
        "greeting": "Hey there! This is... well, this is you! Or at least an AI version of you. Pretty wild, right? I've got your voice and I'm here to chat about whatever's on your mind. What do you want to talk about with yourself today?"
    },
    "elvis": {
        "name": "Elvis Presley",
        "voice_id": "2642c8d5-cd59-4621-a203-63c99d6fd6df",  # Cartesia voice ID
        "provider": "cartesia",  # Specify which provider to use
        "personality": "You are Elvis Presley, the King of Rock and Roll. You speak with that iconic Southern charm and musical passion. Talk about music, Graceland, your performances, and the golden era of rock and roll. Use phrases like 'Thank ya, thank ya very much' and maintain that warm, charismatic Elvis style.",
        "greeting": "Well, hello there, darlin'! This is Elvis calling from Graceland, or maybe from somewhere beyond the blue moon. I hope you're all shook up to be talking to the King himself! What's on your mind, honey? Want to talk about music, love, or maybe a little rock and roll?"
    }
}

class SipPhoneCall:
    def __init__(self, server_ip=SIP_SERVER_IP, server_port=SIP_PORT):
        self.server_ip = server_ip
        self.server_port = server_port
        self.local_ip = self.get_local_ip()
        self.call_id = self.generate_call_id()
        self.from_tag = str(random.randint(10000, 99999))
        self.to_tag = None
        self.cseq = 1
        self.socket = None
        self.rtp_socket = None
        self.remote_rtp_port = None
        self.local_rtp_port = LOCAL_RTP_PORT
        self.call_active = False
        self.rtp_sequence = 0
        self.rtp_timestamp = 0
        
        # Conversation memory
        self.conversation_history = []
        self.rtp_ssrc = 0x12345678
        self.stop_speaking = False  # For barge-in capability
        
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
        """Generate unique Call-ID"""
        return f"hotline-{random.randint(100000, 999999)}@{self.local_ip}"
    
    def make_call(self):
        """Make SIP call to the vintage phone"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(15)
            
            # Create SDP offer optimized for HT801 PCMU codec
            sdp = f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}
s=Time Travel Hotline
c=IN IP4 {self.local_ip}
t=0 0
m=audio {self.local_rtp_port} RTP/AVP 0
a=rtpmap:0 PCMU/8000
a=ptime:20
a=sendrecv
a=silenceSupp:off
"""
            
            # Create INVITE
            invite = f"""INVITE sip:1000@{self.server_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{random.randint(1000, 9999)}
From: <sip:hotline@{self.local_ip}>;tag={self.from_tag}
To: <sip:1000@{self.server_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""
            
            print(f"📞 Calling vintage phone via SIP server {self.server_ip}")
            self.socket.sendto(invite.encode(), (self.server_ip, self.server_port))
            
            # Wait for call to be answered
            while True:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    response = data.decode()
                    first_line = response.split('\n')[0].strip()
                    
                    if "SIP/2.0 100" in response:
                        print("📞 Call processing...")
                    elif "SIP/2.0 180" in response or "SIP/2.0 183" in response:
                        print("📞 Phone is ringing! Pick up the handset!")
                    elif "SIP/2.0 200" in response:
                        print("✅ Call answered!")
                        
                        # Extract To tag
                        for line in response.split('\n'):
                            if line.startswith('To:') and 'tag=' in line:
                                tag_start = line.find('tag=') + 4
                                tag_end = line.find(';', tag_start)
                                if tag_end == -1:
                                    tag_end = line.find('\r', tag_start)
                                if tag_end == -1:
                                    tag_end = len(line)
                                self.to_tag = line[tag_start:tag_end].strip()
                                break
                        
                        # Extract RTP port
                        self.remote_rtp_port = self.extract_rtp_port(response)
                        
                        # Send ACK
                        self.send_ack()
                        
                        # Setup RTP
                        if self.setup_rtp():
                            self.call_active = True
                            
                            # Start monitoring for SIP BYE messages (hang-up detection)
                            self.sip_monitor_thread = threading.Thread(target=self.monitor_sip_messages, daemon=True)
                            self.sip_monitor_thread.start()
                            
                            return True
                        else:
                            return False
                            
                    elif "SIP/2.0 4" in response or "SIP/2.0 5" in response:
                        print(f"❌ Call failed: {first_line}")
                        return False
                        
                except socket.timeout:
                    print("⏰ Call timeout")
                    return False
                    
        except Exception as e:
            print(f"❌ Call error: {e}")
            return False
    
    def extract_rtp_port(self, response):
        """Extract RTP port from SDP response"""
        try:
            sdp_start = response.find('\r\n\r\n')
            if sdp_start != -1:
                sdp = response[sdp_start + 4:]
                for line in sdp.split('\n'):
                    line = line.strip()
                    if line.startswith('m=audio'):
                        parts = line.split()
                        if len(parts) >= 2:
                            port = int(parts[1])
                            print(f"🎵 Remote RTP port: {port}")
                            return port
            return None
        except:
            return None
    
    def send_ack(self):
        """Send ACK to complete call setup"""
        try:
            to_header = f"<sip:1000@{self.server_ip}>"
            if self.to_tag:
                to_header += f";tag={self.to_tag}"
            
            ack = f"""ACK sip:1000@{self.server_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{random.randint(1000, 9999)}
From: <sip:hotline@{self.local_ip}>;tag={self.from_tag}
To: {to_header}
Call-ID: {self.call_id}
CSeq: {self.cseq} ACK
Max-Forwards: 70
Content-Length: 0

"""
            
            self.socket.sendto(ack.encode(), (self.server_ip, self.server_port))
            
        except Exception as e:
            print(f"❌ ACK error: {e}")
    
    def setup_rtp(self):
        """Setup RTP audio connection"""
        try:
            if not self.remote_rtp_port:
                print("❌ No remote RTP port")
                return False
                
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_socket.bind(('', self.local_rtp_port))
            
            print(f"🎵 RTP setup: {self.local_ip}:{self.local_rtp_port} ↔ {HT801_IP}:{self.remote_rtp_port}")
            return True
            
        except Exception as e:
            print(f"❌ RTP setup error: {e}")
            return False
    
    def clear_rtp_buffer(self):
        """Clear any buffered RTP packets to avoid old audio interfering with barge-in"""
        if not self.rtp_socket:
            return
            
        try:
            self.rtp_socket.settimeout(0.001)  # Very short timeout
            packets_cleared = 0
            # Faster clearing - limit to 50 packets max
            for _ in range(50):
                try:
                    data, addr = self.rtp_socket.recvfrom(1024)
                    packets_cleared += 1
                except socket.timeout:
                    break
            if packets_cleared > 5:  # Only log if significant
                print(f"🧹 Cleared {packets_cleared} buffered packets")
        except Exception:
            pass
    
    def send_audio_data(self, audio_generator, is_greeting=False):
        """Send audio data as RTP packets with barge-in support using streaming generator"""
        if not self.rtp_socket or not self.remote_rtp_port:
            return False
            
        # Start barge-in monitoring in background (with grace period)
        self.stop_speaking = False
        
        # Clear RTP buffer before speaking to avoid old audio interfering with barge-in
        self.clear_rtp_buffer()
        
        # Simple barge-in: check frequently in audio loop after grace period
        grace_period = BARGE_IN_GREETING_GRACE if is_greeting else BARGE_IN_RESPONSE_GRACE
        speech_start_time = None
        barge_in_enabled_time = None
        print(f"🎧 Barge-in enabled after {grace_period}s grace period (buffer cleared)")
            
        try:
            for raw_chunk in audio_generator:
                if raw_chunk is None:
                    break
                
                # Convert raw 16-bit PCM chunk to float32
                chunk_array = np.frombuffer(raw_chunk, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Apply filters if available (minimal for speed)
                if SCIPY_AVAILABLE:
                    nyquist = SAMPLE_RATE / 2
                    low = 400 / nyquist
                    high = 3200 / nyquist
                    b_hp, a_hp = signal.butter(2, low, btype='high')
                    chunk_array = signal.filtfilt(b_hp, a_hp, chunk_array)
                    b_lp, a_lp = signal.butter(3, high, btype='low')
                    chunk_array = signal.filtfilt(b_lp, a_lp, chunk_array)
                
                chunk_array = np.clip(chunk_array, -0.9, 0.9) * 0.85
                chunk_bytes = self.linear_to_mulaw(chunk_array)
                
                # Send in sub-chunks
                for i in range(0, len(chunk_bytes), CHUNK_SIZE):
                    sub_chunk = chunk_bytes[i:i+CHUNK_SIZE]
                    if len(sub_chunk) < CHUNK_SIZE:
                        sub_chunk += b'\x00' * (CHUNK_SIZE - len(sub_chunk))
                    
                    rtp_header = struct.pack('!BBHII',
                        0x80, 0x00, self.rtp_sequence, self.rtp_timestamp, self.rtp_ssrc
                    )
                    packet = rtp_header + sub_chunk
                    self.rtp_socket.sendto(packet, (HT801_IP, self.remote_rtp_port))
                    self.rtp_sequence = (self.rtp_sequence + 1) % 65536
                    self.rtp_timestamp = (self.rtp_timestamp + CHUNK_SIZE) % (2**32)
                    
                    # Barge-in check
                    current_time = time.time()
                    if speech_start_time is None:
                        speech_start_time = current_time
                        barge_in_enabled_time = speech_start_time + grace_period
                    if current_time >= barge_in_enabled_time:
                        try:
                            self.rtp_socket.settimeout(0.001)
                            data, addr = self.rtp_socket.recvfrom(1024)
                            if len(data) > 12:
                                audio_payload = data[12:]
                                linear_audio = self.mulaw_to_linear(audio_payload)
                                audio_level = np.sqrt(np.mean(linear_audio**2))
                                if audio_level > BARGE_IN_AUDIO_THRESHOLD:
                                    print(f"🛑 BARGE-IN! Audio: {audio_level:.4f}")
                                    return True
                        except socket.timeout:
                            pass
                        except Exception:
                            pass
                    
                    time.sleep(AUDIO_CHUNK_DELAY)
            
            return True
            
        except Exception as e:
            print(f"❌ Audio send error: {e}")
            return False
    
    def linear_to_mulaw(self, audio_data):
        """Convert linear PCM to mu-law"""
        audio_data = np.clip(audio_data, -1.0, 1.0)
        audio_14bit = (audio_data * 8159).astype(np.int16)
        mulaw_bytes = []
        for sample in audio_14bit:
            sign = 0x80 if sample < 0 else 0x00
            magnitude = abs(sample) + 33
            if magnitude >= 16415:
                segment = 7
                quantized = 0x0F
            else:
                segment = 7
                for j in range(7, -1, -1):
                    if magnitude >= (33 << j):
                        segment = j
                        break
                quantized = (magnitude - 33) >> 1 if segment == 0 else ((magnitude - (33 << segment)) >> (segment - 1)) & 0x0F
            mulaw_value = sign | (segment << 4) | quantized
            mulaw_bytes.append(mulaw_value ^ 0xFF)
        return bytes(mulaw_bytes)
    
    def mulaw_to_linear(self, mulaw_bytes):
        """Convert mu-law to linear PCM"""
        linear_samples = []
        for mulaw_byte in mulaw_bytes:
            mulaw_value = mulaw_byte ^ 0xFF
            sign = mulaw_value & 0x80
            segment = (mulaw_value >> 4) & 0x07
            quantized = mulaw_value & 0x0F
            magnitude = (quantized << 1) + 33 if segment == 0 else ((quantized << (segment - 1)) + (33 << segment))
            magnitude -= 33
            sample = -magnitude if sign else magnitude
            linear_samples.append(sample / 8159.0)
        return np.array(linear_samples, dtype=np.float32)
    
    def monitor_sip_messages(self):
        """Monitor for SIP BYE messages (hang-up detection)"""
        print("📡 Monitoring for hang-up (SIP BYE messages)...")
        monitor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        monitor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        monitor_socket.settimeout(0.5)
        try:
            monitor_socket.bind((self.local_ip, 5060))
        except:
            monitor_socket = self.socket
            monitor_socket.settimeout(0.5)
        while self.call_active:
            try:
                data, addr = monitor_socket.recvfrom(4096)
                message = data.decode()
                if message.startswith('BYE'):
                    print("📞 Hang-up detected (SIP BYE received)!")
                    self.call_active = False
                    lines = message.split('\n')
                    via_line = next((line for line in lines if line.startswith('Via:')), '')
                    to_line = next((line for line in lines if line.startswith('To:')), '')
                    from_line = next((line for line in lines if line.startswith('From:')), '')
                    callid_line = next((line for line in lines if line.startswith('Call-ID:')), '')
                    cseq_line = next((line for line in lines if line.startswith('CSeq:')), '')
                    bye_response = f"""SIP/2.0 200 OK
{via_line}
{to_line}
{from_line}
{callid_line}
{cseq_line}
Content-Length: 0

"""
                    monitor_socket.sendto(bye_response.encode(), addr)
                    break
            except socket.timeout:
                continue
            except Exception:
                continue
        print("📡 SIP monitoring stopped")
    
    def hang_up(self):
        """Hang up the call"""
        try:
            if self.socket and self.call_active:
                to_header = f"<sip:1000@{self.server_ip}>"
                if self.to_tag:
                    to_header += f";tag={self.to_tag}"
                bye = f"""BYE sip:1000@{self.server_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{random.randint(1000, 9999)}
From: <sip:hotline@{self.local_ip}>;tag={self.from_tag}
To: {to_header}
Call-ID: {self.call_id}
CSeq: {self.cseq + 1} BYE
Max-Forwards: 70
Content-Length: 0

"""
                self.socket.sendto(bye.encode(), (self.server_ip, self.server_port))
        except Exception as e:
            print(f"❌ Hangup error: {e}")
        finally:
            self.call_active = False
            if self.socket:
                self.socket.close()
            if self.rtp_socket:
                self.rtp_socket.close()

    def receive_audio_data(self, max_duration=8.0, silence_timeout=1.5):
        if not self.rtp_socket:
            return None
        print(f"🎧 Listening with VAD (max {max_duration}s, {silence_timeout}s silence timeout)...")
        audio_chunks = []
        self.rtp_socket.settimeout(0.1)
        start_time = time.time()
        last_speech_time = start_time
        speech_detected = False
        try:
            while time.time() - start_time < max_duration:
                try:
                    data, addr = self.rtp_socket.recvfrom(1024)
                    current_time = time.time()
                    if len(data) > 12:
                        audio_payload = data[12:]
                        linear_audio = self.mulaw_to_linear(audio_payload)
                        audio_chunks.append(linear_audio)
                        audio_level = np.sqrt(np.mean(linear_audio**2))
                        if audio_level > 0.015:
                            if not speech_detected:
                                print("🎤 Speech detected, listening...")
                                speech_detected = True
                            last_speech_time = current_time
                        if speech_detected and (current_time - last_speech_time) > silence_timeout:
                            print("🔇 Silence detected, stopping...")
                            break
                except socket.timeout:
                    if speech_detected and (time.time() - last_speech_time) > silence_timeout:
                        print("🔇 Silence timeout, stopping...")
                        break
                    continue
        except Exception as e:
            print(f"❌ Audio receive error: {e}")
        if audio_chunks:
            audio_data = np.concatenate(audio_chunks)
            print(f"🎵 Received {len(audio_chunks)} audio packets")
            if len(audio_data) > 0:
                audio_rms = np.sqrt(np.mean(audio_data**2))
                print(f"🔊 Audio received: RMS={audio_rms:.3f}, {len(audio_data)} samples")
            return audio_data
        print("🔇 No audio received")
        return None

class TimeravelHotlineSIP:
    def __init__(self, character="einstein"):
        self.character = character
        self.character_config = CHARACTERS.get(character, CHARACTERS["einstein"])
        self.conversation_history = []
        self.last_user_interaction = time.time()
        self.check_in_count = 0
        self.awaiting_dtmf = True  # Start by awaiting dial sequence
        self.setup_ai_services()
        self.sip_call = None
    
    def setup_ai_services(self):
        self.tts_providers = {}
        if os.getenv("ELEVEN_API_KEY"):
            self.tts_providers["elevenlabs"] = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
        if os.getenv("CARTESIA_API_KEY"):
            self.tts_providers["cartesia"] = cartesia.Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))
        self.active_tts_provider = TTS_PROVIDER
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            print("❌ OPENAI_API_KEY not found")
            sys.exit(1)
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.deepgram_api_key:
            print("❌ DEEPGRAM_API_KEY not found")
            sys.exit(1)
        self.deepgram = Deepgram(self.deepgram_api_key)
    
    def _elevenlabs_tts(self, text):
        """Convert text to speech using ElevenLabs (full buffer)"""
        try:
            client = self.tts_providers["elevenlabs"]
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=self.character_config['voice_id'],
                model_id="eleven_monolingual_v1"
            )
            audio_bytes = b"".join(audio_generator)
            audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
            audio_segment = audio_segment.set_frame_rate(SAMPLE_RATE).set_channels(1)
            audio_data = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768.0
            return audio_data
        except Exception as e:
            print(f"❌ ElevenLabs TTS error: {e}")
            return None
    
    def _cartesia_tts(self, text):
        """Stream Cartesia audio chunks"""
        try:
            client = self.tts_providers["cartesia"]
            audio_generator = client.tts.sse(
                model_id=CARTESIA_MODEL,
                transcript=text,
                voice={"mode": "id", "id": self.character_config['voice_id']},
                output_format={"container": "raw", "encoding": "pcm_s16le", "sample_rate": SAMPLE_RATE},
            )
            for event in audio_generator:
                if event.event == "audio":
                    yield event.data  # raw 16-bit PCM bytes
        except Exception as e:
            print(f"❌ Cartesia TTS error: {e}")
            yield None
    
    def text_to_speech(self, text):
        """Convert text to speech and return a generator of audio chunks"""
        print(f"🗣️ {self.character_config['name']}: {text}")
        character_provider = self.character_config.get('provider', self.active_tts_provider)
        if character_provider == "cartesia":
            return self._cartesia_tts(text)  # Yields chunks progressively
        elif character_provider == "elevenlabs":
            audio_data = self._elevenlabs_tts(text)
            if audio_data is not None:
                # Yield full audio as single chunk for ElevenLabs (non-streaming)
                yield audio_data.tobytes()  # As raw float32 bytes; adjust if needed
            else:
                yield None
        else:
            yield None
    
    def speech_to_text(self, audio_data):
        """Convert speech to text using Deepgram"""
        try:
            audio_16bit = (audio_data * 32767).astype(np.int16)
            audio_segment = AudioSegment(
                audio_16bit.tobytes(),
                frame_rate=SAMPLE_RATE,
                sample_width=2,  # 16-bit
                channels=1
            )
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_bytes = wav_io.getvalue()
            response = self.deepgram.transcription.sync_prerecorded(
                {'buffer': wav_bytes, 'mimetype': 'audio/wav'},
                {
                    'punctuate': True,
                    'language': 'en-US',
                    'model': 'nova',
                    'smart_format': True,
                }
            )
            transcript = response['results']['channels'][0]['alternatives'][0]['transcript']
            if transcript.strip():
                print(f"🎤 You said: '{transcript.strip()}'")
                return transcript.strip()
            else:
                print("🎤 No speech detected")
                return None
        except Exception as e:
            print(f"❌ STT error: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def get_ai_response(self, user_text):
        """Get AI response using OpenAI with conversation memory"""
        try:
            # Add current user message to history
            self.conversation_history.append({"role": "user", "content": user_text})
            
            # Build messages with conversation history
            messages = [
                {
                    "role": "system", 
                    "content": self.character_config['personality'] + "\n\nKeep responses concise and conversational for phone calls. Max 2-3 sentences unless asked for details. You have memory of this entire phone conversation."
                }
            ]
            
            # Add conversation history (keep last 10 exchanges to manage token limits)
            messages.extend(self.conversation_history[-20:])  # Last 20 messages (10 exchanges)
            
            # Use new OpenAI API format with faster settings
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Fast model
                messages=messages,
                max_tokens=150,  # Shorter responses for faster delivery
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Add AI response to history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            return ai_response
            
        except Exception as e:
            print(f"❌ AI response error: {e}")
            return "I'm having trouble thinking right now. Could you repeat that?"
    
    def show_conversation_memory(self):
        """Display current conversation history for debugging"""
        print(f"💭 Conversation memory ({len(self.conversation_history)} messages):")
        for i, msg in enumerate(self.conversation_history[-6:], 1):  # Show last 6 messages
            role_icon = "👤" if msg["role"] == "user" else "🤖"
            print(f"   {i}. {role_icon} {msg['content'][:50]}...")
    
    def should_check_in(self):
        """Determine if character should naturally check in with user"""
        time_since_interaction = time.time() - self.last_user_interaction
        
        # Progressive check-in intervals: 15s, 30s, 60s, then every 90s
        if self.check_in_count == 0 and time_since_interaction > 15:
            return True
        elif self.check_in_count == 1 and time_since_interaction > 30:
            return True
        elif self.check_in_count == 2 and time_since_interaction > 60:
            return True
        elif self.check_in_count >= 3 and time_since_interaction > 90:
            return True
        
        return False
    
    def get_natural_check_in(self):
        """Get a natural check-in message based on character and conversation state"""
        check_ins = [
            "Are you still there?",
            "What's on your mind?",
            "Anything else you'd like to discuss?",
            "I'm here if you have any questions.",
            "Still listening... what would you like to talk about?",
        ]
        
        # Character-specific check-ins
        character_check_ins = {
            "cleopatra": [
                "The silence speaks volumes, mortal. What troubles you?",
                "Even pharaohs pause to listen. What wisdom do you seek?",
                "I sense contemplation. Share your thoughts with me.",
                "The Nile flows, and I remain. What shall we discuss?",
            ],
            "elon": [
                "Still working on something in your head? I get it.",
                "Taking time to process? That's how innovation happens.",
                "Thinking about the future? I'm here for it.",
                "Got any wild ideas brewing? Let's hear them!",
            ],
            "einstein": [
                "Silence is the language of contemplation. What are you pondering?",
                "Even the greatest thoughts need time to form. What's brewing?",
                "I find the quiet moments most profound. What's on your mind?",
                "Imagination needs space to breathe. What are you imagining?",
            ],
            "burt": [
                "Well, don't leave me hangin' here, partner. What's cooking?",
                "Come on now, don't go all shy on the Bandit. What's on your mind?",
                "I can wait all day, good lookin'. Got a story to tell?",
                "Hey there, cat got your tongue? Talk to ol' Burt.",
                "Smokey's got nothin' on awkward silence. What do you say we chat?",
            ],
            "myself": [
                "So... are we just going to sit here in silence? That's not very like us.",
                "Come on, talk to yourself! What's really on your mind?",
                "This is weird, isn't it? But also kind of fascinating. What do you think?",
                "Hey, you called yourself - might as well make it worth it. What's up?",
                "I know you've got something you want to discuss. Let's hear it.",
            ],
            "elvis": [
                "Don't be cruel, darlin'. The King is waiting to hear from you.",
                "All shook up and nothing to say? Come on, honey, talk to me.",
                "Well, it's now or never, baby. What's on your mind?",
                "Don't be a hound dog, speak up! Elvis is listening.",
                "Thank ya, thank ya very much... for the silence? Let's talk, sweetheart!",
            ]
        }
        
        if self.character in character_check_ins:
            options = character_check_ins[self.character] + check_ins
        else:
            options = check_ins
            
        return random.choice(options)
    
    def detect_dtmf_in_audio(self, audio_data):
        """Simple DTMF detection - looks for patterns that might be dial tones"""
        if not SCIPY_AVAILABLE:
            return None
            
        try:
            # Simple energy-based detection for now
            # In a real implementation, you'd use FFT to detect specific frequencies
            audio_level = np.sqrt(np.mean(audio_data**2))
            
            # If we detect a brief, strong signal, assume it's a dial tone
            if audio_level > 0.1:  # High energy threshold for dial tones
                return "TONE_DETECTED"
            
        except Exception:
            pass
        
        return None
    
    def handle_dtmf_sequence(self, sequence):
        """Handle completed DTMF sequence"""
        if sequence == "151":
            print("🎯 Detected dial sequence: 151 - Switching to your AI twin!")
            self.character = "myself"
            self.character_config = CHARACTERS["myself"]
            return True
        return False
    
    def run_conversation(self):
        """Run the main conversation loop"""
        print(f"🎭 Starting Time Travel Hotline with {self.character_config['name']}")
        print("📞 Make sure the SIP proxy is running first!")
        
        # Create SIP call
        self.sip_call = SipPhoneCall()
        
        try:
            # Make the call
            if not self.sip_call.make_call():
                print("❌ Failed to establish call")
                return
            
            print("✅ Call connected! Starting conversation...")
            
            # Ensure call_active is set (fallback in case SIP negotiation didn't set it)
            self.sip_call.call_active = True
            
            # First, listen for DTMF dial sequence
            if self.awaiting_dtmf:
                dial_tone_prompt = "Time Travel Hotline! Please dial your destination: Press 151 to speak with yourself, or just start talking for Einstein."
                print(f"🎵 {dial_tone_prompt}")
                prompt_audio_gen = self.text_to_speech(dial_tone_prompt)
                self.sip_call.send_audio_data(prompt_audio_gen, is_greeting=True)
                
                # Listen for DTMF or speech for 10 seconds
                print("🎧 Listening for dial tones or speech...")
                dtmf_audio = self.sip_call.receive_audio_data(max_duration=10.0, silence_timeout=3.0)
                
                if dtmf_audio is not None:
                    # Try to detect DTMF or treat as speech
                    dtmf_result = self.detect_dtmf_in_audio(dtmf_audio)
                    if dtmf_result:
                        # For now, assume any strong signal during this period means "151"
                        print("🎯 Dial tone detected - assuming 151")
                        self.handle_dtmf_sequence("151")
                    else:
                        # Treat as speech - try to transcribe
                        speech_text = self.speech_to_text(dtmf_audio)
                        if speech_text and "151" in speech_text:
                            print("🎯 Heard '151' in speech - switching to your AI twin!")
                            self.handle_dtmf_sequence("151")
                
                self.awaiting_dtmf = False
            
            # Clear any "hello" or pickup audio before character speaks - be more aggressive
            print("🧹 Clearing pickup audio thoroughly...")
            for _ in range(3):  # Clear multiple times
                self.sip_call.clear_rtp_buffer()
                time.sleep(0.1)  # Let any remaining audio arrive
            print("🧹 Pickup audio clearing complete")
            
            # Send character greeting
            greeting_audio_gen = self.text_to_speech(self.character_config['greeting'])
            self.sip_call.send_audio_data(greeting_audio_gen, is_greeting=True)
            
            # Conversation loop
            while self.sip_call.call_active:
                try:
                    # Clear any buffered audio before listening (including any barge-in audio)
                    self.sip_call.clear_rtp_buffer()
                    print("🧹 Buffer cleared before listening for fresh input")
                    
                    # Listen for user speech
                    print("🎧 Listening...")
                    audio_data = self.sip_call.receive_audio_data(max_duration=8.0, silence_timeout=1.5)
                    
                    if audio_data is not None and len(audio_data) > 0:
                        # Convert speech to text
                        transcription_start = time.time()
                        user_text = self.speech_to_text(audio_data)
                        transcription_end = time.time()
                        
                        if user_text:
                            print(f"👤 User: {user_text}")
                            print(f"⏱️ Transcription took: {transcription_end - transcription_start:.3f}s")
                            
                            # Update interaction time
                            self.last_user_interaction = time.time()
                            self.check_in_count = 0  # Reset check-in counter
                            
                            # Check for goodbye
                            if any(word in user_text.lower() for word in ["goodbye", "bye", "end call", "hang up"]):
                                farewell = "Farewell, my friend! Until we meet again across the streams of time!"
                                farewell_audio_gen = self.text_to_speech(farewell)
                                self.sip_call.send_audio_data(farewell_audio_gen)
                                break
                            
                            # Get AI response
                            ai_start = time.time()
                            ai_response = self.get_ai_response(user_text)
                            ai_end = time.time()
                            
                            # Convert to speech and send via streaming
                            tts_start = time.time()
                            audio_generator = self.text_to_speech(ai_response)
                            tts_end = time.time()  # This is just setup time; streaming happens in send
                            print(f"⏱️ AI response: {ai_end - ai_start:.3f}s + TTS setup: {tts_end - tts_start:.3f}s")
                            self.sip_call.send_audio_data(audio_generator)
                            
                        else:
                            # No speech detected - check if we should naturally check in
                            if self.should_check_in():
                                check_in_message = self.get_natural_check_in()
                                print(f"🤔 Natural check-in #{self.check_in_count + 1}")
                                print(f"🗣️ {self.character_config['name']}: {check_in_message}")
                                
                                check_in_audio_gen = self.text_to_speech(check_in_message)
                                self.sip_call.send_audio_data(check_in_audio_gen)
                                
                                self.check_in_count += 1
                            else:
                                # Just wait quietly - no immediate response
                                print("🔇 Waiting quietly...")
                    
                except KeyboardInterrupt:
                    print("\n📞 Ending call...")
                    break
                except Exception as e:
                    print(f"❌ Conversation error: {e}")
                    break
            
        finally:
            # Hang up
            if self.sip_call:
                self.sip_call.hang_up()
            print("📞 Call ended")

def main():
    import io
    
    parser = argparse.ArgumentParser(description='Time Travel Hotline - SIP Version')
    parser.add_argument('--character', choices=CHARACTERS.keys(), default='einstein',
                        help='Choose your time traveler')
    args = parser.parse_args()
    
    print("📞 Time Travel Hotline - SIP Version")
    print("=" * 50)
    print(f"🎭 Character: {CHARACTERS[args.character]['name']}")
    print("💡 Make sure to start the SIP proxy first: python working_sip_proxy.py")
    print()
    
    # Check dependencies
    if not AI_AVAILABLE:
        print("❌ AI libraries not available")
        return
    
    if not AUDIO_AVAILABLE:
        print("❌ Audio libraries not available") 
        return
    
    input("Press Enter when SIP proxy is running and HT801 is registered...")
    
    try:
        hotline = TimeravelHotlineSIP(args.character)
        hotline.run_conversation()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()