#!/usr/bin/env python3
"""
Cross-platform setup script for Time Travel Hotline
Works on Windows, Mac, and Raspberry Pi
"""
import os
import sys
import subprocess
import platform

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major != 3:
        print("❌ Python 3 is required")
        return False
    
    if version.minor < 8:
        print("❌ Python 3.8 or higher is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    if os.path.exists("venv"):
        print("✅ Virtual environment already exists")
        return True
    
    print("🔧 Creating virtual environment...")
    return run_command(f"{sys.executable} -m venv venv", "Creating virtual environment")

def install_dependencies():
    """Install dependencies in virtual environment"""
    # Determine the correct pip command for the virtual environment
    if os.name == 'nt':  # Windows
        pip_cmd = "venv\\Scripts\\pip"
    else:  # Unix-like (Mac, Linux, Raspberry Pi)
        pip_cmd = "venv/bin/pip"
    
    # Upgrade pip first
    run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip")
    
    # Install requirements
    return run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies")

def setup_environment_file():
    """Set up .env file if it doesn't exist"""
    if os.path.exists(".env"):
        print("✅ .env file already exists")
        return True
    
    if os.path.exists("env_template.txt"):
        print("🔧 Creating .env file from template...")
        return run_command("cp env_template.txt .env", "Creating .env file")
    else:
        print("⚠️  No env_template.txt found, skipping .env setup")
        return True

def test_audio_system():
    """Test audio system"""
    print("🔧 Testing audio system...")
    
    # Create a simple test script
    test_script = """
import sounddevice as sd

def test_audio():
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if 'max_input_channels' in d and d['max_input_channels'] > 0]
        output_devices = [d for d in devices if 'max_output_channels' in d and d['max_output_channels'] > 0]
        print(f"✅ Audio system ready: {len(input_devices)} input(s), {len(output_devices)} output(s)")
        return True
    except Exception as e:
        print(f"❌ Audio system test failed: {e}")
        return False

if __name__ == "__main__":
    test_audio()
"""
    
    with open("temp_audio_test.py", "w") as f:
        f.write(test_script)
    
    # Run the test
    if os.name == 'nt':  # Windows
        python_cmd = "venv\\Scripts\\python"
    else:  # Unix-like
        python_cmd = "venv/bin/python"
    
    success = run_command(f"{python_cmd} temp_audio_test.py", "Testing audio system")
    
    # Clean up
    if os.path.exists("temp_audio_test.py"):
        os.remove("temp_audio_test.py")
    
    return success

def main():
    """Main setup function"""
    print("🚀 Time Travel Hotline - Cross-Platform Setup")
    print(f"📍 Platform: {platform.system()} {platform.release()}")
    print()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_virtual_environment():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Setup environment file
    if not setup_environment_file():
        sys.exit(1)
    
    # Test audio system
    test_audio_system()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Activate virtual environment:")
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix-like
        print("   source venv/bin/activate")
    print("3. Test the application:")
    print("   python hotline_demo_windows.py --text-mode")
    print("4. For voice mode, add API keys to .env file")

if __name__ == "__main__":
    main()
