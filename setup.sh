#!/bin/bash

echo "=== Blog-autogen Setup for Unix-like Systems ==="

# 1. Check and Install Python if missing
if ! command -v python3 &> /dev/null
then
    echo "Python3 not found. Attempting to install..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y python3 python3-venv python3-pip
        else
            echo "Please install python3, python3-venv, and python3-pip manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install python
        else
            echo "Homebrew not found. Please install Homebrew first or download Python from python.org"
            exit 1
        fi
    else
        echo "OS not supported for auto-install. Please install Python3 manually."
        exit 1
    fi
fi

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment (venv)..."
    python3 -m venv venv || { echo "Error creating venv. You might need to install python3-venv"; exit 1; }
fi

# 3. Activate and Install
echo "Installing dependencies and tool..."
source venv/bin/activate
pip install --upgrade pip
pip install -e .

# 4. Create a global runner script (optional but convenient)
echo "Creating global runner..."
cat <<EOF > blog-autogen-runner
#!/bin/bash
source $(pwd)/venv/bin/activate
blog-autogen "\$@"
EOF
chmod +x blog-autogen-runner

echo ""
echo "=== Setup Complete! ==="
echo "You can now run the tool using:"
echo "./blog-autogen-runner"
echo ""
echo "To run it from ANYWHERE using just 'blog-autogen', run this ONCE (requires sudo):"
echo "sudo ln -sf $(pwd)/blog-autogen-runner /usr/local/bin/blog-autogen"
