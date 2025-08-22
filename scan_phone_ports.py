#!/usr/bin/env python3
"""
Simple Port Scanner for Grandstream HT801
Scans common ports to see what the phone is listening on
"""

import socket
import threading
import time

def scan_port(target_ip, port, timeout=1):
    """Scan a single port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        sock.close()
        return result == 0
    except:
        return False

def scan_udp_port(target_ip, port, timeout=1):
    """Scan a single UDP port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # Send a test packet
        test_data = b"SCAN"
        sock.sendto(test_data, (target_ip, port))
        
        try:
            data, addr = sock.recvfrom(1024)
            sock.close()
            return True
        except socket.timeout:
            sock.close()
            return False
    except:
        return False

def main():
    target_ip = "192.168.1.179"
    
    print(f"🔍 Scanning {target_ip} for open ports...")
    print("=" * 50)
    
    # Common ports to check
    tcp_ports = [
        80,    # HTTP (web interface)
        443,   # HTTPS
        22,    # SSH
        23,    # Telnet
        5060,  # SIP
        5061,  # SIP TLS
        5062,  # SIP alternative
        5063,  # SIP alternative
        5064,  # SIP alternative
        5065,  # SIP alternative
        5066,  # SIP alternative
        5067,  # SIP alternative
        5068,  # SIP alternative
        5069,  # SIP alternative
        5070,  # SIP alternative
        8080,  # HTTP alternative
        8081,  # HTTP alternative
        8082,  # HTTP alternative
    ]
    
    udp_ports = [
        5060,  # SIP
        5061,  # SIP TLS
        5062,  # SIP alternative
        5063,  # SIP alternative
        5064,  # SIP alternative
        5065,  # SIP alternative
        5066,  # SIP alternative
        5067,  # SIP alternative
        5068,  # SIP alternative
        5069,  # SIP alternative
        5070,  # SIP alternative
        161,   # SNMP
        162,   # SNMP trap
    ]
    
    print("🔍 Scanning TCP ports...")
    open_tcp_ports = []
    for port in tcp_ports:
        if scan_port(target_ip, port):
            open_tcp_ports.append(port)
            print(f"✅ TCP {port} - OPEN")
        else:
            print(f"❌ TCP {port} - closed")
    
    print("\n🔍 Scanning UDP ports...")
    open_udp_ports = []
    for port in udp_ports:
        if scan_udp_port(target_ip, port):
            open_udp_ports.append(port)
            print(f"✅ UDP {port} - OPEN")
        else:
            print(f"❌ UDP {port} - closed")
    
    print("\n📋 Summary:")
    print("=" * 30)
    if open_tcp_ports:
        print(f"✅ Open TCP ports: {open_tcp_ports}")
    else:
        print("❌ No open TCP ports found")
        
    if open_udp_ports:
        print(f"✅ Open UDP ports: {open_udp_ports}")
    else:
        print("❌ No open UDP ports found")
    
    if not open_tcp_ports and not open_udp_ports:
        print("\n💡 No open ports found. This could mean:")
        print("   1. The phone is not powered on")
        print("   2. The IP address is incorrect")
        print("   3. The phone has a firewall blocking all connections")
        print("   4. The phone needs to be rebooted")
        print("\n🔧 Try accessing the web interface at:")
        print(f"   http://{target_ip}")
        print(f"   https://{target_ip}")

if __name__ == "__main__":
    main()
