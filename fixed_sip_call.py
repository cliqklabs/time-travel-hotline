#!/usr/bin/env python3
"""
Fixed SIP Call with Proper Audio Handling
Properly parses SDP response and establishes RTP audio connection
"""

import socket
import time
import random
import hashlib
import struct
import re
import threading
import math

class FixedSipCall:
    def __init__(self, target_ip="192.168.1.179", target_port=5060):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = self.get_local_ip()
        self.call_id = self.generate_call_id()
        self.cseq = 1
        self.from_tag = str(random.randint(1000, 9999))
        self.to_tag = None
        self.remote_rtp_port = None
        self.local_rtp_port = 5004
        self.call_active = False
        self.sip_socket = None
        self.rtp_socket = None
        
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
    
    def create_sdp_offer(self):
        """Create SDP offer for audio negotiation"""
        sdp = f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}
s=SIP Call
c=IN IP4 {self.local_ip}
t=0 0
m=audio {self.local_rtp_port} RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=ptime:20
a=sendrecv
"""
        return sdp
    
    def parse_sdp_response(self, response):
        """Parse SDP from 200 OK response to get remote RTP port"""
        try:
            # Look for SDP content after the headers
            sdp_start = response.find('\r\n\r\n')
            if sdp_start == -1:
                return None
                
            sdp_content = response[sdp_start + 4:]
            
            # Find the media line (m=audio port ...)
            for line in sdp_content.split('\n'):
                line = line.strip()
                if line.startswith('m=audio'):
                    parts = line.split()
                    if len(parts) >= 2:
                        port = int(parts[1])
                        print(f"🎵 Found remote RTP port: {port}")
                        return port
            
            return None
        except Exception as e:
            print(f"❌ Error parsing SDP: {e}")
            return None
    
    def extract_to_tag(self, response):
        """Extract To tag from response"""
        try:
            to_line = None
            for line in response.split('\n'):
                if line.startswith('To:'):
                    to_line = line
                    break
            
            if to_line and 'tag=' in to_line:
                tag_start = to_line.find('tag=') + 4
                tag_end = to_line.find(';', tag_start)
                if tag_end == -1:
                    tag_end = len(to_line)
                return to_line[tag_start:tag_end].strip()
            
            return None
        except Exception as e:
            print(f"❌ Error extracting To tag: {e}")
            return None
    
    def make_call(self):
        """Make a SIP call with proper audio setup"""
        try:
            # Create SIP socket
            self.sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sip_socket.settimeout(15)
            
            # Create SDP offer
            sdp = self.create_sdp_offer()
            
            # Create SIP INVITE
            branch = f"z9hG4bK{self.generate_call_id()}"
            invite_message = f"""INVITE sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch={branch}
