# Temporal Engagement Scoring

The fusion pipeline now calculates an explainable activity indicator for every timestamp window and writes it to `multimodal_insights.csv`.

## Scoring (0-100)
- Visual presence: up to 35 points.
- Face-box movement: up to 15 points, based on the fraction of measured movements above the configured movement threshold.
- Probable speech: up to 40 points, based on the share of the window classified as probable speech.
- Background noise: up to 10 points deducted.
- Visual inactivity: 10 points deducted when movement observations are below the inactivity threshold.

Levels: Low (0-34), Moderate (35-69), High (70-100). These are configurable rule-based indicators, not proof of attention, understanding, or learning. Speech is estimated from audio features; it is not speech recognition.

The session JSON includes the average indicator, level counts, peak window, low-score windows, and general teaching suggestions. The Streamlit dashboard plots the score over time.
