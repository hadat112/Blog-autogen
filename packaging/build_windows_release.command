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
CURRENT_VERSION="$(sed -n 's/^version = "\([^"]*\)"/\1/p' pyproject.toml | head -n 1)"
IFS=. read -r VERSION_MAJOR VERSION_MINOR VERSION_PATCH <<< "$CURRENT_VERSION"
if [ -z "$CURRENT_VERSION" ] || ! [[ "$VERSION_MAJOR" =~ ^[0-9]+$ && "$VERSION_MINOR" =~ ^[0-9]+$ && "$VERSION_PATCH" =~ ^[0-9]+$ ]]; then
  echo "ERROR: Could not read a semantic version from pyproject.toml."
  exit 1
fi
NEXT_VERSION="${VERSION_MAJOR}.${VERSION_MINOR}.$((VERSION_PATCH + 1))"
RELEASE_NAME="StoryAutogen-Windows-v${CURRENT_VERSION}"
RELEASE_DIR="release/${RELEASE_NAME}"
if [ -e "$RELEASE_DIR" ] || [ -e "${RELEASE_DIR}.zip" ]; then
  echo "ERROR: Release ${RELEASE_NAME} already exists."
  echo "Remove the existing release or update the version before building again."
  exit 1
fi
mkdir -p "$RELEASE_DIR/frontend"

cp -R app config "$RELEASE_DIR/"
cp README.md prompts.txt pyproject.toml "$RELEASE_DIR/"
cp packaging/windows/README_WINDOWS.txt packaging/windows/install_windows.bat packaging/windows/run.bat packaging/app_launcher.py "$RELEASE_DIR/"
cp -R frontend/dist "$RELEASE_DIR/frontend/"

find "$RELEASE_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$RELEASE_DIR" -type f -name "*.pyc" -delete
find "$RELEASE_DIR" -type f -name ".DS_Store" -delete

cd release
zip -r "${RELEASE_NAME}.zip" "$RELEASE_NAME" >/dev/null
cd ..

sed -i '' "s/^version = \"${CURRENT_VERSION}\"/version = \"${NEXT_VERSION}\"/" pyproject.toml
sed -i '' "s/^version = \"${CURRENT_VERSION}\"/version = \"${NEXT_VERSION}\"/" uv.lock
sed -i '' "s/^  \"version\": \"${CURRENT_VERSION}\"/  \"version\": \"${NEXT_VERSION}\"/" frontend/package.json

echo
echo "Done: ${RELEASE_DIR}.zip"
echo "Version bumped: ${CURRENT_VERSION} -> ${NEXT_VERSION}"
echo
read -n 1 -s -r -p "Press any key to close..."
