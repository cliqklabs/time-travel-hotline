#!/usr/bin/env python3
"""
Simple test script for Chatterbox TTS
"""

import os
import sys

def test_chatterbox_import():
    """Test if Chatterbox can be imported"""
    try:
        print("Testing Chatterbox import...")
        import chatterbox
        print("✅ chatterbox module imported successfully")
        
        # Try to see what's available
        print("Available attributes:", dir(chatterbox))
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_chatterbox_class():
    """Test if Chatterbox class can be instantiated"""
    try:
        print("\nTesting Chatterbox class...")
        from chatterbox import ChatterboxTTS
        print("✅ ChatterboxTTS class imported successfully")
        
        # Try to create an instance (this might take time)
        print("Creating ChatterboxTTS instance...")
        tts = ChatterboxTTS()
        print("✅ ChatterboxTTS instance created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Class instantiation failed: {e}")
        return False

def main():
    print("🎤 Chatterbox TTS Test")
    print("=" * 30)
    
    # Test import
    if not test_chatterbox_import():
        return
    
    # Test class instantiation
    if not test_chatterbox_class():
        return
    
    print("\n✅ All tests passed! Chatterbox is working.")

if __name__ == "__main__":
    main()
