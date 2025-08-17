# Time Travel Hotline

A voice-interactive AI phone system that lets you "call" historical figures and fictional characters through a rotary phone interface.

## 🚀 Quick Start (Cross-Platform)

### Automated Setup (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd time-travel-hotline

# Run the automated setup script
python setup_dev.py
```

### Manual Setup
```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux/Raspberry Pi:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp env_template.txt .env
# Edit .env with your API keys
```

## 🎯 Features

- **Voice Recognition**: Real-time speech-to-text using Deepgram
- **AI Conversations**: GPT-4 powered character responses
- **Text-to-Speech**: ElevenLabs voice synthesis
- **Barge-in Support**: Interrupt AI responses by speaking
- **Rotary Dial Interface**: Hardware integration for Raspberry Pi
- **Cross-Platform**: Works on Windows, Mac, and Raspberry Pi

## 👥 Available Characters

- **3**: Albert Einstein (1946)
- **2**: Elvis Presley
- **5**: Cleopatra VII
- **7**: Beth Dutton
- **9**: Elon Musk

## 🎮 Usage

### Text Mode (No API Keys Required)
```bash
python hotline_demo_windows.py --text-mode
```

### Voice Mode (Requires API Keys)
```bash
# Barge-in mode (stop TTS when user speaks)
python hotline_demo_windows.py --mode barge

# Turn-taking mode (wait for TTS to finish)
python hotline_demo_windows.py --mode turn
```

### Raspberry Pi Hardware Mode
```bash
# With rotary dial and hook switch
python hotline_demo_windows.py
```

## 🔧 Configuration

### Required API Keys
Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
ELEVEN_API_KEY=your_elevenlabs_key
```

### Audio Settings
- **Sample Rate**: 16kHz
- **Channels**: Mono
- **Format**: 16-bit PCM
- **VAD Sensitivity**: Adjustable (1-3)

## 🛠️ Development

### Project Structure
```
time-travel-hotline/
├── hotline_demo_windows.py    # Main application
├── setup_dev.py              # Cross-platform setup script
├── requirements.txt          # Python dependencies
├── env_template.txt          # Environment variables template
├── README.md                 # This file
├── README_PI.md             # Raspberry Pi specific guide
├── README_MACBOOK.md        # MacBook development guide
└── venv/                    # Virtual environment (created by setup)
```

### Cross-Platform Compatibility

#### ✅ What Works Everywhere:
- **Virtual Environment**: Isolated dependencies
- **Lazy Loading**: API clients only initialize when needed
- **Audio System**: Automatic device detection
- **Text Mode**: Works without API keys for testing

#### 🔧 Platform-Specific Features:
- **Windows**: Full voice support, optional PyAudio
- **Mac**: Native audio support, Homebrew for ffmpeg
- **Raspberry Pi**: GPIO hardware integration, optimized settings

### Development Workflow
1. **Setup**: Run `python setup_dev.py` on any platform
2. **Develop**: Make changes and test locally
3. **Test**: Use `--text-mode` for quick testing
4. **Deploy**: Push to GitHub, pull on target platform

## 🐛 Troubleshooting

### Common Issues

#### Audio Problems
```bash
# Test audio system
python setup_dev.py

# List audio devices
python hotline_demo_windows.py --list-devices
```

#### API Key Issues
- Verify `.env` file exists and has correct keys
- Check API key validity and credits
- Test with `--text-mode` first

#### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv/
python setup_dev.py
```

### Platform-Specific

#### Windows
- Install Visual C++ Build Tools for some packages
- Use `venv\Scripts\activate` to activate environment

#### Mac
- Grant microphone permissions in System Preferences
- Install ffmpeg: `brew install ffmpeg`

#### Raspberry Pi
- See `README_PI.md` for detailed setup
- Use `setup_pi.sh` for automated Pi setup

## 📝 Recent Improvements

### v2.0 - Cross-Platform Compatibility
- ✅ **Lazy Loading**: API clients only initialize when needed
- ✅ **Virtual Environments**: Isolated dependencies across platforms
- ✅ **Automated Setup**: `setup_dev.py` works on all platforms
- ✅ **Better Error Handling**: Graceful fallbacks for missing components
- ✅ **Python 3.9 Compatibility**: Fixed Deepgram SDK issues

### Breaking Changes
- **None**: All changes are backward compatible
- **Virtual Environment**: Now required (but automated)
- **API Loading**: Delayed until needed (prevents startup errors)

## 🤝 Contributing

See `CONTRIBUTING.md` for development guidelines.

## 📄 License

See `LICENSE` file for details.

---

**Ready to time travel?** 🕰️📞

Run `python setup_dev.py` to get started on any platform!
