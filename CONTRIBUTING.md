# 贡献指南

## 开发环境

要求 Python 3.11–3.13。虚拟环境固定命名为 `envVideoAdmire`：

```powershell
python -m venv envVideoAdmire
.\envVideoAdmire\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Linux/macOS：

```bash
python3 -m venv envVideoAdmire
./envVideoAdmire/bin/python -m pip install -r requirements-lock.txt
```

## 修改流程

1. 阅读 `docs/CODEX_HANDOFF.md` 和 `docs/ARCHITECTURE.md`。
2. 为行为变化增加或更新测试。
3. 保持核心逻辑与 Streamlit UI 解耦。
4. 运行完整检查。

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

提交中不得包含真实审核视频、审核结果、媒体缓存或凭据。

