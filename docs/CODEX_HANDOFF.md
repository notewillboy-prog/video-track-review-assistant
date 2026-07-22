# Codex 项目交接文档

本文档供新的 Codex/AI 编程代理在没有原始对话的情况下接管项目。

## 项目目标

“人工视频Track辅助”是一个离线、单用户的 Streamlit 工具，用于人工检查目标跟踪输出视频。输入是本地视频目录；输出是本地 JSON 审核状态，以及可下载的 CSV/JSON 汇总。它不是检测器、跟踪器或自动评分模型。

## 快速恢复

1. 确认 Python 版本为 3.11–3.13。
2. 创建根目录虚拟环境 `envVideoAdmire`。
3. 使用 `requirements-lock.txt` 安装可复现依赖。
4. 运行测试和 Ruff。
5. 启动 `app.py`，使用测试视频目录做一次审核和导出。

具体命令见根目录 `README.md`。

## 当前功能基线

- 支持 MP4、MOV、AVI、MKV、WEBM、M4V、WMV，允许递归扫描。
- 支持文件名自然排序、修改时间/大小排序及升降序。
- 支持前后导航、下拉跳转、状态筛选和审核进度。
- 支持问题描述、严重程度、多问题标签和备注。
- 默认问题分类位于 `video_admire/taxonomy.py`，包括“目标移动出画面后重新给予新编号”。
- 审核提交后立即写入 `review_data/<folder-hash>.json`。
- MP4V 等浏览器不兼容视频会自动转换并缓存 H.264 副本。
- 可随时备份当前进度；当前集合全部完成后启用最终问题 CSV。

## 最常见修改

### 增加问题分类

修改 `video_admire/taxonomy.py` 的 `DEFAULT_ISSUE_TAGS`，再更新 `tests/test_taxonomy.py`。已有 JSON 记录中的旧标签不会被删除。

### 修改审核字段

修改 `Review` 数据类、`Review.from_dict`、`_review_rows` 和相关测试。读取旧数据时只能忽略未知字段或提供默认值，不能让旧记录无法加载。

### 增加视频格式

先更新 `core.py` 的 `VIDEO_EXTENSIONS`，再决定 `media.py` 是允许浏览器直通还是统一转 H.264，并为两条路径添加测试。

## 数据与隐私

- 应用不需要联网，也没有账号系统。
- 视频、审核 JSON、媒体缓存都被 `.gitignore` 排除。
- 不要把真实数据写入测试夹具；媒体测试应继续用 FFmpeg 动态生成短视频。
- 公共提交前运行敏感信息和大文件检查。

## 完成定义

- `pytest` 全部通过。
- `ruff check .` 通过。
- Streamlit 健康端点返回 200。
- 至少验证一个浏览器兼容视频和一个 MP4V 自动转换视频。
- 更新 README/交接文档与 `模型记录.md`。

