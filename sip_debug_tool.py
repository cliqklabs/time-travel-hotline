#!/usr/bin/env python3
"""
SIP Debug Tool - Test HT801 SIP Configuration
"""

import socket
import time
import threading

def test_sip_port():
    """Test if HT801 is listening on SIP port"""
    print("🔍 Testing if HT801 is listening on port 5060...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        
        # Send a simple SIP OPTIONS request
        options_msg = """OPTIONS sip:192.168.1.179 SIP/2.0
Via: SIP/2.0/UDP 192.168.1.100:5060;branch=z9hG4bKtest
From: <sip:test@192.168.1.100>;tag=test
To: <sip:192.168.1.179>
Call-ID: test-call-id
CSeq: 1 OPTIONS
Max-Forwards: 70
Content-Length: 0

"""
        
        print("📤 Sending OPTIONS request...")
        sock.sendto(options_msg.encode(), ("192.168.1.179", 5060))
        
        try:
            data, addr = sock.recvfrom(1024)
            response = data.decode()
            print(f"✅ Got response from {addr}:")
            print(response)
            return True
        except socket.timeout:
            print("❌ No response to OPTIONS - HT801 may not be accepting SIP calls")
            return False
            
    except Exception as e:
        print(f"❌ Error testing SIP port: {e}")
        return False
    finally:
        sock.close()

def check_ht801_config():
    """Check HT801 configuration suggestions"""
    print("\n🔧 HT801 Configuration Check:")
    print("=" * 40)
    
    print("1. In HT801 web interface, go to FXS PORT > General Settings")
    print("   - Set 'Port Voltage Off upon no SIP Registration or SIP Registration Failure' to 0")
    print("   - This keeps the phone active even without SIP registration")
    
    print("\n2. In FXS PORT > SIP Settings:")
    print("   - Uncheck 'SIP Registration' (you already did this)")
    print("   - Check 'Outgoing Call without Registration'")
    
    print("\n3. In FXS PORT > Call Settings:")
    print("   - Set 'Unconditional Call Forward' to 'No'")
    print("   - Set 'Call Features' to enable basic calling")
    
    print("\n4. In FXS PORT > Analog Signal Line Configuration:")
    print("   - Check if 'Caller ID Generation' is set properly")
    print("   - Verify 'Ring Frequency' and 'Ring Voltage' settings")

def simple_ring_test():
    """Try the simplest possible SIP call to make phone ring"""
    print("\n📞 Simple Ring Test")
    print("=" * 20)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(10)
        
        # Minimal INVITE - just to make it ring
        invite_msg = """INVITE sip:@192.168.1.179 SIP/2.0
Via: SIP/2.0/UDP 192.168.1.100:5060
From: <sip:test@192.168.1.100>
To: <sip:@192.168.1.179>
Call-ID: simple-test
CSeq: 1 INVITE
Content-Length: 0

"""
        
        print("📤 Sending minimal INVITE...")
        sock.sendto(invite_msg.encode(), ("192.168.1.179", 5060))
        
        print("📞 Does the phone ring? (Check the vintage phone)")
        
        # Listen for any response
        start_time = time.time()
        responses = 0
        
        while time.time() - start_time < 10:
            try:
                data, addr = sock.recvfrom(2048)
                response = data.decode()
                responses += 1
                print(f"\n📥 Response {responses} from {addr}:")
                print(response[:300] + "..." if len(response) > 300 else response)
                
            except socket.timeout:
                break
        
        if responses == 0:
            print("❌ No SIP responses received")
            print("💡 The HT801 may not be configured to accept incoming calls")
        else:
            print(f"✅ Got {responses} SIP responses")
            
    except Exception as e:
        print(f"❌ Simple ring test error: {e}")
    finally:
        sock.close()

def check_network_connectivity():
    """Check basic network connectivity to HT801"""
    print("\n🌐 Network Connectivity Test")
    print("=" * 30)
    
    import subprocess
    import platform
    
    # Ping test
    print("📡 Pinging HT801...")
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(["ping", "-n", "3", "192.168.1.179"], 
                                  capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run(["ping", "-c", "3", "192.168.1.179"], 
                                  capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Ping successful - HT801 is reachable")
        else:
            print("❌ Ping failed - Check network connection")
            print(result.stdout)
    except Exception as e:
        print(f"❌ Ping test failed: {e}")
    
    # Port scan
    print("\n🔍 Checking common ports...")
    ports_to_check = [5060, 5061, 80, 443]
    
    for port in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(("192.168.1.179", port))
            
            if result == 0:
                print(f"✅ Port {port} is open")
            else:
                print(f"❌ Port {port} is closed")
            
            sock.close()
        except Exception as e:
            print(f"❌ Error checking port {port}: {e}")

def main():
    print("🛠️  SIP Debug and Test Tool")
    print("=" * 40)
    print("This tool will help diagnose the SIP connection issue\n")
    
    # Test 1: Network connectivity
    check_network_connectivity()
    
    # Test 2: SIP port response
    test_sip_port()
    
    # Test 3: Simple ring test
    simple_ring_test()
    
    # Test 4: Configuration suggestions
    check_ht801_config()
    
    print("\n💡 Next Steps:")
    print("1. If ping fails: Check network connection")
    print("2. If SIP port doesn't respond: Check HT801 SIP settings")
    print("3. If phone doesn't ring: Check HT801 FXS port settings")
    print("4. Try accessing HT801 web interface and verify settings")
    
    print(f"\n🌐 HT801 Web Interface: http://192.168.1.179")
    print("📋 Check the settings mentioned above")

if __name__ == "__main__":
    main()