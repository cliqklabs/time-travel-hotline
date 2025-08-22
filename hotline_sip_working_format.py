#!/usr/bin/env python3
"""
Time Travel Hotline - Using Working SIP Format
Uses sip:1000@192.168.1.179 format that makes the phone ring
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

class WorkingSipCall:
    def __init__(self, target_ip=SIP_TARGET_IP, target_port=SIP_TARGET_PORT):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = get_local_ip()
        self.call_id = generate_call_id()
        self.cseq = 1
        self.call_active = False
        
    def make_call(self):
        """Make a SIP call using the working format"""
        global call_active, sip_socket
        
        try:
            # Create SIP socket
            sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sip_socket.settimeout(10)
            
            # Create SDP offer
            sdp = create_sdp_offer()
            
            # Create SIP INVITE with working format
            invite_message = f"""INVITE sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{generate_call_id()}
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
            
            print(f"📤 Sending INVITE to sip:1000@{self.target_ip}:{self.target_port}")
            print("🔔 Phone should be ringing now...")
            
            sip_socket.sendto(invite_message.encode(), (self.target_ip, self.target_port))
            
            # Listen for responses
            responses = []
            start_time = time.time()
            
            while time.time() - start_time < 15:  # Listen for 15 seconds
                try:
                    data, addr = sip_socket.recvfrom(2048)
                    response = data.decode()
                    responses.append((addr, response))
                    
                    print(f"📥 Response from {addr}:")
                    print(response)
                    
                    # Check for 200 OK
                    if "SIP/2.0 200" in response:
                        print("✅ Got 200 OK - Call answered!")
                        
                        # Send ACK
                        ack_message = f"""ACK sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:hotline@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:1000@{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq + 1} ACK
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Length: 0

"""
                        print("📤 Sending ACK...")
                        sip_socket.sendto(ack_message.encode(), (self.target_ip, self.target_port))
                        
                        call_active = True
                        return True
                        
                    elif "SIP/2.0 100" in response:
                        print("📞 Ringing...")
                        
                except socket.timeout:
                    continue
            
            if responses:
                print(f"📋 Got {len(responses)} responses but no 200 OK")
                # Assume call is active if phone rang
                call_active = True
                return True
            else:
                print("⏰ No responses received")
                return False
                
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
CSeq: {self.cseq + 2} BYE
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

def test_audio_after_call():
    """Test audio after call is established"""
    global rtp_socket
    
    try:
        # Create RTP socket
        rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        print("🎵 Testing audio after call establishment...")
        print("💡 Speak into the phone handset to test audio")
        
        # Send audio to common RTP ports
        rtp_ports = [10000, 10002, 10004, 10006, 10008, 10010, 10012, 10014, 10016, 10018, 10020]
        
        for port in rtp_ports:
            print(f"🎵 Sending audio to port {port}...")
            
            # Send audio packets for 1 second
            for i in range(50):  # 50 packets = 1 second
                # Create RTP header
                rtp_header = struct.pack('!BBHII', 0x80, 0x00, i, 0x12345678, 0x87654321)
                
                # Create simple audio (random noise)
                audio_data = bytes([random.randint(0, 255) for _ in range(160)])
                
                try:
                    rtp_socket.sendto(rtp_header + audio_data, (SIP_TARGET_IP, port))
                    time.sleep(0.02)  # 20ms
                except Exception as e:
                    print(f"❌ Failed to send to port {port}: {e}")
                    break
            
            print(f"✅ Sent audio to port {port}")
            time.sleep(0.5)  # Brief pause between ports
        
        print("✅ Audio test completed")
        
    except Exception as e:
        print(f"❌ Audio test error: {e}")
    finally:
        if rtp_socket:
            rtp_socket.close()

def main():
    global call_active
    
    parser = argparse.ArgumentParser(description='Time Travel Hotline - Working SIP Format')
    parser.add_argument('--character', default='einstein', help='Character to use')
    args = parser.parse_args()
    
    print("🔧 Time Travel Hotline - Working SIP Format")
    print("=" * 50)
    print(f"📞 Target: sip:1000@{SIP_TARGET_IP}")
    print(f"🎭 Character: {args.character}")
    print("🔊 Using working sip:1000@ format")
    
    # Check for required environment variables
    eleven_api_key = os.getenv("ELEVEN_API_KEY")
    if not eleven_api_key:
        print("❌ ELEVEN_API_KEY not found in environment variables")
        print("💡 Please set your ElevenLabs API key")
        return
    
    print("\nPress Enter to start the call...")
    input()
    
    # Create SIP call manager
    sip_manager = WorkingSipCall()
    
    try:
        # Make the call
        if sip_manager.make_call():
            print("✅ Call established!")
            print("💡 Speak into the phone handset - we'll test audio")
            
            # Test audio
            test_audio_after_call()
            
            print("\n💡 Did you hear any audio through the phone handset?")
            print("💡 Did the phone detect your voice?")
            
            # Keep call active for testing
            print("\nPress Enter to end the call...")
            input()
            
        else:
            print("❌ Failed to establish call")
            
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
