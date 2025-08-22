#!/usr/bin/env python3
"""
SIP Audio Diagnostic v2 - Test audio negotiation and identify busy signal issue
"""

import socket
import time
import random
import hashlib
import struct

# SIP Configuration
SIP_TARGET_IP = "192.168.1.179"
SIP_TARGET_PORT = 5060
RTP_PORT = 5004

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
m=audio {RTP_PORT} RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=ptime:20
a=sendrecv
"""
    return sdp

def test_sip_invite_with_sdp():
    """Test SIP INVITE with SDP offer"""
    print("🔧 Testing SIP INVITE with SDP offer...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        call_id = generate_call_id()
        local_ip = get_local_ip()
        sdp = create_sdp_offer()
        
        invite_message = f"""INVITE sip:{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:test@{local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 1 INVITE
Contact: <sip:test@{local_ip}:5060>
Max-Forwards: 70
User-Agent: SIP Test Client
Content-Type: application/sdp
Content-Length: {len(sdp)}

{sdp}"""
        
        print(f"📤 Sending INVITE with SDP to {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        print(f"🎵 SDP Offer:")
        print(sdp)
        
        sock.sendto(invite_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        # Listen for multiple responses
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < 10:
            try:
                data, addr = sock.recvfrom(2048)
                response = data.decode()
                responses.append((addr, response))
                print(f"📥 Response from {addr}:")
                print(response)
                
                # Check if we got a 200 OK
                if "SIP/2.0 200" in response:
                    print("✅ Got 200 OK - Audio session established!")
                    return True, responses
                    
            except socket.timeout:
                continue
        
        if responses:
            print(f"📋 Got {len(responses)} responses but no 200 OK")
            return False, responses
        else:
            print("⏰ No responses received")
            return False, []
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, []
    finally:
        sock.close()

def test_rtp_connectivity():
    """Test RTP connectivity to phone"""
    print("\n🔧 Testing RTP connectivity...")
    
    try:
        # Create RTP socket
        rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rtp_sock.settimeout(2)
        
        # Try common RTP ports
        rtp_ports = [10000, 10002, 10004, 10006, 10008, 10010, 10012, 10014, 10016, 10018, 10020]
        
        for port in rtp_ports:
            print(f"🎵 Testing RTP port {port}...")
            
            # Send a dummy RTP packet
            rtp_packet = struct.pack('!BBHII', 0x80, 0x00, 0x0001, 0x12345678, 0x87654321)
            
            try:
                rtp_sock.sendto(rtp_packet, (SIP_TARGET_IP, port))
                print(f"✅ Sent RTP packet to port {port}")
            except Exception as e:
                print(f"❌ Failed to send to port {port}: {e}")
        
        rtp_sock.close()
        
    except Exception as e:
        print(f"❌ RTP test error: {e}")

def test_simple_invite_no_sdp():
    """Test simple INVITE without SDP"""
    print("\n🔧 Testing simple INVITE without SDP...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        call_id = generate_call_id()
        local_ip = get_local_ip()
        
        invite_message = f"""INVITE sip:{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:test@{local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 1 INVITE
Contact: <sip:test@{local_ip}:5060>
Max-Forwards: 70
User-Agent: SIP Test Client
Content-Length: 0

"""
        
        print(f"📤 Sending simple INVITE to {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        sock.sendto(invite_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode()
            print(f"📥 Response from {addr}:")
            print(response)
            return True
        except socket.timeout:
            print("⏰ No response to simple INVITE")
            return False
        finally:
            sock.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔧 SIP Audio Diagnostic v2 - Busy Signal Investigation")
    print("=" * 60)
    print(f"📞 Target: {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
    print(f"🏠 Local IP: {get_local_ip()}")
    print()
    
    # Test 1: Simple INVITE (should ring)
    print("🔧 Test 1: Simple INVITE (should ring)")
    simple_ok = test_simple_invite_no_sdp()
    
    if simple_ok:
        print("✅ Simple INVITE works - phone can receive calls")
    else:
        print("❌ Simple INVITE failed")
    
    # Test 2: INVITE with SDP (should establish audio)
    print("\n🔧 Test 2: INVITE with SDP (should establish audio)")
    sdp_ok, responses = test_sip_invite_with_sdp()
    
    if sdp_ok:
        print("✅ SDP negotiation successful!")
    else:
        print("❌ SDP negotiation failed")
        if responses:
            print("📋 Responses received:")
            for addr, response in responses:
                print(f"   From {addr}: {response.split()[0] if response else 'No status'}")
    
    # Test 3: RTP connectivity
    test_rtp_connectivity()
    
    print("\n📋 Diagnosis Summary:")
    print("=" * 30)
    print(f"   Simple INVITE: {'✅' if simple_ok else '❌'}")
    print(f"   SDP Negotiation: {'✅' if sdp_ok else '❌'}")
    
    if simple_ok and not sdp_ok:
        print("\n💡 Busy Signal Cause: SDP negotiation failure")
        print("   The phone rings but can't establish audio session")
        print("   Possible solutions:")
        print("   1. Check phone audio codec settings")
        print("   2. Try different SDP parameters")
        print("   3. Enable SIP registration with a local server")
    elif not simple_ok:
        print("\n💡 Issue: Phone not receiving SIP calls")
        print("   Check SIP settings and network connectivity")
    else:
        print("\n💡 Audio should work! Try the full hotline again")

if __name__ == "__main__":
    main()
