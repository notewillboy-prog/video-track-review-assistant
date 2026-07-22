import subprocess
from pathlib import Path

import imageio_ffmpeg

from video_admire.media import (
    ensure_browser_compatible,
    inspect_video,
    is_browser_compatible,
)


def create_video(path: Path, codec: str) -> Path:
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=160x120:rate=10",
        "-t",
        "0.5",
        "-c:v",
        codec,
        "-pix_fmt",
        "yuv420p",
        "-y",
        str(path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return path


def test_mp4v_is_detected_as_browser_incompatible(tmp_path: Path) -> None:
    source = create_video(tmp_path / "opencv.mp4", "mpeg4")

    metadata = inspect_video(source)

    assert metadata.codec == "mpeg4"
    assert metadata.duration_seconds > 0
    assert not is_browser_compatible(source, metadata)


def test_incompatible_video_is_transcoded_to_cached_h264(tmp_path: Path) -> None:
    source = create_video(tmp_path / "opencv.mp4", "mpeg4")
    cache = tmp_path / "cache"

    result = ensure_browser_compatible(source, cache)
    cached_mtime = result.playable_path.stat().st_mtime_ns
    repeated = ensure_browser_compatible(source, cache)

    assert result.was_converted
    assert result.playable_path != source
    assert result.playable_path.exists()
    assert result.metadata.codec == "h264"
    assert is_browser_compatible(result.playable_path, result.metadata)
    assert repeated.playable_path == result.playable_path
    assert repeated.playable_path.stat().st_mtime_ns == cached_mtime


def test_h264_mp4_is_used_without_conversion(tmp_path: Path) -> None:
    source = create_video(tmp_path / "browser-ready.mp4", "libx264")

    result = ensure_browser_compatible(source, tmp_path / "cache")

    assert not result.was_converted
    assert result.playable_path == source
    assert result.metadata.codec == "h264"
