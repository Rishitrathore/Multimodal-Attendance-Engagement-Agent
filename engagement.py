def calculate_activity_score(face_present, audio_active):
    """
    A simple activity indicator, not a reliable measurement of attention
    or learning. Returns a score from 0 to 100.
    """
    score = 0
    if face_present:
        score += 60
    if audio_active:
        score += 40
    return score

def describe_activity(face_present, audio_active):
    if face_present and audio_active:
        return "Face detected + sound activity"
    if face_present:
        return "Face detected; little sound activity"
    if audio_active:
        return "Sound activity; no face detected"
    return "No face or sound activity detected"
