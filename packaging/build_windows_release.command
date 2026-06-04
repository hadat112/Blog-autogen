#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Building frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
  pnpm install --frozen-lockfile
fi
pnpm build
cd ..

echo "Creating Windows release..."
rm -rf release/StoryAutogen-Windows release/StoryAutogen-Windows.zip
mkdir -p release/StoryAutogen-Windows/frontend

cp -R adapters application apps core infrastructure release/StoryAutogen-Windows/
cp prompts.txt pyproject.toml release/StoryAutogen-Windows/
cp packaging/windows/README_WINDOWS.txt packaging/windows/install_windows.bat packaging/windows/run.bat packaging/app_launcher.py release/StoryAutogen-Windows/
cp -R frontend/dist release/StoryAutogen-Windows/frontend/

cd release
zip -r StoryAutogen-Windows.zip StoryAutogen-Windows >/dev/null
cd ..

echo
echo "Done: release/StoryAutogen-Windows.zip"
echo
read -n 1 -s -r -p "Press any key to close..."
