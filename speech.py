"""Microphone input (speech-to-text) and spoken replies (text-to-speech).

Speech-to-text uses the SpeechRecognition library with Google's free Web
Speech API, so an internet connection is needed. Text-to-speech uses pyttsx3,
which works offline. Both are imported lazily so the rest of the project
(parser, storage, tests, --text mode) runs without them installed.
"""
from __future__ import annotations

from typing import Optional


class SpeechServiceError(RuntimeError):
    """Raised when the online recognition service cannot be reached."""


class Listener:
    """Records one phrase from the microphone and returns it as text."""

    def __init__(self, language: str = "en-IN", timeout: int = 6,
                 phrase_time_limit: int = 8):
        import speech_recognition as sr  # lazy import

        self._sr = sr
        self.language = language
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.microphone = sr.Microphone()
        # Measure background noise once so quiet rooms and noisy rooms both work.
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

    def listen(self) -> Optional[str]:
        """Return the recognised sentence, or None if nothing was understood."""
        sr = self._sr
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )
            except sr.WaitTimeoutError:
                return None
        return _recognize(sr, self.recognizer, audio, self.language)


def transcribe_file(path: str, language: str = "en-IN") -> Optional[str]:
    """Transcribe a WAV/AIFF/FLAC recording. Useful for demos without a mic."""
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.AudioFile(path) as source:
        audio = recognizer.record(source)
    return _recognize(sr, recognizer, audio, language)


def _recognize(sr, recognizer, audio, language: str) -> Optional[str]:
    try:
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        return None  # Speech was unclear.
    except sr.RequestError as exc:
        raise SpeechServiceError(
            "Could not reach the speech recognition service. "
            "Check your internet connection."
        ) from exc


class Speaker:
    """Reads replies aloud. Falls back to silence if pyttsx3 is unavailable."""

    def __init__(self, rate: int = 170):
        self.engine = None
        try:
            import pyttsx3

            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", rate)
        except Exception:  # No TTS engine on this machine: print only.
            self.engine = None

    def say(self, text: str) -> None:
        if self.engine is None:
            return
        self.engine.say(text)
        self.engine.runAndWait()
