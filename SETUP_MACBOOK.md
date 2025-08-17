# Time Travel Hotline - MacBook Setup Guide

## ✅ Current Status
Your MacBook environment is now set up and ready for development!

### What's Working:
- ✅ Python 3.9.6 virtual environment created
- ✅ All dependencies installed in isolated environment
- ✅ Audio system tested and working (MacBook Pro Microphone & Speakers)
- ✅ Deepgram SDK compatibility fixed for Python 3.9
- ✅ Environment variables template ready

### What You Need to Do:

## 1. Set Up API Keys
Edit the `.env` file and replace the placeholder values with your actual API keys:

```bash
# Edit the .env file
nano .env
```

Replace these lines with your actual API keys:
```
OPENAI_API_KEY=your_actual_openai_key_here
DEEPGRAM_API_KEY=your_actual_deepgram_key_here
ELEVEN_API_KEY=your_actual_elevenlabs_key_here
```

## 2. Install ffmpeg (Optional but Recommended)
For better audio processing, install ffmpeg:

```bash
# Add Homebrew to PATH (if not already done)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Install ffmpeg
brew install ffmpeg
```

## 3. Test the Application

### Text Mode (No API Keys Required)
Test the basic functionality without voice:

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run in text mode
python hotline_demo_windows.py --text-mode
```

### Voice Mode (Requires API Keys)
Once you have API keys set up:

```bash
# Run with voice input/output
python hotline_demo_windows.py

# Or specify conversation mode
python hotline_demo_windows.py --mode barge  # Stop TTS when user speaks
python hotline_demo_windows.py --mode turn   # Wait for TTS to finish
```

## 4. Development Workflow

### Activate Virtual Environment
```bash
source venv/bin/activate
```

### Install New Dependencies
```bash
pip install package_name
pip freeze > requirements.txt  # Update requirements
```

### Deactivate When Done
```bash
deactivate
```

## 5. Testing Before Raspberry Pi Deployment

1. **Test locally on MacBook** with `--text-mode` first
2. **Test voice functionality** once API keys are set up
3. **Make changes and test** in the MacBook environment
4. **Push to GitHub** when ready
5. **Pull and test on Raspberry Pi**

## Troubleshooting

### Audio Issues
- Run `python test_audio.py` to check audio devices
- Make sure microphone permissions are granted in System Preferences

### API Key Issues
- Check that `.env` file exists and has correct keys
- Verify API keys are valid and have sufficient credits

### Virtual Environment Issues
- Always activate with `source venv/bin/activate`
- If venv gets corrupted, delete `venv/` folder and recreate with `python3 -m venv venv`

## Next Steps
1. Set up your API keys in `.env`
2. Test the application in text mode
3. Test voice functionality
4. Start developing new features!
5. Deploy to Raspberry Pi when ready
