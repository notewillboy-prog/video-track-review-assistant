$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ProjectRoot "envVideoAdmire\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "未找到 envVideoAdmire。请先按 README.md 创建虚拟环境并安装依赖。"
}

Set-Location -LiteralPath $ProjectRoot
& $PythonPath -m streamlit run app.py

