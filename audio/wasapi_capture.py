"""WASAPI Loopback audio capture using soundcard library.

Captures system audio from the default playback device
without requiring microphone or virtual audio cables.
"""

import queue
import time
import logging
import soundcard as sc
import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000  # Whisper expects 16kHz
BLOCK_SIZE = 1024  # Samples per block
CHANNELS = 1  # Mono


class WasapiCapture:
    """Captures system audio via WASAPI loopback."""

    def __init__(self, audio_queue: queue.Queue):
        self._audio_queue = audio_queue
        self._running = False
        self._speaker = None
        self._device_name = "Unknown"

    def start(self):
        """Start capturing audio from default playback device."""
        self._running = True
        self._find_default_speaker()
        self._capture_loop()

    def stop(self):
        """Stop audio capture."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def device_name(self) -> str:
        return self._device_name

    def _find_default_speaker(self):
        """Find and store the default speaker device."""
        try:
            self._speaker = sc.default_speaker()
            self._device_name = self._speaker.name
            logger.info("Default playback device: %s", self._device_name)
        except Exception as e:
            logger.error("Failed to find default speaker: %s", e)
            self._speaker = None

    def _capture_loop(self):
        """Main capture loop using WASAPI loopback."""
        if self._speaker is None:
            logger.error("No speaker device available")
            return

        try:
            with self._speaker.recorder(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE) as mic:
                while self._running:
                    data = mic.record(numframes=BLOCK_SIZE)
                    if data is not None and len(data) > 0:
                        # Convert to mono if necessary
                        if data.ndim > 1 and data.shape[1] > 1:
                            data = np.mean(data, axis=1, keepdims=True)
                        # Flatten to 1D array
                        audio_data = data.flatten().astype(np.float32)
                        self._audio_queue.put(audio_data)
        except Exception as e:
            logger.error("Audio capture error: %s", e)
            self._running = False

    def refresh_device(self):
        """Refresh the default audio device (call on device change)."""
        logger.info("Refreshing audio device")
        self._find_default_speaker()