#!/usr/bin/env python3
"""
Time Travel Hotline - Simple SIP Audio Version
Simplified version to avoid busy signal issues
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

def create_minimal_sdp():
    """Create minimal SDP offer"""
    local_ip = get_local_ip()
    
    sdp = f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {local_ip}
s=SIP Call
c=IN IP4 {local_ip}
t=0 0
m=audio {RTP_PORT} RTP/AVP 0
a=rtpmap:0 PCMU/8000
"""
    return sdp

class SimpleSipCall:
    def __init__(self, target_ip=SIP_TARGET_IP, target_port=SIP_TARGET_PORT):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = get_local_ip()
        self.call_id = generate_call_id()
        self.cseq = 1
        self.call_active = False
        
    def make_call(self):
        """Make a simple SIP call"""
        global call_active, sip_socket
        
        try:
            # Create SIP socket
            sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sip_socket.settimeout(5)
            
            # Create minimal SDP
            sdp = create_minimal_sdp()
            
            # Create SIP INVITE
            invite_message = f"""INVITE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""
            
            print(f"📤 Sending SIP INVITE to {self.target_ip}:{self.target_port}")
            sip_socket.sendto(invite_message.encode(), (self.target_ip, self.target_port))
            
            # Wait a moment for the call to establish
            time.sleep(2)
            
            # Assume call is active (since phone rings)
            call_active = True
            print("✅ Call established (phone should be ringing)")
            
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
            bye_message = f"""BYE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} BYE
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

def simple_audio_test():
    """Simple audio test - just send some audio data"""
    global rtp_socket
    
    try:
        # Create RTP socket
        rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print("🎵 Starting simple audio test...")
        print("💡 Speak into the phone handset to test audio")
        
        # Send some dummy RTP packets
        for i in range(50):  # Send for 1 second (50 * 20ms)
            # Create simple RTP packet
            rtp_header = struct.pack('!BBHII', 0x80, 0x00, i, 0x12345678, 0x87654321)
            rtp_payload = b'\x00' * 160  # Silent audio
            
            try:
                rtp_socket.sendto(rtp_header + rtp_payload, (SIP_TARGET_IP, 10000))
                time.sleep(0.02)  # 20ms
            except:
                pass
                
        print("✅ Audio test completed")
        
    except Exception as e:
        print(f"❌ Audio test error: {e}")
    finally:
        if rtp_socket:
            rtp_socket.close()

def main():
    global call_active
    
    parser = argparse.ArgumentParser(description='Time Travel Hotline - Simple SIP Audio')
    parser.add_argument('--character', default='einstein', help='Character to use')
    args = parser.parse_args()
    
    print("🔧 Time Travel Hotline - Simple SIP Audio")
    print("=" * 50)
    print(f"📞 Target Phone: {SIP_TARGET_IP}")
    print(f"🎭 Character: {args.character}")
    print("🔊 Simple audio test mode")
    
    # Check for required environment variables
    eleven_api_key = os.getenv("ELEVEN_API_KEY")
    if not eleven_api_key:
        print("❌ ELEVEN_API_KEY not found in environment variables")
        print("💡 Please set your ElevenLabs API key")
        return
    
    print("\nPress Enter to start the call...")
    input()
    
    # Create SIP call manager
    sip_manager = SimpleSipCall()
    
    try:
        # Make the call
        if sip_manager.make_call():
            print("🔔 Phone should be ringing now...")
            print("📞 Pick up the phone when it rings")
            print("💡 We'll test basic audio connectivity")
            
            # Wait for user to pick up
            time.sleep(5)
            
            # Test simple audio
            simple_audio_test()
            
            print("\n💡 Did you hear anything through the phone speaker?")
            print("💡 Did the phone detect your voice?")
            
            # Keep call active for testing
            print("\nPress Enter to end the call...")
            input()
            
        else:
            print("❌ Failed to make call")
            
    except KeyboardInterrupt:
        print("\n📞 Call interrupted by user")
    finally:
        # Hang up
        sip_manager.hang_up()
        print("📞 Call ended")
        print("👋 Goodbye!")

if __name__ == "__main__":
    import struct
    main()
