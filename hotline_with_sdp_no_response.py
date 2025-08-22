#!/usr/bin/env python3
"""
Time Travel Hotline - With SDP but No Response Expected
Send SDP in INVITE to establish audio, but don't wait for SIP responses
"""

import os
import sys
import time
import socket
import random
import hashlib
import threading
import signal
import argparse
import struct
import math
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SIP Configuration
SIP_TARGET_IP = "192.168.1.179"
SIP_TARGET_PORT = 5060
RTP_PORT = 5004

# Audio settings
SAMPLE_RATE = 8000
CHANNELS = 1
CHUNK_SIZE = 160  # 20ms at 8kHz

# Global variables
call_active = False
sip_socket = None
rtp_socket = None

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def generate_call_id():
    """Generate a unique Call-ID"""
    timestamp = str(time.time())
    random_num = str(random.randint(1000, 9999))
    return hashlib.md5(f"{timestamp}{random_num}".encode()).hexdigest()

def create_sdp_offer():
    """Create SDP offer for audio negotiation"""
    local_ip = get_local_ip()
    
    sdp = f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {local_ip}
s=SIP Call
c=IN IP4 {local_ip}
t=0 0
m=audio {RTP_PORT} RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=ptime:20
a=sendrecv
"""
    return sdp

class SdpNoResponseSipCall:
    def __init__(self, target_ip=SIP_TARGET_IP, target_port=SIP_TARGET_PORT):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = get_local_ip()
        self.call_id = generate_call_id()
        self.cseq = 1
        self.call_active = False
        
    def make_call(self):
        """Make a SIP call with SDP but don't wait for response"""
        global call_active, sip_socket
        
        try:
            # Create SIP socket
            sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Create SDP offer
            sdp = create_sdp_offer()
            
            # Create INVITE with SDP
            branch = f"z9hG4bK{generate_call_id()}"
            invite_message = f"""INVITE sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch={branch}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:1000@{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""
            
            print(f"📤 Sending INVITE with SDP to sip:1000@{self.target_ip}:{self.target_port}")
            print("🔔 Phone should be ringing now...")
            print("🎵 SDP included for audio negotiation")
            
            sip_socket.sendto(invite_message.encode(), (self.target_ip, self.target_port))
            
            # Wait a moment for the phone to ring
            time.sleep(3)
            
            print("✅ Assuming call is connected with SDP audio")
            call_active = True
            return True
                
        except Exception as e:
            print(f"❌ Error making call: {e}")
            return False
    
    def hang_up(self):
        """Hang up the call"""
        global call_active, sip_socket
        
        if not call_active:
            return
            
        try:
            # Send BYE message
            bye_message = f"""BYE sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:1000@{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq + 1} BYE
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Length: 0

