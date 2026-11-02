"""Audio capture, preprocessing and lightweight classroom audio analysis.

Audio is normalized to mono 16 kHz, split into fixed windows, and described
using RMS energy, peak amplitude, zero-crossing rate and spectral flatness.
The labels are heuristic (not speech recognition) and should be treated as
indicative audio context rather than guaranteed speech transcription.
"""
import csv
import json
import subprocess
import tempfile
import threading
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
try:
    import sounddevice as sd
except ImportError:  # Offline analysis/tests can run without a microphone backend.
    sd = None


class AudioActivityMonitor:
    def __init__(self, threshold=0.02, sample_rate=16000, window_seconds=1.0,
                 output_file="audio_segments.csv"):
        if threshold <= 0:
            raise ValueError("threshold must be greater than zero")
        if sample_rate <= 0 or window_seconds <= 0:
            raise ValueError("sample_rate and window_seconds must be greater than zero")
        self.threshold = float(threshold)
        self.sample_rate = int(sample_rate)
        self.window_seconds = float(window_seconds)
        self.window_samples = max(1, int(self.sample_rate * self.window_seconds))
        self.output_file = Path(output_file)
        self.summary_file = Path("audio_session_summary.json")
        self.insights_file = Path("audio_insights.csv")
        self.stream = None
        self._buffer = np.empty(0, dtype=np.float32)
        self._lock = threading.Lock()
        self.active = False
        self.last_level = 0.0
        self.metrics = []
        self._write_header()

    def _write_header(self):
        with self.output_file.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "timestamp", "start_offset_seconds", "duration_seconds",
                "sample_rate_hz", "channels", "rms_amplitude", "peak_amplitude",
                "zero_crossing_rate", "spectral_flatness", "audio_class"
            ])

    @staticmethod
    def _features(samples):
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            return 0.0, 0.0, 0.0, 0.0
        # Device glitches can occasionally produce NaN/Inf samples. Replace
        # them before feature extraction to keep metrics and JSON finite.
        samples = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
        rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
        peak = float(np.max(np.abs(samples)))
        signs = np.signbit(samples)
        zcr = float(np.mean(signs[1:] != signs[:-1])) if samples.size > 1 else 0.0
        spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
        power = spectrum[1:] ** 2
        if power.size == 0 or np.sum(power) <= 1e-12:
            flatness = 0.0
        else:
            flatness = float(np.exp(np.mean(np.log(power + 1e-12))) /
                             (np.mean(power) + 1e-12))
        return rms, peak, zcr, flatness

    def _save_window(self, samples, offset_seconds):
        if len(samples) == 0:
            return
        rms, peak, zcr, flatness = self._features(samples)
        # Simple, explainable heuristic: low energy = silence; sustained energy
        # with speech-like crossings/tonality = probable speech; otherwise noise.
        if rms < self.threshold * 0.35:
            label = "Silence"
        elif rms >= self.threshold and (zcr < 0.30 or flatness < 0.45):
            label = "Probable speech"
        else:
            label = "Background noise"
        timestamp = datetime.now().isoformat(timespec="milliseconds")
        duration = len(samples) / self.sample_rate
        row = {
            "timestamp": timestamp,
            "start_offset_seconds": round(offset_seconds, 3),
            "duration_seconds": round(duration, 3),
            "sample_rate_hz": self.sample_rate,
            "channels": 1,
            "rms_amplitude": round(rms, 6),
            "peak_amplitude": round(peak, 6),
            "zero_crossing_rate": round(zcr, 6),
            "spectral_flatness": round(flatness, 6),
            "audio_class": label,
        }
        self.metrics.append(row)
        with self.output_file.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writerow(row)
        self.last_level = rms
        self.active = label == "Probable speech"

    def _consume(self, samples):
        with self._lock:
            self._buffer = np.concatenate((self._buffer, samples.astype(np.float32, copy=False)))
            while len(self._buffer) >= self.window_samples:
                segment = self._buffer[:self.window_samples].copy()
                self._buffer = self._buffer[self.window_samples:]
                offset = getattr(self, "_sample_offset", 0) / self.sample_rate
                self._sample_offset = getattr(self, "_sample_offset", 0) + len(segment)
                self._save_window(segment, offset)

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        mono = np.mean(indata, axis=1) if indata.ndim == 2 else indata
        self._consume(mono)

    def start(self):
        if sd is None:
            raise RuntimeError("Live microphone capture requires the 'sounddevice' package. Install requirements.txt.")
        self._sample_offset = 0
        self._buffer = np.empty(0, dtype=np.float32)
        self.stream = sd.InputStream(channels=1, samplerate=self.sample_rate,
                                     blocksize=0, dtype="float32", callback=self._callback)
        self.stream.start()
        print(f"Microphone capture started ({self.sample_rate} Hz mono, {self.window_seconds}s windows).")

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        with self._lock:
            if len(self._buffer):
                offset = getattr(self, "_sample_offset", 0) / self.sample_rate
                self._save_window(self._buffer.copy(), offset)
                self._sample_offset = getattr(self, "_sample_offset", 0) + len(self._buffer)
                self._buffer = np.empty(0, dtype=np.float32)
        self._write_session_insights()

    def process_video_audio(self, video_path):
        """Extract normalized mono 16 kHz audio from a video using FFmpeg."""
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = Path(temp_dir) / "normalized_audio.wav"
            command = ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1",
                       "-ar", str(self.sample_rate), "-f", "wav", str(wav_path)]
            try:
                subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except (FileNotFoundError, subprocess.CalledProcessError):
                print("Video audio was not processed: FFmpeg is unavailable or the video has no audio track.")
                return
            self._sample_offset = 0
            with wave.open(str(wav_path), "rb") as wav:
                if wav.getnchannels() != 1 or wav.getframerate() != self.sample_rate:
                    raise ValueError("Audio normalization failed; expected mono 16 kHz audio.")
                while True:
                    raw = wav.readframes(self.window_samples)
                    if not raw:
                        break
                    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
                    offset = self._sample_offset / self.sample_rate
                    self._save_window(samples, offset)
                    self._sample_offset += len(samples)
        self._write_session_insights()
        print(f"Audio features and activity analyzed for {video_path}.")

    def _write_session_insights(self):
        totals = {"Silence": 0.0, "Background noise": 0.0, "Probable speech": 0.0}
        for item in self.metrics:
            totals[item["audio_class"]] += item["duration_seconds"]
        count = len(self.metrics)
        mean_rms = float(np.mean([m["rms_amplitude"] for m in self.metrics])) if count else 0.0
        summary = {
            "segments_analyzed": count,
            "total_audio_duration_seconds": round(sum(totals.values()), 3),
            "silence_duration_seconds": round(totals["Silence"], 3),
            "background_noise_duration_seconds": round(totals["Background noise"], 3),
            "probable_speech_duration_seconds": round(totals["Probable speech"], 3),
            "mean_rms_amplitude": round(mean_rms, 6),
            "probable_speech_segment_ratio": round(
                sum(1 for m in self.metrics if m["audio_class"] == "Probable speech") / count, 4
            ) if count else 0.0,
            "classification_note": "Heuristic audio classification; not speech recognition or a verified transcript."
        }
        self.summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        with self.insights_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            for key, value in summary.items():
                writer.writerow([key, value])
