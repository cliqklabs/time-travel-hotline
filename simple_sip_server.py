#!/usr/bin/env python3
"""
Simple SIP Server for HT801 - Fixed Version
This creates a minimal SIP server that the HT801 can register with
"""

import socket
import threading
import time
import re
import random

class SimpleSipServer:
    def __init__(self, host='0.0.0.0', port=5060):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.registered_clients = {}
        
    def start(self):
        """Start the SIP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            print(f"🚀 SIP Server started on {self.host}:{self.port}")
            print("📞 Configure your HT801 to register with this server")
            print(f"   SIP Server: {self.get_local_ip()}")
            print(f"   Port: {self.port}")
            print("   Username: 1000")
            print("   Password: password")
            
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    threading.Thread(target=self.handle_request, args=(data, addr)).start()
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
    
    def handle_request(self, data, addr):
        """Handle incoming SIP request"""
        try:
            message = data.decode('utf-8')
            lines = message.split('\n')
            first_line = lines[0].strip()
            
            print(f"\n📥 Request from {addr}: {first_line}")
            
            if message.startswith('REGISTER'):
                self.handle_register(message, addr)
            elif message.startswith('INVITE'):
                self.handle_invite(message, addr)
            elif message.startswith('ACK'):
                self.handle_ack(message, addr)
            elif message.startswith('BYE'):
                self.handle_bye(message, addr)
            elif message.startswith('OPTIONS'):
                self.handle_options(message, addr)
            elif message.startswith('SIP/2.0'):
                # This is a SIP response, not a request
                self.handle_response(message, addr)
            else:
                print(f"❓ Unknown request type: {first_line}")
                
        except Exception as e:
            print(f"❌ Error handling request: {e}")
    
    def extract_header(self, message, header_name):
        """Extract header value from SIP message"""
        for line in message.split('\n'):
            if line.startswith(header_name + ':'):
                return line[len(header_name + ':'):].strip()
        return None
    
    def handle_register(self, message, addr):
        """Handle SIP REGISTER request"""
        print("📝 Handling REGISTER request")
        
        # Extract key headers
        call_id = self.extract_header(message, 'Call-ID')
        from_header = self.extract_header(message, 'From')
        to_header = self.extract_header(message, 'To')
        via_header = self.extract_header(message, 'Via')
        cseq = self.extract_header(message, 'CSeq')
        contact = self.extract_header(message, 'Contact')
        
        # Simple registration - just accept it
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
        self.registered_clients[addr] = time.time()
        print("✅ Registration accepted")
    
    def handle_options(self, message, addr):
        """Handle SIP OPTIONS request"""
        print("🔍 Handling OPTIONS request")
        
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
    
    def handle_invite(self, message, addr):
        """Handle SIP INVITE request - Forward to registered HT801"""
        print("📞 Handling INVITE request - Forwarding to HT801!")
        
        call_id = self.extract_header(message, 'Call-ID')
        from_header = self.extract_header(message, 'From')
        to_header = self.extract_header(message, 'To')
        via_header = self.extract_header(message, 'Via')
        cseq = self.extract_header(message, 'CSeq')
        contact = self.extract_header(message, 'Contact')
        
        # Find the registered HT801
        ht801_addr = None
        for client_addr in self.registered_clients:
            if client_addr[0] == "192.168.1.179":  # HT801's IP
                ht801_addr = client_addr
                break
        
        if not ht801_addr:
            print("❌ HT801 not found in registered clients")
            # Send 404 Not Found
            not_found = f"""SIP/2.0 404 Not Found
Via: {via_header}
From: {from_header}
To: {to_header};tag={random.randint(1000, 9999)}
Call-ID: {call_id}
CSeq: {cseq}
Content-Length: 0

"""
            self.socket.sendto(not_found.encode(), addr)
            return
        
        print(f"📤 Forwarding INVITE to HT801 at {ht801_addr}")
        
        # Forward the INVITE to the HT801, but modify the Via header
        modified_invite = message.replace(
            f"Via: SIP/2.0/UDP {addr[0]}:5060",
            f"Via: SIP/2.0/UDP {self.get_local_ip()}:5060;branch=z9hG4bK{random.randint(1000, 9999)}\r\nVia: SIP/2.0/UDP {addr[0]}:5060"
        )
        
        try:
            # Send INVITE to HT801
            self.socket.sendto(modified_invite.encode(), ht801_addr)
            print("📤 INVITE forwarded to HT801")
            
            # Listen for HT801's response and forward it back
            threading.Thread(target=self.forward_responses, args=(call_id, addr, ht801_addr)).start()
            
        except Exception as e:
            print(f"❌ Error forwarding INVITE: {e}")
    
    def forward_responses(self, call_id, original_caller, ht801_addr):
        """Forward responses from HT801 back to caller"""
        timeout_time = time.time() + 30  # 30 second timeout
        received_200_ok = False
        
        # Don't create a separate socket - just monitor the main socket
        while time.time() < timeout_time and not received_200_ok:
            try:
                time.sleep(0.1)  # Small delay to prevent tight loop
                # The main socket handler will take care of forwarding
                # We just need to detect when we get 200 OK
                
            except Exception as e:
                print(f"❌ Response monitoring error: {e}")
                break
    
    def handle_response(self, message, addr):
        """Handle SIP responses from HT801"""
        first_line = message.split('\n')[0].strip()
        print(f"📥 Response from HT801: {first_line}")
        
        # Extract Call-ID to match with pending calls
        call_id = self.extract_header(message, 'Call-ID')
        
        # For now, just show the response
        # In a full implementation, we'd track calls and forward to the right caller
        if "200 OK" in message:
            print("✅ Call answered!")
            # Extract and show SDP
            if '\r\n\r\n' in message:
                sdp_content = message.split('\r\n\r\n')[1]
                if sdp_content.strip():
                    print("📝 HT801's SDP response:")
                    print(sdp_content)
    
        """Handle SIP ACK request"""
        print("✅ Call established (ACK received)")
    
    def handle_bye(self, message, addr):
        """Handle SIP BYE request"""
        print("📞 Call ended (BYE received)")
        
        call_id = self.extract_header(message, 'Call-ID')
        from_header = self.extract_header(message, 'From')
        to_header = self.extract_header(message, 'To')
        via_header = self.extract_header(message, 'Via')
        cseq = self.extract_header(message, 'CSeq')
        
        response = f"""SIP/2.0 200 OK
Via: {via_header}
From: {from_header}
To: {to_header}
Call-ID: {call_id}
CSeq: {cseq}
Content-Length: 0

"""
        
        self.socket.sendto(response.encode(), addr)
        print("✅ BYE response sent")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()

def main():
    print("🎯 Simple SIP Server for HT801")
    print("=" * 40)
    
    server = SimpleSipServer()
    
    try:
        print("Starting server...")
        server.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping server...")
        server.stop()
        print("👋 Server stopped")

if __name__ == "__main__":
    main()