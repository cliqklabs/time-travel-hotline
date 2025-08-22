#!/usr/bin/env python3
"""
SIP Call Debug Script
Tests connectivity to Grandstream HT801 and provides detailed debugging info
"""

import socket
import time
import random
import hashlib
from datetime import datetime

class SipDebugTest:
    def __init__(self, target_ip="192.168.1.179", target_port=5060):
        self.target_ip = target_ip
        self.target_port = target_port
        self.local_ip = self.get_local_ip()
        
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
    
    def test_udp_connectivity(self):
        """Test basic UDP connectivity"""
        print("🔍 Testing UDP connectivity...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            
            # Send a simple UDP packet
            test_data = b"TEST"
            sock.sendto(test_data, (self.target_ip, self.target_port))
            print(f"✅ UDP packet sent to {self.target_ip}:{self.target_port}")
            
            # Try to receive any response
            try:
                data, addr = sock.recvfrom(1024)
                print(f"📥 Received response from {addr}: {data}")
                return True
            except socket.timeout:
                print("⏰ No UDP response (this might be normal)")
                return False
            finally:
                sock.close()
                
        except Exception as e:
            print(f"❌ UDP test failed: {e}")
            return False
    
    def test_sip_options(self):
        """Send SIP OPTIONS request (less intrusive than INVITE)"""
        print("\n🔍 Testing SIP OPTIONS...")
        
        call_id = hashlib.md5(f"{time.time()}{random.randint(1000, 9999)}".encode()).hexdigest()
        
        options_message = f"""OPTIONS sip:{self.target_ip} SIP/2.0
Via: SIP/2.0/UDP {self.local_ip}:5060;branch=z9hG4bK{call_id}
From: <sip:test@{self.local_ip}>;tag={random.randint(1000, 9999)}
To: <sip:{self.target_ip}>
Call-ID: {call_id}
CSeq: 1 OPTIONS
Contact: <sip:test@{self.local_ip}:5060>
Max-Forwards: 70
User-Agent: Python SIP Debug Client
Content-Length: 0

"""
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            print(f"📤 Sending SIP OPTIONS to {self.target_ip}:{self.target_port}")
            print(f"Message:\n{options_message}")
            
            sock.sendto(options_message.encode(), (self.target_ip, self.target_port))
            
            try:
                data, addr = sock.recvfrom(1024)
                print(f"📥 Received response from {addr}:")
                print(data.decode())
                return True
            except socket.timeout:
                print("⏰ No SIP response received")
                return False
            finally:
                sock.close()
                
        except Exception as e:
            print(f"❌ SIP OPTIONS failed: {e}")
            return False
    
    def test_different_ports(self):
        """Test common SIP ports"""
        print("\n🔍 Testing different SIP ports...")
        ports_to_test = [5060, 5061, 5062, 5063, 5064, 5065, 5066, 5067, 5068, 5069, 5070]
        
        for port in ports_to_test:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                
                test_data = b"OPTIONS sip:test SIP/2.0\r\n\r\n"
                sock.sendto(test_data, (self.target_ip, port))
                
                try:
                    data, addr = sock.recvfrom(1024)
                    print(f"✅ Port {port} responded: {data[:50]}...")
                except socket.timeout:
                    pass
                finally:
                    sock.close()
                    
            except Exception as e:
                pass
    
    def run_debug_tests(self):
        """Run all debug tests"""
        print("🔧 SIP Debug Test Suite")
        print("=" * 50)
        print(f"📞 Target: {self.target_ip}:{self.target_port}")
        print(f"🏠 Local IP: {self.local_ip}")
        print()
        
        # Test 1: UDP connectivity
        udp_ok = self.test_udp_connectivity()
        
        # Test 2: SIP OPTIONS
        sip_ok = self.test_sip_options()
        
        # Test 3: Different ports
        self.test_different_ports()
        
        print("\n📋 Summary:")
        print(f"   UDP Connectivity: {'✅' if udp_ok else '❌'}")
        print(f"   SIP Response: {'✅' if sip_ok else '❌'}")
        
        if not sip_ok:
            print("\n💡 Troubleshooting suggestions:")
            print("   1. Check if the phone's SIP service is enabled")
            print("   2. Verify the phone's IP address in its web interface")
            print("   3. Check if the phone has any firewall rules blocking SIP")
            print("   4. Try accessing the phone's web interface to verify it's working")
            print("   5. Check if the phone needs to be rebooted")

def main():
    print("🔧 SIP Debug Test Script")
    print("=" * 40)
    
    # Get target IP from user
    target_ip = input("Enter target IP (default: 192.168.1.179): ").strip()
    if not target_ip:
        target_ip = "192.168.1.179"
    
    # Create debug instance
    debug = SipDebugTest(target_ip)
    
    print(f"\n🔍 Ready to debug connection to {target_ip}")
    print("Press Enter to start tests...")
    input()
    
    # Run debug tests
    debug.run_debug_tests()

if __name__ == "__main__":
    main()
