"""视频播放兼容性检测与按需转码。"""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg

BROWSER_CODECS = {"h264", "av1", "vp8", "vp9"}


class VideoProcessingError(RuntimeError):
    """视频无法探测或转换。"""


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    codec: str
    duration_seconds: float
    width: int
    height: int
    fps: float


@dataclass(frozen=True, slots=True)
class PlaybackVideo:
    playable_path: Path
    source_metadata: VideoMetadata
    metadata: VideoMetadata
    was_converted: bool


def inspect_video(path: Path) -> VideoMetadata:
    source = Path(path)
    if not source.is_file():
        raise VideoProcessingError(f"视频文件不存在：{source}")
    reader = imageio_ffmpeg.read_frames(str(source), pix_fmt="rgb24")
    try:
        raw = next(reader)
    except (OSError, StopIteration, RuntimeError) as exc:
        raise VideoProcessingError(f"无法读取视频元数据：{source.name}。{exc}") from exc
    finally:
        reader.close()
    size = raw.get("size", (0, 0))
    return VideoMetadata(
        codec=str(raw.get("codec", "unknown")).casefold(),
        duration_seconds=float(raw.get("duration", 0.0) or 0.0),
        width=int(size[0]),
        height=int(size[1]),
        fps=float(raw.get("fps", 0.0) or 0.0),
    )


def is_browser_compatible(path: Path, metadata: VideoMetadata) -> bool:
    suffix = Path(path).suffix.casefold()
    if suffix == ".mp4":
        return metadata.codec in {"h264", "av1"}
    if suffix == ".webm":
        return metadata.codec in {"vp8", "vp9", "av1"}
    return False


def _cache_path(source: Path, cache_root: Path) -> Path:
    stat = source.stat()
    fingerprint_source = (
        f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}|browser-h264-v1"
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:16]
    safe_stem = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in source.stem[:60]
    )
    return Path(cache_root) / f"{safe_stem}-{fingerprint}.mp4"


def _transcode_to_h264(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.stem}.tmp.mp4")
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-y",
        str(temporary),
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0 or not temporary.is_file():
            details = completed.stderr.strip()[-1200:] or "FFmpeg 未生成输出文件"
            raise VideoProcessingError(f"浏览器兼容转换失败：{source.name}。{details}")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def ensure_browser_compatible(source: Path, cache_root: Path) -> PlaybackVideo:
    source = Path(source)
    source_metadata = inspect_video(source)
    if is_browser_compatible(source, source_metadata):
        return PlaybackVideo(source, source_metadata, source_metadata, was_converted=False)

    target = _cache_path(source, cache_root)
    if target.is_file():
        cached_metadata = inspect_video(target)
        if is_browser_compatible(target, cached_metadata):
            return PlaybackVideo(target, source_metadata, cached_metadata, was_converted=True)

    _transcode_to_h264(source, target)
    converted_metadata = inspect_video(target)
    if not is_browser_compatible(target, converted_metadata):
        raise VideoProcessingError(f"转换完成，但输出仍不受浏览器支持：{target.name}")
    return PlaybackVideo(target, source_metadata, converted_metadata, was_converted=True)
