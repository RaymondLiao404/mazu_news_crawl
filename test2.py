import argparse
import math
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


LOOKBACK_SECONDS = 60
DEFAULT_OUTPUT_DIR = Path("outputs") / "yt_live"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="抓取 YouTube 直播最近 1 分鐘，輸出影片、音訊或逐字稿。"
    )
    parser.add_argument("url", help="YouTube 直播網址")
    parser.add_argument(
        "--mode",
        choices=["video", "audio", "transcript"],
        default="audio",
        help="輸出模式：video=影片、audio=音訊、transcript=音訊轉文字",
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=LOOKBACK_SECONDS,
        help="往前回朔秒數，預設 60 秒",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="輸出資料夾，預設為 outputs/yt_live",
    )
    parser.add_argument(
        "--base-name",
        default="",
        help="自訂輸出檔名前綴，未指定時會自動產生",
    )
    parser.add_argument(
        "--whisper-model",
        default="base",
        help="逐字稿模式下使用的 Whisper 模型名稱，預設 base",
    )
    parser.add_argument(
        "--language",
        default="zh",
        help="逐字稿語言代碼，預設 zh",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda", "auto"],
        default="cpu",
        help="逐字稿運算裝置，預設 cpu",
    )
    return parser.parse_args()


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("找不到 ffmpeg，請先安裝並加入 PATH。")


def load_yt_dlp():
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "找不到 yt_dlp 套件，請先安裝：pip install yt-dlp"
        ) from exc
    return yt_dlp


def extract_live_formats(url: str) -> dict:
    yt_dlp = load_yt_dlp()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise RuntimeError("無法取得 YouTube 資訊。")

    if "entries" in info:
        info = next((entry for entry in info["entries"] if entry), None)
        if not info:
            raise RuntimeError("播放清單中找不到可用的直播項目。")

    if not info.get("is_live"):
        print("注意：這個網址目前不像是正在直播，仍會嘗試擷取最近片段。", file=sys.stderr)

    return info


def pick_format(info: dict, mode: str) -> dict:
    formats = info.get("formats") or []
    if not formats:
        raise RuntimeError("找不到可用的串流格式。")

    if mode == "video":
        candidates = [
            fmt
            for fmt in formats
            if fmt.get("url")
            and fmt.get("vcodec") not in (None, "none")
            and fmt.get("acodec") not in (None, "none")
            and "m3u8" in str(fmt.get("protocol", "")).lower()
        ]
        sort_key = lambda fmt: (
            fmt.get("height") or 0,
            fmt.get("fps") or 0,
            fmt.get("tbr") or 0,
        )
    else:
        candidates = [
            fmt
            for fmt in formats
            if fmt.get("url")
            and fmt.get("acodec") not in (None, "none")
            and "m3u8" in str(fmt.get("protocol", "")).lower()
        ]
        sort_key = lambda fmt: (
            fmt.get("abr") or 0,
            fmt.get("asr") or 0,
            fmt.get("tbr") or 0,
        )

    if not candidates:
        candidates = [fmt for fmt in formats if fmt.get("url")]

    if not candidates:
        raise RuntimeError("找不到可直接讀取的直播串流 URL。")

    return sorted(candidates, key=sort_key, reverse=True)[0]


def fetch_playlist_segment_durations(manifest_url: str) -> list[float]:
    req = urllib.request.Request(
        manifest_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        content = response.read().decode("utf-8", errors="ignore")

    durations: list[float] = []
    for line in content.splitlines():
        if line.startswith("#EXTINF:"):
            raw_value = line.split(":", 1)[1].rstrip(",")
            try:
                durations.append(float(raw_value))
            except ValueError:
                continue

    return durations


def estimate_live_start_index(manifest_url: str, seconds: int) -> int:
    durations = fetch_playlist_segment_durations(manifest_url)
    if not durations:
        return -30

    average_duration = sum(durations) / len(durations)
    needed_segments = math.ceil(seconds / max(average_duration, 1))
    # 多抓幾個 segment，避免邊界少一小段
    return -(needed_segments + 2)


def run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg 執行失敗，exit code={completed.returncode}")


def timestamp_name(prefix: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return prefix or f"yt_live_{ts}"


def capture_video(manifest_url: str, live_start_index: int, seconds: int, output_path: Path) -> Path:
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-protocol_whitelist",
        "file,http,https,tcp,tls,crypto",
        "-live_start_index",
        str(live_start_index),
        "-i",
        manifest_url,
        "-t",
        str(seconds),
        "-c",
        "copy",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def capture_audio(manifest_url: str, live_start_index: int, seconds: int, output_path: Path) -> Path:
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-protocol_whitelist",
        "file,http,https,tcp,tls,crypto",
        "-live_start_index",
        str(live_start_index),
        "-i",
        manifest_url,
        "-t",
        str(seconds),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    run_ffmpeg(command)
    return output_path


def transcribe_audio(
    audio_path: Path,
    text_path: Path,
    model_name: str,
    language: str,
    device: str,
) -> Path:
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(model_name, device=device)
        segments, _ = model.transcribe(str(audio_path), language=language)
        text = "\n".join(segment.text.strip() for segment in segments if segment.text.strip())
    except ImportError:
        try:
            import whisper  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "逐字稿模式需要安裝 faster-whisper 或 openai-whisper。"
            ) from exc

        if device == "cuda":
            print("注意：openai-whisper 在目前腳本下未特別設定 CUDA，將依環境自行判斷。", file=sys.stderr)
        model = whisper.load_model(model_name)
        result = model.transcribe(str(audio_path), language=language)
        text = (result.get("text") or "").strip()

    text_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    return text_path


def main() -> None:
    args = parse_args()
    ensure_ffmpeg()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base_name = timestamp_name(args.base_name)

    info = extract_live_formats(args.url)
    selected_format = pick_format(info, args.mode)
    manifest_url = selected_format["url"]
    live_start_index = estimate_live_start_index(manifest_url, args.seconds)

    if args.mode == "video":
        output_path = args.output_dir / f"{base_name}.mkv"
        capture_video(manifest_url, live_start_index, args.seconds, output_path)
        print(f"已輸出影片：{output_path}")
        return

    audio_path = args.output_dir / f"{base_name}.wav"
    capture_audio(manifest_url, live_start_index, args.seconds, audio_path)
    print(f"已輸出音訊：{audio_path}")

    if args.mode == "transcript":
        text_path = args.output_dir / f"{base_name}.txt"
        print("正在轉逐字稿，這一步通常會比抓音訊久。")
        transcribe_audio(
            audio_path,
            text_path,
            args.whisper_model,
            args.language,
            args.device,
        )
        print(f"已輸出逐字稿：{text_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        sys.exit(1)
