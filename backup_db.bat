@echo off
cd /d "%~dp0"
if not exist backups mkdir backups
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set stamp=%%c-%%a-%%b
copy /Y backend\cement_store.db backups\cement_store-%stamp%.db
 echo Backup saved in the backups folder.
pause
