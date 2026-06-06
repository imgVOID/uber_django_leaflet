@echo off
cd /d %~dp0
echo Starting containers...

REM Build only if changes detected, without checking remote registry every time
docker compose up -d --build

if %errorlevel% neq 0 (
  echo Docker compose failed. Ensure Docker Desktop is running.
  pause
  exit /b %errorlevel%
)

echo Containers started.
echo Waiting for web service to be ready...

:loop
REM -s for silent, -f to fail on HTTP errors, output redirected to nul
curl -sf http://localhost:8000/ >nul
if %errorlevel% neq 0 (
  timeout /t 1 /nobreak >nul
  goto loop
)

echo Opening http://localhost:8000/
start http://localhost:8000/
exit /b 0