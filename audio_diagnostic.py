#!/usr/bin/env python3
"""
Audio Diagnostic Tool - Analyze RTP audio quality issues
"""
import socket
import time
import struct
import numpy as np
from pydub import AudioSegment
import io

# SIP Configuration
SIP_TARGET_IP = "192.168.1.179"  # HT801 IP
SIP_SERVER_IP = "192.168.1.254"  # SIP proxy IP
LOCAL_RTP_PORT = 6000
SAMPLE_RATE = 8000

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def analyze_mulaw_conversion():
    """Test mu-law encoding/decoding with known audio"""
    print("🔬 Testing mu-law encoding/decoding...")
    
    # Generate test tone (440Hz A note)
    duration = 1.0  # 1 second
    samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, samples, False)
    test_audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # 440Hz sine wave
    
    print(f"📊 Original audio: min={test_audio.min():.3f}, max={test_audio.max():.3f}")
    
    # Convert to mu-law
    mulaw_bytes = linear_to_mulaw(test_audio)
    print(f"📊 Mu-law bytes: {len(mulaw_bytes)} bytes, sample: {mulaw_bytes[:10]}")
    
    # Convert back to linear
    decoded_audio = mulaw_to_linear(mulaw_bytes)
    print(f"📊 Decoded audio: min={decoded_audio.min():.3f}, max={decoded_audio.max():.3f}")
    
    # Calculate quality metrics
    mse = np.mean((test_audio - decoded_audio) ** 2)
    print(f"📊 Mean Squared Error: {mse:.6f}")
    
    # Save for comparison
    try:
        original_segment = AudioSegment(
            (test_audio * 32767).astype(np.int16).tobytes(),
            frame_rate=SAMPLE_RATE,
            sample_width=2,
            channels=1
        )
        original_segment.export("test_original.wav", format="wav")
        
        decoded_segment = AudioSegment(
            (decoded_audio * 32767).astype(np.int16).tobytes(),
            frame_rate=SAMPLE_RATE,
            sample_width=2,
            channels=1
        )
        decoded_segment.export("test_decoded.wav", format="wav")
        print("💾 Saved test_original.wav and test_decoded.wav for comparison")
    except Exception as e:
        print(f"⚠️ Could not save audio files: {e}")

def linear_to_mulaw(audio_data):
    """Convert linear PCM to mu-law (G.711) - improved version"""
    # Ensure audio is properly normalized and scaled
    audio_data = np.clip(audio_data, -1.0, 1.0)
    
    # Convert to 16-bit PCM first
    audio_16bit = (audio_data * 32767).astype(np.int16)
    
    # Standard mu-law encoding
    mulaw_bytes = []
    
    for sample in audio_16bit:
        # Get sign and magnitude
        sign = 0x80 if sample < 0 else 0x00
        magnitude = abs(sample)
        
        # Clip to prevent overflow
        magnitude = min(magnitude, 32767)
        
        # Add bias (33 is standard for mu-law)
        magnitude += 33
        
        # Find the segment (exponent) - 8 segments
        segment = 0
        temp = magnitude
        for i in range(8):
            if temp <= 0x1F:  # 5 bits
                segment = i
                break
            temp >>= 1
        
        # Get the quantization value (mantissa)
        if segment == 0:
            quantized = (magnitude >> 1) & 0x0F
        else:
            quantized = ((magnitude >> segment) & 0x0F) + 0x10
        
        # Combine sign, segment, and quantized value
        mulaw_value = sign | (segment << 4) | quantized
        
        # Invert bits for proper mu-law format (important!)
        mulaw_bytes.append(mulaw_value ^ 0xFF)
    
    return bytes(mulaw_bytes)

def mulaw_to_linear(mulaw_bytes):
    """Convert mu-law to linear PCM - improved version"""
    linear_samples = []
    
    for mulaw_byte in mulaw_bytes:
        # Invert bits (reverse the encoding inversion)
        mulaw_value = mulaw_byte ^ 0xFF
        
        # Extract components
        sign = mulaw_value & 0x80
        segment = (mulaw_value >> 4) & 0x07
        quantized = mulaw_value & 0x0F
        
        # Reconstruct the magnitude
        if segment == 0:
            magnitude = (quantized << 1) + 33
        else:
            magnitude = ((quantized + 0x10) << segment) + 33
        
        # Remove bias
        magnitude -= 33
        
        # Apply sign
        if sign:
            sample = -magnitude
        else:
            sample = magnitude
        
        # Normalize to [-1, 1] range
        linear_samples.append(sample / 32768.0)
    
    return np.array(linear_samples, dtype=np.float32)

