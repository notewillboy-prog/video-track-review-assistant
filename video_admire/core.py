"""与 Streamlit 页面解耦的扫描、审核、持久化和导出逻辑。"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv"}
ReviewStatus = Literal["ok", "issue"]


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def natural_key(value: str) -> list[tuple[int, int | str]]:
    """返回不混合比较 int/str 的自然排序键。"""
    parts = re.split(r"(\d+)", value.casefold())
    return [(1, int(part)) if part.isdigit() else (0, part) for part in parts]


@dataclass(frozen=True, slots=True)
class VideoFile:
    video_id: str
    name: str
    relative_path: str
    absolute_path: Path
    size_bytes: int
    modified_at: float


@dataclass(frozen=True, slots=True)
class Review:
    video_id: str
    video_name: str
    relative_path: str
    status: ReviewStatus
    issue_description: str = ""
    severity: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    reviewed_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        if self.status not in {"ok", "issue"}:
            raise ValueError("审核状态必须是 ok 或 issue")
        if self.status == "issue" and not self.issue_description.strip():
            raise ValueError("标记为有问题时必须填写问题描述")
        if self.status == "ok" and self.issue_description:
            object.__setattr__(self, "issue_description", "")
        object.__setattr__(self, "tags", sorted(set(self.tags), key=natural_key))

    def with_updates(self, **changes: Any) -> Review:
        changes.setdefault("reviewed_at", _now_iso())
        return replace(self, **changes)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Review:
        allowed = {field_name for field_name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in allowed})


class ReviewStore:
    """JSON 审核记录仓库；每次写入采用同目录原子替换。"""

    def __init__(self, path: Path, root_folder: Path | None = None) -> None:
        self.path = Path(path)
        self.root_folder = str(Path(root_folder).resolve()) if root_folder else ""
        self.reviews: dict[str, Review] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"无法读取审核记录 {self.path}: {exc}") from exc
        self.root_folder = payload.get("root_folder", self.root_folder)
        raw_reviews = payload.get("reviews", [])
        self.reviews = {
            item["video_id"]: Review.from_dict(item)
            for item in raw_reviews
            if isinstance(item, dict) and item.get("video_id")
        }

    def get(self, video_id: str) -> Review | None:
        return self.reviews.get(video_id)

    def save(self, review: Review) -> None:
        self.reviews[review.video_id] = review
        self._flush()

    def delete(self, video_id: str) -> None:
        if self.reviews.pop(video_id, None) is not None:
            self._flush()

    def all(self) -> list[Review]:
        return sorted(self.reviews.values(), key=lambda item: natural_key(item.relative_path))

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "root_folder": self.root_folder,
            "updated_at": _now_iso(),
            "reviews": [asdict(review) for review in self.all()],
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.path)


def scan_videos(
    folder: Path,
    *,
    recursive: bool = False,
    sort_by: str = "name",
    descending: bool = False,
) -> list[VideoFile]:
    root = Path(folder).expanduser()
    if not root.is_dir():
        raise ValueError(f"文件夹不存在或不可访问：{root}")
    paths = root.rglob("*") if recursive else root.glob("*")
    videos: list[VideoFile] = []
    for path in paths:
        if not path.is_file() or path.suffix.casefold() not in VIDEO_EXTENSIONS:
            continue
        stat = path.stat()
        relative_path = path.relative_to(root).as_posix()
        videos.append(
            VideoFile(
                video_id=relative_path,
                name=path.name,
                relative_path=relative_path,
                absolute_path=path.resolve(),
                size_bytes=stat.st_size,
                modified_at=stat.st_mtime,
            )
        )
    key_functions = {
        "name": lambda item: (natural_key(item.name), natural_key(item.relative_path)),
        "modified": lambda item: item.modified_at,
        "size": lambda item: item.size_bytes,
    }
    if sort_by not in key_functions:
        raise ValueError(f"不支持的排序字段：{sort_by}")
    return sorted(videos, key=key_functions[sort_by], reverse=descending)


def filter_videos(
    videos: list[VideoFile], reviews: dict[str, Review], status_filter: str
) -> list[VideoFile]:
    if status_filter == "全部":
        return videos
    if status_filter == "未审核":
        return [video for video in videos if video.video_id not in reviews]
    if status_filter == "有问题":
        return [
            video
            for video in videos
            if (review := reviews.get(video.video_id)) and review.status == "issue"
        ]
    if status_filter == "无问题":
        return [
            video
            for video in videos
            if (review := reviews.get(video.video_id)) and review.status == "ok"
        ]
    raise ValueError(f"不支持的筛选条件：{status_filter}")


def summarize(videos: list[VideoFile], reviews: dict[str, Review]) -> dict[str, int | float]:
    video_ids = {video.video_id for video in videos}
    current = [review for video_id, review in reviews.items() if video_id in video_ids]
    ok_count = sum(review.status == "ok" for review in current)
    issue_count = sum(review.status == "issue" for review in current)
    reviewed = ok_count + issue_count
    total = len(videos)
    return {
        "total": total,
        "reviewed": reviewed,
        "ok": ok_count,
        "issue": issue_count,
        "pending": max(total - reviewed, 0),
        "progress": reviewed / total if total else 0.0,
    }


def _review_rows(reviews: list[Review]) -> list[dict[str, str]]:
    return [
        {
            "视频名": review.video_name,
            "相对路径": review.relative_path,
            "审核结论": "有问题" if review.status == "issue" else "无问题",
            "严重程度": review.severity,
            "问题标签": ";".join(review.tags),
            "问题描述": review.issue_description,
            "备注": review.notes,
            "审核时间": review.reviewed_at,
        }
        for review in sorted(reviews, key=lambda item: natural_key(item.relative_path))
    ]


def export_csv_bytes(reviews: list[Review]) -> bytes:
    columns = [
        "视频名",
        "相对路径",
        "审核结论",
        "严重程度",
        "问题标签",
        "问题描述",
        "备注",
        "审核时间",
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(_review_rows(reviews))
    return buffer.getvalue().encode("utf-8-sig")


def export_json_bytes(reviews: list[Review]) -> bytes:
    payload = [
        asdict(review)
        for review in sorted(reviews, key=lambda item: natural_key(item.relative_path))
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
