# 人工视频Track辅助

人工视频Track辅助（Video Track Review Assistant）是一个离线运行的 Streamlit 人工评测工具，用于逐个检查目标跟踪输出视频、记录问题并导出汇总。

它不会上传视频，也不包含检测、跟踪或自动质量评分模型。

## 功能

- 输入路径或通过侧边栏目录浏览器选择视频文件夹
- 扫描 MP4、MOV、AVI、MKV、WEBM、M4V、WMV，支持递归子目录
- 按文件名自然排序、修改时间或文件大小升降序排列
- 上一条、下一条和下拉列表跳转
- 快速标记“无问题”，或填写问题描述、严重程度、问题标签和备注
- 包含“目标移动出画面后重新给予新编号”等 Track 问题分类
- 提交后立即保存、断点续审、修改或撤销已有审核
- 按全部、未审核、有问题、无问题筛选，并展示进度
- 自动识别 MP4V 等浏览器不兼容编码，缓存 H.264 播放副本，不修改原视频
- 随时导出当前进度 CSV/JSON；全部审核完成后导出最终问题汇总 CSV

## 环境要求

- Python 3.11–3.13
- Windows、Linux 或 macOS
- 首次自动转码需要约 35 MB 的 `imageio-ffmpeg` 依赖

项目约定虚拟环境名称为 `envVideoAdmire`。不要把虚拟环境提交到 Git。

## 从 GitHub 本地部署

### Windows PowerShell

```powershell
git clone https://github.com/notewillboy-prog/video-track-review-assistant.git
Set-Location video-track-review-assistant
python -m venv envVideoAdmire
.\envVideoAdmire\Scripts\python.exe -m pip install --upgrade pip
.\envVideoAdmire\Scripts\python.exe -m pip install -r requirements-lock.txt
.\envVideoAdmire\Scripts\python.exe -m pytest
.\envVideoAdmire\Scripts\python.exe -m streamlit run app.py
```

也可以在环境安装完成后双击 `启动VideoAdmire.bat`，或执行：

```powershell
.\启动VideoAdmire.ps1
```

### Linux / macOS

```bash
git clone https://github.com/notewillboy-prog/video-track-review-assistant.git
cd video-track-review-assistant
python3 -m venv envVideoAdmire
./envVideoAdmire/bin/python -m pip install --upgrade pip
./envVideoAdmire/bin/python -m pip install -r requirements-lock.txt
./envVideoAdmire/bin/python -m pytest
./envVideoAdmire/bin/python -m streamlit run app.py
```

浏览器通常会自动打开 [http://localhost:8501](http://localhost:8501)。

## 使用流程

1. 在侧边栏输入视频目录，或使用目录浏览器选择目录。
2. 设置是否扫描子目录、排序方式和显示范围。
3. 播放当前视频并填写审核结论。
4. 点击“保存”或“保存并下一条”。
5. 审核完成后，在页面底部下载最终问题汇总。

若播放器显示 `0:00`，应用会检测编码并自动生成 H.264 副本。首次转换需要等待，之后会直接使用缓存。转换失败时页面会显示 FFmpeg 诊断信息。

## 数据位置

- `review_data/`：按视频根目录哈希隔离的审核 JSON
- `media_cache/`：按源文件路径、大小、修改时间生成指纹的 H.264 播放缓存
- CSV 使用 UTF-8 BOM，通常可直接用中文版 Excel 打开

这些目录均已被 `.gitignore` 排除。删除或移动原视频后，旧审核记录会进入独立的历史记录区域，不会混入当前集合的最终汇总。

## 开发与测试

Windows：

```powershell
.\envVideoAdmire\Scripts\python.exe -m pytest
.\envVideoAdmire\Scripts\python.exe -m ruff check .
```

Linux/macOS：

```bash
./envVideoAdmire/bin/python -m pytest
./envVideoAdmire/bin/python -m ruff check .
```

主要修改入口：

- 默认问题分类：`video_admire/taxonomy.py`
- 扫描、审核记录与导出：`video_admire/core.py`
- 视频兼容转换：`video_admire/media.py`
- Streamlit 页面：`app.py`

供 Codex 或其他 AI 编程代理接管时，先阅读 `AGENTS.md` 和 `docs/CODEX_HANDOFF.md`。架构和数据流见 `docs/ARCHITECTURE.md`，贡献约定见 `CONTRIBUTING.md`。

## GitHub 参考

- [Streamlit](https://github.com/streamlit/streamlit)：页面、状态管理和视频播放
- [OpenVidReview](https://github.com/davidguva/OpenVidReview)：视频评论、标签、编辑和导出思路
- [Storia-AI/image-eval](https://github.com/Storia-AI/image-eval)：本地模型输出人工评估流程

本项目仅吸收适合离线、单人 Track 结果审核的交互，不包含账号系统或联网协作。

## 许可证

[MIT](LICENSE)
