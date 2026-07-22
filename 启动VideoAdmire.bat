@echo off
setlocal
cd /d "%~dp0"
if not exist "envVideoAdmire\Scripts\python.exe" (
  echo [ERROR] envVideoAdmire not found. Please follow README.md first.
  pause
  exit /b 1
)
"envVideoAdmire\Scripts\python.exe" -m streamlit run app.py

