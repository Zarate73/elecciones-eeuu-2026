@echo off
REM Georgia - instalacion (una sola vez)
setlocal
cd /d "%~dp0.."
where py >nul 2>&1 && (set PY=py -3) || (set PY=python)
echo Creando entorno virtual .venv ...
%PY% -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :error
echo.
echo Pruebas automaticas (sin red):
python -m pytest -q || goto :error
echo.
echo Verificando fuentes en vivo:
python -m ga_pronostico verificar
echo.
echo Instalacion terminada. Para correr: scripts\correr_pronostico.bat
exit /b 0
:error
echo ERROR durante la instalacion.
exit /b 1
