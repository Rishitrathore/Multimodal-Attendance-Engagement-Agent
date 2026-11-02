import argparse
import csv
import time
from datetime import datetime
from pathlib import Path

import cv2

from vision import create_detector, detect_faces, draw_tracked_faces, FaceTracker, open_camera
from audio import AudioActivityMonitor
from engagement import calculate_activity_score, describe_activity
from analytics import save_session
from multimodal_agent import build_multimodal_report
from recommendation_engine import generate_analytics_and_recommendations
from student_analytics import generate_student_analytics


def main():
    parser = argparse.ArgumentParser(description="Multimodal Attendance & Activity Demo")
    parser.add_argument("--video", help="Optional classroom video file. Leave empty to use webcam.")
    parser.add_argument("--min-presence-seconds", type=float, default=30.0,
                        help="Cumulative visible time required to mark a participant present (default: 30).")
    args = parser.parse_args()
    source = args.video if args.video else 0

    print("Starting Multimodal Attendance & Activity Demo")
    print("Temporary face IDs track faces within this session; they do not identify people.")
    print("Press Q in the video window to end the session.")

    detector = create_detector()
    camera = open_camera(source)
    tracker = FaceTracker()
    audio = AudioActivityMonitor(threshold=0.02)
    tracking_file = Path("face_tracking.csv")
    tracking_records = []
    participant_presence = {}  # participant ID -> cumulative visible seconds

    start = datetime.now()
    face_seconds = 0.0
    audio_seconds = 0.0
    score_total = 0
    samples = 0
    previous_tick = time.monotonic()
    session_tick_start = previous_tick

    try:
        # Capture microphone audio live; prerecorded video audio is extracted after the video ends.
        if not args.video:
            audio.start()
        while True:
            ok, frame = camera.read()
            if not ok:
                break

            frame_time = datetime.now().isoformat(timespec="seconds")
            boxes = detect_faces(frame, detector)
            tracked_faces = tracker.update(boxes)
            face_present = len(tracked_faces) > 0

            now_tick = time.monotonic()
            session_offset = round(now_tick - session_tick_start, 3)
            for track_id, (x, y, w, h) in tracked_faces:
                tracking_records.append([frame_time, session_offset, track_id, x, y, w, h])

            audio_active = audio.active if not args.video else False
            score = calculate_activity_score(face_present, audio_active)
            status = describe_activity(face_present, audio_active)

            elapsed = min(now_tick - previous_tick, 1.0)
            previous_tick = now_tick
            if face_present:
                face_seconds += elapsed
                # Add this frame interval to every participant visible in this frame.
                # Short gaps do not erase earlier presence, so appearances accumulate.
                for track_id, _ in tracked_faces:
                    participant_presence[track_id] = participant_presence.get(track_id, 0.0) + elapsed
            if audio_active:
                audio_seconds += elapsed
            score_total += score
            samples += 1

            frame = draw_tracked_faces(frame, tracked_faces)
            cv2.putText(frame, f"Activity score: {score}/100", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, status[:55], (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.imshow("Face Detection and Tracking - Press Q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except Exception as exc:
        print(f"Application error: {exc}")
    finally:
        end = datetime.now()
        audio.stop()
        if args.video:
            audio.process_video_audio(args.video)
        camera.release()
        cv2.destroyAllWindows()

        duration = max((end - start).total_seconds(), 0)
        result = save_session(start, end, duration, face_seconds, audio_seconds,
                              score_total, samples)
        with tracking_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "session_offset_seconds", "participant_id", "x", "y", "width", "height"])
            writer.writerows(tracking_records)

        print("\nSession summary")
        for key, value in result.items():
            print(f"{key}: {value}")
        print(f"Face tracking records saved to {tracking_file}")

        attendance_file = Path("participant_attendance.csv")
        with attendance_file.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["participant_id", "presence_duration_seconds", "minimum_required_seconds", "attendance_status"])
            for track_id, seconds in sorted(participant_presence.items()):
                status = "Present" if seconds >= args.min_presence_seconds else "Not Present"
                writer.writerow([track_id, round(seconds, 1), args.min_presence_seconds, status])
                print(f"Participant {track_id}: {seconds:.1f}s - {status}")

        print(f"Participant attendance saved to {attendance_file}")
        print("Audio segments saved to audio_segments.csv")
        multimodal_summary = build_multimodal_report()
        print("Multimodal insights saved to multimodal_insights.csv")
        print(f"Multimodal summary saved to multimodal_session_summary.json: {multimodal_summary}")
        analytics_summary = generate_analytics_and_recommendations()
        print("Analytics saved to analytics_recommendations.json")
        print("Recommendations saved to recommendations.csv")
        print("Instructor teaching suggestions saved to teaching_suggestions.csv")
        print(f"Generated {len(analytics_summary['recommendations'])} explainable recommendations")
        student_summary = generate_student_analytics()
        print("Student-facing analytics saved to student_analytics.csv and student_analytics.json")
        print(f"Generated private, non-evaluative summaries for {len(student_summary['participants'])} temporary participant IDs")
        print("Session summary saved to attendance.csv")


if __name__ == "__main__":
    main()
