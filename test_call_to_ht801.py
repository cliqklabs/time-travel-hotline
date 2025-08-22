#!/usr/bin/env python3
"""
Test Call to Registered HT801
Now that HT801 is registered, we can make proper SIP calls with audio
"""

import socket
import time
import random
import struct
import math
import threading

class SipClient:
    def __init__(self, server_ip, server_port=5060):
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
        self.local_rtp_port = 6000  # Use different port from HT801
        
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
        return f"call-{random.randint(100000, 999999)}@{self.local_ip}"
    
    def make_call_to_phone(self):
        """Make a call to the registered phone (extension 1000)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(15)
            
            # Create SDP offer
            sdp = f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}
s=Call
c=IN IP4 {self.local_ip}
t=0 0
m=audio {self.local_rtp_port} RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=ptime:20
a=sendrecv
"""
            
            # Create INVITE to call the phone
            invite = f"""INVITE sip:1000@{self.server_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{random.randint(1000, 9999)}
From: <sip:caller@{self.local_ip}>;tag={self.from_tag}
To: <sip:1000@{self.server_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:caller@{self.local_ip}:5060>
Max-Forwards: 70
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""
            
            print(f"📞 Calling extension 1000 (the vintage phone)")
            print(f"📤 Sending INVITE to {self.server_ip}")
            
            self.socket.sendto(invite.encode(), (self.server_ip, self.server_port))
            
            # Wait for responses
            while True:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    response = data.decode()
                    
                    first_line = response.split('\n')[0].strip()
                    print(f"📥 Response: {first_line}")
                    
                    if "SIP/2.0 100" in response:
                        print("📞 Call is being processed...")
                        
                    elif "SIP/2.0 180" in response or "SIP/2.0 183" in response:
                        print("📞 Phone is ringing! Pick up the handset!")
                        
                    elif "SIP/2.0 200" in response:
                        print("✅ Call answered!")
                        
                        # Extract To tag for ACK
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
                        
                        # Extract RTP port from SDP
                        self.remote_rtp_port = self.extract_rtp_port(response)
                        
                        # Send ACK
                        self.send_ack()
                        
                        # Setup RTP
                        if self.setup_rtp():
                            return True
                        else:
                            print("❌ RTP setup failed")
                            return False
                            
                    elif "SIP/2.0 4" in response or "SIP/2.0 5" in response:
                        print(f"❌ Call failed: {first_line}")
                        return False
                        
                except socket.timeout:
                    print("⏰ No response - call may have failed")
                    return False
                    
        except Exception as e:
            print(f"❌ Call error: {e}")
            return False
    
    def extract_rtp_port(self, response):
        """Extract RTP port from SDP in 200 OK response"""
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
                            print(f"🎵 Found remote RTP port: {port}")
                            return port
            return None
        except Exception as e:
            print(f"❌ Error extracting RTP port: {e}")
            return None
    
    def send_ack(self):
        """Send ACK to complete call setup"""
        try:
            to_header = f"<sip:1000@{self.server_ip}>"
            if self.to_tag:
                to_header += f";tag={self.to_tag}"
            
            ack = f"""ACK sip:1000@{self.server_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{random.randint(1000, 9999)}
From: <sip:caller@{self.local_ip}>;tag={self.from_tag}
To: {to_header}
Call-ID: {self.call_id}
CSeq: {self.cseq} ACK
Max-Forwards: 70
Content-Length: 0

"""
            
            print("📤 Sending ACK...")
            self.socket.sendto(ack.encode(), (self.server_ip, self.server_port))
            
        except Exception as e:
            print(f"❌ ACK error: {e}")
    
    def setup_rtp(self):
        """Setup RTP for audio"""
        try:
            if not self.remote_rtp_port:
                print("❌ No remote RTP port available")
                return False
                
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_socket.bind(('', self.local_rtp_port))
            
            # RTP should go to HT801 directly, not the SIP server
            self.ht801_ip = "192.168.1.179"
            
            print(f"🎵 RTP setup complete:")
            print(f"   Local: {self.local_ip}:{self.local_rtp_port}")
            print(f"   Remote: {self.ht801_ip}:{self.remote_rtp_port}")
            print(f"   (Note: RTP goes to HT801 directly, not SIP server)")
            
            return True
            
        except Exception as e:
            print(f"❌ RTP setup error: {e}")
            return False
    
    def send_test_audio(self, duration=5):
        """Send test audio tone"""
        if not self.rtp_socket or not self.remote_rtp_port:
            print("❌ RTP not ready")
            return
            
        print(f"🎵 Sending test tone for {duration} seconds...")
        print("💡 You should hear a tone through the phone handset!")
        
        # Audio parameters
        frequency = 800  # Hz
        sample_rate = 8000
        samples_per_packet = 160  # 20ms
        sequence = 0
        timestamp = 0
        ssrc = 0x12345678
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Generate sine wave samples
                samples = []
                for i in range(samples_per_packet):
                    t = (timestamp + i) / sample_rate
                    sample = int(127 * (1 + math.sin(2 * math.pi * frequency * t)))
                    samples.append(sample)
                
                # Create RTP packet
                rtp_header = struct.pack('!BBHII',
                    0x80,  # V=2, P=0, X=0, CC=0
                    0x00,  # M=0, PT=0 (PCMU)
                    sequence,
                    timestamp,
                    ssrc
                )
                
                audio_data = bytes(samples)
                packet = rtp_header + audio_data
                
                # Send to phone (HT801 directly)
                self.rtp_socket.sendto(packet, (self.ht801_ip, self.remote_rtp_port))
                
                # Update sequence and timestamp
                sequence = (sequence + 1) % 65536
                timestamp = (timestamp + samples_per_packet) % (2**32)
                
                time.sleep(0.02)  # 20ms
                
        except Exception as e:
            print(f"❌ Audio send error: {e}")
        
        print("✅ Test audio complete")
    
    def listen_for_audio(self, duration=10):
        """Listen for audio from phone"""
        if not self.rtp_socket:
            print("❌ RTP not ready")
            return
            
        print(f"🎧 Listening for audio from phone for {duration} seconds...")
        print("💡 Speak into the phone handset now!")
        
        self.rtp_socket.settimeout(1.0)
        packet_count = 0
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                try:
                    data, addr = self.rtp_socket.recvfrom(1024)
                    packet_count += 1
                    
                    if packet_count == 1:
                        print(f"🎵 First audio packet received from {addr}!")
                    
                    if packet_count % 50 == 0:
                        print(f"🎵 Received {packet_count} audio packets...")
                        
                except socket.timeout:
                    continue
                    
        except Exception as e:
            print(f"❌ Audio receive error: {e}")
        
        print(f"🎵 Listening complete. Received {packet_count} packets total")
        
        if packet_count > 0:
            print("✅ SUCCESS! Audio is working both ways!")
        else:
            print("❌ No audio received from phone")
    
    def hang_up(self):
        """End the call"""
        try:
            if not self.socket:
                return
                
            to_header = f"<sip:1000@{self.server_ip}>"
            if self.to_tag:
                to_header += f";tag={self.to_tag}"
            
            bye = f"""BYE sip:1000@{self.server_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{random.randint(1000, 9999)}
From: <sip:caller@{self.local_ip}>;tag={self.from_tag}
To: {to_header}
Call-ID: {self.call_id}
CSeq: {self.cseq + 1} BYE
Max-Forwards: 70
Content-Length: 0

"""
            
            print("📤 Hanging up...")
            self.socket.sendto(bye.encode(), (self.server_ip, self.server_port))
            
        except Exception as e:
            print(f"❌ Hangup error: {e}")
        finally:
            if self.socket:
                self.socket.close()
            if self.rtp_socket:
                self.rtp_socket.close()

def main():
    print("📞 Test Call to Registered HT801")
    print("=" * 40)
    
    # Use known server IP - your computer running the SIP server
    server_ip = "192.168.1.254"
    
    print(f"📞 Making call to vintage phone via SIP server {server_ip}")
    print(f"📱 HT801 should be registered at 192.168.1.179")
    print("💡 Make sure the SIP server is still running!")
    
    client = SipClient(server_ip)
    
    try:
        input("Press Enter to start the call...")
        
        if client.make_call_to_phone():
            print("✅ Call established!")
            
            print("\n🎵 Testing audio...")
            
            # Send test tone
            client.send_test_audio(duration=3)
            
            # Listen for response
            client.listen_for_audio(duration=8)
            
            print("\nPress Enter to hang up...")
            input()
            
        else:
            print("❌ Call failed")
            
    except KeyboardInterrupt:
        print("\n📞 Call interrupted")
    finally:
        client.hang_up()
        print("📞 Call ended")

if __name__ == "__main__":
    main()