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
        self._loopback_mic = None
        self._device_name = "Unknown"
        self._sample_count = 0

    def start(self):
        """Start capturing audio from default playback device."""
        self._running = True
        self._find_loopback_device()
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

    def _find_loopback_device(self):
        """Find the WASAPI loopback device matching the default speaker."""
        try:
            # Get default speaker name
            speaker = sc.default_speaker()
            speaker_name = speaker.name
            logger.info("Default playback device: %s", speaker_name)

            # Find matching loopback microphone (Speakers = loopback capture)
            mics = sc.all_microphones(include_loopback=True)
            self._loopback_mic = None
            for mic in mics:
                # Loopback devices show as "Speakers (Device Name)"
                # Exclude real microphones (contain "Microphone" in name)
                if "Microphone" in mic.name:
                    continue
                # Exact match or substring match on speaker name
                if speaker_name in mic.name or mic.name in speaker_name:
                    self._loopback_mic = mic
                    self._device_name = mic.name
                    logger.info("Found loopback device: %s", mic.name)
                    break

            if self._loopback_mic is None:
                # Fallback: pick first loopback device that isn't a real mic
                for mic in mics:
                    if "Microphone" in mic.name:
                        continue
                    self._loopback_mic = mic
                    self._device_name = mic.name
                    logger.info("Fallback loopback device: %s", mic.name)
                    break

            if self._loopback_mic is None:
                logger.error("No loopback device found. Available mics: %s", [m.name for m in mics])

        except Exception as e:
            logger.error("Failed to find loopback device: %s", e)
            self._loopback_mic = None

    def _capture_loop(self):
        """Main capture loop using WASAPI loopback."""
        if self._loopback_mic is None:
            logger.error("No loopback device available")
            return

        try:
            with self._loopback_mic.recorder(samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE) as mic:
                logger.info("Audio capture loop started")
                while self._running:
                    data = mic.record(numframes=BLOCK_SIZE)
                    if data is not None and len(data) > 0:
                        # Convert to mono if necessary
                        if data.ndim > 1 and data.shape[1] > 1:
                            data = np.mean(data, axis=1, keepdims=True)
                        # Flatten to 1D array
                        audio_data = data.flatten().astype(np.float32)
                        self._sample_count += len(audio_data)
                        # Log every ~2 seconds of audio
                        if self._sample_count % (SAMPLE_RATE * 2) < BLOCK_SIZE:
                            logger.debug("Captured %d samples (%.1f sec)", self._sample_count, self._sample_count / SAMPLE_RATE)
                        self._audio_queue.put(audio_data)
        except Exception as e:
            logger.error("Audio capture error: %s", e)
            self._running = False

    def refresh_device(self):
        """Refresh the default audio device (call on device change)."""
        logger.info("Refreshing audio device")
        self._find_loopback_device()
