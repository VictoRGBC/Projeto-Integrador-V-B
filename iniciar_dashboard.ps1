# Script auxiliar para iniciar o Dashboard Streamlit do Projeto Integrador V - B
$ErrorActionPreference = "Stop"

$AppDataPythonDir = "C:\Users\INTEGRA\AppData\Local\Programs\Python\Python315"
$RootPythonExe = "C:\Python315\python.exe"
$AppDataPythonExe = Join-Path $AppDataPythonDir "python.exe"

if (Test-Path $AppDataPythonExe) {
    & $AppDataPythonExe -m streamlit run dashboard/app.py
} elseif ((Test-Path $RootPythonExe) -and (Test-Path (Join-Path $AppDataPythonDir "Lib"))) {
    # Caso o python.exe esteja em C:\Python315 e a pasta Lib em AppData
    $env:PYTHONHOME = $AppDataPythonDir
    & $RootPythonExe -m streamlit run dashboard/app.py
} else {
    python -m streamlit run dashboard/app.py
}
