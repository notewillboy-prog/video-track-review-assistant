# Codex / AI Agent Instructions

在修改项目之前，依次阅读：

1. `README.md`
2. `docs/CODEX_HANDOFF.md`
3. `docs/ARCHITECTURE.md`
4. `模型记录.md`

项目约束：

- 所有安装、运行和测试必须使用项目根目录的 `envVideoAdmire` 虚拟环境。
- 不提交视频、`review_data/`、`media_cache/`、虚拟环境、日志、密钥或本机绝对路径。
- 保持扫描/持久化/导出逻辑位于 `video_admire/`，Streamlit 页面编排位于 `app.py`。
- 修改审核记录结构时必须考虑旧 JSON 兼容性，并补充测试。
- 修改视频兼容层时必须测试 MP4V 转 H.264 和已兼容 H.264 直通路径。
- 每次代码修改后运行 `pytest` 与 `ruff check .`。
- 每次面向用户的模型回复都要把请求、改动和验证结果追加到根目录 `模型记录.md`，不得覆盖历史记录。
- 用户数据文件仅用于本地审核，不得上传或复制到第三方服务。

