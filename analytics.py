import csv
from datetime import datetime
from pathlib import Path

CSV_FILE = Path("attendance.csv")
HEADERS = [
    "date", "start_time", "end_time", "duration_seconds",
    "face_presence_percent", "audio_activity_percent",
    "average_activity_score", "suggestion"
]

def save_session(start_time, end_time, duration, face_seconds,
                 audio_seconds, score_total, samples):
    face_pct = (face_seconds / duration * 100) if duration else 0
    audio_pct = (audio_seconds / duration * 100) if duration else 0
    avg_score = (score_total / samples) if samples else 0

    if face_pct < 50:
        suggestion = "Check camera placement and encourage visible participation."
    elif audio_pct < 20:
        suggestion = "Consider adding a short discussion or question-and-answer activity."
    else:
        suggestion = "Activity signals were detected; continue with the current session format."

    row = [
        datetime.now().strftime("%Y-%m-%d"),
        start_time.strftime("%H:%M:%S"),
        end_time.strftime("%H:%M:%S"),
        round(duration, 1),
        round(face_pct, 1),
        round(audio_pct, 1),
        round(avg_score, 1),
        suggestion
    ]

    file_exists = CSV_FILE.exists()
    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADERS)
        writer.writerow(row)

    return dict(zip(HEADERS, row))
