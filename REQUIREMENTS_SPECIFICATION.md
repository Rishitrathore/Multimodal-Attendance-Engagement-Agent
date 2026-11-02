# Milestone 1: Requirements Specification and Environment Setup

## 1. Objective
Define the basic requirements, select suitable libraries, and prepare a reproducible Python development environment for the Multimodal Attendance & Engagement Agent.

## 2. Functional Requirements
1. Capture video from a webcam.
2. Detect one or more faces in each video frame.
3. Assign temporary participant IDs and track faces across consecutive frames using face position.
4. Record each detected face ID, timestamp, and position in a CSV file.
5. Estimate face-presence duration during a session.
6. Read microphone audio levels and detect sound activity when using the webcam.
7. Combine face and audio activity into a simple activity score.
8. Generate a short session summary and recommendation.
9. Save session-level results and face-tracking records in CSV files.

## 3. Non-Functional Requirements
1. Keep the application simple and easy to operate.
2. Run locally on a Windows computer with a compatible Python version.
3. Separate functionality into small Python modules.
4. Avoid saving raw audio or video.
5. Handle unavailable camera or microphone devices with a clear error message.
6. Keep dependencies listed in one requirements file for repeatable setup.

## 4. Selected Libraries and Tools

| Library / Tool | Purpose |
|---|---|
| Python | Main programming language |
| OpenCV | Webcam access and face detection |
| NumPy | Audio-level calculations |
| SoundDevice | Microphone input |
| Streamlit | Optional results dashboard |
| Pandas | Reading session data for the dashboard |
| CSV | Lightweight session-result storage |
| VS Code | Code editor |
| Python venv | Isolated project environment |

## 5. Environment Setup

Run these commands from the project folder in Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks environment activation, run this command in the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

## 6. Verify Installation

```powershell
python --version
pip list
```

Check that OpenCV can be imported:

```powershell
python -c "import cv2, numpy, sounddevice, streamlit, pandas; print('All project libraries imported successfully')"
```

## 7. Expected Outcome
The project has a documented set of functional and non-functional requirements, a selected technology stack, a `requirements.txt` dependency list, and instructions for creating and verifying an isolated Python environment.

## 8. Face Tracking Output
The application writes `face_tracking.csv` with the columns `timestamp`, `participant_id`, `x`, `y`, `width`, and `height`. IDs are temporary labels for a single run, based on face position; they are not facial recognition and do not reveal a person's identity. Use `python main.py --video "path\to\video.mp4"` to process a recorded classroom video instead of the webcam.

## 9. Scope Note
This is a demonstration prototype. Face presence and microphone volume are only rough activity signals; they do not establish a person's identity, speech, attention, or learning. Obtain permission before using camera or microphone input.
