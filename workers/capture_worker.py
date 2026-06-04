"""Audio capture worker thread.

Runs WASAPI loopback capture in a separate thread.
Feeds audio chunks into a queue for the recognition worker.
"""

import queue
import threading
import logging
from audio.wasapi_capture import WasapiCapture

logger = logging.getLogger(__name__)


class CaptureWorker(threading.Thread):
    """Worker thread for audio capture."""

    def __init__(self, audio_queue: queue.Queue):
        super().__init__(daemon=True)
        self._audio_queue = audio_queue
        self._capture = WasapiCapture(audio_queue)
        self._running = False

    def run(self):
        """Run the capture loop."""
        self._running = True
        logger.info("Capture worker started")
        self._capture.start()

    def stop(self):
        """Stop the capture worker."""
        self._running = False
        self._capture.stop()
        logger.info("Capture worker stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def device_name(self) -> str:
        return self._capture.device_name

    def refresh_device(self):
        """Refresh audio device on change."""
        self._capture.refresh_device()