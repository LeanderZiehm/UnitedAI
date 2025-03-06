import time


class DownloadSpeedTracker:
    def __init__(self, window_sec=5):
        self.window_sec = window_sec
        self.download_timestamps = []
        self.start_time = time.time()

    def record_download(self):
        """Records a successful download timestamp."""
        self.download_timestamps.append(time.time())
        self._cleanup_old_timestamps()

    def getDownloadSpeed(self):
        """Returns current, average, and median download speed."""
        self._cleanup_old_timestamps()

        elapsed_time = time.time() - self.start_time
        total_downloads = len(self.download_timestamps)

        current_speed = len(self.download_timestamps) / self.window_sec  
        return current_speed

    def _cleanup_old_timestamps(self):
        """Removes timestamps older than the sliding window."""
        cutoff_time = time.time() - (self.window_sec)
        self.download_timestamps = [t for t in self.download_timestamps if t >= cutoff_time]
