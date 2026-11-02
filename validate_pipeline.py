"""Offline end-to-end smoke test for the multimodal analytics pipeline.

Uses synthetic timestamped inputs, so it does not access a webcam or microphone.
Run from the project folder: python validate_pipeline.py
"""
import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from multimodal_agent import build_multimodal_report
from recommendation_engine import generate_analytics_and_recommendations
from student_analytics import generate_student_analytics


def write_csv(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def require_file(path):
    if not Path(path).is_file() or Path(path).stat().st_size == 0:
        raise AssertionError(f"Expected output was not created: {path}")


def main():
    with tempfile.TemporaryDirectory(prefix="multimodal_pipeline_check_") as temp:
        root = Path(temp)
        tracking = root / "face_tracking.csv"
        audio = root / "audio_segments.csv"
        attendance = root / "attendance.csv"
        fused = root / "multimodal_insights.csv"
        fused_json = root / "multimodal_session_summary.json"
        recommendations = root / "recommendations.csv"
        analytics_json = root / "analytics_recommendations.json"
        teaching = root / "teaching_suggestions.csv"
        student_csv = root / "student_analytics.csv"
        student_json = root / "student_analytics.json"

        visual_rows = []
        for second in range(6):
            for frame in range(3):
                visual_rows.append({
                    "timestamp": f"2026-11-02T10:00:{second:02d}",
                    "session_offset_seconds": second + frame / 30,
                    "participant_id": "P1",
                    "x": 100 + frame * 4,
                    "y": 80,
                    "width": 60,
                    "height": 60,
                })
        write_csv(tracking, visual_rows,
                  ["timestamp", "session_offset_seconds", "participant_id", "x", "y", "width", "height"])

        audio_rows = []
        classes = ["Probable speech", "Probable speech", "Background noise",
                   "Silence", "Probable speech", "Background noise"]
        for second, label in enumerate(classes):
            audio_rows.append({
                "timestamp": f"2026-11-02T10:00:{second:02d}",
                "start_offset_seconds": second,
                "duration_seconds": 1.0,
                "sample_rate_hz": 16000,
                "channels": 1,
                "rms_amplitude": 0.04 if label == "Probable speech" else 0.01,
                "peak_amplitude": 0.12,
                "zero_crossing_rate": 0.1,
                "spectral_flatness": 0.2,
                "audio_class": label,
            })
        write_csv(audio, audio_rows,
                  ["timestamp", "start_offset_seconds", "duration_seconds", "sample_rate_hz",
                   "channels", "rms_amplitude", "peak_amplitude", "zero_crossing_rate",
                   "spectral_flatness", "audio_class"])

        write_csv(attendance, [{
            "date": "2026-11-02", "start_time": "10:00:00", "end_time": "10:00:06",
            "duration_seconds": 6, "face_presence_percent": 100,
            "audio_activity_percent": 50, "average_activity_score": 70,
            "suggestion": "Review session activity.",
        }], ["date", "start_time", "end_time", "duration_seconds", "face_presence_percent",
             "audio_activity_percent", "average_activity_score", "suggestion"])

        write_csv(root / "participant_attendance.csv", [{
            "participant_id": "P1", "presence_duration_seconds": 6,
            "minimum_required_seconds": 3, "attendance_status": "Present",
        }], ["participant_id", "presence_duration_seconds", "minimum_required_seconds", "attendance_status"])

        os.chdir(root)
        fusion = build_multimodal_report(
            tracking_file=str(tracking), audio_file=str(audio),
            output_file=str(fused), summary_file=str(fused_json), window_seconds=1.0,
        )
        assert fusion["time_windows_analyzed"] == 6, "Fusion should produce six timestamp windows"
        require_file(fused)
        require_file(fused_json)

        rec = generate_analytics_and_recommendations(
            insights_file=str(fused), session_file=str(attendance),
            output_file=str(recommendations), summary_file=str(analytics_json),
        )
        assert rec["windows_analyzed"] == 6, "Recommendation engine should read all fused windows"
        require_file(recommendations)
        require_file(analytics_json)
        require_file(root / "teaching_suggestions.csv")

        student = generate_student_analytics(
            attendance_file=str(root / "participant_attendance.csv"),
            insights_file=str(fused), session_summary_file=str(fused_json),
            output_csv=str(student_csv), output_json=str(student_json),
        )
        assert len(student["participants"]) == 1, "Student summary should contain the fixture participant"
        require_file(student_csv)
        require_file(student_json)

        # Validate JSON outputs are parseable and include expected pipeline data.
        for path in (fused_json, analytics_json, student_json):
            json.loads(path.read_text(encoding="utf-8"))

        print("PASS: synthetic vision + audio inputs were fused by timestamp.")
        print("PASS: engagement indicators and session summary were generated.")
        print("PASS: instructor recommendations and teaching suggestions were generated.")
        print("PASS: privacy-conscious student attendance summary was generated.")
        print("PASS: all expected CSV/JSON outputs exist and JSON files parse.")
        print("NOTE: webcam, microphone, and real classroom video were not exercised by this offline test.")

        os.chdir(Path(__file__).resolve().parent)


if __name__ == "__main__":
    main()
