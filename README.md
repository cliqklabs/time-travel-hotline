# Time Travel Hotline 🕰️📞

Transform a vintage rotary payphone into an AI-powered, voice-to-voice experience that connects callers to historical and fictional characters.

## 🌟 Overview

The Time Travel Hotline transforms a vintage rotary payphone into an AI-powered, voice-to-voice experience. At first glance, it appears to be a standard mid-20th-century phone with working bells, rotary dial, and authentic heft. But once lifted off the hook, the phone connects callers to a conversational AI system capable of embodying historical and fictional characters with cloned or stylized voices.

**Dial "3" and suddenly find yourself speaking with Einstein; dial "5" and Cleopatra answers; choose "7" and Beth Dutton fires back sharp one-liners.**

## ✨ Features

- **🎯 Authentic Hardware Integration**: Rotary dial, hook switch, proximity sensor, and bell control
- **🤖 AI Character Conversations**: Einstein, Elvis, Cleopatra, Beth Dutton, Elon Musk, and more
- **🎤 Voice-to-Voice AI**: Full-duplex conversations with barge-in capability
- **🔔 Proximity Detection**: Bells ring when someone approaches
- **📱 Cross-Platform**: Works on Windows PC and Raspberry Pi
- **💬 Text Mode**: Console input for quiet testing

## 🏗️ Architecture

```
Vintage Phone Hardware ←→ Raspberry Pi ←→ Cloud AI Services
     (Rotary Dial)         (GPIO Control)     (OpenAI GPT-4)
     (Hook Switch)         (Audio Bridge)     (Deepgram ASR)
     (Bells)               (Proximity)        (ElevenLabs TTS)
```

## 🚀 Quick Start

### **PC Development Mode**
```bash
# Clone the repository
git clone https://github.com/cliqklabs/time-travel-hotline.git
cd time-travel-hotline

# Install dependencies
pip install -r requirements.txt

# Set up API keys
cp env_template.txt .env
# Edit .env file with your actual API keys

# Run in text mode (no microphone needed)
python hotline_demo_windows.py --text-mode

# Run with voice
python hotline_demo_windows.py --mode barge
```

### **Raspberry Pi Production Mode**
```bash
# Automated setup
sudo bash setup_pi.sh

# Manual setup
pip install -r requirements_pi.txt
python hotline_demo_windows.py
```

## 📋 Requirements

### **Hardware (for Pi deployment)**
- Raspberry Pi 4B/5 (4GB+ RAM recommended)
- Vintage rotary payphone
- HT801 ATA (Analog Telephone Adapter)
- VL53L0X proximity sensor
- Relay module for bell control
- Opto-isolators for rotary dial and hook switch

### **Software**
- Python 3.8+
- OpenAI API key
- Deepgram API key
- ElevenLabs API key

## 🎮 Usage

### **Character Selection**
- **3**: Albert Einstein (1946)
- **2**: Elvis Presley
- **5**: Cleopatra VII
- **7**: Beth Dutton
- **9**: Elon Musk

### **Command Line Options**
```bash
# Text mode (quiet testing)
python hotline_demo_windows.py --text-mode

# Turn-based mode (no barge-in)
python hotline_demo_windows.py --mode turn

# List audio devices
python hotline_demo_windows.py --list-devices
```

## 🔧 Hardware Setup

### **GPIO Pin Mapping (Raspberry Pi)**
```
Rotary Dial A:    GPIO 17
Rotary Dial B:    GPIO 18  
Hook Switch:      GPIO 27
Proximity Sensor: GPIO 22
Bell Relay:       GPIO 23
```

## 📚 Documentation

- **[Raspberry Pi Deployment Guide](README_PI.md)** - Complete hardware setup and deployment
- **[Project Background](project_background.md)** - Detailed project vision and objectives

## 🛠️ Development

### **Adding New Characters**
Edit the `CHARACTERS` dictionary in `hotline_demo_windows.py`:
```python
CHARACTERS = {
    "1": {"name": "New Character", "voice_pref": "voice_id"},
    # ... existing characters
}
```

### **Custom Voice Cloning**
```python
# Clone a voice from audio sample
voice_id = eleven.voices.clone(
    name="custom_voice",
    files=["sample.wav"]
)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 conversational AI
- **Deepgram** for speech recognition
- **ElevenLabs** for voice synthesis
- **Raspberry Pi Foundation** for the amazing hardware platform

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/cliqklabs/time-travel-hotline/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cliqklabs/time-travel-hotline/discussions)
- **Wiki**: [Project Wiki](https://github.com/cliqklabs/time-travel-hotline/wiki)

---

**Made with ❤️ for the love of vintage technology and AI innovation**
