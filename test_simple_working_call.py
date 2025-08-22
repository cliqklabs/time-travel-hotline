#!/usr/bin/env python3
"""
Simple Working Call Test - Using sip:1000@ format without SDP
"""

import socket
import time
import random
import hashlib

# SIP Configuration
SIP_TARGET_IP = "192.168.1.179"
SIP_TARGET_PORT = 5060

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

def make_simple_call():
    """Make a simple call using the working format"""
    print("🔧 Simple Working Call Test")
    print("=" * 40)
    print(f"📞 Target: sip:1000@{SIP_TARGET_IP}")
    print(f"🏠 Local IP: {get_local_ip()}")
    print()
    
    try:
        # Create SIP socket
        sip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sip_sock.settimeout(10)
        
        # Generate call details
        call_id = generate_call_id()
        local_ip = get_local_ip()
        
        # Create simple INVITE without SDP (like the working test)
        invite_message = f"""INVITE sip:1000@{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:hotline@{local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:1000@{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 1 INVITE
Contact: <sip:hotline@{local_ip}:5060>
Max-Forwards: 70
User-Agent: Time Travel Hotline
Content-Length: 0

"""
        
        print(f"📤 Sending INVITE to sip:1000@{SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        print("🔔 Phone should be ringing now...")
        
        sip_sock.sendto(invite_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        # Listen for responses
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < 15:  # Listen for 15 seconds
            try:
                data, addr = sip_sock.recvfrom(2048)
                response = data.decode()
                responses.append((addr, response))
                
                print(f"📥 Response from {addr}:")
                print(response)
                
                # Check for 200 OK
                if "SIP/2.0 200" in response:
                    print("✅ Got 200 OK - Call answered!")
                    return True
                    
                elif "SIP/2.0 100" in response:
                    print("📞 Ringing...")
                    
            except socket.timeout:
                continue
        
        if responses:
            print(f"📋 Got {len(responses)} responses")
            return False
        else:
            print("⏰ No responses received")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        sip_sock.close()

def main():
    success = make_simple_call()
    
    if success:
        print("\n✅ Call successful!")
        print("💡 The phone should have rung")
    else:
        print("\n❌ Call failed")
        print("💡 Check if the phone rang anyway")

if __name__ == "__main__":
    main()
