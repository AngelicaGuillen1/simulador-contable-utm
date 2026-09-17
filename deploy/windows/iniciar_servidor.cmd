@echo off
REM ---------------------------------------------------------------------------
REM  Arranque del Simulador Contable con el servidor de produccion (waitress).
REM  Lo usa la tarea programada de Windows para mantener el servicio 24/7.
REM  Las variables sensibles (SECRET_KEY) se leen de entorno.local.cmd, que
REM  genera el instalador y NO se versiona en el repositorio.
REM ---------------------------------------------------------------------------
setlocal
set "PROYECTO=%~dp0..\.."
pushd "%PROYECTO%"

if exist "%~dp0entorno.local.cmd" call "%~dp0entorno.local.cmd"

if not defined HOST set "HOST=0.0.0.0"
if not defined PORT set "PORT=8080"
if not defined DATABASE_PATH set "DATABASE_PATH=%PROYECTO%\database\simulator.db"
if not defined THREADS set "THREADS=8"

if not exist "logs" mkdir "logs"

echo [%date% %time%] Iniciando Simulador Contable en %HOST%:%PORT% >> "logs\servidor.log"
".venv\Scripts\python.exe" serve.py >> "logs\servidor.log" 2>&1
echo [%date% %time%] El servidor finalizo con codigo %ERRORLEVEL% >> "logs\servidor.log"

popd
endlocal
