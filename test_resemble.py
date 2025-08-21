#!/usr/bin/env python3
"""
Simple test to debug ResembleAI API response structure
"""

import os
from dotenv import load_dotenv
from resemble import Resemble

# Load environment variables
load_dotenv()

def test_resemble_api():
    print("🎭 Testing ResembleAI API...")
    
    try:
        # Initialize ResembleAI
        api_key = os.getenv("RESEMBLE_API_KEY")
        if not api_key:
            print("❌ RESEMBLE_API_KEY not found in .env file")
            return False
        
        Resemble.api_key(api_key)
        print("✅ ResembleAI API key set")
        
        # Get projects
        projects = Resemble.v2.projects.all(1, 10)
        if not projects['items']:
            print("❌ No projects found")
            return False
        
        project_uuid = projects['items'][0]['uuid']
        print(f"✅ Using project: {project_uuid}")
        
        # Test voice UUID (replace with your actual UUID)
        voice_uuid = "cb5730f9"  # Replace with your actual voice UUID
        
        # Create a test clip
        print("🎭 Creating test clip...")
        response = Resemble.v2.clips.create_sync(
            project_uuid=project_uuid,
            voice_uuid=voice_uuid,
            body="Hello, this is a test of the ResembleAI voice cloning.",
            title="Test Clip",
            sample_rate=24000,
            output_format="wav"
        )
        
        print(f"🔍 Response type: {type(response)}")
        print(f"🔍 Response keys: {list(response.keys())}")
        print(f"🔍 Full response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_resemble_api()
    if success:
        print("\n🎉 ResembleAI API test completed!")
    else:
        print("\n💥 ResembleAI API test failed!")
