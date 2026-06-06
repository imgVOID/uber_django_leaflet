@echo off
cd /d %~dp0
echo Stopping and removing containers...
docker compose down
echo Done.
exit /b 0
