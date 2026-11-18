@echo off
rem Abre la pagina de alertas en el navegador (uso local).
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% -c "import streamlit" >nul 2>nul || %PY% -m pip install -r requirements.txt
%PY% -m streamlit run app.py
if errorlevel 1 pause
