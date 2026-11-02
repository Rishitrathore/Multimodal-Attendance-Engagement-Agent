# Audio Capture and Preprocessing

The project captures audio from the computer microphone during a webcam session. For a prerecorded classroom video, it extracts the audio track using FFmpeg.

- Converts audio to **mono, 16 kHz** for consistent processing.
- Splits audio into **1-second windows** (the final window may be shorter).
- Calculates RMS amplitude for each window and stores a timestamp and session offset.
- Writes the results to `audio_segments.csv`.

The current activity indicator is based on sound level only. It is not speech recognition and does not identify who is speaking. Install FFmpeg and make sure it is available on PATH to process audio from prerecorded videos.

Run the project as usual:

```bash
pip install -r requirements.txt
python main.py                 # webcam + microphone
python main.py --video class.mp4  # video + extracted audio (requires FFmpeg)
```
