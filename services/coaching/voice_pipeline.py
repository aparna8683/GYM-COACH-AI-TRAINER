
import time
import streamlit as st
import threading
import base64
import streamlit.components.v1 as components


class VoicePipeline:

    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self.last_spoken_at = 0
        self.cooldown = 5

        self._lock = threading.Lock()
        self._active_form_issue = None

    # 1. Detect exercise form issues

    def _find_form_issue(self, exercise, metrics):

        if not isinstance(metrics, dict):
            return None



        # Direct issue supplied by the video processor
        issue = metrics.get("issue") or metrics.get("form_issue")

        if issue:
            return issue

        # Squats
        if exercise == "Squats":

            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)

            if depth == "TOO HIGH":
                return "Your squat is not deep enough. Bend your knees further."

            if isinstance(back_angle, (int, float)) and back_angle < 130:
                return "You are leaning too far forward during your squat. Keep your chest up."

        # Push-ups
        elif exercise == "Push-ups":

            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")

            if alignment == "Poor Form":
                return "Your body alignment is incorrect. Maintain a straight line from head to heels."

            if hip_status in ["SAGGING", "HIPS SAGGING"]:
                return "Your hips are sagging. Engage your core and maintain a straight body."

        # Bicep Curls
        elif exercise in ["Biceps Curls (Dumbells)", "Bicep Curls"]:

            shoulder_status = metrics.get("shoulder_status", "")
            swing_status = metrics.get("swing_status", "")

            if swing_status in ["Swinging", "SWING DETECTED"]:
                return "Avoid swinging your body. Perform controlled curls using your biceps."

            if shoulder_status == "Unstable":
                return "Keep your shoulders stable and avoid unnecessary upper-body movement."

        # Shoulder Press
        elif exercise == "Shoulder Press":

            shoulder_status = metrics.get("shoulder_status", "")
            back_angle = metrics.get("back_angle", 180)
            extension_status = metrics.get("extension_status", "")

            if shoulder_status == "Unstable":
                return "Stabilize your shoulders before pressing the weights overhead."

            if isinstance(back_angle, (int, float)) and back_angle < 150:
                return "Avoid arching your back. Keep your core engaged during the press."

            if extension_status == "INCOMPLETE":
                return "Extend your arms fully overhead with controlled movement."

        # Lunges
        elif exercise == "Lunges":

            balance_status = metrics.get("balance_status", "")

            if balance_status in ["Poor Balance", "UNSTABLE"]:
                return "Improve your balance. Keep your torso upright and move with control."

        return None

    # 2. Generate voice feedback

    
    def process_event(self, event, exercise, metrics):

        issue = self._find_form_issue(exercise, metrics)

        # Do not generate continuous motivational messages.
        if event == "ongoing_form_check":

            # Reset issue tracking when the user corrects their form.
            if not issue:
                self._active_form_issue = None
                return None

            # Do not repeat the same correction.
            if issue == self._active_form_issue:
                return None

        # No-pose warnings must also respect the cooldown.
        # Only workout lifecycle and set events bypass it.
        priority_events = {
            "workout_started",
            "set_completed",
            "workout_completed",
            "no_pose_detected"
        }

        now = time.monotonic()

        # Prevent simultaneous LLM and TTS requests.
        if not self._lock.acquire(blocking=False):
            return None

        try:
            now = time.monotonic()

            # Reserve cooldown BEFORE calling Groq or TTS.
            if event not in priority_events:
                if now - self.last_spoken_at < self.cooldown:
                    return None

            self.last_spoken_at = now

            text = self.llm.give_feedback(event, issue)

            if not text:
                return None

            voice = self.tts.speak(text)

            if not voice:
                return None

            # Remember the form issue only after successful generation.
            if event == "ongoing_form_check":
                self._active_form_issue = issue

            return voice, text

        except Exception as e:
            print(f"Voice Pipeline Error: {e}")
            return None

        finally:
            self._lock.release()


# 3. Play generated audio in Streamlit

def autoplay_audio(audio_bytes):

    if not audio_bytes:
        return

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    components.html(
        f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{audio_base64}"
                    type="audio/mp3">
        </audio>
        """,
        height=0,
    )