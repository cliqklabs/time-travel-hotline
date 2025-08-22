#!/usr/bin/env python3
"""
SIP Test with Response Handling - Try to establish proper audio session
"""

import socket
import time
import random
import hashlib
import struct
import threading

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
    """Create SDP offer"""
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

def parse_sdp_response(response):
    """Parse SDP from response to get phone's RTP port"""
    lines = response.split('\n')
    rtp_port = None
    
    for line in lines:
        if line.startswith('m=audio'):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    rtp_port = int(parts[1])
                    break
                except:
                    pass
    
    return rtp_port

def send_rtp_audio(target_ip, target_port, duration=5):
    """Send RTP audio to target"""
    print(f"🎵 Sending RTP audio to {target_ip}:{target_port} for {duration} seconds...")
    
    try:
        rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Send audio packets
        for i in range(duration * 50):  # 50 packets per second
            # Create RTP header
            rtp_header = struct.pack('!BBHII', 0x80, 0x00, i, 0x12345678, 0x87654321)
            
            # Create simple audio (sine wave-like)
            audio_data = bytes([random.randint(0, 255) for _ in range(160)])
            
            try:
                rtp_sock.sendto(rtp_header + audio_data, (target_ip, target_port))
                time.sleep(0.02)  # 20ms
            except Exception as e:
                print(f"❌ RTP send error: {e}")
                break
                
        print("✅ RTP audio sent")
        rtp_sock.close()
        
    except Exception as e:
        print(f"❌ RTP error: {e}")

def test_sip_with_response_handling():
    """Test SIP with proper response handling"""
    print("🔧 Testing SIP with Response Handling")
    print("=" * 50)
    
    try:
        # Create SIP socket
        sip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sip_sock.settimeout(10)
        
        # Generate call details
        call_id = generate_call_id()
        local_ip = get_local_ip()
        sdp = create_sdp_offer()
        
        # Create SIP INVITE
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
        
        print(f"📤 Sending INVITE to {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        print(f"🎵 SDP Offer:")
        print(sdp)
        
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
                    print("✅ Got 200 OK - Audio session established!")
                    
                    # Parse SDP to get phone's RTP port
                    rtp_port = parse_sdp_response(response)
                    if rtp_port:
                        print(f"🎵 Phone RTP port: {rtp_port}")
                        
                        # Send ACK
                        ack_message = f"""ACK sip:{SIP_TARGET_IP} SIP/2.0
Via: SIP/2.0/UDP {local_ip}:5060;branch=z9hG4bK{generate_call_id()}
From: <sip:test@{local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{SIP_TARGET_IP}>
Call-ID: {call_id}
CSeq: 2 ACK
Max-Forwards: 70
User-Agent: SIP Test Client
Content-Length: 0

"""
                        print("📤 Sending ACK...")
                        sip_sock.sendto(ack_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
                        
                        # Send RTP audio
                        send_rtp_audio(SIP_TARGET_IP, rtp_port, 5)
                        
                        return True
                    else:
                        print("❌ Could not parse RTP port from SDP")
                        
                elif "SIP/2.0 100" in response:
                    print("📞 Ringing...")
                    
            except socket.timeout:
                continue
        
        if responses:
            print(f"📋 Got {len(responses)} responses but no 200 OK")
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
    print("🔧 SIP Test with Response Handling")
    print("=" * 50)
    print(f"📞 Target: {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
    print(f"🏠 Local IP: {get_local_ip()}")
    print()
    
    success = test_sip_with_response_handling()
    
    if success:
        print("\n✅ Audio session established successfully!")
        print("💡 You should hear audio through the phone handset")
    else:
        print("\n❌ Failed to establish audio session")
        print("💡 The phone may not support this type of audio negotiation")

if __name__ == "__main__":
    main()