From: <sip:hotline@{self.local_ip}>;tag={self.from_tag}
To: <sip:1000@{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:hotline@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""
            
            print(f"📤 Sending INVITE to sip:1000@{self.target_ip}")
            print("📞 Phone should be ringing...")
            
            self.sip_socket.sendto(invite_message.encode(), (self.target_ip, self.target_port))
            
            # Wait for responses
            while True:
                try:
                    data, addr = self.sip_socket.recvfrom(4096)
                    response = data.decode()
                    
                    print(f"📥 Response from {addr}:")
                    print(response[:200] + "..." if len(response) > 200 else response)
                    
                    if "SIP/2.0 100" in response:
                        print("📞 Ringing...")
                        
                    elif "SIP/2.0 180" in response:
                        print("📞 Ringing (180)...")
                        
                    elif "SIP/2.0 200" in response:
                        print("✅ Call answered (200 OK)!")
                        
                        # Extract To tag and RTP port from response
                        self.to_tag = self.extract_to_tag(response)
                        self.remote_rtp_port = self.parse_sdp_response(response)
                        
                        if not self.remote_rtp_port:
                            print("❌ Could not find remote RTP port in response")
                            return False
                        
                        # Send ACK
                        self.cseq += 1
                        ack_branch = f"z9hG4bK{self.generate_call_id()}"
                        to_header = f"<sip:1000@{self.target_ip}>"
                        if self.to_tag:
                            to_header += f";tag={self.to_tag}"
                        
                        ack_message = f"""ACK sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch={ack_branch}
From: <sip:hotline@{self.local_ip}>;tag={self.from_tag}
To: {to_header}
Call-ID: {self.call_id}
CSeq: {self.cseq} ACK
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Length: 0

"""
                        
                        print("📤 Sending ACK...")
                        self.sip_socket.sendto(ack_message.encode(), (self.target_ip, self.target_port))
                        
                        self.call_active = True
                        return True
                        
                    elif "SIP/2.0 4" in response or "SIP/2.0 5" in response or "SIP/2.0 6" in response:
                        print(f"❌ Call failed: {response.split()[2]}")
                        return False
                        
                except socket.timeout:
                    print("⏰ No response received")
                    return False
                    
        except Exception as e:
            print(f"❌ Error making call: {e}")
            return False
    
    def setup_rtp_audio(self):
        """Setup RTP audio connection"""
        if not self.remote_rtp_port or not self.call_active:
            print("❌ Cannot setup RTP - no remote port or call not active")
            return False
            
        try:
            # Create RTP socket
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_socket.bind(('', self.local_rtp_port))
            
            print(f"🎵 RTP setup: Local port {self.local_rtp_port} -> Remote {self.target_ip}:{self.remote_rtp_port}")
            return True
            
        except Exception as e:
            print(f"❌ RTP setup failed: {e}")
            return False
    
    def send_audio_test(self, duration=5):
        """Send test audio (simple tone)"""
        if not self.rtp_socket or not self.remote_rtp_port:
            print("❌ RTP not setup")
            return
            
        print(f"🎵 Sending test audio for {duration} seconds...")
        
        # RTP parameters
        sequence = 0
        timestamp = 0
        ssrc = 0x12345678
        
        # Generate a simple 1000Hz tone
        sample_rate = 8000
        frequency = 1000
        samples_per_packet = 160  # 20ms at 8kHz
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Generate tone samples (simple sine wave)
                samples = []
                for i in range(samples_per_packet):
                    sample_time = (timestamp + i) / sample_rate
                    sample_value = int(127 * (1 + math.sin(2 * math.pi * frequency * sample_time)))
                    samples.append(sample_value)
                
                # Create RTP header
                rtp_header = struct.pack('!BBHII', 
                    0x80,  # Version=2, Padding=0, Extension=0, CC=0
                    0x00,  # Marker=0, Payload Type=0 (PCMU)
                    sequence,
                    timestamp,
                    ssrc
                )
                
                # Create RTP packet
                audio_data = bytes(samples)
                rtp_packet = rtp_header + audio_data
                
                # Send packet
                self.rtp_socket.sendto(rtp_packet, (self.target_ip, self.remote_rtp_port))
                
                # Update counters
                sequence = (sequence + 1) % 65536
                timestamp = (timestamp + samples_per_packet) % (2**32)
                
                # Wait for next packet time (20ms)
                time.sleep(0.02)
                
        except Exception as e:
            print(f"❌ Audio send error: {e}")
    
    def listen_for_audio(self, duration=10):
        """Listen for incoming RTP audio"""
        if not self.rtp_socket:
            print("❌ RTP not setup")
            return
            
        print(f"🎧 Listening for audio for {duration} seconds...")
        print("💡 Speak into the phone handset now!")
        
        self.rtp_socket.settimeout(1.0)
        
        start_time = time.time()
        packet_count = 0
        
        try:
            while time.time() - start_time < duration:
                try:
                    data, addr = self.rtp_socket.recvfrom(1024)
                    packet_count += 1
                    
                    if packet_count == 1:
                        print(f"🎵 First audio packet received from {addr}!")
                        print(f"📊 Packet size: {len(data)} bytes")
                    
                    if packet_count % 50 == 0:  # Every second
                        print(f"🎵 Received {packet_count} audio packets")
                        
                except socket.timeout:
                    continue
                    
        except Exception as e:
            print(f"❌ Audio receive error: {e}")
        
        print(f"🎵 Audio listening complete. Received {packet_count} packets total")
        
        if packet_count > 0:
            print("✅ Audio is working! The phone is sending audio data.")
        else:
            print("❌ No audio received. Check if handset is off hook and you're speaking.")
    
    def hang_up(self):
        """Hang up the call"""
        if not self.call_active:
            return
            
        try:
            # Send BYE message
            self.cseq += 1
            bye_branch = f"z9hG4bK{self.generate_call_id()}"
            to_header = f"<sip:1000@{self.target_ip}>"
            if self.to_tag:
                to_header += f";tag={self.to_tag}"
            
            bye_message = f"""BYE sip:1000@{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch={bye_branch}
From: <sip:hotline@{self.local_ip}>;tag={self.from_tag}
To: {to_header}
Call-ID: {self.call_id}
CSeq: {self.cseq} BYE
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Length: 0

"""
            
            print("📤 Sending BYE message...")
            self.sip_socket.sendto(bye_message.encode(), (self.target_ip, self.target_port))
            
        except Exception as e:
            print(f"❌ Error hanging up: {e}")
        finally:
            self.call_active = False
            if self.sip_socket:
                self.sip_socket.close()
            if self.rtp_socket:
                self.rtp_socket.close()

def main():
    import math
    
    print("📞 Fixed SIP Call with Proper Audio")
    print("=" * 40)
    
    # Create call manager
    call_manager = FixedSipCall()
    
    try:
        print("Press Enter to start the call...")
        input()
        
        # Make the call
        if call_manager.make_call():
            print("✅ Call established successfully!")
            
            # Setup RTP audio
            if call_manager.setup_rtp_audio():
                print("✅ RTP audio setup complete!")
                
                print("\nChoose test:")
                print("1. Send test tone to phone (you should hear it)")
                print("2. Listen for audio from phone (speak into handset)")
                print("3. Both")
                
                choice = input("Enter choice (1/2/3): ").strip()
                
                if choice in ['1', '3']:
                    call_manager.send_audio_test(duration=3)
                    
                if choice in ['2', '3']:
                    call_manager.listen_for_audio(duration=10)
                    
            else:
                print("❌ RTP audio setup failed")
                
            print("\nPress Enter to hang up...")
            input()
            
        else:
            print("❌ Failed to establish call")
            
    except KeyboardInterrupt:
        print("\n📞 Call interrupted")
    finally:
        call_manager.hang_up()
        print("📞 Call ended")

if __name__ == "__main__":
    main()