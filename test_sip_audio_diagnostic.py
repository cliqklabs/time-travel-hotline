#!/usr/bin/env python3
"""
SIP Audio Diagnostic Script
Tests audio negotiation with Grandstream HT801
"""

import socket
import time
import random
import hashlib
import struct

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

def create_sdp_offer():
    """Create SDP offer for audio negotiation"""
    local_ip = get_local_ip()
    return f"""v=0
o=hotline {int(time.time())} {int(time.time())} IN IP4 {local_ip}
s=Time Travel Hotline Audio Session
c=IN IP4 {local_ip}
t=0 0
m=audio 5004 RTP/AVP 0 8 101
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=sendrecv
a=ptime:20
a=maxptime:40
"""

def test_sip_audio_negotiation():
    """Test SIP audio negotiation with the phone"""
    print("🔧 SIP Audio Diagnostic Test")
    print("=" * 50)
    print(f"📞 Target: {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
    print(f"🏠 Local IP: {get_local_ip()}")
    print()
    
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        # Create SIP INVITE with SDP
        call_id = generate_call_id()
        sdp_body = create_sdp_offer()
        
        invite_message = f"""INVITE sip:{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {get_local_ip()}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:test@{get_local_ip()}>;tag={random.randint(1000, 9999)}
To: <sip:{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 1 INVITE
Contact: <sip:test@{get_local_ip()}:5060>
Max-Forwards: 70
User-Agent: SIP Audio Diagnostic Client
Content-Type: application/sdp
Content-Length: {len(sdp_body)}

{sdp_body}"""
        
        print("📤 Sending SIP INVITE with audio capabilities...")
        print("📋 SDP Offer:")
        print(sdp_body)
        print()
        
        sock.sendto(invite_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        print("⏳ Waiting for response...")
        
        # Listen for response
        try:
            data, addr = sock.recvfrom(4096)  # Large buffer for SDP
            response = data.decode()
            
            print("📥 Received Response:")
            print("=" * 30)
            print(response)
            print("=" * 30)
            
            # Parse response
            lines = response.split('\n')
            status_line = lines[0] if lines else ""
            
            print(f"\n📋 Status: {status_line}")
            
            # Look for SDP in response
            sdp_start = response.find('\r\n\r\n') + 4
            if sdp_start > 3:
                sdp_response = response[sdp_start:]
                print(f"\n📋 SDP Response:")
                print(sdp_response)
                
                # Check for audio capabilities
                if "m=audio" in sdp_response:
                    print("✅ Phone supports audio sessions!")
                    
                    # Check for RTP port
                    import re
                    rtp_match = re.search(r'm=audio (\d+) RTP/AVP', sdp_response)
                    if rtp_match:
                        rtp_port = rtp_match.group(1)
                        print(f"📡 Phone RTP port: {rtp_port}")
                    
                    # Check for codecs
                    if "PCMU" in sdp_response:
                        print("✅ Phone supports G.711 μ-law (PCMU)")
                    if "PCMA" in sdp_response:
                        print("✅ Phone supports G.711 A-law (PCMA)")
                    
                    # Check for sendrecv
                    if "sendrecv" in sdp_response:
                        print("✅ Phone supports bidirectional audio")
                    elif "recvonly" in sdp_response:
                        print("⚠️ Phone only supports receive audio")
                    elif "sendonly" in sdp_response:
                        print("⚠️ Phone only supports send audio")
                else:
                    print("❌ Phone doesn't support audio sessions")
            else:
                print("❌ No SDP response received")
                
        except socket.timeout:
            print("⏰ No response received (timeout)")
            print("💡 This suggests the phone might need SIP registration enabled")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_rtp_connectivity():
    """Test RTP port connectivity"""
    print("\n🔧 Testing RTP Connectivity")
    print("=" * 30)
    
    rtp_ports = [5004, 5006, 5008, 5010, 5012, 5014, 5016, 5018, 5020]
    
    for port in rtp_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            
            # Send a test RTP packet
            test_packet = struct.pack('!BBHII', 0x80, 0x00, 1, 0, 0x12345678)
            sock.sendto(test_packet, (SIP_TARGET_IP, port))
            
            try:
                data, addr = sock.recvfrom(1024)
                print(f"✅ Port {port} - RTP response received")
            except socket.timeout:
                print(f"❌ Port {port} - No RTP response")
            
            sock.close()
            
        except Exception as e:
            print(f"❌ Port {port} - Error: {e}")

def main():
    print("🔧 Grandstream HT801 Audio Diagnostic")
    print("=" * 50)
    print("This will test audio negotiation capabilities")
    print()
    
    # Test 1: SIP Audio Negotiation
    test_sip_audio_negotiation()
    
    # Test 2: RTP Connectivity
    test_rtp_connectivity()
    
    print("\n💡 Recommendations:")
    print("1. Enable SIP registration on the HT801")
    print("2. Check audio codec settings (G.711 μ-law)")
    print("3. Verify RTP port range settings")
    print("4. Ensure phone is configured for audio sessions")

if __name__ == "__main__":
    main()
