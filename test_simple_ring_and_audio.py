#!/usr/bin/env python3
"""
Simple Ring and Audio Test - Make phone ring, then try to send audio
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

def make_phone_ring():
    """Make the phone ring with simple INVITE"""
    print("🔔 Making phone ring...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        
        call_id = generate_call_id()
        local_ip = get_local_ip()
        
        # Simple INVITE without SDP
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
        
        print(f"📤 Sending INVITE to {SIP_TARGET_IP}:{SIP_TARGET_PORT}")
        sock.sendto(invite_message.encode(), (SIP_TARGET_IP, SIP_TARGET_PORT))
        
        print("✅ Phone should be ringing now!")
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Error making phone ring: {e}")
        return False

def send_audio_to_common_ports():
    """Send audio to common RTP ports"""
    print("\n🎵 Sending audio to common RTP ports...")
    
    # Common RTP ports used by Grandstream devices
    rtp_ports = [10000, 10002, 10004, 10006, 10008, 10010, 10012, 10014, 10016, 10018, 10020]
    
    try:
        rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        for port in rtp_ports:
            print(f"🎵 Sending audio to port {port}...")
            
            # Send audio packets for 2 seconds
            for i in range(100):  # 100 packets = 2 seconds
                # Create RTP header
                rtp_header = struct.pack('!BBHII', 0x80, 0x00, i, 0x12345678, 0x87654321)
                
                # Create simple audio (random noise)
                audio_data = bytes([random.randint(0, 255) for _ in range(160)])
                
                try:
                    rtp_sock.sendto(rtp_header + audio_data, (SIP_TARGET_IP, port))
                    time.sleep(0.02)  # 20ms
                except Exception as e:
                    print(f"❌ Failed to send to port {port}: {e}")
                    break
            
            print(f"✅ Sent audio to port {port}")
            time.sleep(0.5)  # Brief pause between ports
        
        rtp_sock.close()
        print("✅ Audio test completed")
        
    except Exception as e:
        print(f"❌ Audio test error: {e}")

def main():
    print("🔧 Simple Ring and Audio Test")
    print("=" * 40)
    print(f"📞 Target: {SIP_TARGET_IP}")
    print(f"🏠 Local IP: {get_local_ip()}")
    print()
    
    # Step 1: Make phone ring
    if make_phone_ring():
        print("\n📞 Phone is ringing!")
        print("💡 Pick up the phone when it rings")
        print("⏳ Waiting 5 seconds for you to pick up...")
        
        # Wait for user to pick up
        time.sleep(5)
        
        # Step 2: Send audio to common ports
        send_audio_to_common_ports()
        
        print("\n💡 Did you hear any audio through the phone handset?")
        print("💡 If yes, we found the right RTP port!")
        print("💡 If no, the phone may need different configuration")
        
        # Keep call active for testing
        print("\nPress Enter to end test...")
        input()
        
    else:
        print("❌ Failed to make phone ring")

if __name__ == "__main__":
    main()
