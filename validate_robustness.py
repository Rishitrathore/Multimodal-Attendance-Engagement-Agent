"""Offline edge-case checks for lighting/occlusion-like detection gaps,
short appearances, noisy/intermittent audio, and missing modality data.

These are deterministic synthetic tests; they do not replace testing with a
real camera, microphone, room, or classroom recording.
Run: python validate_robustness.py
"""
import csv
import json
import math
import tempfile
from pathlib import Path

import numpy as np
from audio import AudioActivityMonitor
from multimodal_agent import build_multimodal_report
from vision import FaceTracker


def write_csv(path, rows, fields):
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    # Face tracker: small frame-to-frame shifts and brief occlusion should keep
    # the temporary ID; long gaps may legitimately create a new ID.
    tracker = FaceTracker(max_distance=90, max_missing=2)
    first = tracker.update([(10, 10, 60, 60)])
    pid = first[0][0]
    assert tracker.update([(15, 12, 60, 60)])[0][0] == pid
    assert tracker.update([]) == []
    assert tracker.update([(18, 13, 60, 60)])[0][0] == pid
    assert tracker.update([(0, 0, 0, 0)]) == []  # malformed detection ignored
    assert tracker.update([(500, 500, 60, 60)])[0][0] != pid

    # Audio feature extraction: silence, loud noise, and intermittent samples
    # should produce finite metrics; invalid samples are sanitized.
    silence = AudioActivityMonitor._features(np.zeros(1600, dtype=np.float32))
    noisy = AudioActivityMonitor._features(np.random.default_rng(7).normal(0, .2, 1600))
    interrupted = AudioActivityMonitor._features(np.array([0.0, np.nan, np.inf, -np.inf]))
    assert all(math.isfinite(v) for v in silence + noisy + interrupted)
    assert silence[0] == 0.0
    try:
        AudioActivityMonitor(threshold=0)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid audio threshold should be rejected")

    # Fusion: one short visual appearance, a partial-occlusion gap, a noisy
    # interval, and an audio dropout. The union of modalities must preserve
    # windows and produce bounded, interpretable scores.
    with tempfile.TemporaryDirectory(prefix="multimodal_robustness_") as temp:
        root = Path(temp)
        visual = [
            {"session_offset_seconds": 0.05, "participant_id": "brief", "x": 1, "y": 1, "width": 40, "height": 40},
            {"session_offset_seconds": 2.00, "participant_id": "steady", "x": 10, "y": 10, "width": 50, "height": 50},
            {"session_offset_seconds": 2.04, "participant_id": "steady", "x": 12, "y": 10, "width": 50, "height": 50},
            # Next visual sample after an occlusion/lighting-like gap.
            {"session_offset_seconds": 4.02, "participant_id": "steady", "x": 14, "y": 10, "width": 50, "height": 50},
        ]
        audio = [
            {"start_offset_seconds": 0, "duration_seconds": 1, "audio_class": "Silence", "rms_amplitude": 0},
            {"start_offset_seconds": 1, "duration_seconds": 1, "audio_class": "Background noise", "rms_amplitude": .2},
            # No audio row in window 2: simulate microphone dropout.
            {"start_offset_seconds": 3, "duration_seconds": 1, "audio_class": "Probable speech", "rms_amplitude": .04},
            {"start_offset_seconds": 4, "duration_seconds": .4, "audio_class": "Background noise", "rms_amplitude": .1},
        ]
        vfile, afile = root / "vision.csv", root / "audio.csv"
        write_csv(vfile, visual, ["session_offset_seconds", "participant_id", "x", "y", "width", "height"])
        write_csv(afile, audio, ["start_offset_seconds", "duration_seconds", "audio_class", "rms_amplitude"])
        report = build_multimodal_report(str(vfile), str(afile), str(root / "out.csv"), str(root / "summary.json"), window_seconds=1)
        rows = list(csv.DictReader((root / "out.csv").open(encoding="utf-8")))
        assert report["time_windows_analyzed"] == 5
        assert len(rows) == 5
        assert rows[0]["participant_ids"] == "brief"  # brief appearance retained
        assert rows[2]["audio_class"] == "Unknown"  # audio dropout represented honestly
        assert all(0 <= float(row["engagement_score"]) <= 100 for row in rows)
        assert json.loads((root / "summary.json").read_text(encoding="utf-8"))["time_windows_analyzed"] == 5

    print("PASS: tracker tolerates brief occlusion and rejects malformed boxes.")
    print("PASS: audio features remain finite with silence, noise, and invalid samples.")
    print("PASS: short appearances and visual gaps remain represented in fusion.")
    print("PASS: missing audio is labeled Unknown; scores stay within 0-100.")
    print("NOTE: real lighting, physical occlusion, room noise, and device dropouts require on-site testing.")


if __name__ == "__main__":
    main()
