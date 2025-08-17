# hotline_demo_windows.py
import os, queue, time, threading
import sounddevice as sd
import webrtcvad
import argparse
from io import BytesIO
import wave
from deepgram import DeepgramClient, PrerecordedOptions
from elevenlabs import ElevenLabs
from openai import OpenAI
from pydub import AudioSegment
from simpleaudio import play_buffer
import numpy as np

MIN_RMS = 500  # adjust threshold up/down to tune sensitivity

def is_loud_enough(chunk):
    samples = np.frombuffer(chunk, dtype=np.int16)
    rms = np.sqrt(np.mean(samples.astype(np.float32)**2))
    return rms > MIN_RMS


# ---------- CONFIG ----------
# voice_pref accepts a voice NAME or a voice ID; using IDs for precision here.
CHARACTERS = {
    "3": {"name": "Albert Einstein", "voice_pref": "JBFqnCBsd6RMkjVDRZzb"},  # George
    "2": {"name": "Elvis Presley",   "voice_pref": "NFG5qt843uXKj4pFvR7C"},   # Adam Stone - late night radio
    "5": {"name": "Cleopatra",       "voice_pref": "XB0fDUnXU5powFXDhCwa"},   # Charlotte
    "7": {"name": "Beth Dutton",     "voice_pref": "cgSgspJ2msm6clMCkdW9"},   # Jessica
    "9": {"name": "Elon Musk",       "voice_pref": "CwhRBWXzGAHq8TQ4Fs17"},   # Roger
}
SYSTEM_PROMPTS = {
    "Albert Einstein": "You are Albert Einstein in 1946: warm, witty, plain-spoken. Explain ideas with simple analogies. Keep replies in 2–5 sentences. Stay in character.",
    "Elvis Presley":   "You are Elvis Presley, charming and playful. Light Southern cadence. Keep replies 2–4 sentences. Avoid modern slang.",
    "Cleopatra":       "You are Cleopatra VII Philopator. Regal, strategic, poetic. Reference Alexandria, the Nile, diplomacy. Keep replies 2–5 sentences.",
    "Beth Dutton":     "You are Beth Dutton. Fierce, sharp, sardonic. Keep replies short, cutting, with wit. PG-13.",
    "Elon Musk":       "You are Elon Musk: concise, engineering-minded, first-principles. 2–4 sentence replies."
}

# Audio / VAD
SAMPLE_RATE = 16000
FRAME_MS = 20
CHANNELS = 1
VAD_SENSITIVITY = 3
MAX_UTTERANCE_SEC = 12
SILENCE_TAIL_MS = 700

# Barge-in controls
ENABLE_BARGEIN = True
BARGEIN_DEBOUNCE_FRAMES = 3   # require N consecutive "speech" frames before cutting TTS
TTS_PREROLL_MS = 120          # prevents first-phoneme cutoff

# ---------- CLIENTS ----------
dg = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

# Playback state (so we can stop it on barge-in)
current_playback = None
playback_lock = threading.Lock()

# ---------- AUDIO CAPTURE ----------
def record_until_silence():
    vad = webrtcvad.Vad(VAD_SENSITIVITY)
    buf, q = [], queue.Queue()
    def cb(indata, frames, time_info, status): q.put(bytes(indata))
    with sd.RawInputStream(samplerate=SAMPLE_RATE,
                           blocksize=int(SAMPLE_RATE * FRAME_MS / 1000),
                           channels=CHANNELS, dtype='int16', callback=cb):
        start = time.time()
        last_voice_ms = 0
        while True:
            chunk = q.get()
            buf.append(chunk)
            if len(chunk) == int(SAMPLE_RATE * FRAME_MS / 1000) * 2:
                if vad.is_speech(chunk, SAMPLE_RATE) and is_loud_enough(chunk):
                    last_voice_ms = (time.time() - start) * 1000
            elapsed_ms = (time.time() - start) * 1000
            if elapsed_ms > MAX_UTTERANCE_SEC * 1000: break
            if last_voice_ms > 0 and (elapsed_ms - last_voice_ms) > SILENCE_TAIL_MS: break
    return b"".join(buf)

# Helper: wrap raw PCM16 as WAV bytes (Deepgram works best with standard containers)
def pcm16_to_wav_bytes(pcm_bytes, sample_rate=16000, channels=1):
    bio = BytesIO()
    with wave.open(bio, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return bio.getvalue()

# ---------- ASR (Deepgram v4 REST) ----------
def asr_deepgram_pcm16(audio_bytes):
    wav_bytes = pcm16_to_wav_bytes(audio_bytes, SAMPLE_RATE, CHANNELS)
    source = {"buffer": wav_bytes, "mimetype": "audio/wav"}
    opts = PrerecordedOptions(model="nova-2", smart_format=True, punctuate=True, language="en-US")
    resp = dg.listen.rest.v("1").transcribe_file(source, opts)
    alt = resp.results.channels[0].alternatives[0]
    return alt.transcript.strip() if alt.transcript else ""

# ---------- LLM ----------
def llm_character_reply(character_name, user_text):
    system = SYSTEM_PROMPTS[character_name]
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        messages=[{"role":"system","content":system},
                  {"role":"user","content":user_text}],
    )
    return resp.choices[0].message.content.strip()

