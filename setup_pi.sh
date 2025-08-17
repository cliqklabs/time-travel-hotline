#!/bin/bash

# Time Travel Hotline - Raspberry Pi Setup Script
# Run with: sudo bash setup_pi.sh

echo "🍓 Setting up Time Travel Hotline for Raspberry Pi..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    libasound2-dev \
    portaudio19-dev \
    python3-pyaudio \
    git \
    build-essential \
    cmake \
    pkg-config

# Enable audio
echo "🔊 Configuring audio..."
sudo raspi-config nonint do_audio 0  # Enable audio output
sudo raspi-config nonint do_audio 1  # Force audio through 3.5mm jack

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements_pi.txt

# Configure ALSA for better audio performance
echo "🎵 Optimizing ALSA audio settings..."
sudo tee /etc/asound.conf > /dev/null <<EOF
pcm.!default {
    type plug
    slave.pcm "hw:0,0"
}

ctl.!default {
    type hw
    card 0
}
EOF

# Set up GPIO permissions
echo "🔌 Setting up GPIO permissions..."
sudo usermod -a -G gpio $USER
sudo chown root:gpio /dev/gpiomem
sudo chmod g+rw /dev/gpiomem

# Create systemd service for auto-start
echo "🚀 Creating systemd service..."
sudo tee /etc/systemd/system/time-travel-hotline.service > /dev/null <<EOF
[Unit]
Description=Time Travel Hotline
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python hotline_demo_windows.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service (optional - uncomment to auto-start)
# sudo systemctl enable time-travel-hotline.service

echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Set your API keys in the .env file:"
echo "   cp env_template.txt .env"
echo "   nano .env  # Edit with your actual API keys"
echo ""
echo "2. Connect your hardware:"
echo "   - Rotary dial: GPIO 17 & 18"
echo "   - Hook switch: GPIO 27"
echo "   - Proximity sensor: GPIO 22"
echo "   - Bell relay: GPIO 23"
echo ""
echo "3. Test the system:"
echo "   source venv/bin/activate"
echo "   python hotline_demo_windows.py"
echo ""
echo "4. To auto-start on boot (optional):"
echo "   sudo systemctl enable time-travel-hotline.service"
