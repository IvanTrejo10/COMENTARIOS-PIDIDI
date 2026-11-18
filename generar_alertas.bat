@echo off
rem Genera las alertas sin abrir la pagina (linea de comandos).
rem   - Arrastra los PDF (Mexico y LATAM) sobre este archivo, o
rem   - dale doble clic y toma los PDF mas recientes de la carpeta.
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% alertas_cobranza.py %*
if errorlevel 1 (
  echo.
  echo No se generaron las alertas. Revisa el mensaje de arriba.
  pause
)
