# Multimodal Attendance & Engagement Agent

A small, local Python demonstration using webcam face detection and audio-volume activity.

## What it does
- Detects faces in each video frame using OpenCV Haar Cascade.
- Assigns temporary participant IDs and tracks faces across nearby frames using face position.
- Saves each detection with its timestamp, participant ID, and face position in `face_tracking.csv`.
- Supports a live webcam or a pre-recorded classroom video.
- Accumulates visible time separately for each temporary participant ID, including intermittent appearances.
- Marks a participant Present only after reaching a configurable minimum cumulative presence duration (default: 30 seconds).
- Saves participant-level attendance and presence duration to `participant_attendance.csv`.
- Detects sound activity from microphone volume (RMS).
- Calculates a simple 0–100 activity indicator.
- Saves one session summary to `attendance.csv`.
- Provides an optional Streamlit dashboard.

## Important limitations and privacy
- This is a classroom prototype, not a reliable attendance or engagement assessment.
- It does not recognize real identities. Participant IDs are temporary labels for one session and may change after a long disappearance or major movement. Face presence is not proof of attendance.
- Audio volume does not prove speech, participation, or understanding.
- Do not use the score for grading or disciplinary decisions.
- Obtain informed permission before using a webcam or microphone. Use only in an appropriate, supervised setting.
- Raw audio and video are not saved. Session-level percentages and summaries are saved locally in CSV.

## Setup (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the main application
```powershell
python main.py
```
To change the attendance threshold (for example, 60 seconds):
```powershell
python main.py --min-presence-seconds 60
```
Press `Q` in the video window to end the session. The session summary is saved to `attendance.csv`, frame-by-frame face data to `face_tracking.csv`, and participant attendance to `participant_attendance.csv`. By default, a participant needs 30 cumulative seconds of visibility to be marked Present.

To process a recorded video instead of the webcam:
```powershell
python main.py --video "path\to\classroom_video.mp4"
```
Audio activity monitoring runs with the live webcam; it is disabled for prerecorded video.

## Optional dashboard
```powershell
streamlit run dashboard.py
```

## Audio threshold
If the microphone activity indicator is too sensitive or not sensitive enough, change
`threshold=0.02` in `main.py`. Microphone levels vary by device and room.

## Troubleshooting
- Webcam unavailable: close apps that may already be using the camera and check Windows camera permissions.
- Microphone unavailable: check Windows microphone permissions and the selected input device.
- Installation issues: use Python 3.10–3.12 for broad package compatibility.

## Multimodal Agent (rule-based fusion)
The `multimodal_agent.py` module combines face-tracking observations with the
per-second audio classes (Silence, Background noise, or Probable speech). It
applies transparent rules and records a context label, score, and explanation
for each time window. After a session, it creates:
- `multimodal_insights.csv` – aligned visual/audio observations and the rule used.
- `multimodal_session_summary.json` – counts of context labels and an overall summary.

The context score is an explainable activity indicator, not a measure of a
student's attention, understanding, identity, or learning. Audio labels are
heuristic and are not speech recognition. For prerecorded video, visual and
audio observations are aligned approximately by elapsed seconds.

## Timestamp-Based Multimodal Fusion

The fusion stage groups face-tracking observations and audio-analysis segments
into matching fixed-duration session windows (1 second by default). Each fused
row includes participant presence, estimated face-box movement, a simple
visual-inactivity indicator, audio class, mean audio features, a combined
context label, and an explainable rule-based score. The JSON summary records
session-level metrics and the fusion schema version.

The fusion function can be extended with additional numeric feature columns by
passing `extra_visual_features=[...]` or `extra_audio_features=[...]` to
`build_multimodal_report`. The current implementation uses timestamps relative
to the beginning of the session; it does not infer real-world identity or prove
attention or learning. Face-box movement is only a basic movement estimate.

## Analytics and Recommendation Engine

After each session, `recommendation_engine.py` reads the timestamp-aligned
multimodal engagement indicators and creates human-readable, rule-based
analytics and suggestions for instructors and students. It produces:
- `recommendations.csv` – recommendation, audience, priority, evidence, and rationale.
- `analytics_recommendations.json` – session-level metrics and all recommendations.

The dashboard displays these outputs after a session. Suggestions are contextual
prompts for human review, not automated judgments. The system does not assess
individual attention, ability, understanding, or learning and must not be used
for grading, ranking, or disciplinary decisions.


## Instructor Teaching Suggestions

