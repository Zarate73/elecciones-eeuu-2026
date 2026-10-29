@echo off
REM Muestra las generales 1974-2022 (en vivo) y el backtest LOYO sin correr el pronostico
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m dc_pronostico historico %*
pause
