import time


class DownloadSpeedTracker:
    def __init__(self, window_sec):
        self.window_sec = window_sec
        self.download_timestamps = []
        self.start_time = time.time()

    def record_download(self):

        self.download_timestamps.append(time.time())

    def getDownloadSpeed(self):

        self._cleanup_old_timestamps()
        total_downloads = len(self.download_timestamps)
        return total_downloads

    def _cleanup_old_timestamps(self):

        cutoff_time = time.time() - (self.window_sec)
        self.download_timestamps = [t for t in self.download_timestamps if t >= cutoff_time]
