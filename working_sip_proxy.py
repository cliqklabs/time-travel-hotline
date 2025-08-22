#!/usr/bin/env python3
"""
Working SIP Proxy Server
Simplified proxy that properly forwards calls between test client and HT801
"""

import socket
import threading
import time
import random

class SipProxy:
    def __init__(self, host='0.0.0.0', port=5060):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.registered_clients = {}
        self.call_mappings = {}  # Track call routing
        
    def start(self):
        """Start the SIP proxy"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            print(f"🚀 SIP Proxy started on {self.host}:{self.port}")
            print("📞 HT801 should register, then test client can call")
            
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    threading.Thread(target=self.handle_message, args=(data, addr)).start()
                except socket.error:
                    if self.running:
                        print("❌ Socket error")
                    break
                    
        except Exception as e:
            print(f"❌ Server error: {e}")
        finally:
            if self.socket:
                self.socket.close()
    
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
    
    def handle_message(self, data, addr):
        """Handle any SIP message"""
        try:
            message = data.decode('utf-8')
            first_line = message.split('\n')[0].strip()
            
            print(f"📥 From {addr}: {first_line}")
            
            if message.startswith('REGISTER'):
                self.handle_register(message, addr)
            elif message.startswith('INVITE'):
                self.route_invite(message, addr)
            elif message.startswith('SIP/2.0'):
                self.route_response(message, addr)
            elif message.startswith('ACK'):
                self.route_ack(message, addr)
            elif message.startswith('BYE'):
                self.route_bye(message, addr)
            elif message.startswith('OPTIONS'):
                self.handle_options(message, addr)
            else:
                print(f"❓ Unknown: {first_line}")
                
        except Exception as e:
            print(f"❌ Error handling message: {e}")
    
    def extract_header(self, message, header_name):
        """Extract header value"""
        for line in message.split('\n'):
            if line.startswith(header_name + ':'):
                return line[len(header_name + ':'):].strip()
        return None
    
    def handle_register(self, message, addr):
        """Handle REGISTER"""
        print(f"📝 Registration from {addr}")
        
        # Extract headers
        call_id = self.extract_header(message, 'Call-ID')
        from_header = self.extract_header(message, 'From')
        to_header = self.extract_header(message, 'To')
        via_header = self.extract_header(message, 'Via')
        cseq = self.extract_header(message, 'CSeq')
        contact = self.extract_header(message, 'Contact')
        
        # Accept registration
        response = f"""SIP/2.0 200 OK
Via: {via_header}
From: {from_header}
To: {to_header};tag={random.randint(1000, 9999)}
Call-ID: {call_id}
CSeq: {cseq}
Contact: {contact}
Expires: 3600
Content-Length: 0

"""
        
        self.socket.sendto(response.encode(), addr)
        self.registered_clients[addr] = {"time": time.time(), "contact": contact}
        print(f"✅ Registered {addr}")
    
    def handle_options(self, message, addr):
        """Handle OPTIONS"""
        print(f"🔍 OPTIONS from {addr}")
        
        call_id = self.extract_header(message, 'Call-ID')
        from_header = self.extract_header(message, 'From')
        to_header = self.extract_header(message, 'To')
        via_header = self.extract_header(message, 'Via')
        cseq = self.extract_header(message, 'CSeq')
        
        response = f"""SIP/2.0 200 OK
Via: {via_header}
From: {from_header}
To: {to_header};tag={random.randint(1000, 9999)}
Call-ID: {call_id}
CSeq: {cseq}
Allow: INVITE,ACK,BYE,CANCEL,OPTIONS,REGISTER
Content-Length: 0

"""
        
        self.socket.sendto(response.encode(), addr)
        print("✅ OPTIONS response sent")
    
    def route_invite(self, message, addr):
        """Route INVITE to HT801"""
        print(f"📞 INVITE from {addr} - routing to HT801")
        
        # Find HT801
        ht801_addr = None
        for client_addr in self.registered_clients:
            if client_addr[0] == "192.168.1.179":
                ht801_addr = client_addr
                break
        
        if not ht801_addr:
            print("❌ HT801 not registered")
            self.send_404(message, addr)
            return
        
        # Extract Call-ID for mapping
        call_id = self.extract_header(message, 'Call-ID')
        self.call_mappings[call_id] = {"caller": addr, "callee": ht801_addr}
        
        print(f"📤 Forwarding INVITE to HT801 {ht801_addr}")
        self.socket.sendto(message.encode(), ht801_addr)
    
    def route_response(self, message, addr):
        """Route SIP response back to caller"""
        call_id = self.extract_header(message, 'Call-ID')
        
        if call_id in self.call_mappings:
            mapping = self.call_mappings[call_id]
            
            if addr == mapping["callee"]:  # Response from HT801
                caller_addr = mapping["caller"]
                print(f"📤 Forwarding response to caller {caller_addr}")
                self.socket.sendto(message.encode(), caller_addr)
                
                # Show SDP if this is 200 OK
                if "200 OK" in message and '\r\n\r\n' in message:
                    sdp = message.split('\r\n\r\n')[1]
                    if sdp.strip():
                        print("📝 SDP in response:")
                        print(sdp)
            else:
                print(f"❓ Unexpected response from {addr}")
        else:
            print(f"❓ No call mapping for Call-ID: {call_id}")
    
    def route_ack(self, message, addr):
        """Route ACK to HT801"""
        call_id = self.extract_header(message, 'Call-ID')
        
        if call_id in self.call_mappings:
            mapping = self.call_mappings[call_id]
            if addr == mapping["caller"]:  # ACK from caller
                ht801_addr = mapping["callee"]
                print(f"📤 Forwarding ACK to HT801 {ht801_addr}")
                self.socket.sendto(message.encode(), ht801_addr)
                print("✅ Call established")
    
    def route_bye(self, message, addr):
        """Route BYE"""
        call_id = self.extract_header(message, 'Call-ID')
        
        if call_id in self.call_mappings:
            mapping = self.call_mappings[call_id]
            
            if addr == mapping["caller"]:  # BYE from caller
                ht801_addr = mapping["callee"]
                print(f"📤 Forwarding BYE to HT801 {ht801_addr}")
                self.socket.sendto(message.encode(), ht801_addr)
            elif addr == mapping["callee"]:  # BYE from HT801
                caller_addr = mapping["caller"]
                print(f"📤 Forwarding BYE response to caller {caller_addr}")
                self.socket.sendto(message.encode(), caller_addr)
            
            # Clean up mapping
            del self.call_mappings[call_id]
            print("📞 Call ended")
    
    def send_404(self, original_message, addr):
        """Send 404 Not Found"""
        call_id = self.extract_header(original_message, 'Call-ID')
        from_header = self.extract_header(original_message, 'From')
        to_header = self.extract_header(original_message, 'To')
        via_header = self.extract_header(original_message, 'Via')
        cseq = self.extract_header(original_message, 'CSeq')
        
        response = f"""SIP/2.0 404 Not Found
Via: {via_header}
From: {from_header}
To: {to_header};tag={random.randint(1000, 9999)}
Call-ID: {call_id}
CSeq: {cseq}
Content-Length: 0

"""
        
        self.socket.sendto(response.encode(), addr)
    
    def stop(self):
        """Stop the proxy"""
        self.running = False
        if self.socket:
            self.socket.close()

def main():
    print("🎯 Working SIP Proxy Server")
    print("=" * 30)
    
    proxy = SipProxy()
    
    try:
        proxy.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping proxy...")
        proxy.stop()
        print("👋 Proxy stopped")

if __name__ == "__main__":
    main()