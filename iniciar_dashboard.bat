@echo off
set "APPDATA_PY=C:\Users\INTEGRA\AppData\Local\Programs\Python\Python315"
set "ROOT_PY=C:\Python315\python.exe"

if exist "%APPDATA_PY%\python.exe" (
    "%APPDATA_PY%\python.exe" -m streamlit run dashboard/app.py
) else if exist "%ROOT_PY%" (
    set "PYTHONHOME=%APPDATA_PY%"
    "%ROOT_PY%" -m streamlit run dashboard/app.py
) else (
    python -m streamlit run dashboard/app.py
)
