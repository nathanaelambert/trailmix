#!/usr/bin/env bash
set -euo pipefail

PYTHON_VERSION="3.11.7"
PROJECT_DIR="$(pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"

echo "Installing build dependencies..."
sudo apt update
sudo apt install -y build-essential curl git libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev libffi-dev liblzma-dev

# Install pyenv if missing
if [ ! -d "${HOME}/.pyenv" ]; then
  echo "Installing pyenv..."
  curl https://pyenv.run | bash
else
  echo "pyenv already installed."
fi

# Ensure pyenv is available in this script
export PATH="${HOME}/.pyenv/bin:${PATH}"
eval "$(pyenv init -)"

echo "Installing Python ${PYTHON_VERSION} via pyenv..."
pyenv install -s "${PYTHON_VERSION}"
pyenv local "${PYTHON_VERSION}"

echo "Creating venv at ${VENV_DIR}..."
rm -rf "${VENV_DIR}"
python -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing project dependencies (pinned, CPU torch)..."
pip install "dash>=2.15,<3" "dash-bootstrap-components>=1.5,<2" "gunicorn>=21,<22" \
            "openai>=1.35,<2" "python-dotenv>=1,<2" \
            "numpy>=1.24,<2" "transformers>=4.39,<4.42" \
            torch==2.2.2 --extra-index-url https://download.pytorch.org/whl/cpu

echo "Done. Activate with: source ${VENV_DIR}/bin/activate"
echo "If pyenv isn’t found in new shells, add to ~/.bashrc:"
echo 'export PATH="$HOME/.pyenv/bin:$PATH"'
echo 'eval "$(pyenv init -)"'