The instructor-facing suggestion stage examines the time-ordered engagement
profile and audio context. It flags sustained low-activity runs (three or more
consecutive windows below 35), sharp adjacent-window drops (20 points or more),
peak activity windows (70 or above), and recurring noisy conditions. Each prompt
includes the observed evidence, a possible teaching response, and a short
rationale. Suggestions are non-prescriptive and intended for instructor review.

After each session, the stage creates `teaching_suggestions.csv` and adds the
structured `instructor_teaching_suggestions` list to
`analytics_recommendations.json`. The Streamlit dashboard displays each prompt
in an expandable card. Thresholds are simple defaults and can be adjusted in
`recommendation_engine.py`; they are not validated measures of attention or
learning.

## Student-Facing Session Analytics

After each completed session, `student_analytics.py` creates a privacy-conscious
summary for each temporary participant tracker ID. It includes the recorded
presence duration, attendance threshold/status, and the number/share of fused
time windows in which that ID was visible. It also provides a reflective prompt
and shared room-level session context for dashboard review.

Outputs:
- `student_analytics.csv` – participant-level presence and reflection fields.
- `student_analytics.json` – structured participant summaries, shared session
  reflection, and privacy/ethics notes.

No individual engagement score, grade, peer comparison, or ranking is generated.
The room-level engagement timeline is shown only as shared session context and
must not be attributed to an individual learner. Tracker IDs are temporary and
are not linked to names. Camera visibility is approximate and is not proof of
attendance, attention, participation quality, or learning. Use these summaries
for private reflection, not grading or disciplinary decisions.

## End-to-End Pipeline Verification

Run the offline integration check from the project folder:

```powershell
python validate_pipeline.py
```

This creates synthetic timestamped vision/audio inputs in a temporary folder
and checks the complete downstream data flow: timestamp fusion, engagement
indicators, session analytics, instructor recommendations, teaching prompts,
and privacy-conscious student summaries. The test does not access a webcam,
microphone, or real classroom recording, and it does not change your session
CSV files.

### Manual device checks

To verify the actual devices on your computer, install the requirements and run
`python main.py` with webcam/microphone permissions enabled. Press `Q` to finish
and confirm that `attendance.csv`, `face_tracking.csv`, `participant_attendance.csv`,
`audio_segments.csv`, `multimodal_insights.csv`, `analytics_recommendations.json`,
`recommendations.csv`, `teaching_suggestions.csv`, `student_analytics.csv`, and
`student_analytics.json` are created. For a recorded video, run
`python main.py --video "path\\to\\classroom_video.mp4"`; FFmpeg is required for
its audio track. Device testing must be performed on the target computer because
this offline validation environment cannot access the user's webcam or microphone.


## Optional Streamlit Visualization Dashboard

The dashboard is an optional visualization layer; it is not required to run the
attendance and analytics pipeline. It presents:
- attendance session records and participant presence summaries;
- the room-level engagement/activity timeline and fusion-window details;
- instructor recommendations and expandable teaching suggestions;
- temporary-ID student presence summaries and shared session reflection.

Install the project requirements, run at least one session with `python main.py`,
then launch the dashboard from the project folder:

```powershell
streamlit run dashboard.py
```

Open the local address printed by Streamlit in your browser. Use **Refresh
session data** in the sidebar after generating new session outputs. The dashboard
reads the CSV/JSON files in the project folder and does not itself start webcam or
microphone capture. It also works before data exists by showing informative
empty-state messages.

## Robustness and edge-case validation

Run the deterministic offline edge-case suite with:

```powershell
python validate_robustness.py
```

The suite checks temporary face-track continuity across short detection gaps,
malformed detection rejection, finite audio features for silence/noise and
invalid samples, brief participant appearances, intermittent/missing audio,
and bounded engagement scores. It complements the end-to-end smoke test:

```powershell
python validate_pipeline.py
```

These tests use synthetic inputs. They do **not** establish real-world
accuracy or deployment readiness. Before classroom use, conduct supervised
on-site trials across different lighting, camera angles, partial occlusions,
room noise levels, microphone dropouts, and participant entry/exit patterns.
Review attendance against consented ground truth and tune `--min-presence-seconds`,
`FaceTracker` distance/missing-frame settings, and the audio `threshold` for the
specific camera and microphone. Treat all scores as approximate activity
indicators, not evidence of attention, learning, or individual performance.


## Final Project Summary

See [`FINAL_PROJECT_SUMMARY.md`](FINAL_PROJECT_SUMMARY.md) for the consolidated project overview, component descriptions, conclusion, validation scope, ethical safeguards, and quick-start commands.
