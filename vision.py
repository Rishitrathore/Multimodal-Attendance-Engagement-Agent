"""Face detection and short-term tracking for the classroom demo.

IDs are temporary tracking labels for one video session; they do not identify
real people and are not retained between sessions.
"""
import cv2
from math import hypot


def open_camera(source=0):
    camera = cv2.VideoCapture(source)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")
    return camera


def create_detector():
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        raise RuntimeError("Could not load OpenCV Haar Cascade.")
    return detector


def detect_faces(frame, detector):
    """Return face boxes as (x, y, width, height)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
    )
    return [tuple(map(int, box)) for box in faces]


class FaceTracker:
    """Associate face boxes between frames using their centre positions."""
    def __init__(self, max_distance=90, max_missing=8):
        self.max_distance = max_distance
        self.max_missing = max_missing
        self.next_id = 1
        self.tracks = {}  # id -> {center, box, missing}

    def update(self, boxes):
        # Ignore malformed detections (zero/negative dimensions) so transient
        # detector glitches cannot create unstable participant tracks.
        valid_boxes = []
        for box in boxes:
            if len(box) != 4:
                continue
            x, y, w, h = map(int, box)
            if w > 0 and h > 0:
                valid_boxes.append((x, y, w, h))
        boxes = valid_boxes
        current_centers = [
            (x + w // 2, y + h // 2) for x, y, w, h in boxes
        ]
        assigned = {}
        used_ids = set()

        # Match each new face to the nearest unmatched existing track.
        candidates = []
        for track_id, track in self.tracks.items():
            for index, center in enumerate(current_centers):
                distance = hypot(center[0] - track["center"][0],
                                 center[1] - track["center"][1])
                if distance <= self.max_distance:
                    candidates.append((distance, track_id, index))
        for _, track_id, index in sorted(candidates):
            if track_id not in used_ids and index not in assigned:
                assigned[index] = track_id
                used_ids.add(track_id)

        # Give new faces a new temporary ID.
        for index in range(len(boxes)):
            if index not in assigned:
                assigned[index] = self.next_id
                self.next_id += 1

        seen_ids = set()
        results = []
        for index, box in enumerate(boxes):
            track_id = assigned[index]
            x, y, w, h = box
            center = current_centers[index]
            self.tracks[track_id] = {
                "center": center, "box": box, "missing": 0
            }
            seen_ids.add(track_id)
            results.append((track_id, box))

        for track_id in list(self.tracks):
            if track_id not in seen_ids:
                self.tracks[track_id]["missing"] += 1
                if self.tracks[track_id]["missing"] > self.max_missing:
                    del self.tracks[track_id]
        return results


def draw_tracked_faces(frame, tracked_faces):
    for track_id, (x, y, w, h) in tracked_faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, f"Participant {track_id}", (x, max(y - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return frame
