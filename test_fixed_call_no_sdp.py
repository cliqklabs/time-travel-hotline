#!/usr/bin/env python3
"""
Test Fixed Call without SDP - See if phone rings first
"""

import socket
import time
import random
import hashlib
import struct
import re
import threading
import math

class TestFixedSipCall:
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
    
    def make_call_no_sdp(self):
        """Make a SIP call without SDP to test if phone rings"""
        try:
            # Create SIP socket
            self.sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sip_socket.settimeout(15)
            
            # Create SIP INVITE without SDP
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
Content-Length: 0

"""
            
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
                        
                        # Extract To tag from response
                        self.to_tag = self.extract_to_tag(response)
                        
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

def main():
    print("📞 Test Fixed Call without SDP")
    print("=" * 40)
    
    # Create call manager
    call_manager = TestFixedSipCall()
    
    try:
        print("Press Enter to start the call...")
        input()
        
        # Make the call
        if call_manager.make_call_no_sdp():
            print("✅ Call established successfully!")
            print("💡 The phone should have rung and been answered")
            
            print("\nPress Enter to hang up...")
            input()
            
        else:
            print("❌ Failed to establish call")
            print("💡 Check if the phone rang anyway")
            
    except KeyboardInterrupt:
        print("\n📞 Call interrupted")
    finally:
        call_manager.hang_up()
        print("📞 Call ended")

if __name__ == "__main__":
    main()
