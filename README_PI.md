# Time Travel Hotline - Raspberry Pi Deployment

## 🍓 Overview

This guide covers deploying the Time Travel Hotline on a Raspberry Pi with full hardware integration, including rotary dial, hook switch, proximity sensor, and bell control.

## 📋 Requirements

### Hardware
- **Raspberry Pi 4B or 5** (recommended: 4GB+ RAM)
- **Vintage rotary payphone** (Automatic Electric or similar)
- **HT801 ATA** (Analog Telephone Adapter) for safe ringing voltage
- **VL53L0X time-of-flight sensor** for proximity detection
- **Relay module** for bell control
- **Opto-isolators** for rotary dial and hook switch
- **Audio interface** (USB or I2S DAC recommended)

### Software
- **Raspberry Pi OS** (Bullseye or newer)
- **Python 3.8+**
- **Required Python packages** (see requirements_pi.txt)

## 🔧 Hardware Setup

### GPIO Pin Mapping
```
Rotary Dial A:    GPIO 17
Rotary Dial B:    GPIO 18  
Hook Switch:      GPIO 27
Proximity Sensor: GPIO 22
Bell Relay:       GPIO 23
```

### Wiring Diagram
```
Raspberry Pi GPIO ──┐
                    ├── Opto-isolator ── Rotary Dial
                    ├── Opto-isolator ── Hook Switch  
                    ├── VL53L0X ──────── Proximity Sensor
                    └── Relay ────────── Bell
```

### Audio Connection
```
Raspberry Pi Audio ── HT801 ATA ── Phone Handset
```

## 🚀 Quick Setup

### 1. Automated Setup
```bash
# Clone the repository
git clone <repository-url>
cd telephone

# Run the setup script
sudo bash setup_pi.sh
```

### 2. Manual Setup
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3-pip python3-venv libasound2-dev portaudio19-dev

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements_pi.txt
```

## ⚙️ Configuration

### 1. Set API Keys
```bash
export OPENAI_API_KEY="your-openai-key"
export DEEPGRAM_API_KEY="your-deepgram-key"  
export ELEVEN_API_KEY="your-elevenlabs-key"
```

### 2. Audio Configuration
```bash
# Configure audio output
sudo raspi-config
# Navigate to: System Options → Audio → Force 3.5mm jack
```

### 3. GPIO Permissions
```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Set permissions
sudo chown root:gpio /dev/gpiomem
sudo chmod g+rw /dev/gpiomem
```

## 🎯 Usage

### Basic Operation
```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python hotline_demo_windows.py
```

### Command Line Options
```bash
# Text mode (for testing without audio)
python hotline_demo_windows.py --text-mode

# Turn-based mode (no barge-in)
python hotline_demo_windows.py --mode turn

# List audio devices
python hotline_demo_windows.py --list-devices
```

## 🔄 Operation Flow

1. **Proximity Detection**: VL53L0X sensor detects someone approaching
2. **Bell Ringing**: Relay activates the original phone bells
3. **Hook Detection**: Opto-isolator detects when handset is lifted
4. **Dial Input**: Rotary dial pulses are decoded via GPIO interrupts
5. **Character Selection**: Dialed number selects the AI character
6. **Voice Conversation**: Full-duplex voice-to-voice AI interaction
7. **Hang-up Detection**: System resets when handset is replaced

## 🛠️ Troubleshooting

### Audio Issues
```bash
# Check audio devices
python hotline_demo_windows.py --list-devices

# Test audio
speaker-test -t wav -c 2 -f 1000

# Fix ALSA configuration
sudo nano /etc/asound.conf
```

### GPIO Issues
```bash
# Check GPIO permissions
ls -la /dev/gpiomem

# Test GPIO
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"
```

### Performance Issues
```bash
# Monitor system resources
htop

# Check temperature
vcgencmd measure_temp

# Optimize for performance
sudo raspi-config
# Navigate to: Performance Options → GPU Memory → 128
```

## 🔧 Advanced Configuration

### Custom GPIO Pins
Edit the GPIO pin assignments in `hotline_demo_windows.py`:
```python
ROTARY_PIN_A = 17  # Change to your preferred pins
ROTARY_PIN_B = 18
HOOK_PIN = 27
PROXIMITY_PIN = 22
BELL_PIN = 23
```

### Audio Optimization
For better audio performance, consider:
- **USB Audio Interface**: Focusrite Scarlett Solo or similar
- **I2S DAC**: HiFiBerry DAC+ or similar
- **External Amplifier**: For louder bell output

### Auto-Start Service
```bash
# Enable auto-start
sudo systemctl enable time-travel-hotline.service

# Check service status
sudo systemctl status time-travel-hotline.service

# View logs
sudo journalctl -u time-travel-hotline.service -f
```

## 📊 Performance Tips

### Raspberry Pi Optimization
1. **Overclock** (if needed): `sudo raspi-config` → Performance Options
2. **GPU Memory**: Allocate 128MB for GPU
3. **CPU Governor**: Set to performance mode
4. **Cooling**: Ensure adequate cooling for sustained operation

### Audio Latency Reduction
1. **ALSA Buffer Size**: Reduce in `/etc/asound.conf`
2. **Real-time Priority**: Run with `sudo nice -n -20`
3. **CPU Isolation**: Isolate cores for audio processing

## 🔒 Security Considerations

1. **API Key Protection**: Store keys in environment variables
2. **Network Security**: Use firewall rules if exposed to network
3. **Physical Security**: Secure the Pi and wiring
4. **Audio Privacy**: Consider local logging policies

## 📝 Logging and Monitoring

### Enable Logging
```python
# Add to hotline_demo_windows.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hotline.log'),
        logging.StreamHandler()
    ]
)
```

### Monitor System Health
```bash
# Check system resources
watch -n 1 'free -h && df -h && vcgencmd measure_temp'

# Monitor audio levels
alsamixer
```

## 🎨 Customization

### Adding New Characters
Edit the `CHARACTERS` dictionary in `hotline_demo_windows.py`:
```python
CHARACTERS = {
    "1": {"name": "New Character", "voice_pref": "voice_id"},
    # ... existing characters
}
```

### Custom Voice Cloning
```python
# Clone a voice from audio sample
voice_id = eleven.voices.clone(
    name="custom_voice",
    files=["sample.wav"]
)
```

## 🆘 Support

### Common Issues
1. **No Audio**: Check ALSA configuration and permissions
2. **GPIO Errors**: Verify wiring and permissions
3. **API Errors**: Check internet connection and API keys
4. **Performance**: Monitor CPU usage and temperature

### Getting Help
- Check the logs: `tail -f hotline.log`
- Test individual components separately
- Verify hardware connections with multimeter
- Check Raspberry Pi forums for similar issues

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
