"""Timestamp-based, extensible fusion of visual and audio classroom signals.

The fusion output is a contextual activity representation, not a measure or
proof of any learner's attention, identity, understanding, or learning.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

AUDIO_CLASSES = {"Silence", "Background noise", "Probable speech"}
DEFAULT_WINDOW_SECONDS = 1.0
MOVEMENT_THRESHOLD_PX = 3.0


def calculate_engagement_indicator(face_present, movements, audio_rows,
                                   window_seconds, inactivity):
    """Calculate an explainable 0-100 activity indicator for one time window.

    This is a classroom activity proxy, not a measurement of attention or learning.
    """
    presence_points = 35 if face_present else 0
    movement_points = 0
    if movements:
        active_fraction = sum(value > MOVEMENT_THRESHOLD_PX for value in movements) / len(movements)
        movement_points = 15 * active_fraction
    speech_seconds = sum(
        _number(row, "duration_seconds", window_seconds)
        for row in audio_rows if row.get("audio_class") == "Probable speech"
    )
    noise_seconds = sum(
        _number(row, "duration_seconds", window_seconds)
        for row in audio_rows if row.get("audio_class") == "Background noise"
    )
    speech_fraction = min(1.0, speech_seconds / window_seconds) if window_seconds else 0.0
    noise_fraction = min(1.0, noise_seconds / window_seconds) if window_seconds else 0.0
    speech_points = 40 * speech_fraction
    noise_penalty = 10 * noise_fraction
    inactivity_penalty = 10 if inactivity else 0
    score = round(max(0, min(100, presence_points + movement_points + speech_points
                              - noise_penalty - inactivity_penalty)), 1)
    level = "High" if score >= 70 else "Moderate" if score >= 35 else "Low"
    explanation = (f"Presence: {presence_points:.1f}/35; movement: {movement_points:.1f}/15; "
                   f"probable speech: {speech_points:.1f}/40; background-noise adjustment: "
                   f"-{noise_penalty:.1f}; inactivity adjustment: -{inactivity_penalty:.1f}.")
    return score, level, speech_fraction, noise_fraction, explanation


def reason_about_frame(face_ids, audio_class):
    """Return a transparent context label, score and human-readable explanation."""
    face_present = bool(face_ids)
    if audio_class not in AUDIO_CLASSES:
        audio_class = "Unknown"
    if face_present and audio_class == "Probable speech":
        return ("Visual presence + probable speech", 100,
                "At least one face was tracked while speech-like audio features were detected.")
    if face_present and audio_class == "Background noise":
        return ("Visual presence + background noise", 65,
                "At least one face was tracked; the audio was classified as background noise.")
    if face_present and audio_class == "Silence":
        return ("Visual presence + silence", 60,
                "At least one face was tracked while the audio segment was classified as silence.")
    if face_present:
        return ("Visual presence only", 55,
                "A face was tracked, but no matching audio classification was available.")
    if audio_class == "Probable speech":
        return ("Probable speech without visible face", 40,
                "Speech-like audio features were detected, but no face was tracked in this interval.")
    if audio_class == "Background noise":
        return ("Background noise only", 20,
                "Background noise was detected and no face was tracked.")
    if audio_class == "Silence":
        return ("No visible face + silence", 0,
                "No face was tracked and the audio segment was classified as silence.")
    return ("Insufficient multimodal data", 0,
            "Neither a face observation nor an audio classification was available.")


def _read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _number(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def build_multimodal_report(tracking_file="face_tracking.csv",
                            audio_file="audio_segments.csv",
                            output_file="multimodal_insights.csv",
                            summary_file="multimodal_session_summary.json",
                            window_seconds=DEFAULT_WINDOW_SECONDS,
                            movement_threshold_px=MOVEMENT_THRESHOLD_PX,
                            extra_visual_features=None,
                            extra_audio_features=None):
    """Synchronize visual/audio observations into fixed timestamp windows.

    Optional feature-name lists let future modules add columns without changing
    the fusion pipeline. Visual movement is estimated from face-box centres.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than zero")
    extra_visual_features = extra_visual_features or []
    extra_audio_features = extra_audio_features or []

    visual = defaultdict(list)
    audio = defaultdict(list)
    for row in _read_csv(tracking_file):
        offset = _number(row, "session_offset_seconds", -1)
        if offset < 0:
            continue
        bucket = int(offset // window_seconds)
        visual[bucket].append(row)
    for row in _read_csv(audio_file):
        offset = _number(row, "start_offset_seconds", -1)
        if offset < 0:
            continue
        bucket = int(offset // window_seconds)
        audio[bucket].append(row)

    buckets = sorted(set(visual) | set(audio))
    output_rows = []
    context_counts = Counter()
    audio_class_seconds = Counter()
    total_visible_seconds = defaultdict(float)
    movement_values = []

    for bucket in buckets:
        vrows, arows = visual[bucket], audio[bucket]
        start = round(bucket * window_seconds, 3)
        end = round(start + window_seconds, 3)
        participant_ids = sorted({r.get("participant_id", "") for r in vrows if r.get("participant_id")})

        # Estimate movement by sorting each participant's observations by time
        # and measuring centre-point displacement between consecutive frames.
        movements = []
        by_person = defaultdict(list)
        for row in vrows:
            pid = row.get("participant_id", "")
            if not pid:
                continue
            cx = _number(row, "x") + _number(row, "width") / 2
            cy = _number(row, "y") + _number(row, "height") / 2
            by_person[pid].append((_number(row, "session_offset_seconds"), cx, cy))
        for pid, observations in by_person.items():
            observations.sort()
            distances = [((b[1]-a[1])**2 + (b[2]-a[2])**2)**0.5
                         for a, b in zip(observations, observations[1:])]
            if distances:
                movements.extend(distances)
            # Estimate observed span; use the median frame interval to account
            # for the final observed frame without assuming a fixed camera FPS.
            times = sorted({item[0] for item in observations})
            gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
            frame_step = sorted(gaps)[len(gaps) // 2] if gaps else 1.0 / 30.0
            observed_span = (times[-1] - times[0] + frame_step) if times else 0.0
            total_visible_seconds[pid] += min(window_seconds, observed_span)

        avg_movement = round(sum(movements) / len(movements), 3) if movements else 0.0
        inactivity = bool(movements) and avg_movement <= movement_threshold_px
        classes = [r.get("audio_class", "Unknown") for r in arows]
        audio_class = Counter(classes).most_common(1)[0][0] if classes else "Unknown"
        if audio_class not in AUDIO_CLASSES:
            audio_class = "Unknown"
        label, context_score, context_explanation = reason_about_frame(participant_ids, audio_class)
        engagement_score, engagement_level, speech_fraction, noise_fraction, score_explanation = calculate_engagement_indicator(
            bool(participant_ids), movements, arows, window_seconds, inactivity)
        explanation = context_explanation + " " + score_explanation
        context_counts[label] += 1
        for row in arows:
            cls = row.get("audio_class", "Unknown")
            audio_class_seconds[cls] += _number(row, "duration_seconds", window_seconds)
        movement_values.extend(movements)

        record = {
            "window_start_seconds": start,
            "window_end_seconds": end,
            "participant_ids": ";".join(participant_ids),
            "visible_face_count": len(participant_ids),
            "visual_observation_count": len(vrows),
            "estimated_average_movement_px": avg_movement,
            "visual_inactivity": inactivity,
            "audio_class": audio_class,
            "audio_segment_count": len(arows),
            "mean_rms_amplitude": round(sum(_number(r, "rms_amplitude") for r in arows) / len(arows), 6) if arows else "",
            "mean_peak_amplitude": round(sum(_number(r, "peak_amplitude") for r in arows) / len(arows), 6) if arows else "",
            "mean_zero_crossing_rate": round(sum(_number(r, "zero_crossing_rate") for r in arows) / len(arows), 6) if arows else "",
            "mean_spectral_flatness": round(sum(_number(r, "spectral_flatness") for r in arows) / len(arows), 6) if arows else "",
            "combined_context": label,
            "context_score": context_score,
            "engagement_score": engagement_score,
            "engagement_level": engagement_level,
            "speech_activity_fraction": round(speech_fraction, 3),
            "background_noise_fraction": round(noise_fraction, 3),
            "score_explanation": score_explanation,
            "explanation": explanation,
        }
        # Extensible pass-through: preserve requested future feature columns.
        for feature in extra_visual_features:
            vals = [_number(r, feature) for r in vrows if r.get(feature, "") != ""]
            record[f"visual_{feature}"] = round(sum(vals) / len(vals), 6) if vals else ""
        for feature in extra_audio_features:
            vals = [_number(r, feature) for r in arows if r.get(feature, "") != ""]
            record[f"audio_{feature}"] = round(sum(vals) / len(vals), 6) if vals else ""
        output_rows.append(record)

    fields = list(output_rows[0].keys()) if output_rows else [
        "window_start_seconds", "window_end_seconds", "participant_ids", "visible_face_count",
        "visual_observation_count", "estimated_average_movement_px", "visual_inactivity",
        "audio_class", "audio_segment_count", "mean_rms_amplitude", "mean_peak_amplitude",
        "mean_zero_crossing_rate", "mean_spectral_flatness", "combined_context",
        "context_score", "explanation"]
    with Path(output_file).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    summary = {
        "schema_version": "1.1",
        "synchronization": {"method": "session timestamp fixed-window aggregation", "window_seconds": window_seconds},
        "time_windows_analyzed": len(output_rows),
        "combined_context_counts": dict(context_counts),
        "average_context_score": round(sum(r["context_score"] for r in output_rows) / len(output_rows), 1) if output_rows else 0,
        "average_engagement_indicator": round(sum(r["engagement_score"] for r in output_rows) / len(output_rows), 1) if output_rows else 0,
        "engagement_level_counts": dict(Counter(r["engagement_level"] for r in output_rows)),
        "peak_engagement_window": ({"start_seconds": max(output_rows, key=lambda r: r["engagement_score"])["window_start_seconds"],
                                    "end_seconds": max(output_rows, key=lambda r: r["engagement_score"])["window_end_seconds"],
                                    "score": max(r["engagement_score"] for r in output_rows)} if output_rows else None),
        "lowest_engagement_windows": [{"start_seconds": r["window_start_seconds"], "end_seconds": r["window_end_seconds"], "score": r["engagement_score"]}
                                      for r in output_rows if r["engagement_score"] < 35],
        "teaching_suggestions": ( ["Consider a short interactive question or discussion during low-activity periods.",
                                   "Check camera framing if visual presence is frequently missing.",
                                   "Review noisy intervals and microphone placement."] if output_rows else []),
        "most_common_context": context_counts.most_common(1)[0][0] if context_counts else "No data",
        "audio_class_duration_seconds": dict(audio_class_seconds),
        "average_visual_movement_px": round(sum(movement_values) / len(movement_values), 3) if movement_values else 0,
        "participant_estimated_visible_window_seconds": {str(k): round(v, 2) for k, v in total_visible_seconds.items()},
        "reasoning_method": "Timestamp-aligned rule-based score per window: presence 35 points, movement 15, probable speech 40, with background-noise and visual-inactivity adjustments.",
        "score_levels": {"low": "0-34", "moderate": "35-69", "high": "70-100"},
        "extensibility": {"optional_visual_features": extra_visual_features, "optional_audio_features": extra_audio_features},
        "interpretation_limit": "Engagement scores are explainable classroom activity indicators only; they do not prove attention, understanding, identity, or learning. Movement is a simple face-box displacement estimate and probable speech is a heuristic audio class."
    }
    Path(summary_file).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
