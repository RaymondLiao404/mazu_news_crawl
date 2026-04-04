import shutil
import subprocess
import tempfile
from pathlib import Path


class YtSnapshotService:
    def ensure_ffmpeg(self) -> None:
        if self._resolve_ffmpeg_executable() is None:
            raise RuntimeError("找不到 ffmpeg，可安裝 imageio-ffmpeg 或系統 ffmpeg")

    def load_yt_dlp(self):
        try:
            import yt_dlp  # type: ignore
        except ImportError as exc:
            raise RuntimeError("找不到 yt-dlp，請先安裝 requirements.txt 內套件") from exc
        return yt_dlp

    def capture_snapshot_bytes(self, url: str) -> bytes:
        if "youtube.com" not in url and "youtu.be" not in url:
            raise RuntimeError("目前只支援 YouTube 直播或影片網址")

        self.ensure_ffmpeg()
        stream_url = self._extract_stream_url(url)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "snapshot.jpg"
            self._run_ffmpeg(stream_url=stream_url, output_path=output_path)
            if not output_path.exists():
                raise RuntimeError("截圖失敗，沒有產生圖片檔")
            return output_path.read_bytes()

    def _resolve_ffmpeg_executable(self) -> str | None:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        try:
            from imageio_ffmpeg import get_ffmpeg_exe  # type: ignore
        except ImportError:
            return None

        try:
            return get_ffmpeg_exe()
        except Exception:
            return None

    def _extract_stream_url(self, url: str) -> str:
        yt_dlp = self.load_yt_dlp()
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "format": "best",
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise RuntimeError("無法解析 YouTube 網址")

        if "entries" in info:
            info = next((entry for entry in info["entries"] if entry), None)
            if not info:
                raise RuntimeError("找不到可用的影片資訊")

        stream_url = info.get("url")
        if stream_url:
            return stream_url

        formats = info.get("formats") or []
        for fmt in formats:
            if fmt.get("url"):
                return fmt["url"]

        raise RuntimeError("找不到可用的串流網址")

    def _run_ffmpeg(self, stream_url: str, output_path: Path) -> None:
        ffmpeg_executable = self._resolve_ffmpeg_executable()
        if ffmpeg_executable is None:
            raise RuntimeError("找不到可用的 ffmpeg 執行檔")

        command = [
            ffmpeg_executable,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            stream_url,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ]
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg 截圖失敗，exit code={completed.returncode}")
