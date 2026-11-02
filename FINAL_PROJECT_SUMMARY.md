# Multimodal Attendance & Engagement Agent

## Final Project Summary and Conclusion

The **Multimodal Attendance & Engagement Agent** demonstrates how computer vision, audio signal processing, timestamp-based multimodal fusion, and explainable rule-based reasoning can be combined in an educational-session prototype. Rather than relying only on a conventional attendance mechanism, the system brings together visual presence observations and coarse audio activity indicators to produce session-level context, attendance summaries, and interpretable activity trends.

The project was developed through a milestone-driven process. The Vision Module detects faces in video frames and assigns temporary participant tracker IDs. Presence-based logic accumulates observed visibility over time and applies a configurable threshold when generating attendance summaries. The Audio Module processes microphone input or supported video audio into short segments and extracts basic signal features to classify intervals as silence, background noise, probable speech, or unknown when data is unavailable. It does not perform speech recognition or identify speakers.

The Multimodal Agent aligns visual and audio observations into fixed time windows. Its transparent, rule-based logic produces contextual labels, activity indicators, and explanations that can be inspected in generated CSV and JSON reports. The Analytics and Recommendation Engine converts these outputs into room-level summaries and optional instructor suggestions. Student-facing analytics are limited to temporary-ID presence information and reflective prompts; individual engagement scores, rankings, and assessments are intentionally excluded. An optional Streamlit dashboard presents attendance records, activity timelines, recommendations, and student session summaries through charts, tables, and expandable sections.

The project includes offline integration and robustness checks for data flow, short appearances, brief tracking gaps, malformed detections, invalid audio samples, intermittent audio, missing modality data, and score boundaries. These automated checks use synthetic inputs. They verify selected software behaviours but do not establish measured accuracy under real classroom conditions. Before any operational use, the application must undergo supervised on-site evaluation with consented participants, varied lighting and camera positions, partial occlusions, realistic room noise, microphone interruptions, and independently reviewed attendance ground truth. Parameters should be calibrated for the target environment.

Privacy, transparency, and human oversight are central design principles. Participant IDs are temporary and are not linked to real identities. Raw audio and video are not retained by the analytics pipeline; generated session reports are stored locally and should be handled securely. Audio activity and face visibility are approximate signals: neither proves attendance, attention, participation quality, understanding, or learning. All scores and recommendations are decision-support indicators for human review and must not be used for grading, ranking, disciplinary action, or other consequential decisions.

Overall, this project provides a modular foundation for exploring multimodal classroom analytics in classrooms, training sessions, and workshops. Its components can be extended with stronger tracking, calibrated audio analysis, configurable data-retention controls, accessibility features, and further privacy safeguards. Any future deployment should be conditional on real-world validation, informed consent, institutional approval, and ongoing human supervision.

## Implemented Components

- `vision.py` — face detection and temporary face tracking.
- `audio.py` — audio capture/extraction, preprocessing, and signal-feature analysis.
- `main.py` — session execution, attendance accumulation, and output orchestration.
- `engagement.py` — basic activity indicator.
- `multimodal_agent.py` — timestamp-based visual/audio fusion and explainable context scoring.
- `analytics.py` — session-level attendance summary.
- `recommendation_engine.py` — room-level analytics and instructor suggestions.
- `student_analytics.py` — privacy-conscious temporary-ID presence summaries.
- `dashboard.py` — optional Streamlit visualization dashboard.
- `validate_pipeline.py` — offline end-to-end integration checks.
- `validate_robustness.py` — deterministic synthetic edge-case checks.

## Quick Start

Install dependencies from the project directory:

```bash
python -m pip install -r requirements.txt
```

Run the webcam-based application:

```bash
python main.py
```

Run the optional dashboard after generating session data:

```bash
streamlit run dashboard.py
```

Run the offline checks:

```bash
python validate_pipeline.py
python validate_robustness.py
```

See `README.md` for detailed setup, prerecorded-video usage, output files, troubleshooting, and manual device-testing instructions.
