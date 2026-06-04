@echo off
cd /d "%~dp0\.."
title Build Story Autogen Windows Release

echo Building frontend...
cd frontend
if not exist node_modules (
  npm install
)
npm run build
if errorlevel 1 (
  echo Frontend build failed.
  pause
  exit /b 1
)
cd ..

echo Creating release folder...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$release='release';" ^
  "$dest=Join-Path $release 'StoryAutogen-Windows';" ^
  "Remove-Item $release -Recurse -Force -ErrorAction SilentlyContinue;" ^
  "New-Item -ItemType Directory -Path $dest | Out-Null;" ^
  "$items=@('adapters','application','apps','core','infrastructure','prompts.txt','pyproject.toml');" ^
  "foreach($item in $items){ Copy-Item $item -Destination $dest -Recurse -Force };" ^
  "Copy-Item 'packaging\windows\README_WINDOWS.txt' -Destination $dest -Force;" ^
  "Copy-Item 'packaging\windows\run.bat' -Destination $dest -Force;" ^
  "Copy-Item 'packaging\windows\install_windows.bat' -Destination $dest -Force;" ^
  "Copy-Item 'packaging\app_launcher.py' -Destination $dest -Force;" ^
  "New-Item -ItemType Directory -Path (Join-Path $dest 'frontend') | Out-Null;" ^
  "Copy-Item 'frontend\dist' -Destination (Join-Path $dest 'frontend') -Recurse -Force;" ^
  "Compress-Archive -Path $dest -DestinationPath (Join-Path $release 'StoryAutogen-Windows.zip') -Force;"

echo.
echo Done: release\StoryAutogen-Windows.zip
pause
