from elevenlabs import ElevenLabs
import os
from pydub import AudioSegment
from io import BytesIO
from simpleaudio import play_buffer

eleven = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
audio = eleven.text_to_speech.convert(
    "Rachel", model_id="eleven_multilingual_v2", text="Testing, one, two, three."
)
audio_bytes = b"".join(audio)
seg = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
play_obj = play_buffer(seg.raw_data, seg.channels, seg.sample_width, seg.frame_rate)
play_obj.wait_done()
