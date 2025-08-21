# AI Character Hotline - Alternative TTS Providers

This version of the AI Character Hotline supports multiple Text-to-Speech (TTS) providers, allowing you to choose between different voice synthesis options based on your needs.

## Multiple TTS Providers

The system now supports:

1. **ElevenLabs** (Original) - High-quality, character-specific voices
2. **Azure Speech** - Microsoft's neural voices
3. **Google Text-to-Speech (gTTS)** - Free, online TTS
4. **pyttsx3** - Free, offline TTS using system voices
5. **ResembleAI** - Professional voice cloning with reference audio
6. **XTTS (Coqui TTS)** - Open-source voice cloning

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install requirements
pip install -r requirements_alternative_tts.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
# Required for all providers
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# ElevenLabs (original)
ELEVEN_API_KEY=your_elevenlabs_api_key

# Azure Speech (optional)
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=your_azure_region

# ResembleAI (optional)
RESEMBLE_API_KEY=your_resemble_api_key
```

### 3. Run the Hotline

```bash
# Use default TTS provider (ElevenLabs)
python hotline_demo_alternative_tts.py

# Use specific TTS provider
python hotline_demo_alternative_tts.py --tts resemble
python hotline_demo_alternative_tts.py --tts xtts
python hotline_demo_alternative_tts.py --tts azure
python hotline_demo_alternative_tts.py --tts gtts
python hotline_demo_alternative_tts.py --tts pyttsx3

# Enable barge-in mode (interrupt AI while speaking)
python hotline_demo_alternative_tts.py --tts resemble --mode bargein
```

## TTS Provider Comparison

| Provider | Quality | Speed | Cost | Voice Cloning | Offline | Setup |
|----------|---------|-------|------|---------------|---------|-------|
| ElevenLabs | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Paid | ✅ | ❌ | Easy |
| Azure Speech | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Paid | ❌ | ❌ | Easy |
| ResembleAI | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Paid | ✅ | ❌ | Easy |
| XTTS | ⭐⭐⭐⭐ | ⭐⭐⭐ | Free | ✅ | ✅ | Medium |
| gTTS | ⭐⭐⭐ | ⭐⭐⭐ | Free | ❌ | ❌ | Easy |
| pyttsx3 | ⭐⭐ | ⭐⭐⭐⭐ | Free | ❌ | ✅ | Easy |

## Voice Cloning Mode

### ResembleAI Voice Cloning

ResembleAI provides professional-grade voice cloning using reference audio files:

1. **Set up ResembleAI account** at [app.resemble.ai](https://app.resemble.ai)
2. **Get your API key** from the ResembleAI dashboard
3. **Add API key to `.env`**:
   ```env
   RESEMBLE_API_KEY=your_resemble_api_key
   ```
4. **Place reference audio files** in the `voices/` directory:
   - `elon_reference.wav` - Elon Musk voice sample
   - `elvis_reference.wav` - Elvis Presley voice sample
   - `einstein_reference.wav` - Albert Einstein voice sample
   - `cleopatra_reference.wav` - Cleopatra voice sample
   - `beth_reference.wav` - Beth Dutton voice sample

5. **Run with ResembleAI**:
   ```bash
   python hotline_demo_alternative_tts.py --tts resemble
   ```

**Features:**
- Professional voice cloning quality
- Automatic voice creation from reference audio
- High-quality output (24kHz WAV)
- Voice caching (created once, reused)

### XTTS Voice Cloning

XTTS provides free, open-source voice cloning:

1. **Install XTTS** (included in requirements):
   ```bash
   pip install TTS
   ```

2. **Place reference audio files** in the `voices/` directory (same as ResembleAI)

3. **Run with XTTS**:
   ```bash
   python hotline_demo_alternative_tts.py --tts xtts
   ```

**Features:**
- Free and open-source
- Local processing (no API calls)
- GPU acceleration support
- Good voice cloning quality

## Setup Instructions

### ResembleAI Setup

1. **Sign up** at [app.resemble.ai](https://app.resemble.ai)
2. **Create a project** in your ResembleAI dashboard
3. **Get your API key** from Account Settings
4. **Add to `.env`**:
   ```env
   RESEMBLE_API_KEY=your_api_key_here
   ```
5. **Install the ResembleAI library**:
   ```bash
   pip install resemble
   ```

### Reference Audio Requirements

For voice cloning (ResembleAI and XTTS), reference audio files should be:

- **Format**: WAV, MP3, or M4A
- **Duration**: 10-30 seconds of clear speech
- **Quality**: High quality, minimal background noise
- **Content**: Natural speech, not singing or effects
- **Language**: English (for best results)

### Example Reference Audio Setup

```bash
# Create voices directory
mkdir voices

# Add your reference audio files
# Example: elon_reference.wav, elvis_reference.wav, etc.
```

## Usage Examples

### Basic Usage

```bash
# Use ResembleAI for voice cloning
python hotline_demo_alternative_tts.py --tts resemble

# Use XTTS for free voice cloning
python hotline_demo_alternative_tts.py --tts xtts

# Use Azure Speech for high-quality TTS
python hotline_demo_alternative_tts.py --tts azure
```

### Advanced Usage

```bash
# Enable barge-in mode (interrupt AI while speaking)
python hotline_demo_alternative_tts.py --tts resemble --mode bargein

# Use microphone input for conversation
# (Automatically enabled in all modes)
```

## Troubleshooting

### ResembleAI Issues

**"No ResembleAI projects found"**
- Create a project in your ResembleAI dashboard
- Ensure your API key is correct

**"Failed to create ResembleAI voice"**
- Check reference audio file exists and is valid
- Verify API key has sufficient credits
- Ensure audio file meets quality requirements

**"Failed to download ResembleAI audio"**
- Check internet connection
- Verify API key is valid
- Check ResembleAI service status

### XTTS Issues

**"XTTS initialization failed"**
- Install PyTorch with CUDA support for GPU acceleration
- Ensure sufficient disk space for model download
- Check internet connection for initial model download

**"Reference audio file not found"**
- Place reference audio files in `voices/` directory
- Check file names match configuration

### General Issues

**"TTS provider not available"**
- Install missing dependencies: `pip install -r requirements_alternative_tts.txt`
- Check import statements in the script

**Audio playback issues**
- Check system audio settings
- Ensure audio drivers are installed
- Try different audio output devices

## Performance Tips

### ResembleAI
- Voice creation happens once per character
- Subsequent uses are much faster
- High-quality output (24kHz) for best results

### XTTS
- First run downloads models (~2GB)
- GPU acceleration significantly improves speed
- Models are cached locally for future use

### General
- Use barge-in mode for more natural conversations
- Reference audio quality directly affects cloning quality
- Longer reference audio (20-30 seconds) often produces better results

## Contributing

To add new TTS providers:

1. Add import and availability check
2. Add voice configuration
3. Implement `generate_[provider]_audio()` function
4. Update `generate_tts_audio()` function
5. Add to command-line arguments
6. Update requirements and documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.
