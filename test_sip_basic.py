#!/usr/bin/env python3
"""
Simple SIP Test - Check if phone responds after enabling registration
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

def test_sip_options():
    """Test SIP OPTIONS (less intrusive than INVITE)"""
    print("🔧 Testing SIP OPTIONS...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        call_id = generate_call_id()
        options_message = f"""OPTIONS sip:{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {get_local_ip()}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:test@{get_local_ip()}>;tag={random.randint(1000, 9999)}
To: <sip:{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 1 OPTIONS
Contact: <sip:test@{get_local_ip()}:5060>
Max-Forwards: 70
User-Agent: SIP Test Client
Content-Length: 0

"""
        
        print(f"📤 Sending OPTIONS to {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        sock.sendto(options_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode()
            print(f"📥 Response from {addr}:")
            print(response)
            return True
        except socket.timeout:
            print("⏰ No response to OPTIONS")
            return False
        finally:
            sock.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_sip_invite_simple():
    """Test simple SIP INVITE without SDP"""
    print("\n🔧 Testing simple SIP INVITE...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        call_id = generate_call_id()
        invite_message = f"""INVITE sip:{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {get_local_ip()}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:test@{get_local_ip()}>;tag={random.randint(1000, 9999)}
To: <sip:{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 1 INVITE
Contact: <sip:test@{get_local_ip()}:5060>
Max-Forwards: 70
User-Agent: SIP Test Client
Content-Length: 0

"""
        
        print(f"📤 Sending INVITE to {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        sock.sendto(invite_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode()
            print(f"📥 Response from {addr}:")
            print(response)
            return True
        except socket.timeout:
            print("⏰ No response to INVITE")
            return False
        finally:
            sock.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔧 Simple SIP Test - After Enabling Registration")
    print("=" * 50)
    print(f"📞 Target: {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
    print(f"🏠 Local IP: {get_local_ip()}")
    print()
    
    # Test 1: SIP OPTIONS
    options_ok = test_sip_options()
    
    # Test 2: Simple SIP INVITE
    invite_ok = test_sip_invite_simple()
    
    print("\n📋 Results:")
    print(f"   SIP OPTIONS: {'✅' if options_ok else '❌'}")
    print(f"   SIP INVITE: {'✅' if invite_ok else '❌'}")
    
    if not options_ok and not invite_ok:
        print("\n💡 Phone still not responding. Check:")
        print("   1. SIP registration is actually enabled")
        print("   2. Phone has rebooted after enabling registration")
        print("   3. No firewall blocking SIP traffic")
        print("   4. Phone IP address is correct")

if __name__ == "__main__":
    main()
