# Changelog

All notable changes to the Time Travel Hotline project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD workflow
- Comprehensive documentation
- Contributing guidelines
- Security scanning with Bandit

## [1.0.0] - 2024-01-XX

### Added
- **Core AI Integration**: OpenAI GPT-4, Deepgram ASR, ElevenLabs TTS
- **Voice-to-Voice Conversations**: Full-duplex AI character interactions
- **Barge-in Capability**: Interrupt AI speech with natural conversation flow
- **Character System**: Einstein, Elvis, Cleopatra, Beth Dutton, Elon Musk
- **Cross-Platform Support**: Windows PC and Raspberry Pi compatibility
- **Text Mode**: Console input for quiet testing and development
- **Hardware Integration**: GPIO support for rotary dial, hook switch, proximity sensor, bell control
- **Audio Optimization**: ALSA configuration for Raspberry Pi
- **Error Handling**: Comprehensive error recovery and user feedback
- **Audio Device Validation**: Automatic detection and troubleshooting

### Technical Features
- **Rotary Dial Decoding**: Gray code pulse detection and number interpretation
- **Proximity Detection**: VL53L0X sensor integration for automatic bell ringing
- **Hook Switch Monitoring**: Real-time off-hook detection
- **Bell Control**: Relay-based activation of original phone bells
- **Audio Processing**: WebRTC VAD, silence detection, audio format conversion
- **Threading**: Non-blocking audio capture and playback
- **Configuration Management**: Environment variable support and CLI options

### Documentation
- **README.md**: Comprehensive project overview and quick start guide
- **README_PI.md**: Detailed Raspberry Pi deployment instructions
- **project_background.md**: Project vision and objectives
- **CONTRIBUTING.md**: Development guidelines and contribution process
- **CHANGELOG.md**: Version history and change tracking

### Deployment
- **Automated Setup**: `setup_pi.sh` script for Raspberry Pi installation
- **Requirements Files**: Separate dependency lists for PC and Pi
- **Systemd Service**: Auto-start configuration for production deployment
- **GPIO Permissions**: Proper setup for hardware access

## [0.9.0] - 2024-01-XX

### Added
- Initial prototype with basic voice-to-voice functionality
- Character system with 5 historical/fictional personalities
- Text mode for development and testing
- Basic error handling and audio validation

### Changed
- Improved Elon Musk system prompt for more authentic responses
- Enhanced audio device detection and validation
- Better error messages and user feedback

### Fixed
- Audio device validation attribute names (`max_input_channels` vs `max_inputs`)
- EENABLE_BARGEIN typo in configuration
- API error handling for all external services

---

## Version History

- **1.0.0**: Production-ready release with full hardware integration
- **0.9.0**: Initial prototype with core functionality

## Release Notes

### Version 1.0.0
This is the first production-ready release of the Time Travel Hotline project. It includes full hardware integration for Raspberry Pi deployment, comprehensive documentation, and robust error handling.

**Key Features:**
- Complete hardware integration (rotary dial, hook switch, proximity sensor, bell control)
- Cross-platform support (Windows PC and Raspberry Pi)
- Production-ready deployment with systemd service
- Comprehensive documentation and setup guides

**Breaking Changes:**
- None (first release)

**Migration Guide:**
- N/A (first release)

### Version 0.9.0
Initial prototype release with core voice-to-voice AI functionality.

**Key Features:**
- Basic voice-to-voice conversations
- Character system with 5 personalities
- Text mode for development
- Audio device validation

**Known Issues:**
- Limited hardware integration
- Basic error handling
- Minimal documentation
