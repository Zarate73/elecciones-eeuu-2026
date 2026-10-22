@echo off
REM Florida - corrida. Acepta las opciones de la CLI:
REM   correr_pronostico.bat              (normal, fuentes en vivo)
REM   correr_pronostico.bat --offline    (solo caches)
REM   correr_pronostico.bat --estricto   (codigo 2 si alguna fuente no estuvo en vivo)
setlocal
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo No existe .venv. Ejecuta primero scripts\instalar.bat
  exit /b 1
)
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m fl_pronostico correr %*
set RC=%ERRORLEVEL%
if "%RC%"=="0" (echo Corrida OK. Resultados en salidas\ultimo) else (echo Corrida termino con codigo %RC%. Revisa logs\pronostico.log)
exit /b %RC%
