@echo off
title Cement Store Billing ^& Accounts App
echo Starting Cement Store Billing ^& Accounting System...
echo Access the App at: http://localhost:8000
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
	py -3 backend\run_server.py
) else (
	python backend\run_server.py
)
pause
