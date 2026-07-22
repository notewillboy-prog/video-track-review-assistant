"""Video Admire 的 Streamlit 页面入口。"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import streamlit as st

from video_admire.core import (
    Review,
    ReviewStore,
    export_csv_bytes,
    export_json_bytes,
    filter_videos,
    scan_videos,
    summarize,
)
from video_admire.media import PlaybackVideo, VideoProcessingError, ensure_browser_compatible
from video_admire.taxonomy import DEFAULT_ISSUE_TAGS

st.set_page_config(page_title="人工视频Track辅助", page_icon="🎬", layout="wide")

SORT_FIELDS = {"文件名（自然排序）": "name", "修改时间": "modified", "文件大小": "size"}


def data_path_for(folder: Path) -> Path:
    identity = hashlib.sha256(str(folder.resolve()).casefold().encode("utf-8")).hexdigest()[:16]
    return Path(__file__).parent / "review_data" / f"{identity}.json"


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


@st.cache_data(max_entries=256, show_spinner=False)
def prepare_playback(
    source_path: str, source_size: int, source_mtime: float, cache_folder: str
) -> PlaybackVideo:
    del source_size, source_mtime  # 参与缓存键；文件变化时自动重新处理。
    return ensure_browser_compatible(Path(source_path), Path(cache_folder))


def go_to(video_id: str) -> None:
    st.session_state.current_video_id = video_id


def choose_folder(path: str) -> None:
    st.session_state.folder_input = path


def directory_browser() -> None:
    with st.sidebar.expander("📁 可视化选择文件夹"):
        browse = Path(st.session_state.get("browse_path", Path.cwd()))
        if not browse.is_dir():
            browse = Path.cwd()
        st.caption(f"当前浏览：{browse}")
        col_parent, col_use = st.columns(2)
        if col_parent.button("⬆ 上级", width="stretch", disabled=browse.parent == browse):
            st.session_state.browse_path = str(browse.parent)
            st.rerun()
        col_use.button(
            "使用此目录",
            type="primary",
            width="stretch",
            on_click=choose_folder,
            args=(str(browse),),
        )
        try:
            children = sorted(
                [item for item in browse.iterdir() if item.is_dir()],
                key=lambda item: item.name.casefold(),
            )
        except OSError:
            children = []
        choice = st.selectbox("进入子目录", ["请选择…", *[item.name for item in children]])
        if choice != "请选择…" and st.button("进入", width="stretch"):
            st.session_state.browse_path = str(browse / choice)
            st.rerun()


def advance(visible_ids: list[str], current_id: str) -> None:
    if not visible_ids:
        return
    try:
        index = visible_ids.index(current_id)
    except ValueError:
        index = -1
    st.session_state.current_video_id = visible_ids[min(index + 1, len(visible_ids) - 1)]


def render_exports(store: ReviewStore, video_ids: set[str], pending: int) -> None:
    st.divider()
    st.subheader("汇总与导出")
    current_reviews = [review for review in store.all() if review.video_id in video_ids]
    issue_reviews = [review for review in current_reviews if review.status == "issue"]
    final_ready = bool(video_ids) and pending == 0
    export_col1, export_col2, export_col3 = st.columns(3)
    export_col1.download_button(
        "下载当前审核进度 CSV",
        data=export_csv_bytes(current_reviews),
        file_name="video_admire_current_reviews.csv",
        mime="text/csv",
        width="stretch",
        disabled=not current_reviews,
    )
    export_col2.download_button(
        "下载最终问题汇总 CSV",
        data=export_csv_bytes(issue_reviews),
        file_name="video_admire_issues.csv",
        mime="text/csv",
        width="stretch",
        disabled=not final_ready,
        help="当前文件夹全部视频审核完成后启用",
    )
    export_col3.download_button(
        "下载当前审核进度 JSON",
        data=export_json_bytes(current_reviews),
        file_name="video_admire_current_reviews.json",
        mime="application/json",
        width="stretch",
        disabled=not current_reviews,
    )
    if video_ids and pending:
        st.info(f"还有 {pending} 个视频未审核；完成后即可下载最终问题汇总。")
    if issue_reviews:
        st.dataframe(
            [
                {
                    "视频名": item.video_name,
                    "相对路径": item.relative_path,
                    "严重程度": item.severity,
                    "问题标签": "、".join(item.tags),
                    "问题描述": item.issue_description,
                    "备注": item.notes,
                }
                for item in issue_reviews
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("当前视频集合中没有标记为有问题的视频。")

    historical_reviews = [review for review in store.all() if review.video_id not in video_ids]
    if historical_reviews:
        with st.expander(f"历史记录（当前文件夹中已找不到 {len(historical_reviews)} 个视频）"):
            st.warning("这些记录不计入当前进度和最终问题汇总，可单独备份后再决定是否保留。")
            history_csv, history_json = st.columns(2)
            history_csv.download_button(
                "下载历史记录 CSV",
                data=export_csv_bytes(historical_reviews),
                file_name="video_admire_missing_video_history.csv",
                mime="text/csv",
                width="stretch",
            )
            history_json.download_button(
                "下载历史记录 JSON",
                data=export_json_bytes(historical_reviews),
                file_name="video_admire_missing_video_history.json",
                mime="application/json",
                width="stretch",
            )


st.title("🎬 人工视频Track辅助")
st.caption("面向视频 Track 结果的本地人工评测工具 · 提交审核后立即保存")

if "folder_input" not in st.session_state:
    st.session_state.folder_input = str(Path.cwd())
with st.sidebar:
    st.header("视频来源")
    st.text_input("视频文件夹路径", key="folder_input")
directory_browser()

with st.sidebar:
    recursive = st.checkbox("包含子文件夹", value=True)
    sort_label = st.selectbox("排序方式", list(SORT_FIELDS))
    descending = st.toggle("降序", value=False)
    status_filter = st.radio("显示范围", ["全部", "未审核", "有问题", "无问题"])

folder = Path(st.session_state.folder_input).expanduser()
try:
    videos = scan_videos(
        folder,
        recursive=recursive,
        sort_by=SORT_FIELDS[sort_label],
        descending=descending,
    )
    store = ReviewStore(data_path_for(folder), root_folder=folder)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

stats = summarize(videos, store.reviews)
with st.sidebar:
    st.header("审核进度")
    st.progress(float(stats["progress"]), text=f'{stats["reviewed"]} / {stats["total"]}')
    col_ok, col_issue, col_pending = st.columns(3)
    col_ok.metric("无问题", stats["ok"])
    col_issue.metric("有问题", stats["issue"])
    col_pending.metric("待审核", stats["pending"])
    st.caption(f"记录文件：{store.path}")

visible_videos = filter_videos(videos, store.reviews, status_filter)
if not videos:
    st.info("该文件夹中没有支持的视频。支持 MP4、MOV、AVI、MKV、WEBM、M4V、WMV。")
    render_exports(store, set(), int(stats["pending"]))
    st.stop()
if not visible_videos:
    st.success(f'“{status_filter}”范围内没有视频。可切换左侧显示范围。')
    render_exports(store, {video.video_id for video in videos}, int(stats["pending"]))
    st.stop()

visible_ids = [video.video_id for video in visible_videos]
current_id = st.session_state.get("current_video_id")
if current_id not in visible_ids:
    current_id = visible_ids[0]
    st.session_state.current_video_id = current_id
current_index = visible_ids.index(current_id)
current = visible_videos[current_index]
existing = store.get(current.video_id)

nav_left, nav_select, nav_right = st.columns([1, 4, 1])
if nav_left.button("⬅ 上一个", width="stretch", disabled=current_index == 0):
    go_to(visible_ids[current_index - 1])
    st.rerun()
selected_id = nav_select.selectbox(
    "跳转到视频",
    visible_ids,
    index=current_index,
    format_func=lambda video_id: (
        f"{visible_ids.index(video_id) + 1}/{len(visible_ids)} · {video_id}"
    ),
)
if selected_id != current_id:
    go_to(selected_id)
    st.rerun()
if nav_right.button(
    "下一个 ➡",
    width="stretch",
    disabled=current_index == len(visible_ids) - 1,
):
    go_to(visible_ids[current_index + 1])
    st.rerun()

video_col, review_col = st.columns([3, 2], gap="large")
with video_col:
    st.subheader(current.name)
    cache_folder = Path(__file__).parent / "media_cache" / data_path_for(folder).stem
    try:
        with st.spinner("正在检查视频编码；不兼容时自动生成 H.264 播放副本…"):
            playback = prepare_playback(
                str(current.absolute_path),
                current.size_bytes,
                current.modified_at,
                str(cache_folder),
            )
    except VideoProcessingError as exc:
        st.error("该视频文件无法读取或转换。")
        st.code(str(exc), language=None)
    else:
        video_format = (
            "video/webm"
            if playback.playable_path.suffix.casefold() == ".webm"
            else "video/mp4"
        )
        st.video(playback.playable_path, format=video_format)
        if playback.was_converted:
            st.success(
                f"检测到原视频编码为 {playback.source_metadata.codec.upper()}；"
                "已自动缓存 H.264 播放副本，原文件未被修改。"
            )
    modified = datetime.fromtimestamp(current.modified_at).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(
        f"路径：{current.relative_path}　|　"
        f"大小：{format_size(current.size_bytes)}　|　修改：{modified}"
    )

with review_col:
    st.subheader("审核结论")
    if existing:
        conclusion = "有问题" if existing.status == "issue" else "无问题"
        st.info(f"当前记录：{conclusion} · {existing.reviewed_at}")

    if st.button("✅ 无问题并进入下一个", type="primary", width="stretch"):
        store.save(
            Review(
                video_id=current.video_id,
                video_name=current.name,
                relative_path=current.relative_path,
                status="ok",
                notes=existing.notes if existing else "",
            )
        )
        advance(visible_ids, current.video_id)
        st.rerun()

    status_options = ["有问题", "无问题"]
    default_status = 0 if not existing or existing.status == "issue" else 1
    with st.form(f"review_form_{current.video_id}", clear_on_submit=False):
        status_label = st.radio("结论", status_options, index=default_status, horizontal=True)
        issue_description = st.text_area(
            "问题描述（有问题时必填）",
            value=existing.issue_description if existing else "",
            placeholder="例如：第 120 帧后目标框漂移到相邻目标",
        )
        severity_options = ["轻微", "一般", "严重"]
        severity_index = (
            severity_options.index(existing.severity)
            if existing and existing.severity in severity_options
            else 1
        )
        severity = st.select_slider(
            "严重程度", severity_options, value=severity_options[severity_index]
        )
        tags = st.multiselect(
            "问题标签", DEFAULT_ISSUE_TAGS, default=existing.tags if existing else []
        )
        notes = st.text_area("补充备注（可选）", value=existing.notes if existing else "")
        save_only, save_next = st.columns(2)
        submitted_only = save_only.form_submit_button("保存", width="stretch")
        submitted_next = save_next.form_submit_button("保存并下一条", width="stretch")

    if submitted_only or submitted_next:
        try:
            review = Review(
                video_id=current.video_id,
                video_name=current.name,
                relative_path=current.relative_path,
                status="issue" if status_label == "有问题" else "ok",
                issue_description=issue_description.strip(),
                severity=severity if status_label == "有问题" else "",
                tags=tags if status_label == "有问题" else [],
                notes=notes.strip(),
            )
            store.save(review)
        except ValueError as exc:
            st.error(str(exc))
        else:
            if submitted_next:
                advance(visible_ids, current.video_id)
            st.rerun()

    if existing and st.button("🗑 撤销当前审核", width="stretch"):
        store.delete(current.video_id)
        st.rerun()

render_exports(store, {video.video_id for video in videos}, int(stats["pending"]))
