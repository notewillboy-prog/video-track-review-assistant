import csv
import json
from pathlib import Path

import pytest

from video_admire.core import (
    Review,
    ReviewStore,
    export_csv_bytes,
    export_json_bytes,
    filter_videos,
    scan_videos,
    summarize,
)


def touch(path: Path, content: bytes = b"video") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_scan_videos_supports_natural_name_sort_and_extensions(tmp_path: Path) -> None:
    touch(tmp_path / "track10.mp4")
    touch(tmp_path / "track2.MOV")
    touch(tmp_path / "notes.txt")

    videos = scan_videos(tmp_path, recursive=False, sort_by="name", descending=False)

    assert [video.name for video in videos] == ["track2.MOV", "track10.mp4"]


def test_scan_videos_can_recurse_and_rejects_invalid_folder(tmp_path: Path) -> None:
    touch(tmp_path / "nested" / "clip.webm")

    assert scan_videos(tmp_path, recursive=False) == []
    assert [item.relative_path for item in scan_videos(tmp_path, recursive=True)] == [
        "nested/clip.webm"
    ]
    with pytest.raises(ValueError, match="不存在"):
        scan_videos(tmp_path / "missing")


def test_name_sort_uses_file_name_before_parent_folder(tmp_path: Path) -> None:
    touch(tmp_path / "z_folder" / "clip2.mp4")
    touch(tmp_path / "a_folder" / "clip10.mp4")

    videos = scan_videos(tmp_path, recursive=True, sort_by="name")

    assert [item.name for item in videos] == ["clip2.mp4", "clip10.mp4"]


def test_review_store_round_trip_and_update(tmp_path: Path) -> None:
    store = ReviewStore(tmp_path / "reviews.json", root_folder=tmp_path / "videos")
    review = Review(
        video_id="a.mp4",
        video_name="a.mp4",
        relative_path="a.mp4",
        status="issue",
        issue_description="目标漂移",
        severity="严重",
        tags=["漂移", "遮挡"],
        notes="第 30 帧附近",
    )

    store.save(review)
    loaded = ReviewStore(tmp_path / "reviews.json", root_folder=tmp_path / "videos")

    assert loaded.get("a.mp4") == review
    loaded.save(review.with_updates(issue_description="目标丢失"))
    assert ReviewStore(tmp_path / "reviews.json").get("a.mp4").issue_description == "目标丢失"


def test_issue_review_requires_description() -> None:
    with pytest.raises(ValueError, match="问题描述"):
        Review(
            video_id="a.mp4",
            video_name="a.mp4",
            relative_path="a.mp4",
            status="issue",
        )


def test_filter_and_summary(tmp_path: Path) -> None:
    videos = [
        touch(tmp_path / "a.mp4"),
        touch(tmp_path / "b.mp4"),
        touch(tmp_path / "c.mp4"),
    ]
    scanned = scan_videos(tmp_path)
    reviews = {
        "a.mp4": Review("a.mp4", "a.mp4", "a.mp4", "ok"),
        "b.mp4": Review("b.mp4", "b.mp4", "b.mp4", "issue", "闪烁"),
    }

    assert videos  # Ensure files remain alive for platforms with eager cleanup.
    assert [item.name for item in filter_videos(scanned, reviews, "未审核")] == ["c.mp4"]
    assert [item.name for item in filter_videos(scanned, reviews, "有问题")] == ["b.mp4"]
    assert summarize(scanned, reviews) == {
        "total": 3,
        "reviewed": 2,
        "ok": 1,
        "issue": 1,
        "pending": 1,
        "progress": pytest.approx(2 / 3),
    }


def test_exports_include_video_name_and_issue(tmp_path: Path) -> None:
    reviews = [
        Review("b.mp4", "b.mp4", "nested/b.mp4", "issue", "框抖动", "一般", ["抖动"]),
        Review("a.mp4", "a.mp4", "a.mp4", "ok"),
    ]

    csv_text = export_csv_bytes(reviews).decode("utf-8-sig")
    rows = list(csv.DictReader(csv_text.splitlines()))
    json_rows = json.loads(export_json_bytes(reviews).decode("utf-8"))

    assert rows[0]["视频名"] == "a.mp4"
    assert rows[1]["问题描述"] == "框抖动"
    assert json_rows[1]["video_name"] == "b.mp4"