"""
            
            print("📤 Sending BYE message...")
            sip_socket.sendto(bye_message.encode(), (self.target_ip, self.target_port))
            
        except Exception as e:
            print(f"❌ Error hanging up: {e}")
        finally:
            call_active = False
            if sip_socket:
                sip_socket.close()

def test_audio_with_negotiated_port():
    """Test audio using the RTP port from our SDP offer"""
    global rtp_socket
    
    try:
        # Create RTP socket
        rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print("🎵 Testing audio with negotiated RTP...")
        print(f"💡 Sending to our offered RTP port: {RTP_PORT}")
        print("💡 Pick up the phone handset and listen for audio")
        
        # First try our negotiated port
        print(f"🎵 Sending test tone to negotiated port {RTP_PORT}...")
        
        # Send a 1000Hz test tone for 3 seconds
        frequency = 1000  # Hz
        duration = 3  # seconds
        samples_per_packet = 160  # 20ms at 8kHz
        packets_per_second = 50
        
        for packet_num in range(duration * packets_per_second):
            # Generate sine wave samples
            samples = []
            for i in range(samples_per_packet):
                sample_time = (packet_num * samples_per_packet + i) / SAMPLE_RATE
                sample_value = int(127 * (1 + math.sin(2 * math.pi * frequency * sample_time)))
                samples.append(sample_value)
            
            # Create RTP header
            rtp_header = struct.pack('!BBHII', 
                0x80,  # Version=2, Padding=0, Extension=0, CC=0
                0x00,  # Marker=0, Payload Type=0 (PCMU)
                packet_num,
                packet_num * samples_per_packet,
                0x12345678  # SSRC
            )
            
            # Create RTP packet
            audio_data = bytes(samples)
            rtp_packet = rtp_header + audio_data
            
            try:
                rtp_socket.sendto(rtp_packet, (SIP_TARGET_IP, RTP_PORT))
                time.sleep(0.02)  # 20ms
            except Exception as e:
                print(f"❌ Failed to send to port {RTP_PORT}: {e}")
                break
        
        print(f"✅ Sent test tone to negotiated port {RTP_PORT}")
        
        # If that didn't work, try common Grandstream ports
        print("\n🎵 Also trying common Grandstream RTP ports...")
        common_ports = [10000, 10002, 10004, 10006, 10008, 10010]
        
        for port in common_ports:
            print(f"🎵 Sending brief tone to port {port}...")
            
            # Send shorter tone (1 second) to each port
            for packet_num in range(50):  # 1 second
                # Generate sine wave samples
                samples = []
                for i in range(samples_per_packet):
                    sample_time = (packet_num * samples_per_packet + i) / SAMPLE_RATE
                    sample_value = int(127 * (1 + math.sin(2 * math.pi * frequency * sample_time)))
                    samples.append(sample_value)
                
                # Create RTP header
                rtp_header = struct.pack('!BBHII', 
                    0x80, 0x00, packet_num, packet_num * samples_per_packet, 0x12345678
                )
                
                # Create RTP packet
                audio_data = bytes(samples)
                rtp_packet = rtp_header + audio_data
                
                try:
                    rtp_socket.sendto(rtp_packet, (SIP_TARGET_IP, port))
                    time.sleep(0.02)  # 20ms
                except Exception as e:
                    print(f"❌ Failed to send to port {port}: {e}")
                    break
            
            print(f"✅ Sent tone to port {port}")
            time.sleep(0.3)  # Brief pause between ports
        
        print("✅ Audio test completed")
        
    except Exception as e:
        print(f"❌ Audio test error: {e}")
    finally:
        if rtp_socket:
            rtp_socket.close()

def main():
    global call_active
    
    parser = argparse.ArgumentParser(description='Time Travel Hotline - SDP No Response')
    parser.add_argument('--character', default='einstein', help='Character to use')
    args = parser.parse_args()
    
    print("🔧 Time Travel Hotline - SDP No Response")
    print("=" * 50)
    print(f"📞 Target: sip:1000@{SIP_TARGET_IP}")
    print(f"🎭 Character: {args.character}")
    print("🔊 Sending SDP for audio negotiation but not waiting for response")
    
    # Check for required environment variables
    eleven_api_key = os.getenv("ELEVEN_API_KEY")
    if not eleven_api_key:
        print("❌ ELEVEN_API_KEY not found in environment variables")
        print("💡 Please set your ElevenLabs API key")
        return
    
    print("\nPress Enter to start the call...")
    input()
    
    # Create SIP call manager
    sip_manager = SdpNoResponseSipCall()
    
    try:
        # Make the call
        if sip_manager.make_call():
            print("📞 Phone should be ringing!")
            print("💡 Pick up the phone handset when it rings")
            print("⏳ Waiting 5 seconds for you to pick up...")
            
            # Wait for user to pick up
            time.sleep(5)
            
            # Test audio with SDP negotiation
            test_audio_with_negotiated_port()
            
            print("\n💡 Did you hear the test tone through the phone handset?")
            print("💡 If yes, SDP negotiation is working!")
            
            # Keep call active for testing
            print("\nPress Enter to end the call...")
            input()
            
        else:
            print("❌ Failed to send INVITE")
            
    except KeyboardInterrupt:
        print("\n📞 Call interrupted by user")
    finally:
        # Hang up
        sip_manager.hang_up()
        print("📞 Call ended")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
