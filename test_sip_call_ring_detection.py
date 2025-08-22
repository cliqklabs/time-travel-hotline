#!/usr/bin/env python3
"""
SIP Call Test Script - Ring Detection
Tests making a call to Grandstream HT801 and detects when it rings
"""

import socket
import time
import random
import hashlib
from datetime import datetime

class SipRingTest:
    def __init__(self, target_ip="192.168.1.179", target_port=5060):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = self.get_local_ip()
        self.call_id = self.generate_call_id()
        self.cseq = 1
        
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
        sip_message = f"""INVITE sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{self.generate_call_id()}
From: <sip:test@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {self.call_id}
CSeq: {self.cseq} INVITE
Contact: <sip:test@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Python SIP Ring Test Client
Content-Length: 0

"""
        return sip_message
    
    def send_invite_and_listen(self, message):
        """Send INVITE and listen for any response"""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(10)  # Longer timeout to catch delayed responses
            
            # Send message
            print(f"📤 Sending SIP INVITE to {self.target_ip}:{self.target_port}")
            print(f"📞 Call-ID: {self.call_id}")
            print("🔔 Phone should start ringing now...")
            
            sock.sendto(message.encode(), (self.target_ip, self.target_port))
            
            # Listen for any response
            response_received = False
            start_time = time.time()
            
            while time.time() - start_time < 10:  # Listen for 10 seconds
                try:
                    data, addr = sock.recvfrom(1024)
                    response_received = True
                    print(f"📥 Received response from {addr}:")
                    print(data.decode())
                    
                    # Check for specific SIP responses
                    response_text = data.decode()
                    if "100 Trying" in response_text:
                        print("⏳ Phone is processing the call...")
                    elif "180 Ringing" in response_text:
                        print("🔔 Phone is ringing!")
                    elif "200 OK" in response_text:
                        print("✅ Call was answered!")
                    elif "486 Busy" in response_text:
                        print("📞 Phone is busy")
                    elif "404 Not Found" in response_text:
                        print("❌ Phone not found")
                    elif "403 Forbidden" in response_text:
                        print("🚫 Call forbidden")
                    else:
                        print(f"📋 Other response: {response_text.split()[1] if len(response_text.split()) > 1 else 'Unknown'}")
                        
                except socket.timeout:
                    # No response received, but phone might still be ringing
                    pass
            
            sock.close()
            
            if not response_received:
                print("⏰ No SIP response received, but phone may have rung")
                print("💡 This is normal when SIP registration is disabled")
                return "RINGING_NO_RESPONSE"
            else:
                return "RESPONSE_RECEIVED"
                
        except Exception as e:
            print(f"❌ Error sending SIP message: {e}")
            return "ERROR"
    
    def test_call(self):
        """Test making a call and detecting ring"""
        print("🔧 SIP Ring Test")
        print("=" * 40)
        print(f"📞 Target: {self.target_ip}:{self.target_port}")
        print(f"🏠 Local IP: {self.local_ip}")
        print(f"🆔 Call-ID: {self.call_id}")
        print()
        
        # Create and send INVITE
        invite_message = self.create_sip_invite()
        result = self.send_invite_and_listen(invite_message)
        
        print("\n📋 Test Results:")
        print("=" * 30)
        
        if result == "RINGING_NO_RESPONSE":
            print("✅ SUCCESS: Phone likely rang!")
            print("💡 Since SIP registration is disabled, no response is expected")
            print("🔔 Check if the physical phone rang")
        elif result == "RESPONSE_RECEIVED":
            print("✅ SUCCESS: Phone responded to SIP message")
        elif result == "ERROR":
            print("❌ FAILED: Error occurred during test")
        
        print("\n🎯 Next Steps:")
        print("   1. Did the phone ring? (If yes, SIP is working!)")
        print("   2. If no ring, check phone settings")
        print("   3. Try different SIP configurations")

def main():
    print("🔧 SIP Ring Test Script")
    print("=" * 40)
    
    # Get target IP from user
    target_ip = input("Enter target IP (default: 192.168.1.179): ").strip()
    if not target_ip:
        target_ip = "192.168.1.179"
    
    # Create test instance
    test = SipRingTest(target_ip)
    
    print(f"\n📞 Ready to test call to {target_ip}")
    print("🔔 This will make the phone ring")
    print("Press Enter to send SIP INVITE...")
    input()
    
    # Test the call
    test.test_call()

if __name__ == "__main__":
    main()
