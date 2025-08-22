#!/usr/bin/env python3
"""
Simple SIP Call Test Script
Tests making a call to Grandstream HT801 at 192.168.1.179
"""

import time
import sys
import threading
from datetime import datetime

try:
    import pjsua2 as pj
    PJSUA2_AVAILABLE = True
except ImportError:
    PJSUA2_AVAILABLE = False
    print("⚠️  pjsua2 not available. Install with: pip install pjsua2")

class SipCallTest:
    def __init__(self):
        self.ep = None
        self.acc = None
        self.call = None
        self.call_connected = False
        
    def log_cb(self, level, str, len):
        """Log callback"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {str}")
        
    def on_incoming_call(self, prm):
        """Handle incoming calls"""
        print(f"📞 Incoming call from: {prm.callInfo.remoteUri}")
        
    def on_call_state(self, prm):
        """Handle call state changes"""
        print(f"📞 Call state: {prm.e.state}")
        
        if prm.e.state == pj.PJSIP_INV_STATE_CONFIRMED:
            print("✅ Call connected!")
            self.call_connected = True
        elif prm.e.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            print("❌ Call disconnected")
            self.call_connected = False
            
    def on_reg_state(self, prm):
        """Handle registration state changes"""
        print(f"📝 Registration state: {prm.code}/{prm.reason}")
        
    def make_call(self, target_uri):
        """Make a call to the specified URI"""
        try:
            # Create endpoint
            self.ep = pj.Endpoint()
            self.ep.libCreate()
            
            # Configure logging
            ep_cfg = pj.EpConfig()
            ep_cfg.logConfig.level = 4
            ep_cfg.logConfig.consoleLevel = 4
            ep_cfg.logConfig.cb = self.log_cb
            self.ep.libInit(ep_cfg)
            
            # Create SIP transport
            sipTpConfig = pj.TransportConfig()
            sipTpConfig.port = 5060
            self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, sipTpConfig)
            
            # Start the library
            self.ep.libStart()
            
            # Create account configuration
            acc_cfg = pj.AccountConfig()
            acc_cfg.idUri = "sip:test@192.168.1.179"
            acc_cfg.regConfig.registrarUri = "sip:192.168.1.179"
            
            # Create account
            self.acc = pj.Account()
            self.acc.create(acc_cfg)
            
            # Set callbacks
            self.acc.setIncomingCallCallback(self.on_incoming_call)
            self.acc.setRegStateCallback(self.on_reg_state)
            
            print(f"📞 Making call to: {target_uri}")
            
            # Create call
            call_param = pj.CallOpParam(True)
            self.call = pj.Call(self.acc)
            self.call.setCallCallback(self.on_call_state)
            self.call.makeCall(target_uri, call_param)
            
            # Wait for call to connect
            timeout = 30
            start_time = time.time()
            while not self.call_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            if self.call_connected:
                print("✅ Call successful! Press Enter to hang up...")
                input()
            else:
                print("❌ Call failed or timed out")
                
        except Exception as e:
            print(f"❌ Error making call: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.call:
                self.call.hangup()
            if self.acc:
                self.acc.shutdown()
            if self.ep:
                self.ep.libDestroy()
        except:
            pass

def main():
    if not PJSUA2_AVAILABLE:
        print("❌ pjsua2 library not available")
        print("Install with: pip install pjsua2")
        return
        
    print("🔧 SIP Call Test Script")
    print("=" * 40)
    
    # Target phone URI
    target_uri = "sip:192.168.1.179"
    
    # Create test instance
    test = SipCallTest()
    
    print(f"📞 Target: {target_uri}")
    print("Press Enter to start call...")
    input()
    
    # Make the call
    test.make_call(target_uri)

if __name__ == "__main__":
    main()
