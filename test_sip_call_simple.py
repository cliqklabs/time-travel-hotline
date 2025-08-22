#!/usr/bin/env python3
"""
Simple SIP Call Test Script (Alternative)
Tests making a call to Grandstream HT801 at 192.168.1.179
Uses socket-based approach for simplicity
"""

import socket
import time
import random
import hashlib
from datetime import datetime

class SimpleSipCall:
    def __init__(self, target_ip="192.168.1.179", target_port=5060):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = self.get_local_ip()
        self.call_id = self.generate_call_id()
        self.cseq = 1
        
    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Create a socket to get local IP
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
        sip_message = f"""INVITE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{self.generate_call_id()}
From: <sip:test@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:test@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Python SIP Test Client
Content-Length: 0

"""
        return sip_message
    
    def send_sip_message(self, message):
        """Send SIP message to target"""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # Send message
            print(f"📤 Sending SIP message to {self.target_ip}:{self.target_port}")
            print(f"Message:\n{message}")
            
            sock.sendto(message.encode(), (self.target_ip, self.target_port))
            
            # Try to receive response
            try:
                data, addr = sock.recvfrom(1024)
                print(f"📥 Received response from {addr}:")
                print(data.decode())
                return data.decode()
            except socket.timeout:
                print("⏰ No response received (timeout)")
                return None
            finally:
                sock.close()
                
        except Exception as e:
            print(f"❌ Error sending SIP message: {e}")
            return None
    
    def test_call(self):
        """Test making a call"""
        print("🔧 Simple SIP Call Test")
        print("=" * 40)
        print(f"📞 Target: {self.target_ip}:{self.target_port}")
        print(f"🏠 Local IP: {self.local_ip}")
        print(f"🆔 Call-ID: {self.call_id}")
        print()
        
        # Create and send INVITE
        invite_message = self.create_sip_invite()
        response = self.send_sip_message(invite_message)
        
        if response:
            print("✅ SIP message sent successfully!")
            if "200 OK" in response:
                print("🎉 Call accepted by phone!")
            elif "100 Trying" in response:
                print("⏳ Call is being processed...")
            elif "180 Ringing" in response:
                print("🔔 Phone is ringing!")
            else:
                print(f"📋 Response received: {response.split()[1] if len(response.split()) > 1 else 'Unknown'}")
        else:
            print("❌ No response from phone")
            print("💡 Make sure:")
            print("   - Phone is powered on and connected")
            print("   - IP address is correct")
            print("   - SIP registration is disabled (as you mentioned)")
            print("   - Firewall allows UDP port 5060")

def main():
    print("🔧 Simple SIP Call Test Script")
    print("=" * 40)
    
    # Get target IP from user
    target_ip = input("Enter target IP (default: 192.168.1.179): ").strip()
    if not target_ip:
        target_ip = "192.168.1.179"
    
    # Create test instance
    test = SimpleSipCall(target_ip)
    
    print(f"\n📞 Ready to test call to {target_ip}")
    print("Press Enter to send SIP INVITE...")
    input()
    
    # Test the call
    test.test_call()

if __name__ == "__main__":
    main()
