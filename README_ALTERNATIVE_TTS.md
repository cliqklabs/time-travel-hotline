# AI Character Hotline - Alternative TTS Providers

This version of the AI Character Hotline supports multiple Text-to-Speech providers, allowing you to choose the best option for your needs.

## 🎯 Features

- **Multiple TTS Providers**: ElevenLabs, Azure Speech, Google TTS (gTTS), and pyttsx3 (offline)
- **Easy Switching**: Change TTS providers via command line argument
- **Cross-Platform**: Works on Windows, macOS, Linux, and Raspberry Pi
- **Barge-in Support**: Interrupt AI speech with your own voice
- **Character Voices**: Different voices for each AI character

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_alternative_tts.txt
```

### 2. Set Up Environment Variables

Create a `.env` file with your API keys:

```env
# Required for all providers
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key

# ElevenLabs (optional)
ELEVEN_API_KEY=your_elevenlabs_key

# Azure Speech (optional)
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=your_azure_region

# gTTS and pyttsx3 don't require API keys
```

### 3. Run the Application

```bash
# Use ElevenLabs (default)
python hotline_demo_alternative_tts.py

# Use Azure Speech
python hotline_demo_alternative_tts.py --tts azure

# Use Google TTS
python hotline_demo_alternative_tts.py --tts gtts

# Use offline pyttsx3
python hotline_demo_alternative_tts.py --tts pyttsx3

# Enable barge-in mode
python hotline_demo_alternative_tts.py --tts azure --mode bargein
```

## 🎤 TTS Provider Comparison

| Provider | Quality | Cost | Offline | Setup Difficulty |
|----------|---------|------|---------|------------------|
| **ElevenLabs** | ⭐⭐⭐⭐⭐ | Paid | ❌ | Easy |
| **Azure Speech** | ⭐⭐⭐⭐ | Paid | ❌ | Medium |
| **Google TTS** | ⭐⭐⭐ | Free | ❌ | Easy |
| **pyttsx3** | ⭐⭐ | Free | ✅ | Easy |

### ElevenLabs
- **Best quality** and most natural-sounding voices
- **Character-specific voices** with unique personalities
- **Paid service** with usage limits
- **Requires API key**

### Azure Speech
- **High quality** neural voices
- **Good variety** of voices and languages
- **Paid service** but often cheaper than ElevenLabs
- **Requires Azure account and API key**

### Google TTS (gTTS)
- **Free** and reliable
- **Good quality** for basic use
- **Limited voice options** (no character-specific voices)
- **Requires internet connection**

### pyttsx3 (Offline)
- **Completely free** and offline
- **System voices** only (quality varies by OS)
- **No internet required**
- **Limited voice customization**

## 🔧 Configuration

### Changing Default TTS Provider

Edit the `TTS_PROVIDER` variable in the script:

```python
TTS_PROVIDER = "azure"  # Change from "elevenlabs" to your preferred provider
```

### Voice Configuration

Each TTS provider has different voice configurations:

#### ElevenLabs
```python
CHARACTERS = {
    "3": {"name": "Albert Einstein", "voice_pref": "JBFqnCBsd6RMkjVDRZzb"},
    # ... more characters
}
```

#### Azure Speech
```python
AZURE_VOICES = {
    "Albert Einstein": "en-US-DavisNeural",
    "Elvis Presley": "en-US-GuyNeural",
    # ... more characters
}
```

#### gTTS and pyttsx3
```python
GTTS_LANGUAGES = {
    "Albert Einstein": "en",
    "Elvis Presley": "en",
    # ... more characters
}
```

## 🎭 Available Characters

1. **Albert Einstein** - Wise, thoughtful physicist
2. **Elvis Presley** - Charming, playful entertainer
3. **Cleopatra** - Regal, strategic queen
4. **Beth Dutton** - Fierce, sharp businesswoman
5. **Elon Musk** - Visionary, technical entrepreneur

## 🔄 Switching Between Providers

You can easily switch TTS providers without changing code:

```bash
# Try different providers
python hotline_demo_alternative_tts.py --tts elevenlabs
python hotline_demo_alternative_tts.py --tts azure
python hotline_demo_alternative_tts.py --tts gtts
python hotline_demo_alternative_tts.py --tts pyttsx3
```

## 🛠️ Troubleshooting

### ElevenLabs Issues
- Check your API key is valid
- Ensure you have sufficient credits
- Verify voice IDs exist in your account

### Azure Speech Issues
- Verify your Azure Speech key and region
- Check your Azure subscription is active
- Ensure the voice names are correct

### gTTS Issues
- Check internet connection
- Some networks may block Google services
- Try different language codes if needed

### pyttsx3 Issues
- Install system TTS engines (e.g., espeak on Linux)
- On Windows, ensure Windows Speech is enabled
- On macOS, ensure system voices are installed

## 📝 Usage Examples

### Basic Usage
```bash
# Start with default ElevenLabs
python hotline_demo_alternative_tts.py
```

### With Barge-in
```bash
# Use Azure with barge-in enabled
python hotline_demo_alternative_tts.py --tts azure --mode bargein
```

### Offline Mode
```bash
# Use pyttsx3 for offline operation
python hotline_demo_alternative_tts.py --tts pyttsx3
```

## 🤝 Contributing

To add a new TTS provider:

1. Add the import and availability check
2. Create a `generate_[provider]_audio()` function
3. Add the provider to the `generate_tts_audio()` function
4. Update the argument parser
5. Add voice configuration if needed

## 📄 License

Same as the main project. See LICENSE file for details.