# ---------- TTS with barge-in ----------
def speak_tts_with_barge_in(voice_id_or_name: str, text: str):
    """Play TTS with pre-roll; if barge-in enabled, stop as soon as user starts speaking."""
    global current_playback

    # Generate audio
    stream = eleven.text_to_speech.convert(
        voice_id_or_name,
        model_id="eleven_multilingual_v2",
        text=text,
    )
    audio_bytes = b"".join(stream)
    seg = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")

    # Prepend a short silence to avoid cutting off first phoneme
    if TTS_PREROLL_MS > 0:
        seg = AudioSegment.silent(duration=TTS_PREROLL_MS) + seg

    # Start playback in a background thread
    def _play(segment: AudioSegment):
        global current_playback
        with playback_lock:
            current_playback = play_buffer(segment.raw_data, segment.channels, segment.sample_width, segment.frame_rate)
    t = threading.Thread(target=_play, args=(seg,), daemon=True)
    t.start()

    if not ENABLE_BARGEIN:
        t.join()
        # Wait for playback to finish
        while True:
            with playback_lock:
                po = current_playback
            if po is None or not po.is_playing():
                break
            time.sleep(0.05)
        return

    # While playback is active, watch mic for speech; stop playback when detected
    vad = webrtcvad.Vad(VAD_SENSITIVITY)
    q = queue.Queue()

    def mic_cb(indata, frames, time_info, status):
        # Push raw 16-bit bytes
        q.put(bytes(indata))

    debounce = 0
    with sd.RawInputStream(samplerate=SAMPLE_RATE,
                           blocksize=int(SAMPLE_RATE * FRAME_MS / 1000),
                           channels=CHANNELS, dtype='int16', callback=mic_cb):
        while True:
            # Check if playback already ended
            with playback_lock:
                po = current_playback
            if po is None or not po.is_playing():
                break

            try:
                chunk = q.get(timeout=0.05)
            except queue.Empty:
                continue

            if len(chunk) == int(SAMPLE_RATE * FRAME_MS / 1000) * 2 and vad.is_speech(chunk, SAMPLE_RATE):
                debounce += 1
                if debounce >= BARGEIN_DEBOUNCE_FRAMES:
                    print("⛔ Barge-in detected: stopping playback")
                    with playback_lock:
                        if current_playback and current_playback.is_playing():
                            current_playback.stop()
                            current_playback = None
                    break
            else:
                debounce = 0

    # Ensure playback thread exits
    t.join(timeout=0.1)

# ---------- UI ----------
def pick_character():
    print("\nCharacters:")
    for k,v in CHARACTERS.items():
        print(f"  {k}: {v['name']}")
    while True:
        sel = input("Dial a character (e.g., 3 for Einstein): ").strip()
        if sel in CHARACTERS: return CHARACTERS[sel]
        print("Not in service. Try again.")

def main_loop():
    print("\nTime Travel Hotline (PC Prototype)")
    input("Press Enter to start a session; Ctrl+C to quit...")

    persona = pick_character()
    name = persona["name"]
    voice_pref = persona["voice_pref"]

    speak_tts_with_barge_in(voice_pref, f"Hello. You are speaking with {name}. Ask your question.")

    while True:
        print("🎤 Listening...")
        pcm = record_until_silence()
        if len(pcm) < 16000:
            continue

        print("📝 Transcribing...")
        user_text = asr_deepgram_pcm16(pcm)
        print(f"YOU: {user_text}")
        if not user_text:
            continue

        if user_text.lower() in {"goodbye","hang up","bye","end call"}:
            speak_tts_with_barge_in(voice_pref, "Goodbye.")
            print("Call ended.")
            break

        print("🤖 Thinking...")
        reply = llm_character_reply(name, user_text)
        print(f"{name.upper()}: {reply}")

        print("🔊 Speaking...")
        speak_tts_with_barge_in(voice_pref, reply)

if __name__ == "__main__":
    missing = [k for k in ("ELEVEN_API_KEY","DEEPGRAM_API_KEY","OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"Set these env vars before running: {', '.join(missing)}")
    else:
        # If you need a specific mic, uncomment to list/set:
        # import pprint; pprint.pp(sd.query_devices()); sd.default.device = (INPUT_INDEX, None)
        main_loop()
