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

echo "Creating Mac release..."
RELEASE_TIMESTAMP="$(date +%Y-%m-%d-%H%M%S)"
RELEASE_SUFFIX=""
RELEASE_NAME="StoryAutogen-Mac-${RELEASE_TIMESTAMP}${RELEASE_SUFFIX}"
RELEASE_DIR="release/${RELEASE_NAME}"
while [ -e "$RELEASE_DIR" ] || [ -e "${RELEASE_DIR}.zip" ]; do
  if [ -z "$RELEASE_SUFFIX" ]; then
    RELEASE_SUFFIX="-2"
  else
    RELEASE_SUFFIX="-$((10#${RELEASE_SUFFIX#-} + 1))"
  fi
  RELEASE_NAME="StoryAutogen-Mac-${RELEASE_TIMESTAMP}${RELEASE_SUFFIX}"
  RELEASE_DIR="release/${RELEASE_NAME}"
done
mkdir -p "$RELEASE_DIR/frontend"

cp -R app config "$RELEASE_DIR/"
cp README.md prompts.txt pyproject.toml "$RELEASE_DIR/"
cp packaging/mac/README_MAC.txt packaging/mac/install_mac.command packaging/mac/run_mac.command packaging/app_launcher.py "$RELEASE_DIR/"
cp -R frontend/dist "$RELEASE_DIR/frontend/"

find "$RELEASE_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$RELEASE_DIR" -type f -name "*.pyc" -delete
find "$RELEASE_DIR" -type f -name ".DS_Store" -delete

chmod +x "$RELEASE_DIR/install_mac.command"
chmod +x "$RELEASE_DIR/run_mac.command"

cd release
zip -r "${RELEASE_NAME}.zip" "$RELEASE_NAME" >/dev/null
cd ..

echo
echo "Done: ${RELEASE_DIR}.zip"
echo
read -n 1 -s -r -p "Press any key to close..."
