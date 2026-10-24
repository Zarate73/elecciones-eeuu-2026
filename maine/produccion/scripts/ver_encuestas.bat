@echo off
REM Muestra las encuestas que usaria el modelo hoy (en vivo) sin correr el pronostico
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m me_pronostico encuestas %*
pause
