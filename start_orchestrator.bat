@echo off
title TaskShift - Control Room (API)
color 0B
echo ==================================================
echo      Iniciando TaskShift Control Room...
echo ==================================================
cd /d "%~dp0"

:: Se usar ambiente virtual (venv), remova o "::" da linha abaixo
:: call venv\Scripts\activate

uvicorn api.main:app --host 0.0.0.0 --port 8000
pause