def capture_and_analyze_rtp(duration=5):
    """Capture RTP packets and analyze audio content"""
    print(f"🎧 Capturing RTP audio for {duration} seconds...")
    print("📞 Make sure call is active and speak into handset!")
    
    # Setup RTP socket
    rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rtp_socket.bind((get_local_ip(), LOCAL_RTP_PORT))
    rtp_socket.settimeout(0.1)
    
    audio_packets = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            try:
                data, addr = rtp_socket.recvfrom(1024)
                
                if len(data) > 12:  # RTP header is 12 bytes
                    # Parse RTP header
                    rtp_header = struct.unpack('!BBHII', data[:12])
                    version = (rtp_header[0] >> 6) & 0x3
                    padding = (rtp_header[0] >> 5) & 0x1
                    extension = (rtp_header[0] >> 4) & 0x1
                    cc = rtp_header[0] & 0xF
                    marker = (rtp_header[1] >> 7) & 0x1
                    payload_type = rtp_header[1] & 0x7F
                    sequence = rtp_header[2]
                    timestamp = rtp_header[3]
                    ssrc = rtp_header[4]
                    
                    audio_payload = data[12:]
                    audio_packets.append({
                        'payload': audio_payload,
                        'payload_type': payload_type,
                        'sequence': sequence,
                        'timestamp': timestamp,
                        'size': len(audio_payload)
                    })
                    
            except socket.timeout:
                continue
                
    except KeyboardInterrupt:
        print("\n🛑 Capture interrupted")
    finally:
        rtp_socket.close()
    
    print(f"📊 Captured {len(audio_packets)} RTP packets")
    
    if audio_packets:
        # Analyze packet structure
        payload_types = set(p['payload_type'] for p in audio_packets)
        packet_sizes = [p['size'] for p in audio_packets]
        
        print(f"📊 Payload types found: {payload_types}")
        print(f"📊 Packet sizes: min={min(packet_sizes)}, max={max(packet_sizes)}, avg={np.mean(packet_sizes):.1f}")
        
        # Analyze first few packets
        print("📊 First 5 packets:")
        for i, packet in enumerate(audio_packets[:5]):
            payload = packet['payload']
            print(f"  Packet {i}: PT={packet['payload_type']}, size={len(payload)}, data={payload[:8].hex()}")
        
        # Try to decode and analyze audio
        all_audio_data = []
        for packet in audio_packets:
            try:
                linear_audio = mulaw_to_linear(packet['payload'])
                all_audio_data.extend(linear_audio)
            except Exception as e:
                print(f"⚠️ Error decoding packet: {e}")
        
        if all_audio_data:
            audio_array = np.array(all_audio_data)
            print(f"📊 Decoded audio: {len(audio_array)} samples")
            print(f"📊 Audio range: min={audio_array.min():.3f}, max={audio_array.max():.3f}")
            print(f"📊 Audio RMS: {np.sqrt(np.mean(audio_array**2)):.3f}")
            
            # Check for silence vs signal
            rms_threshold = 0.01
            signal_samples = np.sum(np.abs(audio_array) > rms_threshold)
            print(f"📊 Signal samples: {signal_samples}/{len(audio_array)} ({100*signal_samples/len(audio_array):.1f}%)")
            
            # Save captured audio
            try:
                audio_segment = AudioSegment(
                    (audio_array * 32767).astype(np.int16).tobytes(),
                    frame_rate=SAMPLE_RATE,
                    sample_width=2,
                    channels=1
                )
                audio_segment.export("captured_audio.wav", format="wav")
                print("💾 Saved captured_audio.wav")
            except Exception as e:
                print(f"⚠️ Could not save captured audio: {e}")
    else:
        print("❌ No RTP packets received - check if call is active!")

def main():
    print("🔬 Audio Diagnostic Tool")
    print("=" * 50)
    
    print("\n1️⃣ Testing mu-law codec...")
    analyze_mulaw_conversion()
    
    print("\n2️⃣ Ready to capture live RTP audio...")
    input("Press Enter when call is active and you're ready to speak...")
    capture_and_analyze_rtp(10)  # 10 seconds of capture
    
    print("\n✅ Diagnostic complete!")
    print("Check the generated .wav files to compare audio quality")

if __name__ == "__main__":
    main()
