@echo off
title TaskShift - Worker Agent
color 0A
echo ==================================================
echo      Iniciando TaskShift Worker Agent...
echo ==================================================
cd /d "%~dp0"

:: Se usar ambiente virtual (venv), remova o "::" da linha abaixo
:: call venv\Scripts\activate

python agents\worker.py
pause