@echo off
rem Instala lo necesario (Streamlit y PyMuPDF). Solo hace falta una vez.
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% -m pip install -r requirements.txt
echo.
echo Listo. Abre la pagina con abrir_pagina.bat
pause
