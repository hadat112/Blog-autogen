#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Building frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
  npm install
fi
npm run build
cd ..

echo "Creating Mac release..."
rm -rf release
mkdir -p release/StoryAutogen-Mac/frontend

cp -R adapters application apps core infrastructure release/StoryAutogen-Mac/
cp prompts.txt pyproject.toml release/StoryAutogen-Mac/
cp packaging/mac/README_MAC.txt packaging/mac/install_mac.command packaging/mac/run_mac.command packaging/app_launcher.py release/StoryAutogen-Mac/
cp -R frontend/dist release/StoryAutogen-Mac/frontend/

chmod +x release/StoryAutogen-Mac/install_mac.command
chmod +x release/StoryAutogen-Mac/run_mac.command

cd release
zip -r StoryAutogen-Mac.zip StoryAutogen-Mac >/dev/null
cd ..

echo
echo "Done: release/StoryAutogen-Mac.zip"
echo
read -n 1 -s -r -p "Press any key to close..."
