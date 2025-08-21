#!/usr/bin/env python3
"""
Simple test to check if Chatterbox can initialize
"""

import time

def test_chatterbox_init():
    print("🎭 Testing Chatterbox initialization...")
    
    try:
        print("📥 Importing Chatterbox...")
        from chatterbox import ChatterboxTTS
        print("✅ Import successful")
        
        print("📥 Initializing Chatterbox (this may take a while for first run)...")
        start_time = time.time()
        
        # Try GPU first, fallback to CPU if not available
        try:
            import torch
            if torch.cuda.is_available():
                print("🚀 Using GPU acceleration...")
                tts = ChatterboxTTS.from_pretrained(device='cuda')
            else:
                print("💻 Using CPU...")
                tts = ChatterboxTTS.from_pretrained(device='cpu')
        except Exception as e:
            print(f"⚠️  GPU failed, using CPU: {e}")
            tts = ChatterboxTTS.from_pretrained(device='cpu')
            
        end_time = time.time()
        
        print(f"✅ Chatterbox initialized in {end_time - start_time:.2f} seconds")
        print(f"📊 Sample rate: {tts.sr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Chatterbox test...")
    success = test_chatterbox_init()
    if success:
        print("\n🎉 Chatterbox initialization successful!")
    else:
        print("\n💥 Chatterbox initialization failed!")
